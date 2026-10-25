"""
Temporary File Analyzer for FileGuard.
Identifies potential temporary-file candidates using transparent, configurable rules,
such as extensions (.tmp, .bak, .old), patterns (~*), and age.
"""
import fnmatch
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from fileguard.config import TEMP_EXTENSIONS, TEMP_PATTERNS
from fileguard.models import FileRecord, format_bytes
from fileguard.database import Database
from fileguard.exclusion_manager import ExclusionManager


class TemporaryFileAnalyzer:
    def __init__(self, db: Optional[Database] = None, exclusion_manager: Optional[ExclusionManager] = None):
        self.db = db or Database()
        self.exclusions = exclusion_manager or ExclusionManager(self.db)

    def find_temporary_candidates(
        self,
        scan_id: Optional[int] = None,
        min_age_days: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Scan indexed files in the database for temporary file candidates.
        """
        if scan_id is not None:
            files = self.db.get_files_by_scan(scan_id)
        else:
            latest = self.db.get_latest_scan()
            files = self.db.get_files_by_scan(latest.id) if latest else []

        candidates = []
        now = time.time()
        age_threshold_seconds = min_age_days * 86400

        for f in files:
            ext = f.extension.lower()
            fname = f.filename.lower()

            matched_rules = []

            # Rule 1: Known temporary extension
            if ext in TEMP_EXTENSIONS:
                matched_rules.append(f"Temporary extension '{ext}'")

            # Rule 2: Recognized temporary pattern
            for pat in TEMP_PATTERNS:
                if fnmatch.fnmatch(fname, pat):
                    matched_rules.append(f"Matches temp pattern '{pat}'")
                    break

            if not matched_rules:
                continue

            # Check age rule
            age_days = 0.0
            if f.modified_time:
                file_age = now - f.modified_time
                if file_age < age_threshold_seconds:
                    continue
                age_days = round(file_age / 86400.0, 1)

            # Protected check
            is_prot, prot_reason = self.exclusions.is_protected_cleanup_path(f.path)

            candidates.append({
                "file_id": f.id,
                "filename": f.filename,
                "path": f.path,
                "size_bytes": f.size_bytes,
                "formatted_size": f.formatted_size,
                "age_days": age_days,
                "rules": "; ".join(matched_rules),
                "is_protected": is_prot,
                "protection_warning": prot_reason
            })

        return candidates
