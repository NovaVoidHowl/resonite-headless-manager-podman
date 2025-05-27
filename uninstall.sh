#!/bin/bash

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root (with sudo)"
    exit 1
fi

# Stop and disable the websocket service
echo "Stopping and removing WebSocket server service..."
systemctl stop resonite-manager-websocket.service
systemctl disable resonite-manager-websocket.service

# Check if webserver service exists and remove it if it does
if [ -f /etc/systemd/system/resonite-manager-webserver.service ]; then
    echo "Detected web interface service, removing it..."
    systemctl stop resonite-manager-webserver.service
    systemctl disable resonite-manager-webserver.service
    rm -f /etc/systemd/system/resonite-manager-webserver.service
fi

# Remove websocket service file
rm -f /etc/systemd/system/resonite-manager-websocket.service

# Reload systemd
systemctl daemon-reload

# Clean up virtual environment
echo "Cleaning up Python virtual environment..."
rm -rf Res-Manager

# Remove Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +

# Optionally remove .env file
read -p "Do you want to remove the .env file? (y/N): " remove_env
if [[ $remove_env =~ ^[Yy]$ ]]; then
    rm -f .env
    echo ".env file removed"
fi

echo "Uninstallation complete!"