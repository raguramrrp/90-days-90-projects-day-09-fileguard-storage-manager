@echo off
setlocal

echo =====================================================================
echo   Running FileGuard Automated Test Suite (pytest)
echo =====================================================================
echo.

if exist .\.venv\Scripts\activate.bat (
    call .\.venv\Scripts\activate.bat
)

if exist .\.venv\Scripts\pytest.exe (
    .\.venv\Scripts\pytest.exe -v
) else (
    python -m pytest -v
)

set TEST_EXIT_CODE=%errorlevel%

echo.
if %TEST_EXIT_CODE% equ 0 (
    echo [PASS] All automated tests passed successfully!
) else (
    echo [FAIL] Automated tests failed with exit code %TEST_EXIT_CODE%.
)

exit /b %TEST_EXIT_CODE%
