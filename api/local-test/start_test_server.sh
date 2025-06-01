#!/bin/bash

# Start Test Server Script for Resonite Headless Manager API
# This script starts the test server with dummy data for API testing

echo ""
echo "🧪 Starting Resonite Headless Manager API Test Server"
echo "====================================================="
echo ""

# Check if we're in the right directory
if [ ! -f "test_server.py" ]; then
    echo "❌ Error: test_server.py not found in current directory"
    echo "Please run this script from the api/ directory"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Error: Python not found"
    echo "Please install Python 3.7+ to run the test server"
    exit 1
fi

# Determine Python command
PYTHON_CMD="python"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
fi

echo "✅ Python found: $PYTHON_CMD"

# Check if required packages are installed
echo "🔍 Checking required packages..."

$PYTHON_CMD -c "import fastapi, uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Missing required packages (fastapi, uvicorn)"
    echo "Installing required packages..."
    $PYTHON_CMD -m pip install fastapi uvicorn python-multipart
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install required packages"
        echo "Please install manually: pip install fastapi uvicorn python-multipart"
        exit 1
    fi
fi

echo "✅ All required packages are available"
echo ""

# Check if port 8000 is in use
if command -v netstat &> /dev/null; then
    PORT_CHECK=$(netstat -tulpn 2>/dev/null | grep :8000)
    if [ ! -z "$PORT_CHECK" ]; then
        echo "⚠️  Warning: Port 8000 appears to be in use"
        echo "   The server may fail to start if another process is using this port"
        echo ""
    fi
fi

echo "🚀 Starting test server..."
echo "   Server will be available at: http://localhost:8000"
echo "   Press Ctrl+C to stop the server"
echo ""
echo "====================================================="

# Start the test server
$PYTHON_CMD test_server.py
