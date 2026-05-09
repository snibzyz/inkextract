@echo off
REM First-time install for INKEXTRACT (Windows).
REM
REM You only need this if you downloaded "Source code (zip)" from GitHub
REM or cloned the repo. The pre-built release bundle
REM (INKEXTRACT-windows-x64.zip) does NOT need this - it ships with
REM Python and libs already inside, just run Start.bat directly.
REM
REM What this does:
REM   1. Find a system Python 3.x
REM   2. Create a local .venv folder
REM   3. pip-install everything in .app\requirements.txt
REM
REM Re-run if you ever delete .venv or want to refresh dependencies.

setlocal enabledelayedexpansion
cd /d "%~dp0"

chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo.
echo ============================================================
echo        INKEXTRACT - First-time Install
echo ============================================================
echo.

REM ---- 1. Find system Python ----
set "SYS_PY="
where py >nul 2>&1
if not errorlevel 1 (
    py -3 --version >nul 2>&1
    if not errorlevel 1 set "SYS_PY=py -3"
)
if "!SYS_PY!"=="" (
    where python >nul 2>&1
    if not errorlevel 1 set "SYS_PY=python"
)
if "!SYS_PY!"=="" (
    where python3 >nul 2>&1
    if not errorlevel 1 set "SYS_PY=python3"
)

if "!SYS_PY!"=="" (
    echo [X] No Python found on this machine.
    echo.
    echo Easiest fix: download the pre-built bundle which already includes Python:
    echo     https://github.com/snibzyz/inkextract/releases/latest
    echo.
    echo Or install Python from python.org ^(check "Add Python to PATH"^):
    echo     https://www.python.org/downloads/windows/
    echo.
    pause
    exit /b 1
)

REM Validate Python is 3.10+ (streamlit 1.28+ and pandas need this).
for /f "tokens=*" %%v in ('!SYS_PY! -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2^>nul') do set "PY_VER=%%v"
if "!PY_VER!"=="" (
    echo [X] Could not determine Python version from: !SYS_PY!
    pause
    exit /b 1
)
for /f "tokens=1,2 delims=." %%a in ("!PY_VER!") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)
set "TOO_OLD="
if !PY_MAJOR! LSS 3 set "TOO_OLD=1"
if !PY_MAJOR! EQU 3 if !PY_MINOR! LSS 10 set "TOO_OLD=1"
if defined TOO_OLD (
    echo [X] Python !PY_VER! is too old - INKEXTRACT needs Python 3.10 or newer.
    echo.
    echo     Install a newer Python: https://www.python.org/downloads/windows/
    echo     ^(make sure to check "Add Python to PATH"^)
    echo.
    pause
    exit /b 1
)
echo [1/3] Found Python !PY_VER! ^(!SYS_PY!^)
echo.

REM ---- 2. Create venv ----
REM Re-create if .venv exists but its python.exe doesn't work (e.g. left over
REM from a Python uninstall, or from a different Python version that's gone).
set "RECREATE_VENV="
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" --version >nul 2>&1
    if errorlevel 1 set "RECREATE_VENV=broken"
)
if defined RECREATE_VENV (
    echo [2/3] Existing .venv is broken ^(stale Python^) - recreating...
    rmdir /s /q .venv
)
if exist ".venv\Scripts\python.exe" (
    echo [2/3] .venv already exists - keeping it.
) else (
    echo [2/3] Creating .venv ...
    !SYS_PY! -m venv .venv
    if errorlevel 1 (
        echo [X] Failed to create .venv
        pause
        exit /b 1
    )
)
echo.

REM ---- 3. Install dependencies ----
echo [3/3] Installing dependencies ^(may take 1-3 minutes^) ...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet --disable-pip-version-check
".venv\Scripts\python.exe" -m pip install -r ".app\requirements.txt" --disable-pip-version-check
if errorlevel 1 (
    echo.
    echo [X] Failed to install dependencies.
    echo     Check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Install complete!
echo.
echo   Double-click Start.bat to launch the app.
echo ============================================================
echo.
pause
