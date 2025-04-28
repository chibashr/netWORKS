#!/usr/bin/env python3
# launcher.py - Consolidated launcher for netWORKS application
# This script handles environment setup, first-time configuration, and error handling

import os
import sys
import subprocess
import platform
import venv
import shutil
from pathlib import Path
import time
import logging

# Initialize basic logging
if not os.path.exists('logs'):
    os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    filename=os.path.join('logs', 'launcher.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Console output colors
class Colors:
    if platform.system() == 'Windows':
        HEADER = '\033[95m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        GREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        END = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'
    else:
        HEADER = '\033[95m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        GREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        END = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'

def print_status(message, status="info"):
    """Print a formatted status message"""
    status_prefix = {
        "info": f"{Colors.BLUE}[INFO]{Colors.END}",
        "success": f"{Colors.GREEN}[SUCCESS]{Colors.END}",
        "warning": f"{Colors.WARNING}[WARNING]{Colors.END}",
        "error": f"{Colors.FAIL}[ERROR]{Colors.END}",
        "progress": f"{Colors.CYAN}[...]{Colors.END}"
    }
    
    prefix = status_prefix.get(status.lower(), status_prefix["info"])
    print(f"{prefix} {message}")
    
    # Also log the message without color codes
    log_level = {
        "info": logging.INFO,
        "success": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "progress": logging.INFO
    }
    logging.log(log_level.get(status.lower(), logging.INFO), message)

def check_python_version():
    """Check if the Python version is compatible"""
    if sys.version_info < (3, 9):
        print_status(f"Python 3.9 or higher is required. You are using {sys.version.split()[0]}", "error")
        return False
    return True

def create_virtual_environment():
    """Create virtual environment if it doesn't exist"""
    venv_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv')
    
    if not os.path.exists(venv_dir):
        print_status("Creating virtual environment...", "progress")
        try:
            venv.create(venv_dir, with_pip=True)
            print_status("Virtual environment created successfully", "success")
            return True
        except Exception as e:
            print_status(f"Failed to create virtual environment: {str(e)}", "error")
            logging.error(f"Virtual environment creation error: {str(e)}", exc_info=True)
            return False
    return True

def get_pip_path():
    """Get the pip executable path based on the platform"""
    base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv')
    
    if platform.system() == 'Windows':
        return os.path.join(base_path, 'Scripts', 'pip.exe')
    return os.path.join(base_path, 'bin', 'pip')

def get_python_path():
    """Get the python executable path based on the platform"""
    base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv')
    
    if platform.system() == 'Windows':
        return os.path.join(base_path, 'Scripts', 'python.exe')
    return os.path.join(base_path, 'bin', 'python')

def install_dependencies(force_upgrade=False):
    """Install required dependencies from requirements.txt"""
    req_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'requirements.txt')
    
    if not os.path.exists(req_file):
        print_status("requirements.txt not found. Cannot install dependencies.", "error")
        return False
    
    pip_path = get_pip_path()
    
    if not os.path.exists(pip_path):
        print_status(f"pip not found at {pip_path}. Cannot install dependencies.", "error")
        return False
    
    print_status("Installing dependencies...", "progress")
    
    try:
        # First upgrade pip itself
        print_status("Upgrading pip...", "progress")
        upgrade_cmd = [pip_path, "install", "--upgrade", "pip"]
        pip_upgrade = subprocess.run(upgrade_cmd, capture_output=True, text=True)
        if pip_upgrade.returncode != 0:
            print_status("Warning: Failed to upgrade pip. Continuing with existing version.", "warning")
            print(pip_upgrade.stderr)
        
        # Install requirements with or without upgrade flag
        print_status(f"Installing {'and upgrading ' if force_upgrade else ''}packages from requirements.txt...", "progress")
        
        # Use a temporary file to capture detailed installation output
        log_file = os.path.join('logs', 'dependency_install.log')
        with open(log_file, 'w') as f:
            f.write(f"Dependency installation started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"Using pip: {pip_path}\n")
            f.write(f"Using requirements file: {req_file}\n\n")
        
        # Split installation into chunks to better identify problematic packages
        with open(req_file, 'r') as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        # Try to install all requirements first
        if force_upgrade:
            cmd = [pip_path, "install", "--upgrade", "-r", req_file]
        else:
            cmd = [pip_path, "install", "-r", req_file]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        # Log the full output
        with open(log_file, 'a') as f:
            f.write("FULL INSTALL OUTPUT:\n")
            f.write(process.stdout + "\n")
            f.write(process.stderr + "\n\n")
        
        # Handle errors
        if process.returncode != 0 or "error" in process.stderr.lower():
            print_status("Warning: Issues detected during dependency installation.", "warning")
            print_status("Attempting to install packages individually to identify problems...", "progress")
            
            # Try to install each package individually to identify problematic ones
            failed_packages = []
            for req in requirements:
                if not req or req.startswith('#'):
                    continue
                    
                print_status(f"Installing {req}...", "progress")
                cmd = [pip_path, "install", req]
                pkg_process = subprocess.run(cmd, capture_output=True, text=True)
                
                if pkg_process.returncode != 0:
                    print_status(f"Failed to install {req}", "error")
                    failed_packages.append(req)
                    # Log the error
                    with open(log_file, 'a') as f:
                        f.write(f"FAILED PACKAGE: {req}\n")
                        f.write(pkg_process.stderr + "\n\n")
            
            if failed_packages:
                print_status(f"Failed to install {len(failed_packages)} packages:", "error")
                for pkg in failed_packages:
                    print(f"  - {pkg}")
                print_status("See logs/dependency_install.log for details", "info")
                return False
            
        print_status("Dependencies installed successfully", "success")
        return True
    except subprocess.CalledProcessError as e:
        print_status(f"Failed to install dependencies: {e}", "error")
        print(e.stderr if e.stderr else "No error output available")
        logging.error(f"Dependency installation error: {str(e)}\nOutput: {e.stderr}", exc_info=True)
        return False
    except Exception as e:
        print_status(f"Unexpected error installing dependencies: {str(e)}", "error")
        logging.error(f"Dependency installation unexpected error: {str(e)}", exc_info=True)
        return False

def setup_core_plugins():
    """Setup core plugins if needed"""
    # Look for the setup script
    setup_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                               'scripts', 'setup_core_plugins.py')
    
    if not os.path.exists(setup_script):
        print_status("Core plugins setup script not found. Skipping plugin setup.", "warning")
        return False
    
    python_path = get_python_path()
    
    if not os.path.exists(python_path):
        print_status(f"Python not found at {python_path}. Cannot setup plugins.", "error")
        return False
    
    print_status("Setting up core plugins...", "progress")
    
    try:
        cmd = [python_path, setup_script]
        process = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        if "error" in process.stderr.lower():
            print_status("Warning: Possible errors during plugin setup:", "warning")
            print(process.stderr)
            return False
            
        print_status("Core plugins setup completed", "success")
        return True
    except subprocess.CalledProcessError as e:
        print_status(f"Failed to setup core plugins: {e}", "error")
        print(e.stderr if e.stderr else "No error output available")
        logging.error(f"Plugin setup error: {str(e)}\nOutput: {e.stderr}", exc_info=True)
        return False
    except Exception as e:
        print_status(f"Unexpected error setting up plugins: {str(e)}", "error")
        logging.error(f"Plugin setup unexpected error: {str(e)}", exc_info=True)
        return False

