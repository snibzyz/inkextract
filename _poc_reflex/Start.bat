@echo off
chcp 65001 >nul
title INKEXTRACT POC (Reflex)
cd /d "%~dp0"

echo.
echo ===========================================
echo   INKEXTRACT POC - Reflex Dev Server
echo ===========================================
echo   Frontend: http://localhost:3500
echo   Backend : http://localhost:3501
echo.
echo   Press Ctrl+C to stop
echo ===========================================
echo.

REM ---- Auto-kill any process holding ports 3500 / 3501 -------------------
call :killport 3500
call :killport 3501
echo.

set "PY=..\.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo [ERROR] .venv not found at ..\.venv\Scripts\python.exe
    echo         Run Install.bat first
    pause
    exit /b 1
)

"%PY%" -m reflex run --frontend-port 3500 --backend-port 3501

pause
exit /b 0


REM ============================================================
REM  :killport PORT
REM  - Finds processes LISTENING on PORT and kills them
REM ============================================================
:killport
set "P=%~1"
set "FOUND="
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr /R /C:":%P% .*LISTENING"') do (
    if not "%%a"=="0" (
        echo [INFO] Port %P% in use by PID %%a - killing
        taskkill /F /PID %%a >nul 2>&1
        set "FOUND=1"
    )
)
if not defined FOUND echo [OK]   Port %P% is free
exit /b 0
