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
    # add CONTAINER_NAME and CONFIG_PATH to .env file
    echo "CONTAINER_NAME=$CONTAINER_NAME" >> .env
    echo "CONFIG_PATH=$CONFIG_PATH" >> .env
else
    echo ".env file found."
    # source the .env file
    source .env
    # check if CONTAINER_NAME and CONFIG_PATH are set
    if [ -z "$CONTAINER_NAME" ] || [ -z "$CONFIG_PATH" ]; then
        echo "CONTAINER_NAME or CONFIG_PATH not set in .env file!"
        echo "Please delete the .env file and run the script again."
        exit 1
    else
        echo "CONTAINER_NAME: $CONTAINER_NAME"
        echo "CONFIG_PATH: $CONFIG_PATH"
    fi
fi

python -m venv Res-Manager
source Res-Manager/bin/activate

pip install -r requirements.txt

# Start the static web server in the background
python webserver.py &

# Start the WebSocket server
python server.py
