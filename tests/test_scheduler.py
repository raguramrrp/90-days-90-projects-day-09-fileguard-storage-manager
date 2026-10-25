"""
Tests for Scheduler (Next run calculations, safe scan triggering).
"""
from datetime import datetime
import pytest
from fileguard.models import ScheduleConfig
from fileguard.scheduler import Scheduler


def test_scheduler_next_run_calculation(test_db):
    scheduler = Scheduler(db=test_db)
    ref_time = datetime(2026, 10, 25, 8, 0, 0)

    # Next run for 09:00 today
    next_daily = scheduler.calculate_next_run("daily", "09:00", from_date=ref_time)
    assert "2026-10-25T09:00:00" in next_daily

    # If time has passed today (target 07:00), schedule for tomorrow
    next_tomorrow = scheduler.calculate_next_run("daily", "07:00", from_date=ref_time)
    assert "2026-10-26T07:00:00" in next_tomorrow


def test_scheduler_trigger_safe_scan(test_db, temp_dir):
    root = temp_dir / "sched_scope"
    root.mkdir()
    (root / "file1.txt").write_bytes(b"DATA")

    cfg = ScheduleConfig(
        name="Test Schedule",
        root_paths=[str(root)],
        frequency="daily",
        target_time="09:00",
        enabled=True
    )
    sid = test_db.add_schedule(cfg)

    scheduler = Scheduler(db=test_db)
    success = scheduler.trigger_scheduled_scan_now(sid)

    assert success is True
    # Verify scan record was created
    latest = test_db.get_latest_scan()
    assert latest is not None
    assert "Scheduled:" in latest.scan_name
