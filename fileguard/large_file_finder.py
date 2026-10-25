"""
Large File Finder for FileGuard.
Identifies storage-heavy files based on configurable thresholds, provides metadata filtering,
and supports safe Windows Explorer integration.
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

from fileguard.models import FileRecord
from fileguard.database import Database
from fileguard.config import LARGE_FILE_THRESHOLD_BYTES


class LargeFileFinder:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    def find_large_files(
        self,
        min_size_bytes: int = LARGE_FILE_THRESHOLD_BYTES,
        scan_id: Optional[int] = None,
        category: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[FileRecord]:
        """Query database for files exceeding threshold with optional filters."""
        candidates = self.db.get_large_files(min_size_bytes, scan_id)

        filtered = []
        q = search_query.lower() if search_query else None
        cat = category.lower() if category and category != "All" else None

        for f in candidates:
            if cat and f.category.lower() != cat:
                continue
            if q and (q not in f.filename.lower() and q not in f.path.lower()):
                continue
            filtered.append(f)

        return filtered

    @staticmethod
    def open_containing_folder(file_path: str) -> bool:
        """Safely open Windows File Explorer with the target file highlighted."""
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            return False

        try:
            if sys.platform.startswith("win"):
                # Use explorer.exe /select,"path" to reveal file
                subprocess.Popen(["explorer.exe", f"/select,{abs_path}"])
                return True
            else:
                # Fallback for other platforms
                subprocess.Popen(["xdg-open", os.path.dirname(abs_path)])
                return True
        except Exception:
            return False
