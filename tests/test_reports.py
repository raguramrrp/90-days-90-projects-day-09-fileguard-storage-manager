"""
Tests for Report Generator (CSV exports, HTML generation, and escaping).
"""
import os
import csv
from pathlib import Path
import pytest

from fileguard.models import DuplicateGroup, FileRecord
from fileguard.report_generator import ReportGenerator


def test_export_duplicates_csv(temp_dir):
    rep_dir = temp_dir / "reports"
    generator = ReportGenerator(output_dir=rep_dir)

    m1 = FileRecord(id=1, path="C:\\test\\doc1.txt", filename="doc1.txt", size_bytes=1000)
    m2 = FileRecord(id=2, path="C:\\test\\doc2.txt", filename="doc2.txt", size_bytes=1000)

    group = DuplicateGroup(
        id=1,
        sha256_hash="abcdef1234567890",
        size_bytes=1000,
        file_count=2,
        total_size_bytes=2000,
        max_recoverable_bytes=1000,
        members=[m1, m2],
        suggested_retained_file_id=1,
        suggestion_reasons={1: "Retained", 2: "Quarantine"}
    )

    csv_path = generator.export_duplicates_csv([group])
    assert os.path.exists(csv_path)

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        assert len(reader) == 3  # Header + 2 rows
        assert reader[0][0] == "Group ID"
        assert reader[1][1] == "abcdef1234567890"


def test_generate_duplicates_html(temp_dir):
    rep_dir = temp_dir / "reports"
    generator = ReportGenerator(output_dir=rep_dir)

    m1 = FileRecord(id=1, path="C:\\test\\file<>&.txt", filename="file<>&.txt", size_bytes=500)
    m2 = FileRecord(id=2, path="C:\\test\\file2.txt", filename="file2.txt", size_bytes=500)

    group = DuplicateGroup(
        id=1,
        sha256_hash="1234567890abcdef",
        size_bytes=500,
        file_count=2,
        total_size_bytes=1000,
        max_recoverable_bytes=500,
        members=[m1, m2],
        suggested_retained_file_id=1
    )

    html_path = generator.generate_duplicates_html([group])
    assert os.path.exists(html_path)

    content = Path(html_path).read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "FileGuard Storage Intelligence" in content
    # Check proper HTML escaping: file<>&.txt -> file&lt;&gt;&amp;.txt
    assert "file&lt;&gt;&amp;.txt" in content
