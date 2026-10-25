"""
Integrity Checker for FileGuard.
Verifies file integrity by recalculating SHA-256 fingerprints and comparing them
against stored baseline fingerprints in the database.
"""
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

from fileguard.models import FileRecord, IntegrityResult
from fileguard.database import Database
from fileguard.hash_engine import compute_sha256, FileInaccessibleError, FileModifiedDuringHashError


class IntegrityChecker:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    def check_files(
        self,
        files: List[FileRecord],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[IntegrityResult]:
        """
        Verify integrity of provided files against their recorded hashes.
        """
        results: List[IntegrityResult] = []
        check_uuid = str(uuid.uuid4())
        total = len(files)

        for idx, f in enumerate(files):
            if progress_callback:
                progress_callback(idx + 1, total, f.filename)

            if not f.sha256_hash:
                continue

            status = "unchanged"
            observed_hash = None

            if not os.path.exists(f.path):
                status = "missing"
            else:
                try:
                    observed_hash, _ = compute_sha256(f.path)
                    if observed_hash.lower() == f.sha256_hash.lower():
                        status = "unchanged"
                    else:
                        status = "modified"
                except (PermissionError, FileInaccessibleError):
                    status = "inaccessible"
                except Exception:
                    status = "error"

            res = IntegrityResult(
                check_uuid=check_uuid,
                file_id=f.id,
                file_path=f.path,
                reference_hash=f.sha256_hash,
                observed_hash=observed_hash,
                status=status,
                verified_at=datetime.now().isoformat()
            )
            self.db.log_integrity_check(res)
            results.append(res)

        return results
