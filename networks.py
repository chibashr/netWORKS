#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main entry point for NetWORKS application
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path for imports
if __name__ == "__main__":
    # Determine the application directory
    if getattr(sys, 'frozen', False):
        # Running as executable
        app_dir = Path(sys.executable).parent
        # Add the bundled src directory to sys.path
        src_path = app_dir / "src"
        if src_path.exists():
            sys.path.insert(0, str(src_path))
        else:
            # Fallback - look for src in the temp directory created by PyInstaller
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            for item in temp_dir.iterdir():
                if item.name.startswith('_MEI') and item.is_dir():
                    src_path = item / "src"
                    if src_path.exists():
                        sys.path.insert(0, str(src_path))
                        break
    else:
        # Running as script
        app_dir = Path(__file__).parent
        src_path = app_dir / "src"
        sys.path.insert(0, str(src_path))

try:
    # Import first-time setup
    from src.core.first_time_setup import run_first_time_setup_if_needed
    
    # Run first-time setup if needed
    if not run_first_time_setup_if_needed():
        print("First-time setup failed. Exiting.")
        sys.exit(1)
    
    # Import and run the main application
    from src.app import Application
    
    app = Application(sys.argv)
    sys.exit(app.run())
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all dependencies are installed.")
    print("Try running: pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"Application error: {e}")
    sys.exit(1)
