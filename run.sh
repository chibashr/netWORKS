#!/bin/bash
# netWORKS Application Launcher for Unix-based systems

echo "======================================="
echo "netWORKS - Network Scanner Application"
echo "======================================="
echo

# Create logs directory if it doesn't exist
if [ ! -d "logs" ]; then
    echo "[INFO] Creating logs directory..."
    mkdir -p logs
fi

# Log file path
LOG_FILE="logs/launcher.log"
echo "[$(date)] Launcher started" > "$LOG_FILE"

# Check if Python is available
echo "[INFO] Checking for Python installation..."
if command -v python3 &>/dev/null; then
    echo "[INFO] Found Python 3 in PATH" >> "$LOG_FILE"
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    # Check if 'python' is actually Python 3
    PYTHON_VERSION=$(python --version 2>&1 | grep -oP '(?<=Python )\d+\.\d+')
    MAJOR_VERSION=$(echo $PYTHON_VERSION | cut -d. -f1)
    
    if [ "$MAJOR_VERSION" -eq 3 ]; then
        echo "[INFO] Found Python 3 as 'python'" >> "$LOG_FILE"
        PYTHON_CMD="python"
    else
        echo "[ERROR] Python 3 is required but found Python $PYTHON_VERSION" >> "$LOG_FILE"
        echo "[ERROR] Python 3 is required but found Python $PYTHON_VERSION"
        echo "[INFO] Please install Python 3.9+ from your package manager or https://www.python.org/downloads/"
        exit 1
    fi
else
    echo "[ERROR] Python is not installed or not in PATH" >> "$LOG_FILE"
    echo "[ERROR] Python is not installed or not in PATH"
    echo "[INFO] Please install Python 3.9+ from your package manager or https://www.python.org/downloads/"
    exit 1
fi

# Check Python version
$PYTHON_CMD -c "import sys; sys.exit(1 if sys.version_info < (3,9) else 0)" &>/dev/null
if [ $? -ne 0 ]; then
    echo "[ERROR] Python 3.9 or higher is required" >> "$LOG_FILE"
    echo "[ERROR] Python 3.9 or higher is required"
    echo "[INFO] Current Python version:"
    $PYTHON_CMD --version
    echo "[INFO] Please install Python 3.9+ from your package manager or https://www.python.org/downloads/"
    exit 1
else
    echo "[INFO] Python version check passed" >> "$LOG_FILE"
    $PYTHON_CMD --version >> "$LOG_FILE"
fi

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "[ERROR] requirements.txt not found" >> "$LOG_FILE"
    echo "[ERROR] requirements.txt not found"
    echo "[INFO] Please make sure you're running this from the correct directory"
    exit 1
fi

# Check for virtual environment and create if missing
SETUP_NEEDED=0
if [ ! -d "venv" ]; then
    SETUP_NEEDED=1
    echo "[INFO] First-time setup detected" >> "$LOG_FILE"
    echo "[INFO] First-time setup detected"
    echo "[INFO] Setting up virtual environment and installing dependencies"
    echo "[INFO] This may take a few minutes. Please be patient."
    
    # Create a timestamp file to track installation attempts
    date > setup_in_progress.tmp
    
    # Create virtual environment
    echo "[INFO] Creating virtual environment..." >> "$LOG_FILE"
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment" >> "$LOG_FILE"
        echo "[ERROR] Failed to create virtual environment"
        echo "[INFO] Try installing venv module: $PYTHON_CMD -m pip install virtualenv"
        exit 1
    fi
    
    # Install dependencies
    echo "[INFO] Installing dependencies..." >> "$LOG_FILE"
    echo "[INFO] Installing dependencies..."
    
    if [ -f "venv/bin/python" ]; then
        venv/bin/python -m pip install --upgrade pip >> logs/dependency_install.log 2>&1
        venv/bin/python -m pip install -r requirements.txt >> logs/dependency_install.log 2>&1
        if [ $? -ne 0 ]; then
            echo "[WARNING] Some dependencies may have failed to install" >> "$LOG_FILE"
            echo "[WARNING] Some dependencies may have failed to install"
            echo "[INFO] Check logs/dependency_install.log for details"
        else
            echo "[INFO] Dependencies installed successfully" >> "$LOG_FILE"
            echo "[INFO] Dependencies installed successfully"
        fi
    else
        echo "[ERROR] Virtual environment creation failed" >> "$LOG_FILE"
        echo "[ERROR] Virtual environment creation failed"
        exit 1
    fi
fi

# If setup_in_progress.tmp exists and venv exists, it means a previous install may have been interrupted
if [ -f "setup_in_progress.tmp" ] && [ -d "venv" ]; then
    echo "[INFO] Checking previous incomplete setup..." >> "$LOG_FILE"
    echo "[INFO] Checking previous incomplete setup..."
    
    # Verify the virtual environment is working
    venv/bin/python -c "import sys; print('Python check successful')" &>/dev/null
    if [ $? -ne 0 ]; then
        echo "[WARNING] Virtual environment may be corrupted, will attempt repair" >> "$LOG_FILE"
        echo "[WARNING] Virtual environment may be corrupted, will attempt repair"
        rm -rf venv
        echo "[INFO] Removed damaged virtual environment, will reinstall" >> "$LOG_FILE"
        echo "[INFO] Removed damaged virtual environment, will reinstall"
        
        # Recreate virtual environment
        $PYTHON_CMD -m venv venv
        venv/bin/python -m pip install --upgrade pip >> logs/dependency_install.log 2>&1
        venv/bin/python -m pip install -r requirements.txt >> logs/dependency_install.log 2>&1
    else
        echo "[INFO] Virtual environment check passed" >> "$LOG_FILE"
    fi
