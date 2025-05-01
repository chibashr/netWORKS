#!/usr/bin/env python3
# repair_dependencies.py - Script to repair dependencies for netWORKS application

import os
import sys
import subprocess
import platform
import shutil
import time
import logging
from pathlib import Path

# Setup logging
if not os.path.exists('logs'):
    os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)

# Console colors for Windows and other platforms
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

def check_environment():
    """Check the current environment for issues"""
    print_status("Checking environment...", "progress")
    
    # Get the base directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    venv_dir = os.path.join(base_dir, 'venv')
    req_file = os.path.join(base_dir, 'requirements.txt')
    
    # Check if we're in the right directory
    if not os.path.exists(req_file):
        print_status("Requirements file not found. Are you running from the correct directory?", "error")
        return False
    
    # Check if virtual environment exists
    if not os.path.exists(venv_dir):
        print_status("Virtual environment not found.", "warning")
        print_status("Will create a new virtual environment.", "info")
        return True
    
    # Check if venv is functional
    if platform.system() == 'Windows':
        python_path = os.path.join(venv_dir, 'Scripts', 'python.exe')
    else:
        python_path = os.path.join(venv_dir, 'bin', 'python')
        
    if not os.path.exists(python_path):
        print_status("Virtual environment appears damaged (Python executable not found).", "error")
        print_status("Will recreate the virtual environment.", "info")
        return True
    
    # Test if the Python interpreter works
    try:
        result = subprocess.run([python_path, "-c", "print('Python test successful')"], 
                               capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            print_status("Virtual environment Python test failed.", "error")
            print_status("Will recreate the virtual environment.", "info")
            return True
    except Exception as e:
        print_status(f"Error testing Python interpreter: {e}", "error")
        print_status("Will recreate the virtual environment.", "info")
        return True
    
    print_status("Environment check completed.", "success")
    return True

def remove_virtual_environment():
    """Remove the existing virtual environment"""
    venv_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv')
    
    if os.path.exists(venv_dir):
        print_status("Removing existing virtual environment...", "progress")
        try:
            shutil.rmtree(venv_dir)
            print_status("Virtual environment removed successfully.", "success")
            return True
        except Exception as e:
            print_status(f"Failed to remove virtual environment: {str(e)}", "error")
            logging.error(f"Failed to remove virtual environment: {str(e)}", exc_info=True)
            return False
    return True

def create_virtual_environment():
    """Create a new virtual environment"""
    import venv as venv_module
    
    venv_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv')
    
    print_status("Creating new virtual environment...", "progress")
    try:
        venv_module.create(venv_dir, with_pip=True)
        print_status("Virtual environment created successfully.", "success")
        return True
    except Exception as e:
        print_status(f"Failed to create virtual environment: {str(e)}", "error")
        logging.error(f"Failed to create virtual environment: {str(e)}", exc_info=True)
        return False

def get_pip_path():
    """Get the path to pip executable"""
    base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv')
    
    if platform.system() == 'Windows':
        return os.path.join(base_path, 'Scripts', 'pip.exe')
    return os.path.join(base_path, 'bin', 'pip')

def install_dependencies(pip_path=None):
    """Install dependencies from requirements.txt"""
    if pip_path is None:
        pip_path = get_pip_path()
    
    req_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'requirements.txt')
    
    if not os.path.exists(pip_path):
        print_status(f"pip not found at {pip_path}. Cannot install dependencies.", "error")
        return False
    
    if not os.path.exists(req_file):
        print_status("requirements.txt not found. Cannot install dependencies.", "error")
        return False
    
    print_status("Installing dependencies...", "progress")
    
    # First upgrade pip
    try:
        print_status("Upgrading pip...", "info")
        upgrade_cmd = [pip_path, "install", "--upgrade", "pip"]
        subprocess.run(upgrade_cmd, check=True, capture_output=True)
    except Exception as e:
        print_status(f"Warning: Failed to upgrade pip: {e}", "warning")
    
    # Install all dependencies
    try:
        print_status("Installing packages from requirements.txt...", "progress")
        cmd = [pip_path, "install", "-r", req_file]
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            print_status("Warning: Issues detected during dependency installation.", "warning")
            print(process.stderr)
            
            # Try to identify problematic packages
            with open(req_file, 'r') as f:
                requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            problem_packages = []
            for req in requirements:
                cmd = [pip_path, "install", req]
                pkg_process = subprocess.run(cmd, capture_output=True, text=True)
                if pkg_process.returncode != 0:
                    problem_packages.append(req)
                    print_status(f"Failed to install: {req}", "error")
            
            if problem_packages:
                print_status("The following packages failed to install:", "error")
                for pkg in problem_packages:
                    print(f"  - {pkg}")
                print_status("You may need to install these packages manually or check for system dependencies.", "info")
                return False
        
        print_status("Dependencies installed successfully.", "success")
        return True
    except Exception as e:
        print_status(f"Failed to install dependencies: {str(e)}", "error")
        logging.error(f"Dependency installation error: {str(e)}", exc_info=True)
        return False