def run_application():
    """Run the main application"""
    python_path = get_python_path()
    
    if not os.path.exists(python_path):
        print_status(f"Python not found at {python_path}. Cannot run application.", "error")
        print_status("Try running setup again or reinstalling the application.", "info")
        return 1
    
    app_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'netWORKS.py')
    
    if not os.path.exists(app_script):
        print_status("Application script (netWORKS.py) not found.", "error")
        print_status("Please ensure all files were correctly installed.", "info")
        print_status("Try downloading the application again or check your installation.", "info")
        return 1
    
    print_status("Starting netWORKS application...", "progress")
    
    # Check for plugins directory
    plugins_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'plugins')
    if not os.path.exists(plugins_dir) or not os.path.isdir(plugins_dir):
        print_status("Warning: Plugins directory not found. Core functionality may be limited.", "warning")
        try:
            os.makedirs(plugins_dir, exist_ok=True)
            print_status("Created plugins directory.", "info")
        except Exception as e:
            logging.warning(f"Failed to create plugins directory: {e}")
    
    # Check for required plugin directories
    core_plugins_dir = os.path.join(plugins_dir, 'core')
    if not os.path.exists(core_plugins_dir):
        print_status("Warning: Core plugins directory not found. Setting up now...", "warning")
        try:
            os.makedirs(core_plugins_dir, exist_ok=True)
            setup_core_plugins()
        except Exception as e:
            logging.warning(f"Failed to set up core plugins: {e}")
    
    try:
        # Pass through any command-line arguments to the main script
        cmd = [python_path, app_script] + sys.argv[1:]
        
        # Log the exact command being run
        logging.info(f"Running command: {' '.join(cmd)}")
        
        # Run the application
        process = subprocess.run(cmd, check=False)
        
        # Log the application exit code
        exit_code = process.returncode
        if exit_code == 0:
            logging.info("Application exited successfully with code 0")
        else:
            logging.error(f"Application exited with error code: {exit_code}")
            
            # Provide additional diagnostic information
            if exit_code == 1:
                print_status("The application exited with a general error.", "error")
            elif exit_code == 2:
                print_status("The application exited with a command line syntax error.", "error")
            elif exit_code == 9:
                print_status("The application encountered a permission error.", "error")
                print_status("Try running the application with administrator privileges.", "info")
            elif exit_code == 137 or exit_code == 134 or exit_code == 139:
                print_status("The application crashed due to a memory error or segmentation fault.", "error")
                print_status("This could be due to insufficient system resources or a bug.", "info")
        
        return exit_code
    except KeyboardInterrupt:
        print_status("Application terminated by user.", "warning")
        return 130  # Standard exit code for Ctrl+C
    except Exception as e:
        print_status(f"Failed to run application: {str(e)}", "error")
        logging.error(f"Application run error: {str(e)}", exc_info=True)
        
        # Try to get more diagnostic information
        print_status("Performing diagnostic checks...", "info")
        try:
            # Check Python executable
            subprocess.run([python_path, "--version"], check=True, capture_output=True)
            print_status("Python executable is working correctly.", "success")
            
            # Check module imports
            test_cmd = [python_path, "-c", "import sys; print('Python path:', sys.path)"]
            subprocess.run(test_cmd, check=True)
            
            # Test import of a few key modules
            modules_to_test = ["PyQt5", "scapy", "nmap", "psutil"]
            for module in modules_to_test:
                test_import = subprocess.run(
                    [python_path, "-c", f"import {module}; print('{module} imported successfully')"],
                    capture_output=True,
                    text=True
                )
                if test_import.returncode == 0:
                    print_status(f"Module '{module}' is available.", "success")
                else:
                    print_status(f"Module '{module}' could not be imported.", "error")
                    print_status(f"Error: {test_import.stderr.strip()}", "error")
                    
        except Exception as diag_error:
            print_status(f"Diagnostic check failed: {diag_error}", "error")
            
        return 1

