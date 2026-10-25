# FileGuard — Troubleshooting Guide

Common issues, Windows filesystem anomalies, and recommended remediation steps.

---

## 1. Locked Files & Access Denied (`PermissionError`)
- **Symptom:** During scanning or quarantine, a file is marked with an error: `Permission denied while reading` or `Access is denied`.
- **Cause:** Another active Windows process (e.g., Microsoft Word, Outlook, anti-virus scanner, or active database) holds an exclusive locking handle on the file.
- **Resolution:**
  - Close the application locking the file.
  - FileGuard's safe exception handling skips locked files automatically and continues scanning unrelated folders without crashing.

---

## 2. Windows Long Paths (> 260 Characters)
- **Symptom:** Operations on deeply nested directories report `FileNotFoundError` or path truncation.
- **Resolution:**
  - FileGuard includes built-in `normalize_windows_path()` that automatically prefixes Windows extended-length path format `\\?\` for paths approaching or exceeding 260 characters.
  - You can also enable Windows Win32 Long Paths in the Windows Registry:
    `HKLM\SYSTEM\CurrentControlSet\Control\FileSystem\LongPathsEnabled = 1`.

---

## 3. High CPU Usage During Scanning
- **Symptom:** CPU usage rises during Stage 3 (SHA-256 computation).
- **Cause:** Computing 256-bit cryptographic digests on hundreds of candidate collisions requires cryptographic hashing calculations.
- **Resolution:**
  - FileGuard limits full hashing only to files that have already collided on both file size and initial 4 KB quick-hash chunks.
  - Unique-sized files are never hashed during normal deduplication scans.
  - You can cancel the scan at any time; progress and indexed entries are saved safely.

---

## 4. Cannot Restore a File Because Destination Already Exists
- **Symptom:** A file was quarantined, and another file with the same name was created at the original location before restoration.
- **Resolution:**
  - FileGuard's conflict resolver prevents silent data loss by creating a collision-free filename suffixed with `_restored` (e.g., `Report_restored.pdf`).
  - Alternatively, select *Restore to Alternate Folder...* to choose an explicit directory.
