"""
Data models for FileGuard.
Defines strongly typed representations of files, duplicate groups, scans, and operations.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class FileRecord:
    id: Optional[int] = None
    scan_id: Optional[int] = None
    path: str = ""
    filename: str = ""
    size_bytes: int = 0
    extension: str = ""
    category: str = "Other"
    created_time: Optional[float] = None
    modified_time: Optional[float] = None
    last_scanned_time: Optional[float] = None
    sha256_hash: Optional[str] = None
    hash_status: str = "pending"  # pending, verified, failed, stale
    is_available: bool = True
    duplicate_group_id: Optional[int] = None

    @property
    def formatted_size(self) -> str:
        return format_bytes(self.size_bytes)

    @property
    def formatted_modified(self) -> str:
        if not self.modified_time:
            return "Unknown"
        try:
            return datetime.fromtimestamp(self.modified_time).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            return "Invalid Date"


@dataclass
class DuplicateGroup:
    id: Optional[int] = None
    group_key: str = ""
    sha256_hash: str = ""
    size_bytes: int = 0
    file_count: int = 0
    total_size_bytes: int = 0
    max_recoverable_bytes: int = 0  # (N - 1) * S
    created_at: Optional[str] = None
    members: List[FileRecord] = field(default_factory=list)
    suggested_retained_file_id: Optional[int] = None
    suggestion_reasons: Dict[int, str] = field(default_factory=dict)

    @property
    def formatted_copy_size(self) -> str:
        return format_bytes(self.size_bytes)

    @property
    def formatted_total_size(self) -> str:
        return format_bytes(self.total_size_bytes)

    @property
    def formatted_max_recoverable(self) -> str:
        return format_bytes(self.max_recoverable_bytes)


@dataclass
class ScanRecord:
    id: Optional[int] = None
    scan_name: str = ""
    root_paths: List[str] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    status: str = "running"  # running, completed, cancelled, failed
    files_discovered: int = 0
    files_processed: int = 0
    files_hashed: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    duplicate_groups_count: int = 0
    duplicate_files_count: int = 0
    total_indexed_bytes: int = 0
    potential_recoverable_bytes: int = 0
    error_summary: Optional[str] = None

    @property
    def formatted_indexed_size(self) -> str:
        return format_bytes(self.total_indexed_bytes)

    @property
    def formatted_recoverable_size(self) -> str:
        return format_bytes(self.potential_recoverable_bytes)


@dataclass
class CleanupOperation:
    id: Optional[int] = None
    operation_uuid: str = ""
    action_type: str = "quarantine"  # quarantine, undo_quarantine, permanent_delete
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    status: str = "completed"  # completed, failed, partial, undone
    items_count: int = 0
    total_bytes: int = 0
    user_confirmed: bool = True
    error_summary: Optional[str] = None

    @property
    def formatted_bytes(self) -> str:
        return format_bytes(self.total_bytes)


@dataclass
class QuarantineItem:
    id: Optional[int] = None
    operation_id: Optional[int] = None
    original_path: str = ""
    quarantine_path: str = ""
    filename: str = ""
    size_bytes: int = 0
    sha256_hash: str = ""
    original_created_time: Optional[float] = None
    original_modified_time: Optional[float] = None
    quarantined_at: Optional[str] = None
    status: str = "quarantined"  # quarantined, restored, deleted
    restored_at: Optional[str] = None
    restored_path: Optional[str] = None

    @property
    def formatted_size(self) -> str:
        return format_bytes(self.size_bytes)


@dataclass
class ExclusionRule:
    id: Optional[int] = None
    rule_type: str = "directory"  # directory, extension, min_size, max_size, pattern
    rule_value: str = ""
    is_enabled: bool = True
    created_at: Optional[str] = None


@dataclass
class IntegrityResult:
    id: Optional[int] = None
    check_uuid: str = ""
    file_id: Optional[int] = None
    file_path: str = ""
    reference_hash: str = ""
    observed_hash: Optional[str] = None
    status: str = "unchanged"  # unchanged, modified, missing, inaccessible
    verified_at: Optional[str] = None


@dataclass
class ScheduleConfig:
    id: Optional[int] = None
    name: str = ""
    root_paths: List[str] = field(default_factory=list)
    frequency: str = "daily"  # daily, weekly, monthly
    target_time: str = "09:00"  # HH:MM
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class StorageSnapshot:
    id: Optional[int] = None
    scan_id: Optional[int] = None
    snapshot_date: str = ""
    total_files: int = 0
    total_bytes: int = 0
    duplicate_bytes: int = 0
    recoverable_bytes: int = 0
    categories_json: str = "{}"
    scope_hash: str = ""


@dataclass
class SimilarImagePair:
    file_a: FileRecord
    file_b: FileRecord
    similarity_percent: float
    hamming_distance: int
    hash_a: str
    hash_b: str


def format_bytes(bytes_count: int) -> str:
    """Format bytes into human-readable B, KB, MB, GB, TB with 2 decimal precision."""
    if bytes_count < 0:
        return "0 B"
    if bytes_count < 1024:
        return f"{bytes_count} B"
    elif bytes_count < 1024 ** 2:
        return f"{bytes_count / 1024:.2f} KB"
    elif bytes_count < 1024 ** 3:
        return f"{bytes_count / (1024 ** 2):.2f} MB"
    elif bytes_count < 1024 ** 4:
        return f"{bytes_count / (1024 ** 3):.2f} GB"
    else:
        return f"{bytes_count / (1024 ** 4):.2f} TB"
