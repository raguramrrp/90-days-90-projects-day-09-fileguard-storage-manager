"""
History Manager for FileGuard.
Manages scan history, historical scan comparison, and change tracking across scopes.
"""
import json
from typing import List, Dict, Any, Optional, Tuple

from fileguard.models import ScanRecord, DuplicateGroup, format_bytes
from fileguard.database import Database


class HistoryManager:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    def get_all_scans(self) -> List[ScanRecord]:
        return self.db.get_all_scans()

    def get_scan_details(self, scan_id: int) -> Optional[Dict[str, Any]]:
        scan = self.db.get_scan(scan_id)
        if not scan:
            return None

        groups = self.db.get_duplicate_groups(scan_id)
        return {
            "scan": scan,
            "duplicate_groups": groups,
            "duplicate_groups_count": len(groups),
            "duplicate_files_count": sum(g.file_count for g in groups),
            "potential_recoverable_bytes": sum(g.max_recoverable_bytes for g in groups)
        }

    def compare_scans(self, scan_id_a: int, scan_id_b: int) -> Dict[str, Any]:
        """
        Compare two completed scans.
        Checks scan scope comparability and identifies new and resolved duplicate groups.
        """
        scan_a = self.db.get_scan(scan_id_a)
        scan_b = self.db.get_scan(scan_id_b)

        if not scan_a or not scan_b:
            raise ValueError("One or both scans could not be found.")

        # Check scope compatibility
        roots_a = sorted(scan_a.root_paths)
        roots_b = sorted(scan_b.root_paths)
        scopes_identical = (roots_a == roots_b)

        groups_a = self.db.get_duplicate_groups(scan_id_a)
        groups_b = self.db.get_duplicate_groups(scan_id_b)

        hashes_a = {g.sha256_hash: g for g in groups_a}
        hashes_b = {g.sha256_hash: g for g in groups_b}

        new_duplicate_hashes = set(hashes_b.keys()) - set(hashes_a.keys())
        resolved_duplicate_hashes = set(hashes_a.keys()) - set(hashes_b.keys())
        persisting_duplicate_hashes = set(hashes_a.keys()) & set(hashes_b.keys())

        # Calculate metrics deltas (B - A)
        delta_files = scan_b.files_processed - scan_a.files_processed
        delta_bytes = scan_b.total_indexed_bytes - scan_a.total_indexed_bytes
        delta_duplicate_groups = len(groups_b) - len(groups_a)
        delta_recoverable_bytes = scan_b.potential_recoverable_bytes - scan_a.potential_recoverable_bytes

        return {
            "scan_a": scan_a,
            "scan_b": scan_b,
            "scopes_identical": scopes_identical,
            "scope_warning": None if scopes_identical else (
                "Notice: Scans have different root folders. Metric comparisons reflect scope differences rather than pure filesystem changes."
            ),
            "delta_files": delta_files,
            "delta_bytes": delta_bytes,
            "formatted_delta_bytes": format_bytes(abs(delta_bytes)),
            "delta_duplicate_groups": delta_duplicate_groups,
            "delta_recoverable_bytes": delta_recoverable_bytes,
            "formatted_delta_recoverable": format_bytes(abs(delta_recoverable_bytes)),
            "new_duplicate_groups_count": len(new_duplicate_hashes),
            "resolved_duplicate_groups_count": len(resolved_duplicate_hashes),
            "persisting_duplicate_groups_count": len(persisting_duplicate_hashes),
            "new_groups": [hashes_b[h] for h in list(new_duplicate_hashes)[:20]],
            "resolved_groups": [hashes_a[h] for h in list(resolved_duplicate_hashes)[:20]]
        }
