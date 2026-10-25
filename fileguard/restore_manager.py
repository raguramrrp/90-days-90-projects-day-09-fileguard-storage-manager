"""
Restore Manager for FileGuard.
Handles single-file and bulk restoration, undo of the last quarantine operation,
destination conflict prevention, and integrity verification.
"""
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from fileguard.models import QuarantineItem, CleanupOperation
from fileguard.database import Database
from fileguard.hash_engine import compute_sha256


class RestoreError(Exception):
    """Raised when restoration encounters an unrecoverable failure."""
    pass


class RestoreManager:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    def restore_item(
        self,
        item_id: int,
        target_directory: Optional[str] = None,
        overwrite: bool = False
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Restore a quarantined item back to its original path or an alternate directory.
        Returns: (success, restored_path, error_message)
        """
        item = self.db.get_quarantine_item(item_id)
        if not item:
            return False, None, "Quarantine record not found in database."

        if item.status != "quarantined":
            return False, None, f"Item is already '{item.status}'."

        if not os.path.exists(item.quarantine_path):
            return False, None, f"Quarantined file missing from disk: {item.quarantine_path}"

        # Determine destination path
        if target_directory:
            dest_dir = os.path.abspath(target_directory)
            dest_path = os.path.join(dest_dir, item.filename)
        else:
            dest_path = item.original_path
            dest_dir = os.path.dirname(dest_path)

        # Destination collision check
        if os.path.exists(dest_path) and not overwrite:
            # Generate collision-safe restored filename
            p = Path(dest_path)
            dest_path = str(p.parent / f"{p.stem}_restored{p.suffix}")
            if os.path.exists(dest_path):
                dest_path = str(p.parent / f"{p.stem}_restored_{uuid.uuid4().hex[:6]}{p.suffix}")

        try:
            os.makedirs(dest_dir, exist_ok=True)

            # Copy quarantined file to destination
            shutil.copy2(item.quarantine_path, dest_path)

            # Verify restored file hash
            restored_hash, _ = compute_sha256(dest_path)
            if item.sha256_hash and restored_hash.lower() != item.sha256_hash.lower():
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                return False, None, "Hash mismatch: Restored file does not match original quarantined hash."

            # Remove from quarantine directory
            os.remove(item.quarantine_path)

            # Mark restored in database
            self.db.mark_quarantine_item_restored(item.id, dest_path)

            # Log audit event
            self.db.log_audit_event("restore", {
                "item_id": item.id,
                "original_path": item.original_path,
                "restored_path": dest_path,
                "filename": item.filename,
                "size_bytes": item.size_bytes
            })

            return True, dest_path, None

        except Exception as e:
            # Preserve quarantined copy if error
            return False, None, f"Failed to restore file: {e}"

    def undo_last_quarantine(self) -> Tuple[bool, int, List[str]]:
        """
        Undo the most recent quarantine operation by restoring all of its items.
        Returns: (success, restored_count, error_messages)
        """
        last_op = self.db.get_latest_quarantine_operation()
        if not last_op:
            return False, 0, ["No eligible quarantine operations found to undo."]

        items = self.db.get_quarantine_items_by_operation(last_op.id)
        quarantined_items = [i for i in items if i.status == "quarantined"]

        if not quarantined_items:
            return False, 0, ["All items in the last quarantine operation have already been restored or deleted."]

        restored_count = 0
        errors = []

        for item in quarantined_items:
            success, path, err = self.restore_item(item.id)
            if success:
                restored_count += 1
            else:
                errors.append(f"{item.filename}: {err}")

        # Update operation record
        undo_status = "undone" if not errors else "partial_undo"
        self.db.complete_cleanup_operation(last_op.id, undo_status, "; ".join(errors) if errors else None)

        self.db.log_audit_event("undo_quarantine", {
            "operation_id": last_op.id,
            "operation_uuid": last_op.operation_uuid,
            "items_restored": restored_count,
            "total_items": len(quarantined_items),
            "errors": errors
        })

        return (restored_count > 0), restored_count, errors
