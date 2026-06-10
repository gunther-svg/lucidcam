@echo off
:: Check if python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python was not found. Please install Python from python.org or the Microsoft Store.
    pause
    exit /b
)

:: Run the installer/launcher
python install.py
pause
