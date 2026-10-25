"""
Tests for Cleanup, Quarantine, Restore, and Undo.
Verifies retained-copy protection, conflict prevention, atomic safety rollbacks, and audit trails.
"""
import os
from pathlib import Path
import pytest
from fileguard.models import FileRecord, DuplicateGroup
from fileguard.cleanup_manager import CleanupManager
from fileguard.quarantine_manager import QuarantineManager
from fileguard.restore_manager import RestoreManager


def test_retained_copy_protection_blocks_all_selected(test_db, temp_dir):
    """Safety Test: If user selects ALL copies in a group, operation is blocked."""
    f1 = temp_dir / "copy1.txt"
    f2 = temp_dir / "copy2.txt"
    content = b"IDENTICAL"
    f1.write_bytes(content)
    f2.write_bytes(content)

    rec1 = FileRecord(id=1, path=str(f1), filename="copy1.txt", size_bytes=len(content))
    rec2 = FileRecord(id=2, path=str(f2), filename="copy2.txt", size_bytes=len(content))

    group = DuplicateGroup(id=1, members=[rec1, rec2], size_bytes=len(content), file_count=2)

    cleanup_mgr = CleanupManager(db=test_db)

    # User attempts to clean both ID 1 and ID 2
    preview = cleanup_mgr.prepare_cleanup_preview(
        selected_file_ids=[1, 2],
        groups=[group]
    )

    assert preview["can_proceed"] is False
    assert len(preview["items_to_clean"]) == 0
    assert len(preview["blocked_items"]) == 2
    assert "at least one verified copy must remain" in preview["blocked_items"][0]["reason"].lower()


def test_quarantine_and_restore_workflow(test_db, temp_dir):
    quarantine_dir = temp_dir / "quarantine_box"
    quarantine_dir.mkdir()

    f1 = temp_dir / "original_file.txt"
    content = b"CRITICAL_USER_DATA_CONTENT_12345"
    f1.write_bytes(content)

    # 1. Execute quarantine
    quarantine_mgr = QuarantineManager(db=test_db, quarantine_dir=quarantine_dir)
    op = quarantine_mgr.execute_quarantine([{
        "path": str(f1),
        "filename": "original_file.txt",
        "size_bytes": len(content),
        "sha256_hash": None
    }])

    assert op.status == "completed"
    assert op.items_count == 1
    # Original file must no longer be at original location
    assert not f1.exists()

    # Quarantined item must exist in quarantine folder
    items = test_db.get_all_quarantine_items()
    assert len(items) == 1
    q_item = items[0]
    assert q_item.status == "quarantined"
    assert os.path.exists(q_item.quarantine_path)

    # 2. Restore file
    restore_mgr = RestoreManager(db=test_db)
    success, restored_path, err = restore_mgr.restore_item(q_item.id)

    assert success is True
    assert err is None
    assert os.path.exists(restored_path)
    assert Path(restored_path).read_bytes() == content

    # Item marked restored in DB
    updated_item = test_db.get_quarantine_item(q_item.id)
    assert updated_item.status == "restored"


def test_undo_last_quarantine(test_db, temp_dir):
    quarantine_dir = temp_dir / "quarantine_box"
    quarantine_dir.mkdir()

    f1 = temp_dir / "file1.txt"
    f2 = temp_dir / "file2.txt"
    f1.write_bytes(b"DATA_1")
    f2.write_bytes(b"DATA_2")

    quarantine_mgr = QuarantineManager(db=test_db, quarantine_dir=quarantine_dir)
    op = quarantine_mgr.execute_quarantine([
        {"path": str(f1), "filename": "file1.txt", "size_bytes": 6, "sha256_hash": None},
        {"path": str(f2), "filename": "file2.txt", "size_bytes": 6, "sha256_hash": None}
    ])

    assert not f1.exists()
    assert not f2.exists()

    # Undo operation
    restore_mgr = RestoreManager(db=test_db)
    success, count, errors = restore_mgr.undo_last_quarantine()

    assert success is True
    assert count == 2
    assert f1.exists()
    assert f2.exists()
    assert f1.read_bytes() == b"DATA_1"
    assert f2.read_bytes() == b"DATA_2"


def test_restore_conflict_prevention_does_not_overwrite(test_db, temp_dir):
    quarantine_dir = temp_dir / "quarantine_box"
    quarantine_dir.mkdir()

    target_file = temp_dir / "document.txt"
    target_file.write_bytes(b"ORIGINAL_OLD")

    quarantine_mgr = QuarantineManager(db=test_db, quarantine_dir=quarantine_dir)
    quarantine_mgr.execute_quarantine([{
        "path": str(target_file),
        "filename": "document.txt",
        "size_bytes": len(b"ORIGINAL_OLD"),
        "sha256_hash": None
    }])

    # Simulate a new file being created at the original location before restore
    target_file.write_bytes(b"NEW_EXISTING_FILE_DO_NOT_OVERWRITE")

    items = test_db.get_all_quarantine_items()
    restore_mgr = RestoreManager(db=test_db)

    # Restoring without overwrite flag must NOT overwrite target_file
    success, restored_path, err = restore_mgr.restore_item(items[0].id, overwrite=False)

    assert success is True
    # The existing file was preserved!
    assert target_file.read_bytes() == b"NEW_EXISTING_FILE_DO_NOT_OVERWRITE"
    # Restored file was placed at safe collision-free path
    assert restored_path != str(target_file)
    assert os.path.exists(restored_path)
    assert Path(restored_path).read_bytes() == b"ORIGINAL_OLD"
