"""
Trend Analyzer for FileGuard.
Computes timeline metrics across historical scans and storage snapshots.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from fileguard.models import StorageSnapshot, format_bytes
from fileguard.database import Database


class TrendAnalyzer:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    def get_historical_trends(self) -> Dict[str, Any]:
        """
        Extract timeline trends from scans and snapshots.
        """
        scans = self.db.get_all_scans()
        completed_scans = [s for s in scans if s.status == "completed"]
        # Order chronologically for trend lines
        completed_scans.sort(key=lambda s: s.completed_at or s.started_at or "")

        if not completed_scans:
            return {
                "has_trends": False,
                "points": [],
                "summary": "No completed scans available yet."
            }

        points = []
        for s in completed_scans:
            points.append({
                "scan_id": s.id,
                "date": (s.completed_at or s.started_at or "")[:10],
                "files_count": s.files_processed,
                "total_bytes": s.total_indexed_bytes,
                "formatted_total_bytes": s.formatted_indexed_size,
                "duplicate_groups": s.duplicate_groups_count,
                "recoverable_bytes": s.potential_recoverable_bytes,
                "formatted_recoverable_bytes": s.formatted_recoverable_size
            })

        return {
            "has_trends": True,
            "points": points,
            "total_snapshots": len(points),
            "first_date": points[0]["date"],
            "latest_date": points[-1]["date"]
        }