fi

# Verify all required modules are installed
echo "[INFO] Verifying required modules..." >> "$LOG_FILE"
venv/bin/python -c "import PySide6; import netaddr; import paramiko; print('Module check successful')" &>/dev/null
if [ $? -ne 0 ]; then
    echo "[WARNING] Some required modules may be missing, attempting to reinstall" >> "$LOG_FILE"
    echo "[WARNING] Some required modules may be missing, attempting to reinstall"
    venv/bin/python -m pip install --upgrade -r requirements.txt >> logs/dependency_install.log 2>&1
fi

# Launch the application with error handling
echo "[INFO] Launching netWORKS..." >> "$LOG_FILE"
echo "[INFO] Launching netWORKS..."

# Use the virtual environment's Python to run start.py
venv/bin/python start.py "$@"
APP_EXIT_CODE=$?
echo "[INFO] Application exited with code: $APP_EXIT_CODE" >> "$LOG_FILE"

# Clean up temporary file if setup completed successfully
if [ -f "setup_in_progress.tmp" ] && [ -d "venv" ]; then
    rm -f setup_in_progress.tmp
fi

# Check for specific error codes
if [ $APP_EXIT_CODE -ne 0 ]; then
    echo
    echo "[ERROR] The application exited with an error code: $APP_EXIT_CODE"
    
    # Specific error handling for common issues
    if [ $APP_EXIT_CODE -eq 1 ]; then
        echo "[INFO] The application encountered a general error" >> "$LOG_FILE"
        echo "[INFO] The application encountered a general error"
        
        if [ -f "logs/dependency_install.log" ]; then
            echo "[INFO] Dependency installation log found. Checking for issues..." >> "$LOG_FILE"
            echo "[INFO] Dependency installation log found. Checking for issues..."
            grep -q "Failed to install" logs/dependency_install.log
            if [ $? -eq 0 ]; then
                echo "[WARNING] Some dependencies failed to install" >> "$LOG_FILE"
                echo "[WARNING] Some dependencies failed to install"
                echo "[INFO] You may need to manually install missing packages"
                echo "[INFO] See logs/dependency_install.log for details"
            fi
        fi
        
        if [ -d "venv" ]; then
            echo "[INFO] Would you like to try repairing the dependencies? (y/n)"
            read REPAIR
            if [ "$REPAIR" = "y" ] || [ "$REPAIR" = "Y" ]; then
                echo "[INFO] Repairing virtual environment..." >> "$LOG_FILE"
                echo "[INFO] Repairing virtual environment..."
                rm -rf venv
                $PYTHON_CMD -m venv venv
                if [ -f "venv/bin/pip" ]; then
                    venv/bin/pip install --upgrade pip >> logs/dependency_install.log 2>&1
                    venv/bin/pip install -r requirements.txt >> logs/dependency_install.log 2>&1
                    echo "[INFO] Dependencies reinstalled. Please run the application again." >> "$LOG_FILE"
                    echo "[INFO] Dependencies reinstalled. Please run the application again."
                else
                    echo "[ERROR] Failed to repair virtual environment" >> "$LOG_FILE"
                    echo "[ERROR] Failed to repair virtual environment"
                fi
            fi
        fi
    elif [ $APP_EXIT_CODE -eq 2 ]; then
        echo "[INFO] The application encountered a command line syntax error" >> "$LOG_FILE"
        echo "[INFO] The application encountered a command line syntax error"
        echo "[INFO] Run the application without any command line arguments"
    elif [ $APP_EXIT_CODE -eq 9 ]; then
        echo "[INFO] The application encountered a permission error" >> "$LOG_FILE"
        echo "[INFO] The application encountered a permission error"
        echo "[INFO] Try running with sudo: sudo ./run.sh"
    elif [ $APP_EXIT_CODE -eq 130 ]; then
        echo "[INFO] The application was terminated by the user (Ctrl+C)" >> "$LOG_FILE"
        echo "[INFO] The application was terminated by the user (Ctrl+C)"
    elif [ $APP_EXIT_CODE -eq 137 ]; then
        echo "[WARNING] The application crashed, possibly due to insufficient memory" >> "$LOG_FILE"
        echo "[WARNING] The application crashed, possibly due to insufficient memory"
        echo "[INFO] Try closing other applications and running again"
    fi
    
    echo
    echo "[INFO] Check the logs directory for more details:"
    if [ -d "logs" ]; then
        echo "[INFO] - Check logs/launcher.log for launcher errors"
        echo "[INFO] - Check logs/dependency_install.log for dependency issues"
    else
        echo "[INFO] No logs directory found. The application may not have started properly."
    fi
    
    exit $APP_EXIT_CODE
else
    echo "[SUCCESS] netWORKS completed successfully" >> "$LOG_FILE"
    echo "[SUCCESS] netWORKS completed successfully"
fi

exit 0 