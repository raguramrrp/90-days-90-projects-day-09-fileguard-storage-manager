"""
Scan Scheduler for FileGuard.
Provides in-app background scheduling with next-run calculations and safe execution safeguards:
CRITICAL: Scheduled scans NEVER trigger automatic cleanup or file deletion.
"""
import threading
import time
from datetime import datetime, timedelta
from typing import List, Optional, Callable, Dict, Any

from fileguard.models import ScheduleConfig
from fileguard.database import Database
from fileguard.scanner import Scanner


class Scheduler:
    def __init__(self, db: Optional[Database] = None, scanner: Optional[Scanner] = None):
        self.db = db or Database()
        self.scanner = scanner or Scanner(self.db)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self):
        """Start the background scheduler evaluation loop."""
        with self._lock:
            if not self._running:
                self._running = True
                self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
                self._thread.start()

    def stop(self):
        """Stop background scheduler."""
        with self._lock:
            self._running = False

    def is_running(self) -> bool:
        return self._running

    def calculate_next_run(self, frequency: str, target_time: str, from_date: Optional[datetime] = None) -> str:
        """
        Calculate next execution timestamp (ISO format) based on frequency and target_time (HH:MM).
        """
        now = from_date or datetime.now()
        try:
            target_hour, target_minute = map(int, target_time.split(":"))
        except Exception:
            target_hour, target_minute = 9, 0

        candidate = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

        if candidate <= now:
            # Advance based on frequency
            if frequency == "daily":
                candidate += timedelta(days=1)
            elif frequency == "weekly":
                candidate += timedelta(weeks=1)
            elif frequency == "monthly":
                # Advance 30 days approximately
                candidate += timedelta(days=30)
            else:
                candidate += timedelta(days=1)

        return candidate.isoformat()

    def trigger_scheduled_scan_now(self, schedule_id: int) -> bool:
        """
        Execute scheduled scan manually or when triggered by timer.
        CRITICAL SAFETY: Scans only, never auto-cleans!
        """
        schedules = self.db.get_schedules()
        target = next((s for s in schedules if s.id == schedule_id), None)
        if not target or not target.root_paths:
            return False

        now_str = datetime.now().isoformat()
        next_run_str = self.calculate_next_run(target.frequency, target.target_time)

        try:
            self.scanner.scan(
                root_paths=target.root_paths,
                scan_name=f"Scheduled: {target.name}"
            )
            self.db.update_schedule_run(schedule_id, now_str, next_run_str)
            self.db.log_audit_event("scheduled_scan_run", {
                "schedule_id": schedule_id,
                "schedule_name": target.name,
                "completed_at": now_str,
                "next_run": next_run_str
            })
            return True
        except Exception as e:
            self.db.log_audit_event("scheduled_scan_failed", {
                "schedule_id": schedule_id,
                "error": str(e)
            })
            return False

    def _scheduler_loop(self):
        """Worker loop checking schedules every 30 seconds."""
        while self._running:
            try:
                now = datetime.now()
                schedules = self.db.get_schedules()
                for s in schedules:
                    if not s.enabled or not s.next_run:
                        continue
                    try:
                        next_dt = datetime.fromisoformat(s.next_run)
                        if now >= next_dt:
                            # Time to run
                            self.trigger_scheduled_scan_now(s.id)
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(30)
