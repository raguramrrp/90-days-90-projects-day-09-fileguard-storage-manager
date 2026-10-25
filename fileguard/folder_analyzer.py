"""
Folder Analyzer for FileGuard.
Identifies genuinely empty directory trees and distinguishes them from inaccessible locations.
"""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from fileguard.config import is_path_protected
from fileguard.exclusion_manager import ExclusionManager
from fileguard.database import Database


class FolderAnalyzer:
    def __init__(self, db: Optional[Database] = None, exclusion_manager: Optional[ExclusionManager] = None):
        self.db = db or Database()
        self.exclusions = exclusion_manager or ExclusionManager(self.db)

    def find_empty_folders(self, root_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Traverse directory trees bottom-up to identify genuinely empty folders.
        Returns list of dicts: {'path', 'is_protected', 'is_inaccessible', 'reason'}
        """
        empty_folders: List[Dict[str, Any]] = []

        for root in root_paths:
            abs_root = os.path.abspath(root)
            if not os.path.exists(abs_root):
                continue

            # Bottom-up walk so subdirectories are evaluated before parent directories
            for dirpath, dirnames, filenames in os.walk(abs_root, topdown=False, followlinks=False):
                # Never evaluate the root scan folder itself as empty to delete
                if os.path.abspath(dirpath) == abs_root:
                    continue

                # Exclusions check
                excluded, reason = self.exclusions.is_directory_excluded(dirpath)
                if excluded:
                    continue

                # Protected location check
                is_prot, prot_reason = self.exclusions.is_protected_cleanup_path(dirpath)

                try:
                    # Check current contents
                    entries = os.listdir(dirpath)
                    if not entries:
                        empty_folders.append({
                            "path": dirpath,
                            "folder_name": Path(dirpath).name,
                            "is_protected": is_prot,
                            "is_inaccessible": False,
                            "status": "Protected" if is_prot else "Genuinely Empty",
                            "reason": prot_reason if is_prot else "Zero files and zero subdirectories"
                        })
                except PermissionError:
                    empty_folders.append({
                        "path": dirpath,
                        "folder_name": Path(dirpath).name,
                        "is_protected": True,
                        "is_inaccessible": True,
                        "status": "Inaccessible",
                        "reason": "Permission denied while accessing directory"
                    })
                except OSError as e:
                    pass

        return empty_folders

    def safely_remove_empty_folder(self, folder_path: str) -> bool:
        """Safely remove an empty directory if confirmed empty and not protected."""
        abs_path = os.path.abspath(folder_path)
        is_prot, _ = self.exclusions.is_protected_cleanup_path(abs_path)
        if is_prot:
            return False

        try:
            os.rmdir(abs_path)
            return True
        except OSError:
            return False
