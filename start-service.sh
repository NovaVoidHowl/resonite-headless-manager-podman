#!/bin/bash

# check if .env file exists
if [ ! -f .env ]; then
    echo "environment file .env not found!"
    # create a new .env file
    echo "Creating a new .env file..."
    touch .env
    # ask user for CONTAINER_NAME
    read -p "Enter CONTAINER_NAME: " CONTAINER_NAME
    # ask user for CONFIG_PATH
    read -p "Enter CONFIG_PATH: " CONFIG_PATH
    # ask user for SERVER_IP
    read -p "Enter SERVER_IP (e.g. 192.168.1.100): " SERVER_IP
    # add values to .env file
    echo "CONTAINER_NAME=$CONTAINER_NAME" >> .env
    echo "CONFIG_PATH=$CONFIG_PATH" >> .env
    echo "SERVER_IP=$SERVER_IP" >> .env
else
    echo ".env file found."
    # source the .env file
    source .env
    # check if required variables are set
    if [ -z "$CONTAINER_NAME" ] || [ -z "$CONFIG_PATH" ] || [ -z "$SERVER_IP" ]; then
        echo "CONTAINER_NAME, CONFIG_PATH or SERVER_IP not set in .env file!"
        echo "Please delete the .env file and run the script again."
        exit 1
    else
        echo "CONTAINER_NAME: $CONTAINER_NAME"
        echo "CONFIG_PATH: $CONFIG_PATH"
        echo "SERVER_IP: $SERVER_IP"
    fi
fi

python -m venv Res-Manager
source Res-Manager/bin/activate

pip install -r requirements.txt

# Start the static web server in the background
python webserver.py &

# Start the WebSocket server
python server.py
