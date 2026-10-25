"""
Tests for Folder Analyzer and Temporary File Analyzer.
"""
import pytest
from fileguard.folder_analyzer import FolderAnalyzer
from fileguard.temporary_file_analyzer import TemporaryFileAnalyzer
from fileguard.scanner import Scanner


def test_empty_folder_detection(test_db, temp_dir):
    root = temp_dir / "base"
    root.mkdir()
    empty_sub = root / "EmptySub"
    empty_sub.mkdir()

    non_empty_sub = root / "HasFiles"
    non_empty_sub.mkdir()
    (non_empty_sub / "file.txt").write_bytes(b"HELLO")

    analyzer = FolderAnalyzer(db=test_db)
    results = analyzer.find_empty_folders([str(root)])

    paths = [r["path"] for r in results]
    assert str(empty_sub) in paths
    assert str(non_empty_sub) not in paths


def test_temp_file_analyzer(test_db, sample_test_files):
    scanner = Scanner(db=test_db)
    scan_rec = scanner.scan(root_paths=[str(sample_test_files["root"])])

    analyzer = TemporaryFileAnalyzer(db=test_db)
    candidates = analyzer.find_temporary_candidates(scan_id=scan_rec.id)

    filenames = [c["filename"] for c in candidates]
    # sample_test_files contains 'cache.tmp'
    assert "cache.tmp" in filenames
    assert any("tmp" in c["rules"].lower() for c in candidates)
