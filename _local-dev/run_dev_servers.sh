#!/bin/bash
# Development server launcher for Linux/macOS
# This script runs the Python development server script

echo "Starting Resonite Headless Manager Development Servers..."
echo

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "Error: Python is not installed or not in PATH"
    echo "Please install Python and try again"
    exit 1
fi

# Use python3 if available, otherwise python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

# Run the development servers
$PYTHON_CMD run_dev_servers.py

# Exit with the same code as the Python script
exit $?
