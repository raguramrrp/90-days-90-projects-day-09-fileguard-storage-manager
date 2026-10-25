"""
Tests for Hash Engine (SHA-256 calculation, chunked reads, and integrity verification).
"""
import pytest
from pathlib import Path
from fileguard.hash_engine import compute_sha256, compute_quick_hash, verify_file_hash


def test_identical_content_different_names(temp_dir):
    f1 = temp_dir / "file1.txt"
    f2 = temp_dir / "file2_rename.txt"
    content = b"Exact duplicate content stream test 12345"
    f1.write_bytes(content)
    f2.write_bytes(content)

    h1, sz1 = compute_sha256(str(f1))
    h2, sz2 = compute_sha256(str(f2))

    assert sz1 == len(content)
    assert sz2 == len(content)
    assert h1 == h2
    assert len(h1) == 64


def test_same_name_different_content(temp_dir):
    d1 = temp_dir / "dir1"
    d2 = temp_dir / "dir2"
    d1.mkdir()
    d2.mkdir()

    f1 = d1 / "data.csv"
    f2 = d2 / "data.csv"
    f1.write_bytes(b"col1,col2\n1,2")
    f2.write_bytes(b"col1,col2\n3,4")

    h1, _ = compute_sha256(str(f1))
    h2, _ = compute_sha256(str(f2))

    assert h1 != h2


def test_empty_file_hashing(temp_dir):
    empty_f = temp_dir / "empty.dat"
    empty_f.write_bytes(b"")

    h, sz = compute_sha256(str(empty_f))
    assert sz == 0
    # Standard SHA-256 for empty string: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
    assert h.lower() == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_chunked_read_consistency(temp_dir):
    f = temp_dir / "stream.dat"
    content = b"A" * 150000  # 150 KB
    f.write_bytes(content)

    # Hash with 1 KB chunk size
    h_small, sz1 = compute_sha256(str(f), chunk_size=1024)
    # Hash with 64 KB chunk size
    h_large, sz2 = compute_sha256(str(f), chunk_size=65536)

    assert sz1 == 150000
    assert sz2 == 150000
    assert h_small == h_large


def test_missing_file_raises(temp_dir):
    missing_path = str(temp_dir / "non_existent_file.xyz")
    with pytest.raises(FileNotFoundError):
        compute_sha256(missing_path)


def test_verify_file_hash(temp_dir):
    f = temp_dir / "sample.txt"
    f.write_bytes(b"Sample verification content")

    valid_hash, _ = compute_sha256(str(f))
    is_match, observed, err = verify_file_hash(str(f), valid_hash)
    assert is_match is True
    assert observed == valid_hash
    assert err is None

    # Tampered hash
    is_match, observed, err = verify_file_hash(str(f), "0000000000000000000000000000000000000000000000000000000000000000")
    assert is_match is False
