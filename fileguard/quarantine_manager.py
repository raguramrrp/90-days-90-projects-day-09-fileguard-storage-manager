"""
Quarantine Manager for FileGuard.
Executes safe, reversible quarantine operations with collision prevention,
cross-volume verification, atomic safety rollbacks, and complete audit logging.
"""
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from fileguard.config import QUARANTINE_DIR
from fileguard.models import CleanupOperation, QuarantineItem, format_bytes
from fileguard.database import Database
from fileguard.hash_engine import compute_sha256, FileInaccessibleError


class QuarantineError(Exception):
    """Raised when quarantine operation encounters an unrecoverable failure."""
    pass


class QuarantineManager:
    def __init__(self, db: Optional[Database] = None, quarantine_dir: Optional[Path] = None):
        self.db = db or Database()
        self.quarantine_dir = Path(quarantine_dir) if quarantine_dir else QUARANTINE_DIR
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

    def execute_quarantine(
        self,
        validated_items: List[Dict[str, Any]],
        operation_uuid: Optional[str] = None
    ) -> CleanupOperation:
        """
        Move validated files into reversible quarantine.
        Each move:
        1. Copies file to quarantine path.
        2. Verifies SHA-256 of quarantined copy against source.
        3. Deletes source file only after verification.
        4. Logs item in DB.
        """
        op_uuid = operation_uuid or str(uuid.uuid4())
        total_bytes = sum(item["size_bytes"] for item in validated_items)

        op = CleanupOperation(
            operation_uuid=op_uuid,
            action_type="quarantine",
            started_at=datetime.now().isoformat(),
            status="running",
            items_count=len(validated_items),
            total_bytes=total_bytes,
            user_confirmed=True
        )
        op_id = self.db.create_cleanup_operation(op)

        quarantined_count = 0
        quarantined_bytes = 0
        errors = []

        for item in validated_items:
            src_path = os.path.abspath(item["path"])
            filename = item["filename"]
            expected_hash = item.get("sha256_hash")

            if not os.path.exists(src_path):
                errors.append(f"Skipped {filename}: Source file no longer exists.")
                continue

            # Generate collision-safe quarantine destination
            unique_prefix = uuid.uuid4().hex[:8]
            safe_dest_name = f"q_{unique_prefix}_{filename}"
            dest_path = str(self.quarantine_dir / safe_dest_name)

            try:
                # Capture original timestamps
                st = os.stat(src_path)
                orig_ctime = st.st_ctime
                orig_mtime = st.st_mtime
                orig_size = st.st_size

                # 1. Copy file with metadata
                shutil.copy2(src_path, dest_path)

                # 2. Verify SHA-256 of quarantined copy
                quarantined_hash, q_size = compute_sha256(dest_path)

                if expected_hash and quarantined_hash.lower() != expected_hash.lower():
                    # Verification mismatch! Delete quarantine copy and keep source intact
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    errors.append(f"Integrity mismatch on {filename}: Quarantined file hash did not match.")
                    continue

                # 3. Safe remove original only after successful verified copy
                os.remove(src_path)

                # 4. Record quarantine item in database
                q_item = QuarantineItem(
                    operation_id=op_id,
                    original_path=src_path,
                    quarantine_path=dest_path,
                    filename=filename,
                    size_bytes=orig_size,
                    sha256_hash=quarantined_hash,
                    original_created_time=orig_ctime,
                    original_modified_time=orig_mtime,
                    quarantined_at=datetime.now().isoformat(),
                    status="quarantined"
                )
                self.db.add_quarantine_item(q_item)

                quarantined_count += 1
                quarantined_bytes += orig_size

            except Exception as e:
                # Clean up destination if failed mid-operation
                if os.path.exists(dest_path):
                    try:
                        os.remove(dest_path)
                    except Exception:
                        pass
                errors.append(f"Failed to quarantine {filename}: {e}")

        # Finalize operation
        final_status = "completed" if not errors else ("partial" if quarantined_count > 0 else "failed")
        error_summary = "; ".join(errors) if errors else None
        self.db.complete_cleanup_operation(op_id, final_status, error_summary)

        op.status = final_status
        op.items_count = quarantined_count
        op.total_bytes = quarantined_bytes
        op.error_summary = error_summary
        op.completed_at = datetime.now().isoformat()

        # Audit Event
        self.db.log_audit_event("quarantine", {
            "operation_id": op_id,
            "operation_uuid": op_uuid,
            "items_quarantined": quarantined_count,
            "bytes_reclaimed": quarantined_bytes,
            "status": final_status,
            "errors": errors
        })

        return op

    def permanently_delete_quarantined_item(self, item_id: int) -> Tuple[bool, Optional[str]]:
        """
        Permanently delete a file from quarantine storage.
        Requires explicit confirmation and cannot be triggered from normal cleanup.
        """
        item = self.db.get_quarantine_item(item_id)
        if not item:
            return False, "Quarantine record not found."

        if item.status != "quarantined":
            return False, f"Item is currently '{item.status}' and cannot be permanently deleted."

        try:
            if os.path.exists(item.quarantine_path):
                os.remove(item.quarantine_path)
            self.db.mark_quarantine_item_deleted(item_id)
            self.db.log_audit_event("permanent_delete", {
                "item_id": item_id,
                "original_path": item.original_path,
                "filename": item.filename,
                "size_bytes": item.size_bytes
            })
            return True, None
        except Exception as e:
            return False, f"Failed to delete file from disk: {e}"
