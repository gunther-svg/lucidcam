@echo off
title LucidCam Build Script
cd /d "%~dp0"

echo ============================================================
echo   LucidCam Automated Build System (greatware)
echo ============================================================

if exist ".venv\Scripts\python.exe" (
    echo [+] Using virtual environment Python...
    ".venv\Scripts\python.exe" build.py
) else (
    echo [+] Using system Python...
    python build.py
)

pause
