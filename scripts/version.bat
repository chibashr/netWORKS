@echo off
REM netWORKS Version Management Utility

REM Check if Python is available
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python is not installed or not in PATH
    echo Please install Python 3.9+ and try again
    exit /b 1
)

REM Pass all arguments to the version manager script
python core/version_manager.py %*

REM If no arguments provided, show help
if "%~1"=="" (
    echo.
    echo netWORKS Version Management
    echo ------------------------
    echo.
    echo Available commands:
    echo   version get               - Show current version
    echo   version set               - Set version information
    echo   version bump [component]  - Increment version component
    echo   version change [message]  - Add change to changelog
    echo   version changelog         - Update changelog file
    echo   version manifest          - Display current manifest
    echo.
    echo For more details, see docs/versioning.md
) 