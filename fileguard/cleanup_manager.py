"""
Cleanup Manager for FileGuard.
Prepares and validates cleanup previews, enforces retained-copy protection,
verifies target files on disk, and delegates execution to QuarantineManager.
"""
import os
import uuid
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

from fileguard.models import FileRecord, DuplicateGroup, format_bytes
from fileguard.database import Database
from fileguard.exclusion_manager import ExclusionManager
from fileguard.hash_engine import compute_sha256, FileInaccessibleError


class CleanupValidationError(Exception):
    """Raised when safety validation fails for a proposed cleanup."""
    pass


class CleanupManager:
    def __init__(self, db: Optional[Database] = None, exclusion_manager: Optional[ExclusionManager] = None):
        self.db = db or Database()
        self.exclusions = exclusion_manager or ExclusionManager(self.db)

    def prepare_cleanup_preview(
        self,
        selected_file_ids: List[int],
        groups: List[DuplicateGroup]
    ) -> Dict[str, Any]:
        """
        Build an exhaustive, non-destructive preview of the proposed cleanup.
        Validates:
        1. Retained copy protection (blocks if all copies in a group are selected)
        2. Protected location check (blocks system files)
        3. Disk availability
        """
        selected_set = set(selected_file_ids)
        file_map: Dict[int, FileRecord] = {}
        for g in groups:
            for m in g.members:
                file_map[m.id] = m

        items_to_clean: List[Dict[str, Any]] = []
        blocked_items: List[Dict[str, Any]] = []
        total_proposed_bytes = 0
        groups_affected = set()

        # Check each duplicate group for retained-copy violation
        for g in groups:
            group_selected_members = [m for m in g.members if m.id in selected_set]
            if not group_selected_members:
                continue

            groups_affected.add(g.id)
            all_selected = (len(group_selected_members) == len(g.members))

            if all_selected:
                # VIOLATION: All copies selected! Block all of them
                for m in group_selected_members:
                    blocked_items.append({
                        "file_id": m.id,
                        "path": m.path,
                        "filename": m.filename,
                        "size_bytes": m.size_bytes,
                        "formatted_size": m.formatted_size,
                        "reason": "CRITICAL: All copies in duplicate group are selected. At least one verified copy must remain outside quarantine."
                    })
                continue

            # Check individual members in this valid group
            for m in group_selected_members:
                # Protected location check
                is_prot, prot_reason = self.exclusions.is_protected_cleanup_path(m.path)
                if is_prot:
                    blocked_items.append({
                        "file_id": m.id,
                        "path": m.path,
                        "filename": m.filename,
                        "size_bytes": m.size_bytes,
                        "formatted_size": m.formatted_size,
                        "reason": f"Protected Location: {prot_reason}"
                    })
                    continue

                # Check existence on disk
                if not os.path.exists(m.path):
                    blocked_items.append({
                        "file_id": m.id,
                        "path": m.path,
                        "filename": m.filename,
                        "size_bytes": m.size_bytes,
                        "formatted_size": m.formatted_size,
                        "reason": "File is missing on disk."
                    })
                    continue

                # Identify the retained copy for this file
                retained_copies = [other.path for other in g.members if other.id not in selected_set]

                items_to_clean.append({
                    "file_id": m.id,
                    "path": m.path,
                    "filename": m.filename,
                    "size_bytes": m.size_bytes,
                    "formatted_size": m.formatted_size,
                    "sha256_hash": m.sha256_hash,
                    "group_id": g.id,
                    "retained_copy": retained_copies[0] if retained_copies else "Unknown"
                })
                total_proposed_bytes += m.size_bytes

        return {
            "can_proceed": len(items_to_clean) > 0,
            "items_to_clean": items_to_clean,
            "blocked_items": blocked_items,
            "total_items_count": len(items_to_clean),
            "total_bytes": total_proposed_bytes,
            "formatted_total_bytes": format_bytes(total_proposed_bytes),
            "groups_affected_count": len(groups_affected)
        }
