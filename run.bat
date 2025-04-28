@echo off
REM netWORKS Application Launcher
TITLE netWORKS - Network Scanner

ECHO =======================================
ECHO netWORKS - Network Scanner Application
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

REM Check for logs directory and create if missing
IF NOT EXIST logs (
    ECHO [INFO] Creating logs directory...
    mkdir logs
)

REM Check if it's first run or recovering from a failed setup
SET SETUP_NEEDED=0
IF NOT EXIST venv (
    SET SETUP_NEEDED=1
    ECHO [INFO] First-time setup detected
    ECHO [INFO] Setting up virtual environment and installing dependencies
    ECHO [INFO] This may take a few minutes. Please be patient.
    
    REM Create a timestamp file to track installation attempts
    ECHO %DATE% %TIME% > setup_in_progress.tmp
)

REM If setup_in_progress.tmp exists and venv doesn't, it means a previous install failed
IF EXIST setup_in_progress.tmp IF NOT EXIST venv (
    ECHO [WARNING] A previous setup attempt may have failed
    ECHO [INFO] Attempting setup again...
)

REM Check for common dependency issues before launching
SET CHECK_DEPS=0
IF EXIST venv IF EXIST setup_in_progress.tmp (
    SET CHECK_DEPS=1
    ECHO [INFO] Checking dependencies from previous incomplete setup...
)

IF %CHECK_DEPS% EQU 1 (
    IF EXIST venv\Scripts\python.exe (
        ECHO [INFO] Testing installed dependencies...
        venv\Scripts\python.exe -c "import sys; print('Python check successful')" >nul 2>nul
        IF %ERRORLEVEL% NEQ 0 (
            ECHO [WARNING] Virtual environment may be corrupted, will attempt repair
            RMDIR /S /Q venv
            ECHO [INFO] Removed damaged virtual environment, will reinstall
            SET SETUP_NEEDED=1
        )
    ) ELSE (
        ECHO [WARNING] Incomplete virtual environment detected, will reinstall
        RMDIR /S /Q venv
        SET SETUP_NEEDED=1
    )
)

REM Launch the application with error handling
ECHO [INFO] Launching netWORKS...
python start.py %*
SET APP_EXIT_CODE=%ERRORLEVEL%

REM Clean up temporary file if setup completed successfully
IF EXIST setup_in_progress.tmp IF EXIST venv (
    DEL /F /Q setup_in_progress.tmp
)

REM Check for specific error codes
IF %APP_EXIT_CODE% NEQ 0 (
    ECHO.
    ECHO [ERROR] The application exited with an error code: %APP_EXIT_CODE%
    
    REM Specific error handling for common issues
    IF %APP_EXIT_CODE% EQU 1 (
        ECHO [INFO] The application encountered a general error
        
        IF EXIST logs\dependency_install.log (
            ECHO [INFO] Dependency installation log found. Checking for issues...
            FINDSTR /C:"Failed to install" logs\dependency_install.log >nul
            IF %ERRORLEVEL% EQU 0 (
                ECHO [WARNING] Some dependencies failed to install
                ECHO [INFO] You may need to manually install missing packages
                ECHO [INFO] See logs\dependency_install.log for details
            )
        )
        
        IF EXIST venv (
            ECHO [INFO] Would you like to try repairing the dependencies? (y/n)
            SET /P REPAIR=
            IF /I "%REPAIR%"=="y" (
                ECHO [INFO] Repairing virtual environment...
                python -m venv --clear venv
                IF EXIST venv\Scripts\pip.exe (
                    venv\Scripts\pip.exe install --upgrade pip
                    venv\Scripts\pip.exe install -r requirements.txt
                    ECHO [INFO] Dependencies reinstalled. Please run the application again.
                ) ELSE (
                    ECHO [ERROR] Failed to repair virtual environment
                )
            )
        )
    ) ELSE IF %APP_EXIT_CODE% EQU 2 (
        ECHO [INFO] The application encountered a command line syntax error
        ECHO [INFO] Run the application without any command line arguments
    ) ELSE IF %APP_EXIT_CODE% EQU 9 (
        ECHO [INFO] The application encountered a permission error
        ECHO [INFO] Try running as administrator (right-click and select "Run as administrator")
    ) ELSE IF %APP_EXIT_CODE% EQU 130 (
        ECHO [INFO] The application was terminated by the user (Ctrl+C)
    ) ELSE IF %APP_EXIT_CODE% EQU 137 (
        ECHO [WARNING] The application crashed, possibly due to insufficient memory
        ECHO [INFO] Try closing other applications and running again
    )
    
    ECHO.
    ECHO [INFO] Check the logs directory for more details:
    IF EXIST logs (
        ECHO [INFO] - Check logs\launcher.log for launcher errors
        ECHO [INFO] - Check logs\dependency_install.log for dependency issues
    ) ELSE (
        ECHO [INFO] No logs directory found. The application may not have started properly.
    )
    
    ECHO.
    ECHO [INFO] Press any key to exit...
    PAUSE >nul
    EXIT /B %APP_EXIT_CODE%
) ELSE (
    ECHO [SUCCESS] netWORKS completed successfully
)

EXIT /B 0 