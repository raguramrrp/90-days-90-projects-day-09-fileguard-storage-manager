"""
Tests for Selection Advisor (Transparent duplicate retention recommendations).
"""
import pytest
from fileguard.models import FileRecord, DuplicateGroup
from fileguard.selection_advisor import SelectionAdvisor


def test_selection_advisor_prefers_clean_folder():
    advisor = SelectionAdvisor()

    m_docs = FileRecord(
        id=1,
        path="C:\\Users\\User\\Documents\\Financial_Report.pdf",
        filename="Financial_Report.pdf",
        size_bytes=5000,
        created_time=1000.0
    )
    m_downloads = FileRecord(
        id=2,
        path="C:\\Users\\User\\Downloads\\Financial_Report (1).pdf",
        filename="Financial_Report (1).pdf",
        size_bytes=5000,
        created_time=2000.0
    )

    group = DuplicateGroup(
        id=1,
        members=[m_docs, m_downloads],
        size_bytes=5000,
        file_count=2
    )

    retained_id, reasons = advisor.advise_group(group)

    assert retained_id == 1  # Documents copy preferred over Downloads copy
    assert "RETAIN" in reasons[1]
    assert "Candidate for cleanup" in reasons[2]


def test_selection_advisor_single_member():
    advisor = SelectionAdvisor()
    m = FileRecord(id=10, path="C:\\test.txt", filename="test.txt")
    group = DuplicateGroup(id=5, members=[m])

    retained_id, reasons = advisor.advise_group(group)
    assert retained_id == 10
    assert "must be retained" in reasons[10].lower()
