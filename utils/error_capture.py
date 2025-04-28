import sys 
import traceback 
import os 
import datetime 

def run_with_error_capture():
    """Run the main application with error capturing."""
    try: 
        import netWORKS 
        sys.exit(netWORKS.main()) 
    except Exception as e: 
        # Get timestamp 
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") 
        # Ensure logs directory exists 
        os.makedirs("logs", exist_ok=True) 
        # Create crash log 
        with open(f"logs/crash_{timestamp}.log", "w") as f: 
            f.write(f"CRASH REPORT - {datetime.datetime.now()}\n\n") 
            f.write(f"ERROR: {type(e).__name__}: {str(e)}\n\n") 
            f.write("TRACEBACK:\n") 
            f.write(traceback.format_exc()) 
            f.write("\n\nSYSTEM INFO:\n") 
            f.write(f"Python version: {sys.version}\n") 
            f.write(f"OS: {os.name} - {sys.platform}\n") 
            # List modules 
            f.write("\nLOADED MODULES:\n") 
            for name, module in sys.modules.items(): 
                if hasattr(module, "__file__") and module.__file__: 
                    f.write(f"{name}: {module.__file__}\n") 
        # Print error to console 
        print(f"\n[FATAL ERROR] {type(e).__name__}: {str(e)}") 
        print(f"\nA crash report has been saved to logs/crash_{timestamp}.log") 
        print("\nTraceback:") 
        traceback.print_exc() 
        sys.exit(1)

# Run if executed directly
if __name__ == "__main__":
    run_with_error_capture() 