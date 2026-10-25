# FileGuard — Intelligent Duplicate File Detection & Storage Manager

![FileGuard](https://img.shields.io/badge/Project-Day%209%20of%2090%20Days%20Challenge-0d9488?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Tested%20%26%20Production%20Ready-10b981?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10%2B%20%7C%203.14-blue?style=for-the-badge&logo=python)
![Architecture](https://img.shields.io/badge/GUI-Tkinter%2Fttk%20%2B%20SQLite%20WAL-teal?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-gray?style=for-the-badge)

> **FileGuard** is a high-reliability Windows desktop utility engineered to detect exact content duplicates, analyze disk-space consumption, monitor storage trends, safely quarantine redundant copies, restore files with conflict resolution, and verify cryptographic data integrity.

---

## 📑 Table of Contents
1. [Problem Statement & Motivation](#-problem-statement--motivation)
2. [Key Features by Priority](#-key-features-by-priority)
3. [Safety & Disaster Recovery Architecture](#-safety--disaster-recovery-architecture)
4. [Screenshots & UI Walkthrough](#-screenshots--ui-walkthrough)
5. [Technology Stack](#-technology-stack)
6. [Project Structure](#-project-structure)
7. [Prerequisites & System Requirements](#-prerequisites--system-requirements)
8. [Windows Installation & Setup](#-windows-installation--setup)
9. [Running Automated Tests](#-running-automated-tests)
10. [Demonstration & Sample Data](#-demonstration--sample-data)
11. [Keyboard Shortcuts](#-keyboard-shortcuts)
12. [Reports & Audit Compliance](#-reports--audit-compliance)
13. [Security & Privacy Considerations](#-security--privacy-considerations)
14. [Known Limitations & Future Roadmap](#-known-limitations--future-roadmap)
15. [Resume Keywords & Technical Competencies](#-resume-keywords--technical-competencies)
16. [License & Author](#-license--author)

---

## 🎯 Problem Statement & Motivation
Everyday Windows users, developers, media editors, and data science students continuously accumulate duplicate files across download folders, project archives, email attachments, and backup drives. Typical cleanup tools suffer from critical drawbacks:
- **Black-box, Destructive Deletion:** Many utilities erase files directly, offering no recovery when critical documents are accidentally removed.
- **Unreliable Metadata Matching:** Filename, folder, or date-based matching causes false positives (different versions sharing the same filename) or false negatives (identical files renamed `report (1).pdf`).
- **UI Freezing & Memory Exhaustion:** Inefficient hashing reads entire multi-gigabyte files into RAM simultaneously, crashing the application.
- **Nested Folder Double-Counting:** Naive storage analyzers count child folder sizes multiple times when reporting parent directories.

**FileGuard** eliminates these hazards by combining memory-safe chunked SHA-256 cryptographic fingerprints, a multi-stage candidate pruning funnel, an explainable Selection Advisor, and a 100% reversible quarantine architecture with 1-click undo.

---

## 🚀 Key Features by Priority

### Priority 1 — Essential MVP (Fully Implemented & Verified)
- **Deterministic Exact Duplicate Detection:** Calculates SHA-256 content digests using 64 KB memory-safe chunked reads. Never relies on filename or timestamps alone.
- **Multi-Stage Candidate Pruning:**
  1. *Stage 1:* Exact size clustering (unique sizes are never hashed).
  2. *Stage 2:* 4 KB quick-hash pre-filtering for candidate collisions.
  3. *Stage 3:* Full chunked SHA-256 calculation for candidate collisions.
- **Theoretical Savings Calculation:** Accurately computes maximum recoverable space for $N$ identical files of size $S$:
  $$\text{Theoretical Savings} = (N - 1) \times S$$
- **Explainable Selection Advisor:** Scores and recommends which duplicate copy to retain based on directory hygiene (e.g. prioritizing structured `Documents` folders over `Downloads`/`Temp`) and filename patterns (`(1)`, `copy`).
- **Retained-Copy Safety Enforcement:** Hard safety guard blocks cleanup if all copies in a duplicate group are selected. At least one verified copy must stay outside quarantine.
- **Reversible Quarantine & 1-Click Undo (`Ctrl+Z`):** Cleaned files are moved to isolated quarantine storage with UUID prefixing, hash verification, and instant restoration.
- **Destination Conflict Protection:** Never silently overwrites existing destination files during restoration.
- **Large-File Finder:** Configurable minimum size thresholds (`1 MB` to `500 MB`), sortable table, and native Windows File Explorer revelation.
- **Custom Premium Desktop UI:** Hand-crafted, distraction-free visual design with Teal accents (`#0d9488` / `#14b8a6`) and switchable Light/Dark modes.
- **Local SQLite Persistence:** Complete audit trail of scans, duplicates, quarantine actions, and errors in WAL mode.

### Priority 2 — Everyday-Use Upgrades (Fully Implemented)
- **In-App Background Scan Scheduler:** Recurring daily, weekly, or monthly scheduled scans with next-run calculations. *Strict Safety Rule: Scheduled jobs only scan and report; they NEVER trigger automatic cleanup.*
- **Cryptographic File Integrity Verification:** Recalculates SHA-256 fingerprints of indexed files against baseline records to detect bit rot, corruption, modifications, or missing files.
- **Empty Folder Discovery:** Identifies directory trees with zero files and zero subdirectories, while distinguishing genuinely empty folders from permission-restricted folders.
- **Temporary File Candidate Analysis:** Rule-based detection of `.tmp`, `.bak`, `~*`, and `.old` files with age thresholds and preview prior to quarantine.
- **Historical Scan Comparison & Deltas:** Diffs any two completed scans to track newly emerged and resolved duplicate groups, complete with scope comparability warnings.
- **Storage Intelligence & Drive Metrics:** Accurate folder-size calculation without nested double-counting, file-type category distribution, and live disk space metrics.

### Priority 3 — Advanced Capabilities (Fully Implemented)
- **Visual Similar-Photo Discovery (dHash):** Computes 64-bit difference hashes and Hamming distance metrics using Pillow to identify visually similar photos across different sizes or compressions.
- **Side-by-Side Photo Comparison:** Side-by-side thumbnail previews, resolutions, and similarity percentages (75%–95%). Strictly kept distinct from exact SHA-256 duplicates.
- **Standalone Windows Executable Packaging:** PyInstaller specification file (`FileGuard.spec`) and automated packaging batch script (`build_exe.bat`).

---

## 🛡️ Safety & Disaster Recovery Architecture

```
[User Selects Duplicates] ➔ [Retained-Copy Verification]
                                     │
               ┌─────────────────────┴─────────────────────┐
               ▼                                           ▼
      [Violation Detected]                        [Safety Validation Passed]
(All copies in group selected              (At least 1 copy preserved on disk)
  or system path targeted)                                 │
               │                                           ▼
      🛑 ACTION BLOCKED                           [Cleanup Preview Dialog]
(Clear explanatory alert)                         (Shows paths, sizes, retained copy)
                                                           │
                                                           ▼ (User Confirms)
                                                  [Quarantine Manager]
                                                  1. Copy to quarantine with UUID
                                                  2. Verify SHA-256 of quarantined copy
                                                  3. Delete source only after verification
                                                           │
                                                           ▼
                                                  [Quarantine Storage]
                                                  • 1-Click Undo (Ctrl+Z)
                                                  • Restore to Original or Alternate
                                                  • Collision-Safe Auto-Suffixing
```

---

## 🖼️ Screenshots & UI Walkthrough

All screenshots should be placed in `screenshots/` directory:
- `screenshots/overview_dashboard.png`: Executive KPI storage dashboard showing indexed bytes, duplicate groups, and audit history.
- `screenshots/duplicate_review.png`: Explorer-style duplicate treeview with Selection Advisor recommendations and resizable preview pane.
- `screenshots/cleanup_preview_modal.png`: Safety cleanup preview modal showing candidate files, retained copies, and confirmation prompt.
- `screenshots/large_files.png`: Storage-heavy files filtered by size with native Explorer integration.
- `screenshots/similar_photos.png`: Side-by-side perceptual difference hashing comparison.

---

## 💻 Technology Stack

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ / 3.14 | Modern, memory-efficient standard library support. |
| **GUI Framework** | Tkinter & `ttk` | Native Windows desktop controls, lightweight, zero bloat. |
| **Database** | SQLite 3 (`WAL` mode) | Atomic transactions, foreign keys, local file persistence. |
| **Exact Hashing** | `hashlib.sha256()` | Industry-standard 256-bit cryptographic digest with 64 KB chunking. |
| **Perceptual Hashing** | Pillow (`PIL`) | 64-bit difference hashing (`dHash`) and Hamming distance. |
| **Concurrency** | `threading` + `queue.Queue` | Keeps the desktop GUI responsive during heavy I/O operations. |
| **Testing** | `pytest` + `pytest-cov` | Automated test runner with temporary sandboxes and fixtures. |
| **Reporting** | Standalone HTML & CSV | Self-contained, responsive CSS styling and CSV escaping. |
| **Packaging** | PyInstaller | Standalone Windows `.exe` distribution. |

---

## 📂 Project Structure

```text
90-days-90-projects-day-09-fileguard-storage-manager/
├── app.py                          # Desktop application entry point
├── README.md                       # Master documentation and portfolio showcase
├── QUICKSTART.md                   # 2-minute quickstart guide
├── DEMO_SCRIPT.md                  # 90-second structured presentation script
├── LICENSE                         # MIT License
├── requirements.txt                # Pinned dependency manifest
├── pyproject.toml                  # Project packaging and pytest configuration
├── setup.bat                       # Automated 1-click Windows setup
├── run.bat                         # Automated 1-click application runner
├── test.bat                        # Automated 1-click test suite runner
├── build_exe.bat                   # Standalone Windows executable packaging script
├── FileGuard.spec                  # PyInstaller executable bundling specification
├── .gitignore                      # Git exclusion rules
├── .env.example                    # Environment variable template
├── docs/                           # Engineering and technical documentation
│   ├── PROJECT_OVERVIEW.md         # Problem statement, scope, and objectives
│   ├── ARCHITECTURE.md             # System architecture and Mermaid diagrams
│   ├── USER_GUIDE.md               # Feature-by-feature user manual
│   ├── DEVELOPMENT_NOTES.md        # Engineering decisions and trade-offs
│   ├── TESTING.md                  # Comprehensive test matrix and QA report
│   └── TROUBLESHOOTING.md          # Locked files, permissions, and long paths
├── data/
│   ├── README.md                   # Dataset schema and generation instructions
│   └── sample_files/               # Synthetic test files for immediate demo
├── scripts/
│   └── create_sample_data.py       # Script to generate realistic test files
├── fileguard/                      # Core application package
│   ├── __init__.py
│   ├── config.py                   # Paths, protected locations, categories, thresholds
│   ├── database.py                 # SQLite schema, queries, WAL mode, migrations
│   ├── models.py                   # Dataclasses (FileRecord, DuplicateGroup, etc.)
│   ├── hash_engine.py              # Chunked SHA-256 reads and path normalization
│   ├── perceptual_hash.py          # 64-bit dHash and Hamming distance calculations
│   ├── duplicate_detector.py       # 4-stage duplicate detection algorithm
│   ├── selection_advisor.py        # Rule-based copy recommendation engine
│   ├── scanner.py                  # Multi-root traversal and cancellation
│   ├── storage_analyzer.py         # Nested folder calculation without double-counting
│   ├── large_file_finder.py        # Storage-heavy file identification and filtering
│   ├── folder_analyzer.py          # Genuinely empty directory discovery
│   ├── temporary_file_analyzer.py  # Rule-based temporary candidate identification
│   ├── cleanup_manager.py          # Preview preparation and retained-copy guards
│   ├── quarantine_manager.py       # Collision-safe storage and atomic rollbacks
│   ├── restore_manager.py          # Single/bulk restore and 1-click undo (Ctrl+Z)
│   ├── exclusion_manager.py        # Exclusions evaluation and system protection
│   ├── integrity_checker.py        # Cryptographic baseline verification
│   ├── history_manager.py          # Historical scan diffs and change tracking
│   ├── trend_analyzer.py           # Multi-scan timeline trend analysis
│   ├── scheduler.py                # In-app background scan scheduler
│   ├── report_generator.py         # Standalone HTML and CSV report generation
│   ├── workers.py                  # Background thread dispatcher to Tkinter queue
│   └── ui/                         # Desktop user interface
│       ├── __init__.py
│       ├── theme.py                # Teal palettes and ttk style definitions (Light/Dark)
│       ├── components.py           # Stat cards, search bar, preview pane, thumbnails
│       ├── navigation.py           # Sidebar navigation with active indicators
│       ├── dialogs.py              # Cleanup preview modal, exclusion and schedule modals
│       ├── main_window.py          # Main window assembly, shortcuts, page routing
│       └── pages/                  # Modular view screens
│           ├── __init__.py
│           ├── overview_page.py
│           ├── scan_page.py
│           ├── duplicates_page.py
│           ├── large_files_page.py
│           ├── storage_page.py
│           ├── folder_temp_page.py
│           ├── quarantine_page.py
│           ├── history_page.py
│           ├── integrity_page.py
│           ├── reports_page.py
│           ├── schedule_page.py
│           ├── similar_photos_page.py
│           └── settings_page.py
└── tests/                          # Automated Pytest suite (38 tests)
    ├── __init__.py
    ├── conftest.py
    ├── test_hash_engine.py
    ├── test_duplicate_detector.py
    ├── test_scanner.py
    ├── test_selection_advisor.py
    ├── test_storage_analyzer.py
    ├── test_cleanup_quarantine_restore.py
    ├── test_exclusions.py
    ├── test_integrity_checker.py
    ├── test_folder_temp_analyzer.py
    ├── test_scheduler.py
    ├── test_history_and_trends.py
    ├── test_database.py
    ├── test_reports.py
    └── test_perceptual_hash.py
```

---

## ⚙️ Prerequisites & System Requirements
- **Operating System:** Windows 10 or Windows 11 (64-bit recommended). Also compatible with macOS and Linux.
- **Python Version:** Python 3.10, 3.11, 3.12, 3.13, or 3.14.
- **Hardware:** Minimum 2 GB RAM, 100 MB free disk space.
- **Privileges:** Standard user privileges (does NOT require Administrator access).

---

## 🚀 Windows Installation & Setup

### Automated 1-Click Setup
Simply double-click `setup.bat`. The script automatically checks Python, initializes `.venv`, installs requirements, generates sample test files, and initializes the local SQLite database.

### Manual Setup via PowerShell
```powershell
# 1. Clone or navigate to the repository
cd "90-days-90-projects-day-09-fileguard-storage-manager"

# 2. Create isolated virtual environment
py -m venv .venv

# 3. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 4. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 5. Generate sample demonstration data
python scripts\create_sample_data.py

# 6. Launch FileGuard Desktop Application
python app.py
```

---

## 🧪 Running Automated Tests

Run the complete 38-test automated suite using `test.bat` or pytest:

```powershell
.\test.bat
# or directly:
.\.venv\Scripts\pytest.exe -v
```

### Actual Test Status:
```text
============================= 38 passed in 0.82s ==============================
Status: PASS (38/38 Tests Passed — 100% Pass Rate)
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Context | Function |
| :--- | :--- | :--- |
| `Ctrl+O` | Global | Open directory dialog to add scan roots |
| `Ctrl+F` | Duplicates / Large Files | Focus search & filter bar |
| `F5` | Global | Rescan or refresh active workspace view |
| `Esc` | Global | Clear active search query or dismiss modal |
| `Ctrl+E` | Global | Navigate directly to Reports & Export tab |
| `Ctrl+Z` | Global | Undo the last eligible quarantine cleanup operation |

---

## 🔒 Security & Privacy Considerations
1. **100% Offline Utility:** FileGuard performs all hashing, analysis, and persistence locally. It never transmits file paths, names, hashes, or contents over the network.
2. **Protected Windows Locations:** Critical operating system locations (`C:\Windows`, `C:\Program Files`, `System Volume Information`, etc.) are protected from destructive cleanup.
3. **No Silent Overwrites:** Destructive file actions require explicit user confirmation. Restoration conflicts default to safe non-colliding suffixes.
4. **No Administrator Required:** Operates strictly within user-accessible folder permissions.

---

## 🛣️ Known Limitations & Future Roadmap
- **Cross-Volume Move Performance:** Moving files between separate physical drive partitions (e.g. `C:\` to `D:\`) requires a copy-verify-delete sequence rather than an instantaneous directory rename.
- **Future: Perceptual Video Hashing:** Extend perceptual hashing to video keyframes for near-duplicate video clips.
- **Future: Cloud Storage Mount Auditing:** Add specific cloud metadata tags for OneDrive and Google Drive placeholder files (`FILE_ATTRIBUTE_REPARSE_POINT`).

---

## 📄 License & Attribution
Distributed under the **MIT License**. Created by **Raguram Ram P** as part of the **90 Days – 90 Projects Challenge**.
