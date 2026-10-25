"""
SQLite Database Layer for FileGuard.
Handles schema migrations, transactional persistence, indexed lookups, and audit trails.
"""
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from fileguard.config import DB_PATH
from fileguard.models import (
    FileRecord, DuplicateGroup, ScanRecord, CleanupOperation,
    QuarantineItem, ExclusionRule, IntegrityResult, ScheduleConfig,
    StorageSnapshot
)

_LOCAL = threading.local()


class Database:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def get_connection(self) -> sqlite3.Connection:
        """Get thread-local SQLite connection with foreign keys and WAL mode."""
        conn = getattr(_LOCAL, f"conn_{self.db_path}", None)
        if conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA synchronous=NORMAL")
            setattr(_LOCAL, f"conn_{self.db_path}", conn)
        return conn

    def init_schema(self):
        """Create tables and indexes if they do not exist."""
        conn = self.get_connection()
        with conn:
            # 1. Scans Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_name TEXT NOT NULL,
                    root_paths TEXT NOT NULL,  -- JSON array
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT NOT NULL,       -- running, completed, cancelled, failed
                    files_discovered INTEGER DEFAULT 0,
                    files_processed INTEGER DEFAULT 0,
                    files_hashed INTEGER DEFAULT 0,
                    files_skipped INTEGER DEFAULT 0,
                    files_failed INTEGER DEFAULT 0,
                    duplicate_groups_count INTEGER DEFAULT 0,
                    duplicate_files_count INTEGER DEFAULT 0,
                    total_indexed_bytes INTEGER DEFAULT 0,
                    potential_recoverable_bytes INTEGER DEFAULT 0,
                    error_summary TEXT
                )
            """)

            # 2. Files Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id INTEGER,
                    path TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    extension TEXT,
                    category TEXT NOT NULL,
                    created_time REAL,
                    modified_time REAL,
                    last_scanned_time REAL,
                    sha256_hash TEXT,
                    hash_status TEXT DEFAULT 'pending',
                    is_available INTEGER DEFAULT 1,
                    FOREIGN KEY(scan_id) REFERENCES scans(id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files(path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_hash ON files(sha256_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_size ON files(size_bytes)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_scan_id ON files(scan_id)")

            # 3. Duplicate Groups Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS duplicate_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id INTEGER,
                    group_key TEXT NOT NULL,
                    sha256_hash TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    file_count INTEGER NOT NULL,
                    total_size_bytes INTEGER NOT NULL,
                    max_recoverable_bytes INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(scan_id) REFERENCES scans(id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_groups_hash ON duplicate_groups(sha256_hash)")

            # 4. Duplicate Group Members Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS duplicate_group_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    file_id INTEGER NOT NULL,
                    is_suggested_retained INTEGER DEFAULT 0,
                    suggestion_reason TEXT,
                    FOREIGN KEY(group_id) REFERENCES duplicate_groups(id) ON DELETE CASCADE,
                    FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_group_members ON duplicate_group_members(group_id, file_id)")

            # 5. Scan Errors Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scan_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(scan_id) REFERENCES scans(id) ON DELETE CASCADE
                )
            """)

            # 6. Cleanup Operations Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cleanup_operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_uuid TEXT UNIQUE NOT NULL,
                    action_type TEXT NOT NULL,  -- quarantine, undo_quarantine, permanent_delete
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT NOT NULL,        -- completed, failed, partial, undone
                    items_count INTEGER DEFAULT 0,
                    total_bytes INTEGER DEFAULT 0,
                    user_confirmed INTEGER DEFAULT 1,
                    error_summary TEXT
                )
            """)

            # 7. Quarantine Items Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quarantine_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id INTEGER NOT NULL,
                    original_path TEXT NOT NULL,
                    quarantine_path TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    sha256_hash TEXT NOT NULL,
                    original_created_time REAL,
                    original_modified_time REAL,
                    quarantined_at TEXT NOT NULL,
                    status TEXT DEFAULT 'quarantined',  -- quarantined, restored, deleted
                    restored_at TEXT,
                    restored_path TEXT,
                    FOREIGN KEY(operation_id) REFERENCES cleanup_operations(id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_quarantine_status ON quarantine_items(status)")

            # 8. Exclusions Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS exclusions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_type TEXT NOT NULL, -- directory, extension, min_size, max_size, pattern
                    rule_value TEXT NOT NULL,
                    is_enabled INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)

            # 9. Settings Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # 10. Integrity Checks Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS integrity_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    check_uuid TEXT NOT NULL,
                    file_id INTEGER,
                    file_path TEXT NOT NULL,
                    reference_hash TEXT NOT NULL,
                    observed_hash TEXT,
                    status TEXT NOT NULL, -- unchanged, modified, missing, inaccessible
                    verified_at TEXT NOT NULL
                )
            """)

            # 11. Scheduled Scans Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    root_paths TEXT NOT NULL, -- JSON array
                    frequency TEXT NOT NULL,  -- daily, weekly, monthly
                    target_time TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    last_run TEXT,
                    next_run TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # 12. Storage Snapshots Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS storage_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id INTEGER,
                    snapshot_date TEXT NOT NULL,
                    total_files INTEGER NOT NULL,
                    total_bytes INTEGER NOT NULL,
                    duplicate_bytes INTEGER NOT NULL,
                    recoverable_bytes INTEGER NOT NULL,
                    categories_json TEXT NOT NULL,
                    scope_hash TEXT NOT NULL,
                    FOREIGN KEY(scan_id) REFERENCES scans(id) ON DELETE SET NULL
                )
            """)

            # 13. Audit Events Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL, -- scan_start, scan_finish, quarantine, restore, undo, permanent_delete
                    details_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

        self._seed_default_settings()

    def _seed_default_settings(self):
        """Seed default user preferences if not already present."""
        defaults = {
            "theme": "dark",
            "confirm_quarantine": "true",
            "auto_open_report": "false",
            "large_file_threshold_mb": "10",
            "chunk_size_kb": "64",
            "preferred_keep_folders": "[]",  # JSON array of folder paths to prioritize keeping
            "allow_link_traversal": "false",
            "similar_photo_threshold": "90"
        }
        conn = self.get_connection()
        with conn:
            for k, v in defaults.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                    (k, v, datetime.now().isoformat())
                )

    # ----------------- SETTINGS METHODS -----------------
    def get_setting(self, key: str, default: str = "") -> str:
        conn = self.get_connection()
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        conn = self.get_connection()
        with conn:
            conn.execute(
                "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key, value, datetime.now().isoformat())
            )

    # ----------------- SCAN PERSISTENCE -----------------
    def create_scan(self, scan_name: str, root_paths: List[str]) -> int:
        conn = self.get_connection()
        with conn:
            cur = conn.execute(
                """INSERT INTO scans (
                    scan_name, root_paths, started_at, status,
                    files_discovered, files_processed, files_hashed, files_skipped, files_failed
                ) VALUES (?, ?, ?, 'running', 0, 0, 0, 0, 0)""",
                (scan_name, json.dumps(root_paths), datetime.now().isoformat())
            )
            return cur.lastrowid

    def update_scan_progress(self, scan_id: int, discovered: int, processed: int, hashed: int, skipped: int, failed: int):
        conn = self.get_connection()
        with conn:
            conn.execute(
                """UPDATE scans SET
                    files_discovered = ?,
                    files_processed = ?,
                    files_hashed = ?,
                    files_skipped = ?,
                    files_failed = ?
                WHERE id = ?""",
                (discovered, processed, hashed, skipped, failed, scan_id)
            )

    def complete_scan(self, scan_id: int, status: str, duplicate_groups: int, duplicate_files: int,
                      total_bytes: int, recoverable_bytes: int, error_summary: Optional[str] = None):
        conn = self.get_connection()
        with conn:
            conn.execute(
                """UPDATE scans SET
                    status = ?,
                    completed_at = ?,
                    duplicate_groups_count = ?,
                    duplicate_files_count = ?,
                    total_indexed_bytes = ?,
                    potential_recoverable_bytes = ?,
                    error_summary = ?
                WHERE id = ?""",
                (status, datetime.now().isoformat(), duplicate_groups, duplicate_files,
                 total_bytes, recoverable_bytes, error_summary, scan_id)
            )

    def log_scan_error(self, scan_id: int, path: str, error_type: str, error_message: str):
        conn = self.get_connection()
        with conn:
            conn.execute(
                """INSERT INTO scan_errors (scan_id, path, error_type, error_message, timestamp)
                VALUES (?, ?, ?, ?, ?)""",
                (scan_id, path, error_type, error_message, datetime.now().isoformat())
            )

    def get_latest_scan(self) -> Optional[ScanRecord]:
        conn = self.get_connection()
        row = conn.execute("SELECT * FROM scans ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return None
        return self._row_to_scan_record(row)

    def get_scan(self, scan_id: int) -> Optional[ScanRecord]:
        conn = self.get_connection()
        row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
        if not row:
            return None
        return self._row_to_scan_record(row)

    def get_all_scans(self) -> List[ScanRecord]:
        conn = self.get_connection()
        rows = conn.execute("SELECT * FROM scans ORDER BY id DESC").fetchall()
        return [self._row_to_scan_record(r) for r in rows]

    def delete_scan(self, scan_id: int):
        """Delete a scan record and all associated files and duplicate groups via cascade."""
        conn = self.get_connection()
        with conn:
            conn.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
            conn.execute(
                "INSERT INTO audit_events (event_type, details_json, timestamp) VALUES (?, ?, ?)",
                ("delete_scan", json.dumps({"scan_id": scan_id}), datetime.now().isoformat())
            )

    def clear_all_scans(self):
        """Remove all scan records and purges indexed files and duplicate groups."""
        conn = self.get_connection()
        with conn:
            conn.execute("DELETE FROM scans")
            conn.execute(
                "INSERT INTO audit_events (event_type, details_json, timestamp) VALUES (?, ?, ?)",
                ("clear_all_scans", "{}", datetime.now().isoformat())
            )

    def _row_to_scan_record(self, row: sqlite3.Row) -> ScanRecord:
        try:
            roots = json.loads(row["root_paths"])
        except Exception:
            roots = [row["root_paths"]]
        return ScanRecord(
            id=row["id"],
            scan_name=row["scan_name"],
            root_paths=roots,
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            status=row["status"],
            files_discovered=row["files_discovered"],
            files_processed=row["files_processed"],
            files_hashed=row["files_hashed"],
            files_skipped=row["files_skipped"],
            files_failed=row["files_failed"],
            duplicate_groups_count=row["duplicate_groups_count"],
            duplicate_files_count=row["duplicate_files_count"],
            total_indexed_bytes=row["total_indexed_bytes"],
            potential_recoverable_bytes=row["potential_recoverable_bytes"],
            error_summary=row["error_summary"]
        )

    # ----------------- FILES & DUPLICATES PERSISTENCE -----------------
    def save_files_batch(self, files: List[FileRecord]) -> List[int]:
        """Save a batch of files and return their generated IDs."""
        conn = self.get_connection()
        file_ids = []
        with conn:
            for f in files:
                cur = conn.execute(
                    """INSERT INTO files (
                        scan_id, path, filename, size_bytes, extension, category,
                        created_time, modified_time, last_scanned_time,
                        sha256_hash, hash_status, is_available
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        f.scan_id, f.path, f.filename, f.size_bytes, f.extension, f.category,
                        f.created_time, f.modified_time, f.last_scanned_time,
                        f.sha256_hash, f.hash_status, 1 if f.is_available else 0
                    )
                )
                f.id = cur.lastrowid
                file_ids.append(cur.lastrowid)
        return file_ids

    def save_duplicate_groups(self, scan_id: int, groups: List[DuplicateGroup]):
        """Persist duplicate groups and member associations transactionally."""
        conn = self.get_connection()
        with conn:
            for g in groups:
                cur = conn.execute(
                    """INSERT INTO duplicate_groups (
                        scan_id, group_key, sha256_hash, size_bytes, file_count,
                        total_size_bytes, max_recoverable_bytes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        scan_id, g.group_key, g.sha256_hash, g.size_bytes, g.file_count,
                        g.total_size_bytes, g.max_recoverable_bytes,
                        g.created_at or datetime.now().isoformat()
                    )
                )
                group_id = cur.lastrowid
                g.id = group_id

                for member in g.members:
                    is_retained = 1 if (g.suggested_retained_file_id and member.id == g.suggested_retained_file_id) else 0
                    reason = g.suggestion_reasons.get(member.id, "")
                    conn.execute(
                        """INSERT INTO duplicate_group_members (
                            group_id, file_id, is_suggested_retained, suggestion_reason
                        ) VALUES (?, ?, ?, ?)""",
                        (group_id, member.id, is_retained, reason)
                    )

    def get_duplicate_groups(self, scan_id: Optional[int] = None) -> List[DuplicateGroup]:
        """Fetch duplicate groups and their members."""
        conn = self.get_connection()
        if scan_id is not None:
            query = "SELECT * FROM duplicate_groups WHERE scan_id = ? ORDER BY total_size_bytes DESC"
            params = (scan_id,)
        else:
            query = "SELECT * FROM duplicate_groups ORDER BY id DESC"
            params = ()

        group_rows = conn.execute(query, params).fetchall()
        groups: List[DuplicateGroup] = []

        for g_row in group_rows:
            group = DuplicateGroup(
                id=g_row["id"],
                group_key=g_row["group_key"],
                sha256_hash=g_row["sha256_hash"],
                size_bytes=g_row["size_bytes"],
                file_count=g_row["file_count"],
                total_size_bytes=g_row["total_size_bytes"],
                max_recoverable_bytes=g_row["max_recoverable_bytes"],
                created_at=g_row["created_at"],
                members=[]
            )

            # Get members
            members_rows = conn.execute(
                """SELECT f.*, m.is_suggested_retained, m.suggestion_reason
                FROM duplicate_group_members m
                JOIN files f ON m.file_id = f.id
                WHERE m.group_id = ?""",
                (group.id,)
            ).fetchall()

            for m in members_rows:
                file_rec = FileRecord(
                    id=m["id"],
                    scan_id=m["scan_id"],
                    path=m["path"],
                    filename=m["filename"],
                    size_bytes=m["size_bytes"],
                    extension=m["extension"],
                    category=m["category"],
                    created_time=m["created_time"],
                    modified_time=m["modified_time"],
                    last_scanned_time=m["last_scanned_time"],
                    sha256_hash=m["sha256_hash"],
                    hash_status=m["hash_status"],
                    is_available=bool(m["is_available"]),
                    duplicate_group_id=group.id
                )
                group.members.append(file_rec)
                if m["is_suggested_retained"]:
                    group.suggested_retained_file_id = file_rec.id
                if m["suggestion_reason"]:
                    group.suggestion_reasons[file_rec.id] = m["suggestion_reason"]

            groups.append(group)
        return groups

    def get_large_files(self, min_size_bytes: int, scan_id: Optional[int] = None) -> List[FileRecord]:
        conn = self.get_connection()
        if scan_id is not None:
            query = "SELECT * FROM files WHERE scan_id = ? AND size_bytes >= ? ORDER BY size_bytes DESC"
            params = (scan_id, min_size_bytes)
        else:
            query = "SELECT * FROM files WHERE size_bytes >= ? ORDER BY size_bytes DESC"
            params = (min_size_bytes,)

        rows = conn.execute(query, params).fetchall()
        return [
            FileRecord(
                id=r["id"],
                scan_id=r["scan_id"],
                path=r["path"],
                filename=r["filename"],
                size_bytes=r["size_bytes"],
                extension=r["extension"],
                category=r["category"],
                created_time=r["created_time"],
                modified_time=r["modified_time"],
                last_scanned_time=r["last_scanned_time"],
                sha256_hash=r["sha256_hash"],
                hash_status=r["hash_status"],
                is_available=bool(r["is_available"])
            )
            for r in rows
        ]

    def get_files_by_scan(self, scan_id: int) -> List[FileRecord]:
        conn = self.get_connection()
        rows = conn.execute("SELECT * FROM files WHERE scan_id = ?", (scan_id,)).fetchall()
        return [
            FileRecord(
                id=r["id"],
                scan_id=r["scan_id"],
                path=r["path"],
                filename=r["filename"],
                size_bytes=r["size_bytes"],
                extension=r["extension"],
                category=r["category"],
                created_time=r["created_time"],
                modified_time=r["modified_time"],
                last_scanned_time=r["last_scanned_time"],
                sha256_hash=r["sha256_hash"],
                hash_status=r["hash_status"],
                is_available=bool(r["is_available"])
            )
            for r in rows
        ]

    # ----------------- CLEANUP & QUARANTINE -----------------
    def create_cleanup_operation(self, op: CleanupOperation) -> int:
        conn = self.get_connection()
        with conn:
            cur = conn.execute(
                """INSERT INTO cleanup_operations (
                    operation_uuid, action_type, started_at, status,
                    items_count, total_bytes, user_confirmed, error_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    op.operation_uuid, op.action_type, op.started_at or datetime.now().isoformat(),
                    op.status, op.items_count, op.total_bytes,
                    1 if op.user_confirmed else 0, op.error_summary
                )
            )
            op.id = cur.lastrowid
            return cur.lastrowid

    def complete_cleanup_operation(self, op_id: int, status: str, error_summary: Optional[str] = None):
        conn = self.get_connection()
        with conn:
            conn.execute(
                """UPDATE cleanup_operations SET
                    completed_at = ?,
                    status = ?,
                    error_summary = ?
                WHERE id = ?""",
                (datetime.now().isoformat(), status, error_summary, op_id)
            )

    def add_quarantine_item(self, item: QuarantineItem) -> int:
        conn = self.get_connection()
        with conn:
            cur = conn.execute(
                """INSERT INTO quarantine_items (
                    operation_id, original_path, quarantine_path, filename,
                    size_bytes, sha256_hash, original_created_time,
                    original_modified_time, quarantined_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'quarantined')""",
                (
                    item.operation_id, item.original_path, item.quarantine_path, item.filename,
                    item.size_bytes, item.sha256_hash, item.original_created_time,
                    item.original_modified_time, item.quarantined_at or datetime.now().isoformat()
                )
            )
            item.id = cur.lastrowid
            return cur.lastrowid

    def get_quarantined_items(self, status: str = "quarantined") -> List[QuarantineItem]:
        conn = self.get_connection()
        rows = conn.execute(
            "SELECT * FROM quarantine_items WHERE status = ? ORDER BY id DESC",
            (status,)
        ).fetchall()
        return [self._row_to_quarantine_item(r) for r in rows]

    def get_all_quarantine_items(self) -> List[QuarantineItem]:
        conn = self.get_connection()
        rows = conn.execute("SELECT * FROM quarantine_items ORDER BY id DESC").fetchall()
        return [self._row_to_quarantine_item(r) for r in rows]

    def get_quarantine_item(self, item_id: int) -> Optional[QuarantineItem]:
        conn = self.get_connection()
        row = conn.execute("SELECT * FROM quarantine_items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            return None
        return self._row_to_quarantine_item(row)

    def mark_quarantine_item_restored(self, item_id: int, restored_path: str):
        conn = self.get_connection()
        with conn:
            conn.execute(
                """UPDATE quarantine_items SET
                    status = 'restored',
                    restored_at = ?,
                    restored_path = ?
                WHERE id = ?""",
                (datetime.now().isoformat(), restored_path, item_id)
            )

    def mark_quarantine_item_deleted(self, item_id: int):
        conn = self.get_connection()
        with conn:
            conn.execute(
                """UPDATE quarantine_items SET
                    status = 'deleted'
                WHERE id = ?""",
                (item_id,)
            )

    def get_latest_quarantine_operation(self) -> Optional[CleanupOperation]:
        conn = self.get_connection()
        row = conn.execute(
            "SELECT * FROM cleanup_operations WHERE action_type = 'quarantine' AND status = 'completed' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        return CleanupOperation(
            id=row["id"],
            operation_uuid=row["operation_uuid"],
            action_type=row["action_type"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            status=row["status"],
            items_count=row["items_count"],
            total_bytes=row["total_bytes"],
            user_confirmed=bool(row["user_confirmed"]),
            error_summary=row["error_summary"]
        )

    def get_quarantine_items_by_operation(self, op_id: int) -> List[QuarantineItem]:
        conn = self.get_connection()
        rows = conn.execute("SELECT * FROM quarantine_items WHERE operation_id = ?", (op_id,)).fetchall()
        return [self._row_to_quarantine_item(r) for r in rows]

    def _row_to_quarantine_item(self, r: sqlite3.Row) -> QuarantineItem:
        return QuarantineItem(
            id=r["id"],
            operation_id=r["operation_id"],
            original_path=r["original_path"],
            quarantine_path=r["quarantine_path"],
            filename=r["filename"],
            size_bytes=r["size_bytes"],
            sha256_hash=r["sha256_hash"],
            original_created_time=r["original_created_time"],
            original_modified_time=r["original_modified_time"],
            quarantined_at=r["quarantined_at"],
            status=r["status"],
            restored_at=r["restored_at"],
            restored_path=r["restored_path"]
        )

    # ----------------- EXCLUSIONS -----------------
    def get_exclusions(self) -> List[ExclusionRule]:
        conn = self.get_connection()
        rows = conn.execute("SELECT * FROM exclusions ORDER BY id ASC").fetchall()
        return [
            ExclusionRule(
                id=r["id"],
                rule_type=r["rule_type"],
                rule_value=r["rule_value"],
                is_enabled=bool(r["is_enabled"]),
                created_at=r["created_at"]
            )
            for r in rows
        ]

    def add_exclusion(self, rule_type: str, rule_value: str, is_enabled: bool = True) -> int:
        conn = self.get_connection()
        with conn:
            cur = conn.execute(
                "INSERT INTO exclusions (rule_type, rule_value, is_enabled, created_at) VALUES (?, ?, ?, ?)",
                (rule_type, rule_value, 1 if is_enabled else 0, datetime.now().isoformat())
            )
            return cur.lastrowid

    def update_exclusion(self, rule_id: int, is_enabled: bool):
        conn = self.get_connection()
        with conn:
            conn.execute("UPDATE exclusions SET is_enabled = ? WHERE id = ?", (1 if is_enabled else 0, rule_id))

    def delete_exclusion(self, rule_id: int):
        conn = self.get_connection()
        with conn:
            conn.execute("DELETE FROM exclusions WHERE id = ?", (rule_id,))

    # ----------------- INTEGRITY CHECKS -----------------
    def log_integrity_check(self, result: IntegrityResult) -> int:
        conn = self.get_connection()
        with conn:
            cur = conn.execute(
                """INSERT INTO integrity_checks (
                    check_uuid, file_id, file_path, reference_hash, observed_hash, status, verified_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    result.check_uuid, result.file_id, result.file_path,
                    result.reference_hash, result.observed_hash, result.status,
                    result.verified_at or datetime.now().isoformat()
                )
            )
            return cur.lastrowid

    def get_integrity_checks(self, limit: int = 100) -> List[IntegrityResult]:
        conn = self.get_connection()
        rows = conn.execute("SELECT * FROM integrity_checks ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [
            IntegrityResult(
                id=r["id"],
                check_uuid=r["check_uuid"],
                file_id=r["file_id"],
                file_path=r["file_path"],
                reference_hash=r["reference_hash"],
                observed_hash=r["observed_hash"],
                status=r["status"],
                verified_at=r["verified_at"]
            )
            for r in rows
        ]

    # ----------------- AUDIT LOGGING -----------------
    def log_audit_event(self, event_type: str, details: Dict[str, Any]):
        conn = self.get_connection()
        with conn:
            conn.execute(
                "INSERT INTO audit_events (event_type, details_json, timestamp) VALUES (?, ?, ?)",
                (event_type, json.dumps(details), datetime.now().isoformat())
            )

    def get_recent_audit_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        rows = conn.execute("SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        events = []
        for r in rows:
            try:
                details = json.loads(r["details_json"])
            except Exception:
                details = {}
            events.append({
                "id": r["id"],
                "event_type": r["event_type"],
                "details": details,
                "timestamp": r["timestamp"]
            })
        return events

    # ----------------- SNAPSHOTS & TRENDS -----------------
    def save_storage_snapshot(self, snapshot: StorageSnapshot) -> int:
        conn = self.get_connection()
        with conn:
            cur = conn.execute(
                """INSERT INTO storage_snapshots (
                    scan_id, snapshot_date, total_files, total_bytes,
                    duplicate_bytes, recoverable_bytes, categories_json, scope_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    snapshot.scan_id, snapshot.snapshot_date or datetime.now().isoformat(),
                    snapshot.total_files, snapshot.total_bytes, snapshot.duplicate_bytes,
                    snapshot.recoverable_bytes, snapshot.categories_json, snapshot.scope_hash
                )
            )
            return cur.lastrowid

    def get_storage_snapshots(self) -> List[StorageSnapshot]:
        conn = self.get_connection()
        rows = conn.execute("SELECT * FROM storage_snapshots ORDER BY id ASC").fetchall()
        return [
            StorageSnapshot(
                id=r["id"],
                scan_id=r["scan_id"],
                snapshot_date=r["snapshot_date"],
                total_files=r["total_files"],
                total_bytes=r["total_bytes"],
                duplicate_bytes=r["duplicate_bytes"],
                recoverable_bytes=r["recoverable_bytes"],
                categories_json=r["categories_json"],
                scope_hash=r["scope_hash"]
            )
            for r in rows
        ]

    # ----------------- SCHEDULED SCANS -----------------
    def get_schedules(self) -> List[ScheduleConfig]:
        conn = self.get_connection()
        rows = conn.execute("SELECT * FROM scheduled_scans ORDER BY id ASC").fetchall()
        schedules = []
        for r in rows:
            try:
                roots = json.loads(r["root_paths"])
            except Exception:
                roots = [r["root_paths"]]
            schedules.append(
                ScheduleConfig(
                    id=r["id"],
                    name=r["name"],
                    root_paths=roots,
                    frequency=r["frequency"],
                    target_time=r["target_time"],
                    enabled=bool(r["enabled"]),
                    last_run=r["last_run"],
                    next_run=r["next_run"],
                    created_at=r["created_at"]
                )
            )
        return schedules

    def add_schedule(self, schedule: ScheduleConfig) -> int:
        conn = self.get_connection()
        with conn:
            cur = conn.execute(
                """INSERT INTO scheduled_scans (
                    name, root_paths, frequency, target_time, enabled, next_run, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    schedule.name, json.dumps(schedule.root_paths), schedule.frequency,
                    schedule.target_time, 1 if schedule.enabled else 0,
                    schedule.next_run, datetime.now().isoformat()
                )
            )
            return cur.lastrowid

    def update_schedule_run(self, schedule_id: int, last_run: str, next_run: str):
        conn = self.get_connection()
        with conn:
            conn.execute(
                "UPDATE scheduled_scans SET last_run = ?, next_run = ? WHERE id = ?",
                (last_run, next_run, schedule_id)
            )

    def toggle_schedule(self, schedule_id: int, enabled: bool):
        conn = self.get_connection()
        with conn:
            conn.execute(
                "UPDATE scheduled_scans SET enabled = ? WHERE id = ?",
                (1 if enabled else 0, schedule_id)
            )

    def delete_schedule(self, schedule_id: int):
        conn = self.get_connection()
        with conn:
            conn.execute("DELETE FROM scheduled_scans WHERE id = ?", (schedule_id,))

    # ----------------- SUMMARY METRICS -----------------
    def get_storage_overview_metrics(self) -> Dict[str, Any]:
        """Aggregate high-level metrics for Overview dashboard from actual DB records."""
        conn = self.get_connection()
        latest_scan = self.get_latest_scan()

        # Quarantined & reclaimed metrics
        reclaimed_row = conn.execute(
            """SELECT COUNT(*) as count, COALESCE(SUM(size_bytes), 0) as total_reclaimed
            FROM quarantine_items WHERE status = 'quarantined'"""
        ).fetchone()

        restored_row = conn.execute(
            """SELECT COUNT(*) as count, COALESCE(SUM(size_bytes), 0) as total_restored
            FROM quarantine_items WHERE status = 'restored'"""
        ).fetchone()

        if latest_scan:
            return {
                "has_scan": True,
                "latest_scan_id": latest_scan.id,
                "latest_scan_name": latest_scan.scan_name,
                "latest_scan_date": latest_scan.completed_at or latest_scan.started_at,
                "total_indexed_files": latest_scan.files_processed,
                "total_indexed_bytes": latest_scan.total_indexed_bytes,
                "duplicate_groups_count": latest_scan.duplicate_groups_count,
                "duplicate_files_count": latest_scan.duplicate_files_count,
                "potential_recoverable_bytes": latest_scan.potential_recoverable_bytes,
                "reclaimed_bytes": reclaimed_row["total_reclaimed"] if reclaimed_row else 0,
                "quarantined_files_count": reclaimed_row["count"] if reclaimed_row else 0,
                "restored_files_count": restored_row["count"] if restored_row else 0,
                "scan_roots": latest_scan.root_paths
            }
        else:
            return {
                "has_scan": False,
                "latest_scan_id": None,
                "latest_scan_name": None,
                "latest_scan_date": None,
                "total_indexed_files": 0,
                "total_indexed_bytes": 0,
                "duplicate_groups_count": 0,
                "duplicate_files_count": 0,
                "potential_recoverable_bytes": 0,
                "reclaimed_bytes": reclaimed_row["total_reclaimed"] if reclaimed_row else 0,
                "quarantined_files_count": reclaimed_row["count"] if reclaimed_row else 0,
                "restored_files_count": restored_row["count"] if restored_row else 0,
                "scan_roots": []
            }
