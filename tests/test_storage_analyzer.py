"""
Tests for Storage Analyzer (Categorization, non-double counting folder calculation).
"""
import pytest
from fileguard.storage_analyzer import StorageAnalyzer
from fileguard.scanner import Scanner


def test_storage_analyzer_metrics(test_db, sample_test_files):
    scanner = Scanner(db=test_db)
    scan_rec = scanner.scan(root_paths=[str(sample_test_files["root"])])

    analyzer = StorageAnalyzer(db=test_db)
    metrics = analyzer.analyze_scan_storage(scan_rec.id)

    assert metrics["has_data"] is True
    assert metrics["total_files"] == scan_rec.files_processed
    assert metrics["total_bytes"] == scan_rec.total_indexed_bytes
    assert len(metrics["categories"]) > 0
    assert len(metrics["largest_direct_folders"]) > 0
    assert len(metrics["largest_files"]) > 0
