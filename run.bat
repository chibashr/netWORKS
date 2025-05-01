@echo off
REM netWORKS Application Launcher
TITLE netWORKS - Network Scanner

ECHO =======================================
ECHO netWORKS - Network Scanner Application
ECHO =======================================
ECHO.

REM Create logs directory if it doesn't exist
IF NOT EXIST logs (
    ECHO [INFO] Creating logs directory...
    mkdir logs
)

REM Log file path
SET LOG_FILE=logs\launcher.log
ECHO [%DATE% %TIME%] Launcher started > %LOG_FILE%

REM Check if Python is available
ECHO [INFO] Checking for Python installation...
WHERE python >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    WHERE py >nul 2>nul
    IF %ERRORLEVEL% NEQ 0 (
        ECHO [ERROR] Python is not installed or not in PATH >> %LOG_FILE%
        ECHO [ERROR] Python is not installed or not in PATH
        ECHO [INFO] Please install Python 3.9+ from https://www.python.org/downloads/
        ECHO [INFO] Make sure to check "Add Python to PATH" during installation
        PAUSE
        EXIT /B 1
    ) ELSE (
        ECHO [INFO] Found Python using py launcher >> %LOG_FILE%
        SET PYTHON_CMD=py -3
    )
) ELSE (
    ECHO [INFO] Found Python in PATH >> %LOG_FILE%
    SET PYTHON_CMD=python
)

REM Check Python version
%PYTHON_CMD% -c "import sys; sys.exit(1 if sys.version_info < (3,9) else 0)" >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    ECHO [ERROR] Python 3.9 or higher is required >> %LOG_FILE%
    ECHO [ERROR] Python 3.9 or higher is required
    ECHO [INFO] Current Python version:
    %PYTHON_CMD% --version
    ECHO [INFO] Please install Python 3.9+ from https://www.python.org/downloads/
    PAUSE
    EXIT /B 1
) ELSE (
    ECHO [INFO] Python version check passed >> %LOG_FILE%
    %PYTHON_CMD% --version >> %LOG_FILE%
)

REM Check if we're in the right directory
IF NOT EXIST requirements.txt (
    ECHO [ERROR] requirements.txt not found >> %LOG_FILE%
    ECHO [ERROR] requirements.txt not found
    ECHO [INFO] Please make sure you're running this from the correct directory
    PAUSE
    EXIT /B 1
)

REM Check for virtual environment and create if missing
SET SETUP_NEEDED=0
IF NOT EXIST venv (
    SET SETUP_NEEDED=1
    ECHO [INFO] First-time setup detected >> %LOG_FILE%
    ECHO [INFO] First-time setup detected
    ECHO [INFO] Setting up virtual environment and installing dependencies
    ECHO [INFO] This may take a few minutes. Please be patient.
    
    REM Create a timestamp file to track installation attempts
    ECHO %DATE% %TIME% > setup_in_progress.tmp
    
    REM Create virtual environment
    ECHO [INFO] Creating virtual environment... >> %LOG_FILE%
    %PYTHON_CMD% -m venv venv
    IF %ERRORLEVEL% NEQ 0 (
        ECHO [ERROR] Failed to create virtual environment >> %LOG_FILE%
        ECHO [ERROR] Failed to create virtual environment
        ECHO [INFO] Try installing venv module: %PYTHON_CMD% -m pip install virtualenv
        PAUSE
        EXIT /B 1
    )
    
    REM Install dependencies
    ECHO [INFO] Installing dependencies... >> %LOG_FILE%
    ECHO [INFO] Installing dependencies...
    
    IF EXIST venv\Scripts\python.exe (
        venv\Scripts\python.exe -m pip install --upgrade pip >> logs\dependency_install.log 2>&1
        venv\Scripts\python.exe -m pip install -r requirements.txt >> logs\dependency_install.log 2>&1
        IF %ERRORLEVEL% NEQ 0 (
            ECHO [WARNING] Some dependencies may have failed to install >> %LOG_FILE%
            ECHO [WARNING] Some dependencies may have failed to install
            ECHO [INFO] Check logs\dependency_install.log for details
        ) ELSE (
            ECHO [INFO] Dependencies installed successfully >> %LOG_FILE%
            ECHO [INFO] Dependencies installed successfully
        )
    ) ELSE (
        ECHO [ERROR] Virtual environment creation failed >> %LOG_FILE%
        ECHO [ERROR] Virtual environment creation failed
        PAUSE
        EXIT /B 1
    )
)

