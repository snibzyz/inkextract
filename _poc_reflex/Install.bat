@echo off
chcp 65001 >nul
title Install INKEXTRACT POC (Reflex)
cd /d "%~dp0"

echo.
echo ===========================================
echo   INKEXTRACT POC - Install Reflex
echo ===========================================
echo.

set "PY=..\.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo [ERROR] .venv not found at ..\.venv\Scripts\python.exe
    pause
    exit /b 1
)

echo [1/2] Installing reflex package...
"%PY%" -m pip install --upgrade reflex
if errorlevel 1 ( echo [FAILED] pip install error & pause & exit /b 1 )

echo.
echo [2/2] Checking reflex...
"%PY%" -m reflex --version
if errorlevel 1 ( echo [FAILED] reflex CLI error & pause & exit /b 1 )

echo.
echo ===========================================
echo   Install complete - now run Start.bat
echo ===========================================
pause
