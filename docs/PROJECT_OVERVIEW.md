# FileGuard — Project Overview

## 1. Problem Statement
Everyday Windows users, developers, media creators, and data analysts accumulate redundant copies of downloads, project archives, financial reports, photos, and temporary build caches. Over time, storage degrades, backup times multiply, and locating canonical versions becomes difficult. 

Most conventional cleanup tools suffer from serious flaws:
- They use opaque "black-box" deletion that permanently deletes user files without clear explanations.
- They rely purely on filename or modification dates, causing false positives or missing identical files with different names.
- They freeze the user interface while computing file hashes.
- They lack reversible recovery mechanisms, causing catastrophic accidental data loss.

## 2. Project Goals & Objectives
**FileGuard** is designed as a dependable, production-grade everyday Windows desktop utility:
1. **Deterministic Exact Duplicate Detection:** Cryptographically verify exact duplicates using memory-safe chunked SHA-256 fingerprints, combined with multi-stage size and quick-hash candidate pruning.
2. **Safety-First Recovery Architecture:** Cleanups default to reversible quarantine with collision-safe filenames, timestamp preservation, and 1-click undo (`Ctrl+Z`).
3. **Retained-Copy Enforcement:** Prevent accidental data loss by blocking any operation where all copies in a duplicate group are selected. At least one verified copy must remain outside quarantine.
4. **Transparent Selection Advisor:** Provide explainable, rule-based suggestions on which copy to retain and which copies to quarantine based on directory structure, user preferences, and filename hygiene.
5. **Storage Intelligence:** Deliver non-double-counted nested directory aggregations, category breakdowns, large file discovery, and drive capacity metrics.
6. **Integrity & Visual Auditing:** Provide standalone cryptographic file integrity verification and perceptual difference hashing (dHash) for near-duplicate photos.

## 3. Product Scope & Priority Breakdown

### Priority 1 — Essential MVP (Complete)
- Multi-root directory scanning with background worker threads and cancellation.
- Memory-safe chunked SHA-256 hashing (64 KB chunks).
- Candidate pre-filtering by size and partial hashing.
- Grouping by exact content with theoretical maximum savings: `(N - 1) * S`.
- Explainable Selection Advisor.
- Reversible quarantine with UUID prefixing, SHA-256 re-validation, and cross-volume atomic safety.
- Single and bulk restore, destination conflict prevention, and 1-click undo (`Ctrl+Z`).
- Large-file finder with configurable size thresholds and native Windows Explorer integration.
- Protected Windows system location restrictions (`C:\Windows`, `Program Files`, etc.).
- Custom premium UI with Teal accents and switchable Light/Dark themes.

### Priority 2 — Everyday-Use Upgrades (Complete)
- In-app background scan scheduler (Daily, Weekly, Monthly) with strict no-auto-clean safety guarantees.
- Cryptographic file integrity verification comparing disk contents against baseline DB hashes.
- Genuinely empty directory analysis distinguishing empty from inaccessible folders.
- Rule-based temporary file candidate analysis (`.tmp`, `.bak`, `~*`, `.old`).
- Scan history browsing and historical scan comparison with scope comparability warnings.
- Standalone responsive HTML and CSV audit reporting.

### Priority 3 — Advanced Capabilities (Complete)
- Visual near-duplicate image detection using 64-bit difference hashing (dHash) and Hamming distance metrics.
- Side-by-side thumbnail comparison with configurable similarity thresholds (75%–95%).
- Standalone Windows executable packaging via PyInstaller (`FileGuard.spec` and `build_exe.bat`).
