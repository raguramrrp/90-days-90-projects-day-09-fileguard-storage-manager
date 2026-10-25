"""
Tests for Duplicate Detector (Exact content matching, size grouping, savings calculations).
"""
import pytest
from fileguard.models import FileRecord
from fileguard.duplicate_detector import DuplicateDetector


def test_detect_duplicates_grouping(temp_dir):
    f1 = temp_dir / "doc1.txt"
    f2 = temp_dir / "doc2.txt"
    f3 = temp_dir / "doc3.txt"
    f_unique = temp_dir / "unique.txt"

    content_dup = b"IDENTICAL_CONTENT_BODY_TEST"
    f1.write_bytes(content_dup)
    f2.write_bytes(content_dup)
    f3.write_bytes(content_dup)
    f_unique.write_bytes(b"COMPLETELY_UNIQUE_BYTES")

    records = [
        FileRecord(id=1, path=str(f1), filename="doc1.txt", size_bytes=len(content_dup)),
        FileRecord(id=2, path=str(f2), filename="doc2.txt", size_bytes=len(content_dup)),
        FileRecord(id=3, path=str(f3), filename="doc3.txt", size_bytes=len(content_dup)),
        FileRecord(id=4, path=str(f_unique), filename="unique.txt", size_bytes=len(b"COMPLETELY_UNIQUE_BYTES")),
    ]

    detector = DuplicateDetector()
    groups = detector.detect_duplicates(records)

    assert len(groups) == 1
    grp = groups[0]
    assert grp.file_count == 3
    assert grp.size_bytes == len(content_dup)
    assert grp.total_size_bytes == len(content_dup) * 3
    # Theoretical savings: (3 - 1) * size = 2 * size
    assert grp.max_recoverable_bytes == (3 - 1) * len(content_dup)
    assert len(grp.members) == 3


def test_no_duplicates_returns_empty(temp_dir):
    f1 = temp_dir / "a.txt"
    f2 = temp_dir / "b.txt"
    f1.write_bytes(b"Content Alpha")
    f2.write_bytes(b"Content Beta")

    records = [
        FileRecord(id=1, path=str(f1), filename="a.txt", size_bytes=len(b"Content Alpha")),
        FileRecord(id=2, path=str(f2), filename="b.txt", size_bytes=len(b"Content Beta")),
    ]

    detector = DuplicateDetector()
    groups = detector.detect_duplicates(records)
    assert len(groups) == 0


def test_detector_cancellation(temp_dir):
    f1 = temp_dir / "a.txt"
    f2 = temp_dir / "b.txt"
    content = b"TEST"
    f1.write_bytes(content)
    f2.write_bytes(content)

    records = [
        FileRecord(id=1, path=str(f1), filename="a.txt", size_bytes=len(content)),
        FileRecord(id=2, path=str(f2), filename="b.txt", size_bytes=len(content)),
    ]

    detector = DuplicateDetector()
    # Cancelled immediately
    groups = detector.detect_duplicates(records, cancel_check=lambda: True)
    assert groups == []