def check_first_time_setup():
    """Perform first-time setup checks and operations"""
    venv_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv')
    setup_marker = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'setup_in_progress.tmp')
    
    # Check if we previously had a failed setup
    recovering_from_failed_setup = False
    if os.path.exists(setup_marker) and not os.path.exists(venv_dir):
        recovering_from_failed_setup = True
        try:
            with open(setup_marker, 'r') as f:
                timestamp = f.read().strip()
            print_status(f"Recovering from a previous failed setup attempt ({timestamp})...", "warning")
        except:
            print_status("Recovering from a previous failed setup attempt...", "warning")
    
    # Create setup tracking file
    if not os.path.exists(venv_dir):
        try:
            with open(setup_marker, 'w') as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
        except Exception as e:
            logging.warning(f"Could not create setup marker file: {e}")
    
    # First time setup
    if not os.path.exists(venv_dir):
        print_status("First-time setup: Creating environment and installing dependencies...", "info")
        print_status("This may take a few minutes. Please be patient.", "info")
        
        # Create the virtual environment
        if not create_virtual_environment():
            print_status("Failed to create virtual environment. Aborting setup.", "error")
            return False
        
        # Give the system a moment to register the new venv
        time.sleep(1)
        
        # Install dependencies
        print_status("Installing required dependencies...", "progress")
        if not install_dependencies(force_upgrade=True):
            print_status("Failed to install all dependencies.", "error")
            print_status("The application may not function correctly.", "warning")
            print_status("Check logs/dependency_install.log for details on failed packages.", "info")
            
            # Ask if user wants to continue despite errors
            print_status("Do you want to continue with setup despite dependency issues? (y/n)", "info")
            response = input().strip().lower()
            if response != 'y':
                return False
        
        # Setup core plugins
        print_status("Setting up core plugins...", "progress")
        if not setup_core_plugins():
            print_status("Core plugins setup had issues, but we'll continue anyway.", "warning")
        
        # Clean up setup marker
        try:
            if os.path.exists(setup_marker):
                os.remove(setup_marker)
        except Exception as e:
            logging.warning(f"Could not remove setup marker file: {e}")
        
        print_status("First-time setup completed successfully!", "success")
        return True
    
    # Check for incomplete setup
    if os.path.exists(setup_marker) and os.path.exists(venv_dir):
        print_status("Cleaning up from previous setup...", "info")
        try:
            os.remove(setup_marker)
        except Exception as e:
            logging.warning(f"Could not remove setup marker file: {e}")
    
    # Check if dependencies might need updating
    try:
        req_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'requirements.txt')
        if os.path.exists(req_file):
            req_mtime = os.path.getmtime(req_file)
            current_time = time.time()
            # If requirements.txt was modified in the last day
            if current_time - req_mtime < 86400:  # 24 hours in seconds
                print_status("Requirements file was recently updated. Updating dependencies...", "info")
                install_dependencies(force_upgrade=True)
            # Or check once a week for updates
            elif not os.path.exists(os.path.join('logs', 'last_dependency_check.txt')) or \
                 current_time - os.path.getmtime(os.path.join('logs', 'last_dependency_check.txt')) > 604800:  # 7 days
                print_status("Performing weekly dependency check...", "info")
                # Update the timestamp file
                with open(os.path.join('logs', 'last_dependency_check.txt'), 'w') as f:
                    f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
                # Check dependencies but don't force upgrade
                install_dependencies(force_upgrade=False)
    except Exception as e:
        print_status(f"Error checking requirements file: {str(e)}", "warning")
        logging.warning(f"Requirements check error: {str(e)}", exc_info=True)
    
    return True

def main():
    """Main entry point for the launcher"""
    try:
        # Enable colors on Windows
        if platform.system() == 'Windows':
            os.system('color')
        
        print_status("netWORKS Launcher v1.0", "info")
        
        if not check_python_version():
            return 1
        
        # Perform first-time setup if needed
        if not check_first_time_setup():
            print_status("First-time setup failed. Please check the errors above.", "error")
            input("Press Enter to exit...")
            return 1
        
        # Run the main application
        return run_application()
        
    except KeyboardInterrupt:
        print_status("\nLauncher terminated by user", "warning")
        return 0
    except Exception as e:
        print_status(f"Unhandled exception in launcher: {str(e)}", "error")
        logging.error("Unhandled exception in launcher", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 