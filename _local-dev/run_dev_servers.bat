@echo off
REM Development server launcher for Windows
REM This batch file runs the Python development server script

echo Starting Resonite Headless Manager Development Servers...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

REM Run the development servers
python run_dev_servers.py

REM Keep the window open if there was an error
if errorlevel 1 (
    echo.
    echo An error occurred. Press any key to close...
    pause >nul
)
