@echo off
setlocal

echo =====================================================================
echo   Launching FileGuard - Intelligent Storage Manager
echo =====================================================================
echo.

:: Activate virtual environment if present
if exist .\.venv\Scripts\activate.bat (
    call .\.venv\Scripts\activate.bat
)

:: Launch desktop application
python app.py %*

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] FileGuard exited with error code %errorlevel%.
    pause
)
