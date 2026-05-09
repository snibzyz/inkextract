@echo off
REM Universal launcher for INKEXTRACT.
REM
REM Same file ships in:
REM   * end-user release bundle  -> uses bundled python/ folder
REM   * source repo (developers) -> uses .venv/ folder (or system Python as last resort)
REM
REM Detection order: bundled python/  >  local .venv/  >  system PATH

setlocal enabledelayedexpansion
cd /d "%~dp0"

REM UTF-8 console for Thai output
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

set "PY="
if exist "python\python.exe" (
    set "PY=python\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    where python >nul 2>&1
    if not errorlevel 1 (
        set "PY=python"
        echo [WARN] Using system Python ^(no python\ bundle, no .venv detected^).
        echo        For dev, run once:
        echo            python -m venv .venv ^&^& .venv\Scripts\pip install -r .app\requirements.txt
        echo.
    )
)

if "%PY%"=="" (
    echo.
    echo [X] No Python interpreter found.
    echo.
    echo If you downloaded a release bundle, the python\ folder should be next to this file.
    echo Re-download from: https://github.com/snibzyz/inkextract/releases/latest
    echo.
    echo If you cloned the source, install Python first then run:
    echo     python -m venv .venv
    echo     .venv\Scripts\pip install -r .app\requirements.txt
    echo.
    pause
    exit /b 1
)

REM Apply staged update if a previous run downloaded one (bundle mode)
if exist ".update_pending\READY" (
    echo Applying queued update...
    "%PY%" -c "import sys; sys.path.insert(0, '.app'); import updater; sys.exit(updater.apply_staged())"
    if errorlevel 1 echo Update apply failed - continuing with current version.
)

echo.
echo ============================================================
echo        INKEXTRACT - Translation Toolkit
echo ============================================================
echo Starting app... your browser will open shortly.
echo To quit: close this window or press Ctrl+C
echo ============================================================
echo.

"%PY%" -m streamlit run ".app\app.py"

if errorlevel 1 (
    echo.
    echo App exited with an error. See the messages above.
    pause
)