REM If setup_in_progress.tmp exists and venv exists, it means a previous install may have been interrupted
IF EXIST setup_in_progress.tmp IF EXIST venv (
    ECHO [INFO] Checking previous incomplete setup... >> %LOG_FILE%
    ECHO [INFO] Checking previous incomplete setup...
    
    REM Verify the virtual environment is working
    venv\Scripts\python.exe -c "import sys; print('Python check successful')" >nul 2>nul
    IF %ERRORLEVEL% NEQ 0 (
        ECHO [WARNING] Virtual environment may be corrupted, will attempt repair >> %LOG_FILE%
        ECHO [WARNING] Virtual environment may be corrupted, will attempt repair
        RMDIR /S /Q venv
        ECHO [INFO] Removed damaged virtual environment, will reinstall >> %LOG_FILE%
        ECHO [INFO] Removed damaged virtual environment, will reinstall
        
        REM Recreate virtual environment
        %PYTHON_CMD% -m venv venv
        venv\Scripts\python.exe -m pip install --upgrade pip >> logs\dependency_install.log 2>&1
        venv\Scripts\python.exe -m pip install -r requirements.txt >> logs\dependency_install.log 2>&1
    ) ELSE (
        ECHO [INFO] Virtual environment check passed >> %LOG_FILE%
    )
)

REM Verify all required modules are installed
ECHO [INFO] Verifying required modules... >> %LOG_FILE%
venv\Scripts\python.exe -c "import PySide6; import netaddr; import paramiko; print('Module check successful')" >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    ECHO [WARNING] Some required modules may be missing, attempting to reinstall >> %LOG_FILE%
    ECHO [WARNING] Some required modules may be missing, attempting to reinstall
    venv\Scripts\python.exe -m pip install --upgrade -r requirements.txt >> logs\dependency_install.log 2>&1
)

REM Launch the application with error handling
ECHO [INFO] Launching netWORKS... >> %LOG_FILE%
ECHO [INFO] Launching netWORKS...

REM Use the virtual environment's Python to run start.py
venv\Scripts\python.exe start.py %*
SET APP_EXIT_CODE=%ERRORLEVEL%
ECHO [INFO] Application exited with code: %APP_EXIT_CODE% >> %LOG_FILE%

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
        ECHO [INFO] The application encountered a general error >> %LOG_FILE%
        ECHO [INFO] The application encountered a general error
        
        IF EXIST logs\dependency_install.log (
            ECHO [INFO] Dependency installation log found. Checking for issues... >> %LOG_FILE%
            ECHO [INFO] Dependency installation log found. Checking for issues...
            FINDSTR /C:"Failed to install" logs\dependency_install.log >nul
            IF %ERRORLEVEL% EQU 0 (
                ECHO [WARNING] Some dependencies failed to install >> %LOG_FILE%
                ECHO [WARNING] Some dependencies failed to install
                ECHO [INFO] You may need to manually install missing packages
                ECHO [INFO] See logs\dependency_install.log for details
            )
        )
        
        IF EXIST venv (
            ECHO [INFO] Would you like to try repairing the dependencies? (y/n)
            SET /P REPAIR=
            IF /I "%REPAIR%"=="y" (
                ECHO [INFO] Repairing virtual environment... >> %LOG_FILE%
                ECHO [INFO] Repairing virtual environment...
                %PYTHON_CMD% -m venv --clear venv
                IF EXIST venv\Scripts\pip.exe (
                    venv\Scripts\pip.exe install --upgrade pip >> logs\dependency_install.log 2>&1
                    venv\Scripts\pip.exe install -r requirements.txt >> logs\dependency_install.log 2>&1
                    ECHO [INFO] Dependencies reinstalled. Please run the application again. >> %LOG_FILE%
                    ECHO [INFO] Dependencies reinstalled. Please run the application again.
                ) ELSE (
                    ECHO [ERROR] Failed to repair virtual environment >> %LOG_FILE%
                    ECHO [ERROR] Failed to repair virtual environment
                )
            )
        )
    ) ELSE IF %APP_EXIT_CODE% EQU 2 (
        ECHO [INFO] The application encountered a command line syntax error >> %LOG_FILE%
        ECHO [INFO] The application encountered a command line syntax error
        ECHO [INFO] Run the application without any command line arguments
    ) ELSE IF %APP_EXIT_CODE% EQU 9 (
        ECHO [INFO] The application encountered a permission error >> %LOG_FILE%
        ECHO [INFO] The application encountered a permission error
        ECHO [INFO] Try running as administrator (right-click and select "Run as administrator")
    ) ELSE IF %APP_EXIT_CODE% EQU 130 (
        ECHO [INFO] The application was terminated by the user (Ctrl+C) >> %LOG_FILE%
        ECHO [INFO] The application was terminated by the user (Ctrl+C)
    ) ELSE IF %APP_EXIT_CODE% EQU 137 (
        ECHO [WARNING] The application crashed, possibly due to insufficient memory >> %LOG_FILE%
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
    ECHO [SUCCESS] netWORKS completed successfully >> %LOG_FILE%
    ECHO [SUCCESS] netWORKS completed successfully
)

EXIT /B 0 