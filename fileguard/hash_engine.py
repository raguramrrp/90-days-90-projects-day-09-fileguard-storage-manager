"""
Hash Engine for FileGuard.
Computes SHA-256 fingerprints using memory-safe chunked reads, guards against mutations,
and handles Windows long paths and permission restrictions.
"""
import hashlib
import os
import sys
from pathlib import Path
from typing import Optional, Tuple, Callable

from fileguard.config import CHUNK_SIZE_BYTES


class HashEngineError(Exception):
    """Base exception for hashing errors."""
    pass


class FileModifiedDuringHashError(HashEngineError):
    """Raised when file size or modification time changes during hashing."""
    pass


class FileInaccessibleError(HashEngineError):
    """Raised when a file cannot be opened due to permission or lock."""
    pass


def normalize_windows_path(path_str: str) -> str:
    """Handle Windows long paths by prefixing \\?\\ if path exceeds standard limits."""
    abs_path = os.path.abspath(path_str)
    if sys.platform.startswith("win") and len(abs_path) >= 256 and not abs_path.startswith("\\\\?\\"):
        return f"\\\\?\\{abs_path}"
    return abs_path


def compute_sha256(
    file_path: str,
    chunk_size: int = CHUNK_SIZE_BYTES,
    cancel_check: Optional[Callable[[], bool]] = None
) -> Tuple[str, int]:
    """
    Calculate the SHA-256 hash of a file using chunked reads.
    Returns (hex_digest, total_bytes_read).
    Raises FileNotFoundError, FileInaccessibleError, FileModifiedDuringHashError, or InterruptedError.
    """
    safe_path = normalize_windows_path(file_path)

    try:
        stat_before = os.stat(safe_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except PermissionError:
        raise FileInaccessibleError(f"Permission denied: {file_path}")
    except OSError as e:
        raise FileInaccessibleError(f"OS error accessing file {file_path}: {e}")

    hasher = hashlib.sha256()
    bytes_read = 0

    try:
        with open(safe_path, "rb") as f:
            while True:
                if cancel_check and cancel_check():
                    raise InterruptedError("Hashing cancelled by user.")
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
                bytes_read += len(chunk)
    except PermissionError:
        raise FileInaccessibleError(f"Permission denied while reading: {file_path}")
    except OSError as e:
        raise FileInaccessibleError(f"I/O error while reading {file_path}: {e}")

    # Re-verify file was not modified while we were reading it
    try:
        stat_after = os.stat(safe_path)
        if stat_before.st_size != stat_after.st_size:
            raise FileModifiedDuringHashError(
                f"File size changed during hashing ({stat_before.st_size} -> {stat_after.st_size}): {file_path}"
            )
        if stat_before.st_mtime != stat_after.st_mtime:
            # File modified time changed during read
            raise FileModifiedDuringHashError(
                f"File timestamp modified during hashing: {file_path}"
            )
    except OSError as e:
        if isinstance(e, FileModifiedDuringHashError):
            raise
        raise FileInaccessibleError(f"File disappeared after hashing: {file_path}")

    return hasher.hexdigest(), bytes_read


def compute_quick_hash(file_path: str, quick_bytes: int = 4096) -> Optional[str]:
    """
    Calculate SHA-256 for only the first `quick_bytes` of a file.
    Used for fast initial collision pruning among files of the same size.
    """
    safe_path = normalize_windows_path(file_path)
    try:
        hasher = hashlib.sha256()
        with open(safe_path, "rb") as f:
            chunk = f.read(quick_bytes)
            hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None


def verify_file_hash(file_path: str, expected_hash: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Recalculate hash and verify against expected hash.
    Returns: (is_match, observed_hash, error_message).
    """
    try:
        observed_hash, _ = compute_sha256(file_path)
        return (observed_hash.lower() == expected_hash.lower(), observed_hash, None)
    except FileNotFoundError:
        return (False, None, "File not found")
    except FileInaccessibleError as e:
        return (False, None, str(e))
    except FileModifiedDuringHashError as e:
        return (False, None, str(e))
    except Exception as e:
        return (False, None, f"Verification failed: {e}")
