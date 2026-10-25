"""
Exclusion Manager for FileGuard.
Evaluates rules (directories, extensions, size thresholds, patterns) and system protections
to determine if files or folders should be skipped during scanning or blocked during cleanup.
"""
import fnmatch
import os
import re
from pathlib import Path
from typing import List, Tuple, Optional

from fileguard.config import (
    DEFAULT_EXCLUDED_DIRS, DEFAULT_EXCLUDED_EXTS,
    is_path_protected
)
from fileguard.models import ExclusionRule
from fileguard.database import Database


class ExclusionManager:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.refresh_rules()

    def refresh_rules(self):
        """Load user-defined rules from database and combine with defaults."""
        self.db_rules: List[ExclusionRule] = self.db.get_exclusions()
        self.custom_excluded_dirs = set()
        self.custom_excluded_exts = set()
        self.custom_patterns = []
        self.min_size_bytes = 0
        self.max_size_bytes = None

        for rule in self.db_rules:
            if not rule.is_enabled:
                continue
            if rule.rule_type == "directory":
                self.custom_excluded_dirs.add(rule.rule_value.lower())
            elif rule.rule_type == "extension":
                ext = rule.rule_value.lower()
                if not ext.startswith("."):
                    ext = "." + ext
                self.custom_excluded_exts.add(ext)
            elif rule.rule_type == "pattern":
                self.custom_patterns.append(rule.rule_value)
            elif rule.rule_type == "min_size":
                try:
                    self.min_size_bytes = max(self.min_size_bytes, int(rule.rule_value))
                except ValueError:
                    pass
            elif rule.rule_type == "max_size":
                try:
                    self.max_size_bytes = int(rule.rule_value)
                except ValueError:
                    pass

    def is_directory_excluded(self, dir_path: str) -> Tuple[bool, Optional[str]]:
        """Check if a directory matches exclusion rules."""
        norm_path = os.path.abspath(dir_path).lower()
        dir_name = Path(norm_path).name.lower()

        # Check default excluded directories
        if dir_name in {d.lower() for d in DEFAULT_EXCLUDED_DIRS}:
            return True, f"Default excluded folder name: {dir_name}"

        # Check custom excluded directories
        for excluded in self.custom_excluded_dirs:
            if excluded in norm_path or fnmatch.fnmatch(norm_path, excluded) or fnmatch.fnmatch(dir_name, excluded):
                return True, f"User excluded directory rule: {excluded}"

        return False, None

    def should_exclude_file(self, file_path: str, size_bytes: int, scan_root: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Evaluate if a file should be skipped during scanning.
        Returns: (is_excluded, reason_string)
        """
        norm_path = os.path.abspath(file_path).lower()
        file_name = Path(norm_path).name.lower()
        ext = Path(norm_path).suffix.lower()

        # Check parent folder exclusions (within scan_root if provided, else immediate parent)
        if scan_root:
            try:
                rel = Path(norm_path).relative_to(os.path.abspath(scan_root).lower())
                parts_to_check = [p.lower() for p in rel.parts[:-1]]
            except ValueError:
                parts_to_check = [Path(norm_path).parent.name.lower()]
        else:
            parts_to_check = [p.lower() for p in Path(norm_path).parts[:-1]]

        for part in parts_to_check:
            if part in {d.lower() for d in DEFAULT_EXCLUDED_DIRS}:
                return True, f"Parent folder '{part}' is excluded by default"
            if part in self.custom_excluded_dirs:
                return True, f"Parent folder '{part}' is excluded by custom rule"

        # Check extension exclusions
        if ext in {e.lower() for e in DEFAULT_EXCLUDED_EXTS}:
            return True, f"Default excluded extension: {ext}"
        if ext in self.custom_excluded_exts:
            return True, f"Custom excluded extension: {ext}"

        # Check size rules
        if self.min_size_bytes > 0 and size_bytes < self.min_size_bytes:
            return True, f"File size ({size_bytes} B) is below minimum threshold ({self.min_size_bytes} B)"
        if self.max_size_bytes is not None and size_bytes > self.max_size_bytes:
            return True, f"File size ({size_bytes} B) exceeds maximum threshold ({self.max_size_bytes} B)"

        # Check patterns
        for pattern in self.custom_patterns:
            if fnmatch.fnmatch(file_name, pattern.lower()) or fnmatch.fnmatch(norm_path, pattern.lower()):
                return True, f"Matches exclusion pattern: {pattern}"

        return False, None

    def is_protected_cleanup_path(self, path: str) -> Tuple[bool, Optional[str]]:
        """
        Strict check for cleanup operations: protects Windows OS and critical system folders.
        Even if scanned, cleanup of protected locations is rejected.
        """
        if is_path_protected(path):
            return True, "Path is within a protected Windows system or application location"
        return False, None
