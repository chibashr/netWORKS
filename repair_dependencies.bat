@echo off
REM netWORKS Dependency Repair Tool Launcher
TITLE netWORKS - Dependency Repair

ECHO =======================================
ECHO netWORKS - Dependency Repair Tool
ECHO =======================================
ECHO.

REM Check if Python is available
WHERE python >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    ECHO [ERROR] Python is not installed or not in PATH
    ECHO [INFO] Please install Python 3.9+ from https://www.python.org/downloads/
    ECHO [INFO] Make sure to check "Add Python to PATH" during installation
    PAUSE
    EXIT /B 1
)

REM Check Python version
python -c "import sys; sys.exit(1 if sys.version_info < (3,9) else 0)" >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    ECHO [ERROR] Python 3.9 or higher is required
    ECHO [INFO] Current Python version:
    python --version
    ECHO [INFO] Please install Python 3.9+ from https://www.python.org/downloads/
    PAUSE
    EXIT /B 1
)

REM Check if we're in the right directory
IF NOT EXIST requirements.txt (
    ECHO [ERROR] requirements.txt not found
    ECHO [INFO] Please make sure you're running this from the correct directory
    PAUSE
    EXIT /B 1
)

REM Check if the repair script exists
IF NOT EXIST scripts\repair_dependencies.py (
    ECHO [ERROR] Repair script not found (scripts\repair_dependencies.py)
    ECHO [INFO] Please make sure you have the complete netWORKS installation
    PAUSE
    EXIT /B 1
)

REM Create logs directory if it doesn't exist
IF NOT EXIST logs (
    ECHO [INFO] Creating logs directory...
    mkdir logs
)

ECHO [INFO] Running dependency repair tool...
ECHO [INFO] This tool will help fix any issues with dependencies.
ECHO [INFO] Follow the on-screen instructions.
ECHO.

REM Run the repair script
python scripts\repair_dependencies.py
SET EXIT_CODE=%ERRORLEVEL%

IF %EXIT_CODE% NEQ 0 (
    ECHO.
    ECHO [ERROR] Repair process exited with code: %EXIT_CODE%
    ECHO [INFO] Please check the logs for details (logs\dependency_repair.log)
    
    REM Specific advice based on error codes
    IF %EXIT_CODE% EQU 1 (
        ECHO [INFO] The repair failed. You may need to:
        ECHO [INFO] 1. Try manually removing the 'venv' directory
        ECHO [INFO] 2. Run this repair tool again
        ECHO [INFO] 3. If that fails, reinstall Python
    )
    
    ECHO.
    ECHO [INFO] Press any key to exit...
    PAUSE >nul
    EXIT /B %EXIT_CODE%
)

ECHO.
ECHO [SUCCESS] Repair process completed successfully
ECHO [INFO] You can now run the application using run.bat
ECHO.
ECHO [INFO] Press any key to exit...
PAUSE >nul
EXIT /B 0 