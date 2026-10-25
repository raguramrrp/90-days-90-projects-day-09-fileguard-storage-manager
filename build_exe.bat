@echo off
setlocal

echo =====================================================================
echo   Building Standalone Windows Executable (FileGuard.exe)
echo =====================================================================
echo.

if exist .\.venv\Scripts\activate.bat (
    call .\.venv\Scripts\activate.bat
)

if exist .\.venv\Scripts\pyinstaller.exe (
    echo [INFO] Running PyInstaller packaging...
    .\.venv\Scripts\pyinstaller.exe --noconfirm FileGuard.spec
) else (
    echo [INFO] Running PyInstaller from python module...
    python -m PyInstaller --noconfirm FileGuard.spec
)

if %errorlevel% equ 0 (
    echo.
    echo [OK] Build completed successfully!
    echo Executable located at: dist\FileGuard.exe
) else (
    echo.
    echo [ERROR] Packaging failed.
)

pause
