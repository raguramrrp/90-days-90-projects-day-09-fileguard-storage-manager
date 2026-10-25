# FileGuard Quickstart Guide

Get up and running with **FileGuard — Intelligent Duplicate File Detection & Storage Manager** in less than 2 minutes.

---

## ⚡ Quick Start (Windows)

### Option 1: Automated 1-Click Launch (Recommended)
1. Double-click `setup.bat` to verify your Python environment, create a virtual environment, and initialize sample test data.
2. Double-click `run.bat` to launch the FileGuard desktop application.
3. Double-click `test.bat` to execute the automated test suite.

---

### Option 2: Manual PowerShell Commands

```powershell
# 1. Navigate to project root
cd "D:\90 days\90-days-90-projects-day-09-fileguard-storage-manager"

# 2. Create virtual environment
py -m venv .venv

# 3. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 4. Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 5. Generate sample demonstration data
python scripts\create_sample_data.py

# 6. Launch FileGuard Desktop Application
python app.py
```

---

## 🧪 Running Automated Tests

Execute all 38 test suites covering hashing, duplicate grouping, safety rollbacks, quarantine recovery, and perceptual similarity:

```powershell
.\test.bat
# or directly:
pytest -v
```

---

## ⌨️ Useful Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl+O` | Choose scan folders |
| `Ctrl+F` | Focus search / filter bar |
| `F5` | Refresh / rescan active view |
| `Esc` | Clear search query or dismiss transient selection |
| `Ctrl+E` | Open Reports & Compliance Export |
| `Ctrl+Z` | Undo last eligible quarantine cleanup |
