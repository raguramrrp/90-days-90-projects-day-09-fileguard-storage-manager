"""
Tests for Exclusion Manager (Rules evaluation, protected path detection).
"""
import pytest
from fileguard.exclusion_manager import ExclusionManager
from fileguard.config import is_path_protected


def test_default_exclusions(test_db):
    mgr = ExclusionManager(db=test_db)

    # .git folder
    excl, reason = mgr.is_directory_excluded("C:\\project\\.git")
    assert excl is True

    # system dll
    excl, reason = mgr.should_exclude_file("C:\\app\\library.dll", 1000)
    assert excl is True


def test_custom_rules(test_db):
    test_db.add_exclusion("extension", ".log")
    test_db.add_exclusion("min_size", "500")

    mgr = ExclusionManager(db=test_db)

    # .log file excluded
    excl, _ = mgr.should_exclude_file("C:\\test\\app.log", 2000)
    assert excl is True

    # Under 500 bytes excluded
    excl, _ = mgr.should_exclude_file("C:\\test\\tiny.txt", 100)
    assert excl is True

    # Over 500 bytes allowed
    excl, _ = mgr.should_exclude_file("C:\\test\\valid.txt", 1000)
    assert excl is False


def test_protected_locations():
    assert is_path_protected("C:\\Windows\\System32\\cmd.exe") is True
    assert is_path_protected("C:\\Program Files\\App\\binary.exe") is True
    assert is_path_protected("D:\\MyProjects\\Notes.txt") is False
