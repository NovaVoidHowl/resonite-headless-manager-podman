#!/bin/bash

# This script is used to clean up the Python virtual environment and remove unnecessary files.
# Remove the Python virtual environment directory
if [ -d "Res-Manager" ]; then
    echo "Removing Python virtual environment..."
    rm -rf Res-Manager
else
    echo "No Python virtual environment found."
fi

# Remove the python cache directories
echo "Removing Python cache directories..."
find . -type d -name "__pycache__" -exec rm -rf {} +

echo "Cleanup completed."
