"""
Tests for SQLite Database layer (Schema migrations, transactional operations, indexes).
"""
import pytest
from fileguard.models import FileRecord, DuplicateGroup
from fileguard.database import Database


def test_database_settings_persistence(test_db):
    test_db.set_setting("theme", "light")
    assert test_db.get_setting("theme") == "light"

    test_db.set_setting("theme", "dark")
    assert test_db.get_setting("theme") == "dark"


def test_database_files_batch_persistence(test_db):
    scan_id = test_db.create_scan("Test Batch Scan", ["C:\\fake"])
    files = [
        FileRecord(scan_id=scan_id, path=f"C:\\fake\\file_{i}.txt", filename=f"file_{i}.txt", size_bytes=100)
        for i in range(10)
    ]
    ids = test_db.save_files_batch(files)
    assert len(ids) == 10

    loaded = test_db.get_files_by_scan(scan_id)
    assert len(loaded) == 10
    assert loaded[0].filename == "file_0.txt"


def test_database_audit_event_logging(test_db):
    test_db.log_audit_event("test_action", {"key": "value"})
    events = test_db.get_recent_audit_events(limit=5)
    assert len(events) >= 1
    assert events[0]["event_type"] == "test_action"
    assert events[0]["details"]["key"] == "value"


def test_database_delete_scan_cascade(test_db):
    scan_id = test_db.create_scan("Delete Scan Test", ["C:\\scope"])
    files = [FileRecord(scan_id=scan_id, path="C:\\scope\\f1.txt", filename="f1.txt", size_bytes=50)]
    test_db.save_files_batch(files)

    assert len(test_db.get_files_by_scan(scan_id)) == 1
    test_db.delete_scan(scan_id)

    assert test_db.get_scan(scan_id) is None
    # Cascaded delete ensures associated files are removed
    assert len(test_db.get_files_by_scan(scan_id)) == 0


def test_database_clear_all_scans(test_db):
    s1 = test_db.create_scan("Scan 1", ["C:\\a"])
    s2 = test_db.create_scan("Scan 2", ["C:\\b"])
    assert len(test_db.get_all_scans()) >= 2

    test_db.clear_all_scans()
    assert len(test_db.get_all_scans()) == 0
