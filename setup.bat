@echo off
setlocal enabledelayedexpansion

echo =====================================================================
echo   FileGuard - Setup & Dependency Configuration
echo   Intelligent Duplicate File Detection ^& Storage Manager
echo =====================================================================
echo.

:: 1. Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in PATH.
    echo Please install Python 3.10+ from https://www.python.org/ and ensure
    echo "Add Python to PATH" is checked during setup.
    pause
    exit /b 1
)

echo [OK] Python detected:
python --version
echo.

:: 2. Set up virtual environment
if not exist .venv (
    echo [INFO] Creating Python virtual environment in .venv...
    py -m venv .venv
    if %errorlevel% neq 0 (
        python -m venv .venv
    )
) else (
    echo [OK] Virtual environment .venv already exists.
)

:: 3. Activate virtual environment
if exist .\.venv\Scripts\activate.bat (
    call .\.venv\Scripts\activate.bat
) else (
    echo [ERROR] Could not find virtual environment activation script.
    pause
    exit /b 1
)

:: 4. Install / upgrade dependencies
echo.
echo [INFO] Installing required dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] Some external packages could not be installed from PyPI.
    echo FileGuard will run using built-in standard libraries (Tkinter, SQLite).
)

:: 5. Initialize sample test files if not present
echo.
echo [INFO] Initializing sample test files...
python scripts\create_sample_data.py

:: 6. Verify database initialization
echo.
echo [INFO] Verifying local SQLite database initialization...
python -c "from fileguard.database import Database; db = Database(); print('[OK] Database schema initialized at:', db.db_path)"

echo.
echo =====================================================================
echo   Setup Completed Successfully!
echo   To launch FileGuard, double-click run.bat or run:
echo     python app.py
echo =====================================================================
echo.
pause
