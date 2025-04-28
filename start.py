#!/usr/bin/env python3
# start.py - Entry point for netWORKS application

import os
import sys
import traceback

# Add the scripts directory to path for importing the launcher
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.join(current_dir, 'scripts')
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

try:
    # Import the launcher module
    import launcher
    
    # Run the main function from the launcher
    sys.exit(launcher.main())
    
except ImportError as e:
    print("\nERROR: Failed to import the launcher module.")
    print(f"Import error: {str(e)}")
    print("\nPossible solutions:")
    print("1. Make sure the 'scripts' directory exists and contains launcher.py")
    print("2. Check if you're running start.py from the correct directory")
    print("3. Make sure you have Python 3.9+ installed correctly")
    
    if not os.path.exists(os.path.join(scripts_dir, 'launcher.py')):
        print("\nThe launcher.py file was not found in the scripts directory.")
    
    print("\nPress Enter to exit...")
    input()
    sys.exit(1)
except Exception as e:
    print("\nERROR: An unexpected error occurred while starting the application.")
    print(f"Error details: {str(e)}")
    print("\nStack trace for debugging:")
    traceback.print_exc()
    print("\nPress Enter to exit...")
    input()
    sys.exit(1) 