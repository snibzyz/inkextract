@echo off
REM Launcher for the bundled INKEXTRACT distribution.
REM Just runs the bundled Python with the app. No install, no venv, no pip.

setlocal enabledelayedexpansion
cd /d "%~dp0"

REM Verify the bundled Python is present (it should be, this is a packaged release)
if not exist "python\python.exe" (
    echo.
    echo [X] Bundled Python is missing.
    echo     Re-download the latest release from:
    echo     https://github.com/snibzyz/inkextract/releases/latest
    echo.
    pause
    exit /b 1
)

REM Set up UTF-8 output so Thai prints correctly
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM Apply staged update (if a previous run downloaded one)
if exist ".update_pending\READY" (
    echo Applying queued update...
    "python\python.exe" -c "import sys; sys.path.insert(0, '.app'); import updater; sys.exit(updater.apply_staged())"
    if errorlevel 1 (
        echo Update apply failed - continuing with current version.
    )
)

echo.
echo ============================================================
echo        INKEXTRACT - Translation Toolkit
echo ============================================================
echo Starting app... your browser will open shortly.
echo To quit: close this window or press Ctrl+C
echo ============================================================
echo.

"python\python.exe" -m streamlit run ".app\app.py" --server.headless=false

REM Keep window open if streamlit exits with error
if errorlevel 1 (
    echo.
    echo App exited with an error. See the messages above.
    pause
)
