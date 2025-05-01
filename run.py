#!/usr/bin/env python3
# Universal launcher for netWORKS
# This script detects the platform and launches the appropriate script

import os
import sys
import platform
import subprocess
import logging
from pathlib import Path

def setup_logging():
    """Set up logging for the launcher"""
    # Configure logging
    os.makedirs('logs', exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(os.path.join('logs', 'run.log')),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('netWORKS-Launcher')

logger = setup_logging()

def is_admin():
    """Check if the script is running with administrator privileges"""
    try:
        if platform.system() == 'Windows':
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.geteuid() == 0
    except:
        return False

def main():
    """Main entry point for the universal launcher"""
    current_os = platform.system()
    logger.info(f"Detected OS: {current_os}")
    
    # Get the directory of this script
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(script_dir)
    
    # Check if we're in the root directory
    if not (script_dir / 'requirements.txt').exists():
        logger.error("requirements.txt not found. Please run from the correct directory.")
        print("[ERROR] requirements.txt not found. Please run from the correct directory.")
        return 1
    
    # Check for admin rights if needed features might require them
    if is_admin():
        logger.info("Running with administrator privileges")
    else:
        logger.info("Running without administrator privileges")
        
    try:
        # Launch the appropriate script based on OS
        if current_os == 'Windows':
            logger.info("Launching Windows batch script (run.bat)")
            
            # Check if run.bat exists
            if not (script_dir / 'run.bat').exists():
                logger.error("run.bat not found")
                print("[ERROR] run.bat not found")
                return 1
                
            # Use subprocess to run the batch file
            process = subprocess.Popen(['cmd.exe', '/c', 'run.bat'] + sys.argv[1:])
            return process.wait()
            
        else:  # Linux, macOS, etc.
            logger.info("Launching Unix shell script (run.sh)")
            
            # Check if run.sh exists
            shell_script = script_dir / 'run.sh'
            if not shell_script.exists():
                logger.error("run.sh not found")
                print("[ERROR] run.sh not found")
                return 1
                
            # Make sure run.sh is executable
            try:
                shell_script.chmod(0o755)  # rwxr-xr-x
            except:
                logger.warning("Could not make run.sh executable. May need manual intervention.")
            
            # Use subprocess to run the shell script
            process = subprocess.Popen(['bash', str(shell_script)] + sys.argv[1:])
            return process.wait()
            
    except Exception as e:
        logger.error(f"Error launching script: {str(e)}")
        print(f"[ERROR] Failed to launch: {str(e)}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Launcher terminated by user (KeyboardInterrupt)")
        print("\nLauncher terminated by user.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        print(f"\n[ERROR] Unhandled exception: {str(e)}")
        print("See logs/run.log for details.")
        sys.exit(1) 