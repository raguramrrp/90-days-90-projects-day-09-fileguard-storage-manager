"""
Tests for Scanner (Filesystem traversal, cancellation, and persistence).
"""
import pytest
from fileguard.scanner import Scanner
from fileguard.exclusion_manager import ExclusionManager


def test_scanner_end_to_end(test_db, sample_test_files):
    scanner = Scanner(db=test_db)
    scan_rec = scanner.scan(
        root_paths=[str(sample_test_files["root"])],
        scan_name="Integration Test Scan"
    )

    assert scan_rec is not None
    assert scan_rec.status == "completed"
    assert scan_rec.files_processed > 0
    # We created 2 duplicate files in sample_test_files (file_a1 and file_b1)
    assert scan_rec.duplicate_groups_count >= 1
    assert scan_rec.potential_recoverable_bytes > 0


def test_scanner_exclusion_handling(test_db, temp_dir):
    root = temp_dir / "scope"
    root.mkdir()
    (root / "regular.txt").write_bytes(b"HELLO")
    (root / "system.dll").write_bytes(b"DLL_CONTENT")  # Default excluded extension
    (root / ".git").mkdir()
    (root / ".git" / "config").write_bytes(b"GIT_CONFIG")  # Default excluded folder

    scanner = Scanner(db=test_db)
    scan_rec = scanner.scan(root_paths=[str(root)])

    files = test_db.get_files_by_scan(scan_rec.id)
    filenames = [f.filename for f in files]

    assert "regular.txt" in filenames
    assert "system.dll" not in filenames
    assert "config" not in filenames
    assert scan_rec.files_skipped >= 1


def test_scanner_cancellation(test_db, temp_dir):
    root = temp_dir / "scope"
    root.mkdir()
    for i in range(10):
        (root / f"file_{i}.txt").write_bytes(b"DATA" * 100)

    scanner = Scanner(db=test_db)
    scanner.cancel()  # Signal cancellation before/during
    scan_rec = scanner.scan(root_paths=[str(root)])

    assert scan_rec.status == "cancelled"


def test_scanner_nonexistent_root(test_db, temp_dir):
    missing_dir = temp_dir / "does_not_exist"
    scanner = Scanner(db=test_db)
    scan_rec = scanner.scan(root_paths=[str(missing_dir)])

    assert scan_rec.status == "completed"
    assert scan_rec.files_failed >= 1
