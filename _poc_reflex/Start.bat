@echo off
chcp 65001 >nul
title INKEXTRACT POC (Reflex)
cd /d "%~dp0"

REM ─── Ports — match rxconfig.py ──────────────────────────────────────────
set "FRONT_PORT=4500"
set "BACK_PORT=4501"

echo.
echo ===========================================
echo   INKEXTRACT POC - Reflex Dev Server
echo ===========================================
echo   Frontend: http://localhost:%FRONT_PORT%
echo   Backend : http://localhost:%BACK_PORT%
echo.
echo   Press Ctrl+C to stop
echo ===========================================
echo.

REM ─── Auto-kill any process holding our ports ────────────────────────────
call :killport %FRONT_PORT%
call :killport %BACK_PORT%
echo.

set "PY=..\.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo [ERROR] .venv not found at ..\.venv\Scripts\python.exe
    echo         Run Install.bat first
    pause
    exit /b 1
)

"%PY%" -m reflex run --frontend-port %FRONT_PORT% --backend-port %BACK_PORT%

pause
exit /b 0


REM ============================================================
REM  :killport PORT
REM  - Find processes LISTENING / CONNECTED on PORT and kill them
REM  - Works around orphan sockets (process dead but socket lingering)
REM    by trying multiple PIDs from netstat
REM ============================================================
:killport
set "P=%~1"
set "FOUND="
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr /R /C:":%P% .*LISTENING" /C:":%P% .*ESTABLISHED"') do (
    if not "%%a"=="0" if not "%%a"=="4" (
        echo [INFO] Port %P% held by PID %%a - killing
        taskkill /F /PID %%a 2>nul
        set "FOUND=1"
    )
)
if not defined FOUND echo [OK]   Port %P% is free
exit /b 0