def verify_installation():
    """Verify that key packages are installed correctly"""
    print_status("Verifying installation...", "progress")
    
    if platform.system() == 'Windows':
        python_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv', 'Scripts', 'python.exe')
    else:
        python_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv', 'bin', 'python')
    
    if not os.path.exists(python_path):
        print_status("Python executable not found in virtual environment.", "error")
        return False
    
    # Test key packages
    key_packages = ["PyQt5", "scapy", "psutil", "nmap"]
    failed_packages = []
    
    for package in key_packages:
        try:
            cmd = [python_path, "-c", f"import {package}; print('{package} successfully imported')"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print_status(f"Package {package} verified.", "success")
            else:
                print_status(f"Package {package} failed to import.", "error")
                failed_packages.append(package)
        except Exception as e:
            print_status(f"Error verifying package {package}: {e}", "error")
            failed_packages.append(package)
    
    if failed_packages:
        print_status("Some packages failed verification:", "warning")
        for pkg in failed_packages:
            print(f"  - {pkg}")
        return False
    
    print_status("All key packages verified successfully.", "success")
    return True

def main():
    """Main function for dependency repair"""
    # Enable colors on Windows
    if platform.system() == 'Windows':
        os.system('color')
    
    print_status("netWORKS Dependency Repair Tool", "info")
    print_status("================================", "info")
    print()
    
    # Check the environment
    if not check_environment():
        print_status("Environment check failed. Cannot continue.", "error")
        input("Press Enter to exit...")
        return 1
    
    # Ask for confirmation
    print()
    print_status("This tool will attempt to repair your netWORKS installation by:", "info")
    print("  1. Removing the existing virtual environment (if present)")
    print("  2. Creating a new virtual environment")
    print("  3. Installing all dependencies from requirements.txt")
    print("  4. Verifying that key packages are installed correctly")
    print()
    print_status("Do you want to continue? (y/n)", "info")
    response = input().strip().lower()
    
    if response != 'y':
        print_status("Repair cancelled.", "info")
        return 0
    
    # Remove existing virtual environment
    if not remove_virtual_environment():
        print_status("Failed to remove existing virtual environment.", "error")
        print_status("Please try to remove the 'venv' directory manually and run this script again.", "info")
        input("Press Enter to exit...")
        return 1
    
    # Create a new virtual environment
    if not create_virtual_environment():
        print_status("Failed to create virtual environment.", "error")
        input("Press Enter to exit...")
        return 1
    
    # Wait a moment for the filesystem to catch up
    time.sleep(1)
    
    # Install dependencies
    if not install_dependencies():
        print_status("Failed to install all dependencies.", "error")
        print_status("Some features may not work correctly.", "warning")
    
    # Verify installation
    if not verify_installation():
        print_status("Installation verification failed.", "warning")
        print_status("The application may not function correctly.", "warning")
        print_status("Try running the application and see if it works.", "info")
    else:
        print_status("Dependency repair completed successfully!", "success")
    
    print()
    print_status("Repair process completed. You can now run the application.", "info")
    input("Press Enter to exit...")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nRepair process cancelled by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        logging.error("Unhandled exception", exc_info=True)
        print("See logs/dependency_repair.log for details.")
        input("Press Enter to exit...")
        sys.exit(1) 