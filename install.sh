#!/bin/bash

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root (with sudo)"
    exit 1
fi

# Get the absolute path of the current directory
INSTALL_DIR=$(pwd)

# Ask about web interface installation
read -p "Do you want to install the web interface? (This is optional if you're only using direct WebSocket connections) (y/N): " install_webserver
install_webserver=${install_webserver:-n}  # Default to no

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating new .env file..."
    touch .env
    read -p "Enter CONTAINER_NAME: " CONTAINER_NAME
    read -p "Enter CONFIG_PATH: " CONFIG_PATH
    read -p "Enter SERVER_IP (e.g. 192.168.1.100): " SERVER_IP
    echo "CONTAINER_NAME=$CONTAINER_NAME" >> .env
    echo "CONFIG_PATH=$CONFIG_PATH" >> .env
    echo "SERVER_IP=$SERVER_IP" >> .env
else
    echo ".env file already exists"
fi

# Create Python virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv Res-Manager
source Res-Manager/bin/activate
pip install -r requirements.txt

# Create systemd service file for the WebSocket server
echo "Creating WebSocket server service file..."
cat > /etc/systemd/system/resonite-manager-websocket.service << EOF
[Unit]
Description=Resonite Headless Manager WebSocket Server
After=network.target
Before=resonite-manager-webserver.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONPATH=$INSTALL_DIR/Res-Manager/lib/python3.11/site-packages
Environment=PATH=$INSTALL_DIR/Res-Manager/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
ExecStart=$INSTALL_DIR/Res-Manager/bin/python $INSTALL_DIR/server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Set permissions for websocket service file
chmod 644 /etc/systemd/system/resonite-manager-websocket.service

if [[ $install_webserver =~ ^[Yy]$ ]]; then
    # Create systemd service file for the static web server
    echo "Creating static web server service file..."
    cat > /etc/systemd/system/resonite-manager-webserver.service << EOF
[Unit]
Description=Resonite Headless Manager Static Web Server
After=network.target resonite-manager-websocket.service
Requires=resonite-manager-websocket.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONPATH=$INSTALL_DIR/Res-Manager/lib/python3.11/site-packages
Environment=PATH=$INSTALL_DIR/Res-Manager/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
ExecStart=$INSTALL_DIR/Res-Manager/bin/python $INSTALL_DIR/webserver.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # Set permissions for webserver service file
    chmod 644 /etc/systemd/system/resonite-manager-webserver.service
fi

# Reload systemd and enable/start services
systemctl daemon-reload
systemctl enable resonite-manager-websocket.service
systemctl start resonite-manager-websocket.service

if [[ $install_webserver =~ ^[Yy]$ ]]; then
    systemctl enable resonite-manager-webserver.service
    systemctl start resonite-manager-webserver.service
fi

echo "Installation complete!"
echo "WebSocket server is now running and will start automatically on boot"
echo "You can check its status with:"
echo "systemctl status resonite-manager-websocket"
echo "View logs with:"
echo "journalctl -u resonite-manager-websocket -f"

if [[ $install_webserver =~ ^[Yy]$ ]]; then
    echo
    echo "Web interface is also running and will start automatically on boot"
    echo "You can check its status with:"
    echo "systemctl status resonite-manager-webserver"
    echo "View logs with:"
    echo "journalctl -u resonite-manager-webserver -f"
fi
