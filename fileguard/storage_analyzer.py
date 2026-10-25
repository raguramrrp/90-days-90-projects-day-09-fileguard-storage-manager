"""
Storage Analyzer for FileGuard.
Provides storage intelligence: nested folder aggregation without double-counting,
file-type breakdown, largest folders/files, drive space metrics, and recoverable estimates.
"""
import os
import shutil
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any, Optional

from fileguard.models import FileRecord, format_bytes
from fileguard.database import Database


class StorageAnalyzer:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    def analyze_scan_storage(self, scan_id: int) -> Dict[str, Any]:
        """
        Analyze storage usage for a completed or historical scan.
        """
        files = self.db.get_files_by_scan(scan_id)
        scan = self.db.get_scan(scan_id)

        if not files:
            return self._empty_analysis()

        total_bytes = sum(f.size_bytes for f in files)
        total_files = len(files)

        # 1. Category Distribution
        cat_bytes: Dict[str, int] = defaultdict(int)
        cat_counts: Dict[str, int] = defaultdict(int)
        ext_bytes: Dict[str, int] = defaultdict(int)

        for f in files:
            cat_bytes[f.category] += f.size_bytes
            cat_counts[f.category] += 1
            ext = f.extension.lower() or "none"
            ext_bytes[ext] += f.size_bytes

        categories = []
        for cat, b in sorted(cat_bytes.items(), key=lambda x: x[1], reverse=True):
            pct = (b / total_bytes * 100.0) if total_bytes > 0 else 0.0
            categories.append({
                "category": cat,
                "bytes": b,
                "formatted_bytes": format_bytes(b),
                "count": cat_counts[cat],
                "percentage": round(pct, 1)
            })

        top_extensions = [
            {"extension": ext, "bytes": b, "formatted_bytes": format_bytes(b)}
            for ext, b in sorted(ext_bytes.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        # 2. Folder Size Analysis (Accurate direct + nested calculation)
        direct_folder_sizes: Dict[str, int] = defaultdict(int)
        direct_folder_counts: Dict[str, int] = defaultdict(int)

        for f in files:
            parent = os.path.dirname(f.path)
            direct_folder_sizes[parent] += f.size_bytes
            direct_folder_counts[parent] += 1

        # Deep folder sizes (including subfolders, calculated hierarchically)
        deep_folder_sizes: Dict[str, int] = defaultdict(int)
        for f in files:
            p = Path(f.path).parent
            # Attribute size up the directory tree
            while True:
                deep_folder_sizes[str(p)] += f.size_bytes
                if p.parent == p:
                    break
                p = p.parent

        largest_direct_folders = [
            {"path": folder, "bytes": b, "formatted_bytes": format_bytes(b), "file_count": direct_folder_counts[folder]}
            for folder, b in sorted(direct_folder_sizes.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        # 3. Largest Files
        sorted_files = sorted(files, key=lambda f: f.size_bytes, reverse=True)
        largest_files = [
            {
                "id": f.id,
                "filename": f.filename,
                "path": f.path,
                "bytes": f.size_bytes,
                "formatted_bytes": f.formatted_size,
                "category": f.category,
                "modified": f.formatted_modified
            }
            for f in sorted_files[:15]
        ]

        # 4. Drive Space Info (for the scan root drives)
        drive_stats = []
        if scan and scan.root_paths:
            seen_roots = set()
            for r in scan.root_paths:
                try:
                    drive_root = os.path.splitdrive(os.path.abspath(r))[0] + "\\"
                    if drive_root not in seen_roots and os.path.exists(drive_root):
                        seen_roots.add(drive_root)
                        usage = shutil.disk_usage(drive_root)
                        drive_stats.append({
                            "drive": drive_root,
                            "total_bytes": usage.total,
                            "used_bytes": usage.used,
                            "free_bytes": usage.free,
                            "formatted_total": format_bytes(usage.total),
                            "formatted_used": format_bytes(usage.used),
                            "formatted_free": format_bytes(usage.free),
                            "free_percent": round((usage.free / usage.total) * 100.0, 1)
                        })
                except Exception:
                    pass

        return {
            "has_data": True,
            "scan_id": scan_id,
            "total_files": total_files,
            "total_bytes": total_bytes,
            "formatted_total_bytes": format_bytes(total_bytes),
            "categories": categories,
            "top_extensions": top_extensions,
            "largest_direct_folders": largest_direct_folders,
            "largest_files": largest_files,
            "drive_stats": drive_stats
        }

    def _empty_analysis(self) -> Dict[str, Any]:
        return {
            "has_data": False,
            "scan_id": None,
            "total_files": 0,
            "total_bytes": 0,
            "formatted_total_bytes": "0 B",
            "categories": [],
            "top_extensions": [],
            "largest_direct_folders": [],
            "largest_files": [],
            "drive_stats": []
        }
