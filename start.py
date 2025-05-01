#!/usr/bin/env python3
# start.py - Entry point for netWORKS application

import os
import sys
import traceback
import subprocess
import platform
import logging
import shutil
from pathlib import Path

# Set up logging
def setup_logging():
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / 'application.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('netWORKS')

logger = setup_logging()

# Determine the current OS
CURRENT_OS = platform.system()
logger.info(f"Detected OS: {CURRENT_OS}")
logger.info(f"Python version: {platform.python_version()}")

# Add the current directory to path for importing modules
current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
scripts_dir = current_dir / 'scripts'
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))
    logger.info(f"Added scripts directory to path: {scripts_dir}")

def check_python_version():
    """Check if Python version is compatible (3.9+)"""
    if sys.version_info < (3, 9):
        logger.error(f"Python 3.9+ required. Current version: {platform.python_version()}")
        print(f"\nERROR: Python 3.9 or higher is required. Current version: {platform.python_version()}")
        print("Please install Python 3.9+ from https://www.python.org/downloads/")
        return False
    return True

def check_venv():
    """Check if running in a virtual environment"""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        logger.info("Running inside a virtual environment")
        return True
    else:
        logger.info("Not running inside a virtual environment")
        return False

def create_venv():
    """Create a virtual environment if it doesn't exist"""
    venv_dir = current_dir / 'venv'
    
    if venv_dir.exists():
        logger.info("Virtual environment directory already exists")
        return True
    
    try:
        logger.info("Creating virtual environment...")
        subprocess.run([sys.executable, '-m', 'venv', str(venv_dir)], check=True)
        logger.info("Virtual environment created successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create virtual environment: {e}")
        print("\nERROR: Failed to create virtual environment.")
        print("Try installing venv module with: python -m pip install virtualenv")
        return False

def install_dependencies():
    """Install required dependencies"""
    requirements_file = current_dir / 'requirements.txt'
    
    if not requirements_file.exists():
        logger.error("requirements.txt not found")
        print("\nERROR: requirements.txt not found.")
        print("Please make sure you're running the script from the correct directory.")
        return False
    
    venv_dir = current_dir / 'venv'
    
    # Determine the path to pip based on the OS
    if CURRENT_OS == 'Windows':
        pip_path = venv_dir / 'Scripts' / 'pip'
    else:  # Linux/MacOS
        pip_path = venv_dir / 'bin' / 'pip'
    
    try:
        logger.info("Installing dependencies...")
        
        # Ensure pip is up to date
        log_file = Path('logs') / 'dependency_install.log'
        with open(log_file, 'w') as f:
            subprocess.run([str(pip_path), 'install', '--upgrade', 'pip'], 
                          stdout=f, stderr=subprocess.STDOUT, check=True)
            
            # Install requirements
            subprocess.run([str(pip_path), 'install', '-r', str(requirements_file)], 
                          stdout=f, stderr=subprocess.STDOUT, check=True)
        
        logger.info("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        print("\nERROR: Failed to install dependencies.")
        print("Check logs/dependency_install.log for details.")
        return False

def run_application():
    """Run the main application"""
    try:
        # Import the launcher module
        import launcher
        logger.info("Launcher module imported successfully")
        
        # Run the main function from the launcher
        return launcher.main()
        
    except ImportError as e:
        logger.error(f"Failed to import launcher module: {e}")
        print("\nERROR: Failed to import the launcher module.")
        print(f"Import error: {str(e)}")
        print("\nPossible solutions:")
        print("1. Make sure the 'scripts' directory exists and contains launcher.py")
        print("2. Check if you're running start.py from the correct directory")
        print("3. Make sure you have Python 3.9+ installed correctly")
        
        if not (scripts_dir / 'launcher.py').exists():
            logger.error("launcher.py not found in scripts directory")
            print("\nThe launcher.py file was not found in the scripts directory.")
        
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during application startup: {str(e)}")
        logger.error(traceback.format_exc())
        print("\nERROR: An unexpected error occurred while starting the application.")
        print(f"Error details: {str(e)}")
        print("\nStack trace for debugging:")
        traceback.print_exc()
        return 1

def main():
    """Main entry point"""
    # Check Python version
    if not check_python_version():
        return 1
    
    # Check if we're in a virtual environment
    in_venv = check_venv()
    
    # If not in a virtual environment, set one up
    if not in_venv:
        logger.info("Not in virtual environment, checking if one exists...")
        
        # Check if venv exists but we're not using it
        venv_dir = current_dir / 'venv'
        
        if not venv_dir.exists():
            if not create_venv():
                return 1
            
            if not install_dependencies():
                return 1
        
        # Re-launch the script using the virtual environment
        logger.info("Relaunching using the virtual environment...")
        
        if CURRENT_OS == 'Windows':
            python_path = venv_dir / 'Scripts' / 'python'
        else:  # Linux/MacOS
            python_path = venv_dir / 'bin' / 'python'
        
        try:
            args = [str(python_path), __file__] + sys.argv[1:]
            sys.exit(subprocess.call(args))
        except Exception as e:
            logger.error(f"Failed to relaunch using virtual environment: {e}")
            print(f"\nERROR: Failed to relaunch using virtual environment: {str(e)}")
            return 1
    
    # Run the actual application
    return run_application()

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Application terminated by user (KeyboardInterrupt)")
        print("\nApplication terminated by user.")
        sys.exit(130)
    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}")
        logger.critical(traceback.format_exc())
        print(f"\nCRITICAL ERROR: {str(e)}")
        print("See logs/application.log for details.")
        sys.exit(1) 