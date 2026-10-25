# FileGuard — Development Notes & Engineering Decisions

## 1. Technology Selection & Rationale
- **Python 3.10+ & Tkinter/ttk:** Chosen to deliver a lightweight, offline-first Windows utility without the memory footprint of Electron or browser engines.
- **SQLite (WAL Mode):** Embedded relational database providing indexed lookups, atomic multi-statement transactions, and persistence across sessions without requiring external database servers or services.
- **hashlib.sha256() with Chunked Reads:** Large files are read in 64 KB chunks (`CHUNK_SIZE_BYTES = 65536`). This ensures steady memory consumption even when inspecting multi-gigabyte disk images or video files.
- **Thread-Safe Architecture:** Scanning, hashing, and integrity checking execute on Python background worker threads. Results and progress updates are dispatched to the UI thread via `queue.Queue` polled through Tkinter's `root.after()`.

---

## 2. Safety & Disaster Recovery Design
Accidental file deletion is the primary failure mode of storage managers. FileGuard addresses this through multiple defensive layers:

1. **Reversible Quarantine as Default Action:** Files are never unlinked directly during cleanup. They are copied with metadata (`shutil.copy2`) to quarantine with collision-safe names (`q_<uuid8>_<filename>`), verified by SHA-256 hash match, and only then removed from the original location.
2. **Atomic Rollback on Copy Failure:** If disk write fails or the quarantined file hash does not match the source hash, FileGuard removes the quarantine artifact and leaves the source file completely untouched.
3. **Retained-Copy Protection:** If a user selects all copies of a duplicate group (or an automated script attempts to do so), `CleanupManager.prepare_cleanup_preview()` blocks the action and flags a critical safety error. At least one verified copy must stay outside quarantine.
4. **Permanent Deletion Isolation:** Permanent deletion is isolated inside the Quarantine tab behind an explicit modal dialog. It is strictly excluded from general cleanup routines, scheduled scans, and keyboard shortcuts.
5. **Collision-Safe Restoration:** If a file of the same name was created at the original path while the original was in quarantine, FileGuard automatically suffixes the restored file with `_restored` rather than silently overwriting disk data.

---

## 3. UI/UX Decisions
- **Restrained Teal Accent:** `#0d9488` (Light) and `#14b8a6` (Dark) provide visual clarity without distracting neon glows or generic dashboard templates.
- **Hybrid Dashboard & Explorer:** The Overview tab gives an executive KPI summary, while the Duplicate Review and Large Files tabs provide standard Windows Explorer-style treeviews with resizable panels (`ttk.PanedWindow`).
- **Real Database Values:** Empty states are displayed cleanly on initial run; no mock, hard-coded, or fake values are shown.
