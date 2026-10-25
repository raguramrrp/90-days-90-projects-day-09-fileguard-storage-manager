"""
Tests for Integrity Checker (Baseline comparison, tampered file detection).
"""
import pytest
from fileguard.models import FileRecord
from fileguard.hash_engine import compute_sha256
from fileguard.integrity_checker import IntegrityChecker


def test_integrity_checker_workflow(test_db, temp_dir):
    f_ok = temp_dir / "valid.txt"
    f_tampered = temp_dir / "tampered.txt"
    f_missing = temp_dir / "missing.txt"

    f_ok.write_bytes(b"VALID_CONTENT")
    f_tampered.write_bytes(b"INITIAL_CONTENT")

    h_ok, _ = compute_sha256(str(f_ok))
    h_tampered, _ = compute_sha256(str(f_tampered))

    # Now tamper with f_tampered
    f_tampered.write_bytes(b"ALTERED_CONTENT_CORRUPTED")

    records = [
        FileRecord(id=1, path=str(f_ok), filename="valid.txt", sha256_hash=h_ok),
        FileRecord(id=2, path=str(f_tampered), filename="tampered.txt", sha256_hash=h_tampered),
        FileRecord(id=3, path=str(f_missing), filename="missing.txt", sha256_hash="dummyhash")
    ]

    checker = IntegrityChecker(db=test_db)
    results = checker.check_files(records)

    assert len(results) == 3
    res_map = {r.file_id: r for r in results}

    assert res_map[1].status == "unchanged"
    assert res_map[2].status == "modified"
    assert res_map[3].status == "missing"

    # Verify records persisted in DB
    db_checks = test_db.get_integrity_checks()
    assert len(db_checks) == 3
