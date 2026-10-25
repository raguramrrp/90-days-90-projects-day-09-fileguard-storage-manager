"""
Tests for History and Trend Analyzer (Comparison between scans and timeline snapshots).
"""
import pytest
from fileguard.history_manager import HistoryManager
from fileguard.trend_analyzer import TrendAnalyzer
from fileguard.scanner import Scanner


def test_scan_comparison_and_scope_warning(test_db, temp_dir):
    # Scan 1: Scope A
    dir_a = temp_dir / "scope_a"
    dir_a.mkdir()
    (dir_a / "f1.txt").write_bytes(b"SAME")
    (dir_a / "f2.txt").write_bytes(b"SAME")

    scanner = Scanner(db=test_db)
    s1 = scanner.scan([str(dir_a)], scan_name="Scan A")

    # Scan 2: Scope B (different root folder)
    dir_b = temp_dir / "scope_b"
    dir_b.mkdir()
    (dir_b / "f1.txt").write_bytes(b"SAME")
    (dir_b / "f2.txt").write_bytes(b"SAME")
    (dir_b / "f3.txt").write_bytes(b"SAME")

    s2 = scanner.scan([str(dir_b)], scan_name="Scan B")

    history_mgr = HistoryManager(db=test_db)
    cmp = history_mgr.compare_scans(s1.id, s2.id)

    # Scopes are different, so scope_warning must be present!
    assert cmp["scopes_identical"] is False
    assert cmp["scope_warning"] is not None
    assert "Notice: Scans have different root folders" in cmp["scope_warning"]


def test_trend_analyzer_snapshots(test_db, temp_dir):
    dir_a = temp_dir / "scope_a"
    dir_a.mkdir()
    (dir_a / "f1.txt").write_bytes(b"A")

    scanner = Scanner(db=test_db)
    scanner.scan([str(dir_a)], scan_name="Trend Scan")

    analyzer = TrendAnalyzer(db=test_db)
    trends = analyzer.get_historical_trends()

    assert trends["has_trends"] is True
    assert len(trends["points"]) >= 1
