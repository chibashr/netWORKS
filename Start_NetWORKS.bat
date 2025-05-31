@echo off
setlocal enabledelayedexpansion

echo [INFO] NetWORKS Startup Script
echo ============================

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8 or later and try again
    pause
    exit /b 1
)

:: Check if virtual environment exists
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Update pip to latest version
echo [INFO] Updating pip...
python -m pip install --upgrade pip

:: Install/Repair dependencies
echo [INFO] Installing/Repairing dependencies...
python -m pip install -r requirements.txt

:: Start the application
echo [INFO] Starting NetWORKS...
python networks.py

:: Deactivate virtual environment
deactivate

:: If we get here, check if there was an error
if errorlevel 1 (
    echo [ERROR] An error occurred while running NetWORKS
    pause
    exit /b 1
)

endlocal 