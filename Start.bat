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

REM ============================================================
REM Apply pending update FIRST, with native robocopy.
REM
REM Why not Python here? On Windows the running python.exe holds an
REM exclusive lock on its own file - if we tried to copy a new
REM python\python.exe over it from inside Python, the copy fails. Doing
REM the apply in cmd before Python starts avoids that lock entirely.
REM ============================================================
if exist ".update_pending\READY" (
    echo Applying staged update...

    set "KIND=source"
    if exist ".update_pending\staged\.update_kind" (
        set /p KIND=<".update_pending\staged\.update_kind"
    )

    REM Always exclude user data and dev folders. For source-only updates,
    REM also exclude python/ so we don't half-update the interpreter.
    REM Start.bat/.command are excluded too: cmd.exe is unpredictable when
    REM its own .bat file is replaced mid-execution, so launcher updates
    REM require a manual re-download.
    REM /E recurse, /IS overwrite same-size, /IT include tweaked, /XF exclude marker file.
    set "ROBO_BASE=/E /IS /IT /R:1 /W:1 /NJH /NJS /NDL /NFL /NP"
    set "ROBO_XD_USER=/XD .git .venv workspace .config __pycache__ .update_pending"
    set "ROBO_XF=/XF .update_kind Start.bat Start.command"

    if /I "!KIND!"=="bundle" (
        robocopy ".update_pending\staged" "." !ROBO_BASE! !ROBO_XF! !ROBO_XD_USER! >nul
    ) else (
        robocopy ".update_pending\staged" "." !ROBO_BASE! !ROBO_XF! !ROBO_XD_USER! python >nul
    )
    REM robocopy uses exit codes 0-7 for success, 8+ for real errors
    set "RC=!ERRORLEVEL!"
    if !RC! GEQ 8 (
        echo [WARN] Update apply had errors ^(robocopy exit !RC!^) - continuing anyway.
    )

    REM Bump VERSION file (strip leading 'v' if present)
    set /p NEW_TAG=<".update_pending\READY"
    if not "!NEW_TAG!"=="" (
        set "NEW_TAG=!NEW_TAG:v=!"
        > ".app\VERSION" echo !NEW_TAG!
    )

    rmdir /s /q ".update_pending" 2>nul
    echo Update applied: !NEW_TAG!

    REM If we're a source-installed user (.venv mode) AND the update was
    REM source-only, refresh dependencies in case requirements.txt changed.
    REM pip is fast when everything is already installed.
    if /I "!KIND!"=="source" (
        if exist ".venv\Scripts\python.exe" (
            echo Refreshing dependencies...
            ".venv\Scripts\python.exe" -m pip install -r ".app\requirements.txt" --quiet --disable-pip-version-check
            if errorlevel 1 (
                echo [WARN] Dependency refresh failed. If the app crashes, run Install.bat again.
            )
        )
    )
    echo.
)

set "PY="
if exist "python\python.exe" (
    set "PY=python\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
)

if "%PY%"=="" (
    echo.
    echo [X] Not set up yet.
    echo.
    echo It looks like neither the bundled python\ folder nor a local .venv\
    echo was found. This usually means you downloaded the "Source code (zip)"
    echo from GitHub instead of a release bundle.
    echo.
    echo Easiest fix - one of:
    echo.
    echo   A^) Run Install.bat once ^(needs Python on your machine^):
    echo        Double-click Install.bat
    echo        Wait 1-3 min for it to finish
    echo        Then double-click Start.bat again
    echo.
    echo   B^) Download the pre-built bundle ^(no Python install needed^):
    echo        https://github.com/snibzyz/inkextract/releases/latest
    echo        File: INKEXTRACT-windows-x64.zip
    echo.
    pause
    exit /b 1
)

REM ============================================================
REM Kill any existing Streamlit process bound to port 8501 to prevent
REM double-launches across multiple INKEXTRACT installs on the same machine
REM ============================================================
set "STREAMLIT_PORT=8501"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%STREAMLIT_PORT% " ^| findstr LISTENING 2^>nul') do (
    echo Found existing process on port %STREAMLIT_PORT% (PID %%a) - killing...
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo ============================================================
echo        INKEXTRACT - Translation Toolkit
echo ============================================================
echo Starting app... your browser will open shortly.
echo To quit: close this window or press Ctrl+C
echo Install root: %CD%
echo ============================================================
echo.

"%PY%" -m streamlit run ".app\app.py" --server.port %STREAMLIT_PORT%

if errorlevel 1 (
    echo.
    echo App exited with an error. See the messages above.
    pause
)
