"""
Configuration and constants for FileGuard.
Handles paths, protected locations, file categories, and default policies.
"""
import os
import sys
from pathlib import Path

# Base Directories
APP_DIR = Path(__file__).resolve().parent.parent

# Default local project data directory (safe inside workspace)
DEFAULT_DATA_DIR = APP_DIR / "data"
DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Allow environment override or project data dir
DATA_DIR = Path(os.environ.get("FILEGUARD_DATA_DIR", str(DEFAULT_DATA_DIR)))

# Default Database Path and Quarantine Directory
DEFAULT_DB_PATH = DATA_DIR / "fileguard.db"
DEFAULT_QUARANTINE_DIR = DATA_DIR / "quarantine"
DEFAULT_REPORTS_DIR = DATA_DIR / "reports"

DEFAULT_QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Allow environment override
DB_PATH = Path(os.environ.get("FILEGUARD_DB_PATH", str(DEFAULT_DB_PATH)))
QUARANTINE_DIR = Path(os.environ.get("FILEGUARD_QUARANTINE_DIR", str(DEFAULT_QUARANTINE_DIR)))
REPORTS_DIR = DEFAULT_REPORTS_DIR

# Performance & Hashing Parameters
CHUNK_SIZE_BYTES = int(os.environ.get("FILEGUARD_CHUNK_SIZE_KB", "64")) * 1024  # 64 KB
LARGE_FILE_THRESHOLD_BYTES = int(os.environ.get("FILEGUARD_LARGE_FILE_THRESHOLD_MB", "10")) * 1024 * 1024  # 10 MB

# Built-in Protected Paths (Windows and Unix)
# These paths are protected from destructive cleanup and warned during scanning.
WINDOWS_PROTECTED_PATHS = [
    os.environ.get("SystemRoot", "C:\\Windows").lower(),
    os.environ.get("ProgramFiles", "C:\\Program Files").lower(),
    os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)").lower(),
    os.environ.get("ProgramData", "C:\\ProgramData").lower(),
    "c:\\windows",
    "c:\\program files",
    "c:\\program files (x86)",
    "c:\\programdata",
    "c:\\recovery",
    "c:\\$recycle.bin",
    "c:\\system volume information",
    "c:\\boot",
    "c:\\msocache",
]

# File Categories by Extension
FILE_CATEGORIES = {
    "Images": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".svg", ".ico", ".raw", ".heic"],
    "Documents": [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt", ".csv", ".tsv", ".md", ".rtf", ".odt", ".ods", ".odp"],
    "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".alac", ".aiff"],
    "Video": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".3gp"],
    "Archives": [".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz", ".iso", ".tgz"],
    "Code": [".py", ".js", ".ts", ".html", ".htm", ".css", ".json", ".sql", ".java", ".cpp", ".c", ".h", ".cs", ".rs", ".go", ".php", ".sh", ".bat", ".ps1", ".xml", ".yaml", ".yml"],
    "Executables": [".exe", ".msi", ".dll", ".sys", ".drv", ".bin", ".com"],
}

# Default Excluded Directory Names
DEFAULT_EXCLUDED_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", ".pytest_cache", ".venv", "venv", "env",
    "node_modules", ".idea", ".vscode", "$Recycle.Bin", "System Volume Information"
}

# Default Excluded Extensions (typically system binaries or dynamic linkers that shouldn't be touched)
DEFAULT_EXCLUDED_EXTS = {".sys", ".dll", ".drv", ".lnk"}

# Temporary File Candidates Extensions and Patterns
TEMP_EXTENSIONS = {".tmp", ".temp", ".bak", ".old", ".dmp", ".swp"}
TEMP_PATTERNS = ["*~", "~*", "*.tmp", "*.temp", "*.bak", "*.old"]


def categorize_file(extension: str) -> str:
    """Return the high-level category for a given file extension."""
    if not extension:
        return "Other"
    ext = extension.lower()
    if not ext.startswith("."):
        ext = "." + ext
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    return "Other"


def is_path_protected(file_or_dir_path: str) -> bool:
    """Check if a path falls within a protected system directory."""
    try:
        norm_path = os.path.abspath(file_or_dir_path).lower()
        for protected in WINDOWS_PROTECTED_PATHS:
            if not protected:
                continue
            if norm_path == protected or norm_path.startswith(protected.rstrip("\\/") + "\\") or norm_path.startswith(protected.rstrip("\\/") + "/"):
                return True
        # Check system special folder names
        parts = [p.lower() for p in Path(norm_path).parts]
        if "windows" in parts or "system volume information" in parts or "$recycle.bin" in parts:
            return True
        return False
    except Exception:
        return True  # If check fails, fail-safe to protected
