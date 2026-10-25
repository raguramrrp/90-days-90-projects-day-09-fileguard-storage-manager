"""
Pytest fixtures for FileGuard tests.
Provides isolated temporary directory environments, clean databases, and synthetic test files.
"""
import os
import shutil
import tempfile
from pathlib import Path
import pytest

from fileguard.database import Database
from fileguard.exclusion_manager import ExclusionManager
from fileguard.selection_advisor import SelectionAdvisor
from fileguard.duplicate_detector import DuplicateDetector
from fileguard.scanner import Scanner
from fileguard.cleanup_manager import CleanupManager
from fileguard.quarantine_manager import QuarantineManager
from fileguard.restore_manager import RestoreManager


@pytest.fixture
def temp_dir():
    """Create a temporary sandbox directory that is cleaned up after each test."""
    d = tempfile.mkdtemp(prefix="fileguard_test_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def test_db(temp_dir):
    """Create an isolated test database in the temporary directory."""
    db_file = temp_dir / "test_fileguard.db"
    db = Database(db_file)
    return db


@pytest.fixture
def sample_test_files(temp_dir):
    """
    Create a realistic test file structure with:
    - 2 identical files in different folders with different names
    - 1 file with same name but different content
    - 1 empty file
    - 1 large file
    - 1 unique file
    - 1 temporary file (.tmp)
    - 1 empty folder
    """
    root = temp_dir / "workspace"
    folder_a = root / "FolderA"
    folder_b = root / "FolderB"
    empty_f = root / "EmptyFolder"
    temp_f = root / "TempFolder"

    folder_a.mkdir(parents=True)
    folder_b.mkdir(parents=True)
    empty_f.mkdir(parents=True)
    temp_f.mkdir(parents=True)

    # Identical content (1 KB)
    dup_content = b"DUPLICATE_CONTENT_STREAM_ALPHA_0123456789\n" * 25
    file_a1 = folder_a / "document.txt"
    file_b1 = folder_b / "document_backup.txt"
    file_a1.write_bytes(dup_content)
    file_b1.write_bytes(dup_content)

    # Same name as document.txt, but DIFFERENT content
    diff_content = b"DIFFERENT_CONTENT_HERE_XYZ\n" * 20
    file_diff = folder_b / "document.txt"
    file_diff.write_bytes(diff_content)

    # Empty file
    empty_file = folder_a / "empty.txt"
    empty_file.write_bytes(b"")

    # Unique file
    unique_file = folder_a / "unique_report.md"
    unique_file.write_text("# Unique Report Notes", encoding="utf-8")

    # Temp file
    temp_file = temp_f / "cache.tmp"
    temp_file.write_bytes(b"TEMPORARY_CACHE_STREAM")

    return {
        "root": root,
        "folder_a": folder_a,
        "folder_b": folder_b,
        "empty_folder": empty_f,
        "temp_folder": temp_f,
        "file_a1": file_a1,
        "file_b1": file_b1,
        "file_diff": file_diff,
        "empty_file": empty_file,
        "unique_file": unique_file,
        "temp_file": temp_file
    }
