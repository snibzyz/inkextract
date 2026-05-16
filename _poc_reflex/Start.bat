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

set "PY=..\.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo [ERROR] .venv not found at ..\.venv\Scripts\python.exe
    echo         Run Install.bat first
    pause
    exit /b 1
)

"%PY%" -m reflex run --frontend-port 3500 --backend-port 3501

pause
