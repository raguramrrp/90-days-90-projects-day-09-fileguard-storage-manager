"""
Filesystem Scanner for FileGuard.
Handles multi-root traversal, exclusion filtering, safe cancellation,
error tracking, symbolic link safety, and integration with the duplicate detector.
"""
import os
import sys
import time
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any

from fileguard.config import categorize_file
from fileguard.hash_engine import normalize_windows_path
from fileguard.models import FileRecord, ScanRecord, DuplicateGroup
from fileguard.database import Database
from fileguard.exclusion_manager import ExclusionManager
from fileguard.duplicate_detector import DuplicateDetector


class Scanner:
    def __init__(
        self,
        db: Optional[Database] = None,
        exclusion_manager: Optional[ExclusionManager] = None,
        duplicate_detector: Optional[DuplicateDetector] = None
    ):
        self.db = db or Database()
        self.exclusions = exclusion_manager or ExclusionManager(self.db)
        self.detector = duplicate_detector or DuplicateDetector()
        self._cancelled = False

    def cancel(self):
        """Signal the running scan to stop safely."""
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled

    def reset_cancellation(self):
        """Reset the cancellation flag before a new scan."""
        self._cancelled = False

    def scan(
        self,
        root_paths: List[str],
        scan_name: str = "Manual Scan",
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> ScanRecord:
        """
        Execute an end-to-end scan over the specified root directories.
        """
        start_time = time.time()

        # Create Scan record in DB
        scan_id = self.db.create_scan(scan_name, root_paths)

        discovered_count = 0
        processed_count = 0
        skipped_count = 0
        failed_count = 0
        total_indexed_bytes = 0

        eligible_files: List[FileRecord] = []
        visited_inodes = set()  # Prevent symlink/junction infinite cycles

        def notify(stage: str, cur_path: str = "", pct: float = 0.0):
            if progress_callback:
                progress_callback({
                    "scan_id": scan_id,
                    "stage": stage,
                    "discovered": discovered_count,
                    "processed": processed_count,
                    "skipped": skipped_count,
                    "failed": failed_count,
                    "current_path": cur_path,
                    "progress_percent": pct,
                    "is_cancelled": self._cancelled
                })

        notify("Initializing scan scope...", "", 0.0)

        # STAGE 1: Discovery & Metadata Collection
        for root in root_paths:
            if self._cancelled:
                break

            abs_root = os.path.abspath(root)
            if not os.path.exists(abs_root):
                self.db.log_scan_error(scan_id, abs_root, "NotFound", "Root directory does not exist")
                failed_count += 1
                continue

            for dirpath, dirnames, filenames in os.walk(abs_root, topdown=True, followlinks=False):
                if self._cancelled:
                    break

                # Symlink / Reparse Point protection
                try:
                    st = os.stat(dirpath)
                    inode_key = (st.st_dev, st.st_ino) if hasattr(st, "st_ino") and st.st_ino else dirpath.lower()
                    if inode_key in visited_inodes:
                        dirnames.clear()
                        continue
                    visited_inodes.add(inode_key)
                except Exception:
                    pass

                # Filter directory names against exclusions in-place
                surviving_dirs = []
                for d in dirnames:
                    full_d = os.path.join(dirpath, d)
                    excluded, reason = self.exclusions.is_directory_excluded(full_d)
                    if excluded:
                        skipped_count += 1
                    else:
                        surviving_dirs.append(d)
                dirnames[:] = surviving_dirs

                # Process files in directory
                for fname in filenames:
                    if self._cancelled:
                        break

                    discovered_count += 1
                    full_path = os.path.join(dirpath, fname)
                    safe_path = normalize_windows_path(full_path)

                    try:
                        fstat = os.stat(safe_path)
                        fsize = fstat.st_size

                        # Exclusion check
                        excluded, reason = self.exclusions.should_exclude_file(full_path, fsize, scan_root=abs_root)
                        if excluded:
                            skipped_count += 1
                            continue

                        ext = Path(fname).suffix.lower()
                        cat = categorize_file(ext)

                        rec = FileRecord(
                            scan_id=scan_id,
                            path=full_path,
                            filename=fname,
                            size_bytes=fsize,
                            extension=ext,
                            category=cat,
                            created_time=fstat.st_ctime,
                            modified_time=fstat.st_mtime,
                            last_scanned_time=time.time(),
                            hash_status="pending",
                            is_available=True
                        )
                        eligible_files.append(rec)
                        processed_count += 1
                        total_indexed_bytes += fsize

                        if processed_count % 100 == 0:
                            notify("Discovering files...", full_path, 20.0)

                    except PermissionError:
                        failed_count += 1
                        self.db.log_scan_error(scan_id, full_path, "PermissionDenied", "Access is denied.")
                    except FileNotFoundError:
                        failed_count += 1
                    except OSError as e:
                        failed_count += 1
                        self.db.log_scan_error(scan_id, full_path, "OSError", str(e))

        # Check for cancellation after discovery
        if self._cancelled:
            self.db.update_scan_progress(scan_id, discovered_count, processed_count, 0, skipped_count, failed_count)
            self.db.complete_scan(scan_id, "cancelled", 0, 0, total_indexed_bytes, 0, "Scan cancelled by user.")
            notify("Scan cancelled.", "", 0.0)
            return self.db.get_scan(scan_id)

        notify("Saving indexed metadata...", "", 40.0)
        # Batch save files to database
        self.db.save_files_batch(eligible_files)

        # STAGE 2: Exact Duplicate Detection
        notify("Analyzing candidate duplicates...", "", 50.0)

        def detector_progress(msg: str, cur: int, tot: int):
            pct = 50.0 + (float(cur) / max(1, tot)) * 40.0
            notify(msg, "", pct)

        duplicate_groups = self.detector.detect_duplicates(
            eligible_files,
            progress_callback=detector_progress,
            cancel_check=self.is_cancelled
        )

        if self._cancelled:
            self.db.complete_scan(scan_id, "cancelled", 0, 0, total_indexed_bytes, 0, "Scan cancelled during hashing.")
            notify("Scan cancelled.", "", 0.0)
            return self.db.get_scan(scan_id)

        # STAGE 3: Persist Duplicate Groups
        notify("Finalizing duplicate records...", "", 95.0)
        self.db.save_duplicate_groups(scan_id, duplicate_groups)

        total_duplicate_files = sum(g.file_count for g in duplicate_groups)
        total_recoverable_bytes = sum(g.max_recoverable_bytes for g in duplicate_groups)

        hashed_files = sum(1 for f in eligible_files if f.hash_status == "verified")

        self.db.update_scan_progress(
            scan_id, discovered_count, processed_count, hashed_files, skipped_count, failed_count
        )
        self.db.complete_scan(
            scan_id,
            status="completed",
            duplicate_groups=len(duplicate_groups),
            duplicate_files=total_duplicate_files,
            total_bytes=total_indexed_bytes,
            recoverable_bytes=total_recoverable_bytes
        )

        # Log audit event
        self.db.log_audit_event("scan_finish", {
            "scan_id": scan_id,
            "scan_name": scan_name,
            "root_paths": root_paths,
            "files_processed": processed_count,
            "duplicate_groups": len(duplicate_groups),
            "recoverable_bytes": total_recoverable_bytes
        })

        notify("Scan complete.", "", 100.0)
        return self.db.get_scan(scan_id)
