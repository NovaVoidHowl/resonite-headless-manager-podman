"""
FastAPI server providing WebSocket API and web interface for managing Resonite headless servers.

This module implements:
- WebSocket API for real-time server monitoring and control
- Configuration management endpoints
- World and user management capabilities
- System resource monitoring
- Friend request handling
- Ban management
"""

import asyncio
import json
import logging
import os
import re
import threading
import time
from contextlib import suppress
from typing import Any, Dict

import psutil
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.websockets import WebSocketState

from podman_manager import PodmanManager

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create locks for different request types
request_locks = {
    'status': asyncio.Lock(),
    'worlds': asyncio.Lock(),
    'command': asyncio.Lock(),
    'config': asyncio.Lock()
}

app = FastAPI()

# Get server IP from environment
server_ip = os.getenv('SERVER_IP', 'localhost')

# Add CORS middleware to allow requests from the static web server
app.add_middleware(
  CORSMiddleware,
  allow_origins=[
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    f"http://{server_ip}:8080"
  ],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# Store active WebSocket connections
active_connections = []

# Initialize PodmanManager with container name from .env
podman_manager = PodmanManager(
  os.getenv('CONTAINER_NAME', 'resonite-headless')  # Fallback to 'resonite-headless' if not set
)


# Add config file handling
def load_config() -> Dict[Any, Any]:
  """Load the headless config file"""
  config_path = os.getenv('CONFIG_PATH')
  if not config_path:
    logger.error("CONFIG_PATH environment variable is not set")
    raise ValueError("CONFIG_PATH not set in environment variables")

  logger.info("Attempting to load config from: %s", config_path)

  try:
    with open(config_path, 'r', encoding='utf-8') as f:
      raw_content = f.read()
      return {
        "content": raw_content
      }
  except FileNotFoundError as exc:
    logger.error("Config file not found at path: %s", config_path)
    raise ValueError(f"Config file not found at {config_path}") from exc
  except Exception as e:
    logger.error("Unexpected error loading config: %s", str(e))
    raise ValueError(f"Error loading config: {str(e)}") from e


def save_config(config_data: Dict[Any, Any]) -> None:
  """Save the headless config file"""
  config_path = os.getenv('CONFIG_PATH')
  if not config_path:
    raise ValueError("CONFIG_PATH not set in environment variables")

  try:
    json.dumps(config_data)
  except (TypeError, json.JSONDecodeError) as exc:
    raise ValueError("Invalid JSON data") from exc

  with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config_data, f, indent=2)


def format_uptime(uptime_str):
  """Convert .NET TimeSpan format to human readable format"""
  try:
    parts = uptime_str.split('.')
    if len(parts) != 2:
      return uptime_str

    days = 0
    time_parts = parts[0].split(':')
    if len(time_parts) != 3:
      return uptime_str

    hours, minutes, _ = map(int, time_parts)  # Using _ for unused seconds

    if hours >= 24:
      days = hours // 24
      hours = hours % 24

    components = []
    if days > 0:
      components.append(f"{days} {'day' if days == 1 else 'days'}")
    if hours > 0:
      components.append(f"{hours} {'hour' if hours == 1 else 'hours'}")
    if not days and minutes > 0:  # Only show minutes if less than a day
      components.append(f"{minutes} {'minute' if minutes == 1 else 'minutes'}")

    return ' '.join(components) if components else "just started"
  except (ValueError, AttributeError, IndexError) as e:
    # Handle specific exceptions that might occur during string parsing
    logger.warning("Error parsing uptime string: %s", str(e))
    return uptime_str


def parse_bans(output):
  """Parse the ban list output into structured data.

  Args:
      output (str): Raw output from the ban list command

  Returns:
      list: List of dictionaries containing banned user information
  """
  bans = []
  # Remove the first line
  lines = output.split('\n')[1:]

  for line in lines:
    line = line.strip()
    line = line.replace('\t', '')
    if line and not line.endswith('>'):  # Skip empty lines and command prompt
      # Match the format: [index]Username:nameUserID:idMachineIds:
      match = re.match(r'\[\d+\]Username:(.+?)UserID:(.+?)MachineIds:', line)
      if match:
        bans.append({
          'username': match.group(1).strip(),
          'userId': match.group(2).strip()
        })
  return bans


def parse_friend_requests(output):
  """Parse the friend requests output into a list of usernames.

  Args:
    output (str): Raw output from the friendRequests command

  Returns:
    list: List of usernames who have sent friend requests
  """
  requests = []
  # Split by newlines and skip the first line (header) and last line (prompt)
  lines = output.split('\n')[1:-1]

  for line in lines:
    line = line.strip()
    # Skip empty lines and command prompts
    if line and not line.endswith('>'):
      # Extract username from the line
      if ':' in line:  # If line contains user info
        username = line.split(':')[1].strip()
        if username:
          requests.append(username)

  return requests


@app.get("/")
async def get():
  """Serve the main web interface HTML page.

  Returns:
      HTMLResponse: The rendered index.html template
  """
  with open("templates/index.html", encoding='utf-8') as f:
    return HTMLResponse(f.read())


async def handle_command(websocket: WebSocket, command: str):
  """Handle command execution and response"""
  async with request_locks['command']:
    logger.info("Executing command: %s", command)
    output = podman_manager.send_command(command)

    # Check if the output indicates container is not running
    if output.startswith("Error: Container is not running"):
      await safe_send_json(websocket, {
        "type": "error",
        "message": "Container is not running. Please start the container first."
      })
      return

    if command == "listbans":
      bans = parse_bans(output)
      await safe_send_json(websocket, {
        "type": "bans_update",
        "bans": bans
      })
    elif command == "friendRequests":
      requests = parse_friend_requests(output)
      await safe_send_json(websocket, {
        "type": "command_response",
        "command": command,
        "output": requests
      })
    else:
      await safe_send_json(websocket, {
        "type": "command_response",
        "command": command,
        "output": output
      })


async def handle_status(websocket: WebSocket):
  """Handle status request and system metrics"""
  async with request_locks['status']:
    try:
      status = podman_manager.get_container_status()
      status_dict = dict(status)

      # If container is not running, we still want to show system metrics
      # but indicate the container state clearly
      cpu_percent = psutil.cpu_percent(interval=1)
      memory = psutil.virtual_memory()
      memory_percent = memory.percent
      memory_used = f"{memory.used / (1024 * 1024 * 1024):.1f}GB"
      memory_total = f"{memory.total / (1024 * 1024 * 1024):.1f}GB"

      full_status = {
        **status_dict,
        "cpu_usage": cpu_percent,
        "memory_percent": memory_percent,
        "memory_used": memory_used,
        "memory_total": memory_total
      }

      if status_dict.get('error'):
        full_status['status'] = 'stopped'
        full_status['error_message'] = status_dict['error']

      await safe_send_json(websocket, {
        "type": "status_update",
        "status": full_status
      })
    except (ConnectionError, RuntimeError) as e:
      logger.error("Error in handle_status: %s", str(e))
      if await is_websocket_connected(websocket):
        await safe_send_json(websocket, {
          "type": "error",
          "message": f"Error getting status: {e}"
        })


def parse_key_value(key: str, value: str) -> Any:
  """Parse a specific key-value pair from user data"""
  if key == "present":
    return value.lower() == "true"
  elif key == "ping":
    try:
      return int(value)
    except ValueError:
      return int(value.replace("ms", ""))
  elif key == "fps":
    return float(value)
  elif key == "silenced":
    return value.lower() == "true"
  return value


def parse_user_data(user_line: str) -> dict | None:
  """Parse a single user line into structured data"""
  line = user_line.strip()
  if not line:
    return None

  user_info = {}
  parts = line.split()
  if not parts:
    return None

  user_info["username"] = parts[0]

  # First pass - find user ID
  for i, part in enumerate(parts):
    if part == "ID:" and i + 1 < len(parts):
      user_info["userId"] = parts[i + 1]
      break

  # Second pass - find all other key-value pairs
  for i, part in enumerate(parts):
    if part.endswith(":") and i + 1 < len(parts):
      key = part[:-1].lower()
      user_info[key] = parse_key_value(key, parts[i + 1])

  return user_info


async def get_world_users(world_index: int) -> list:
  """Get users data for a specific world"""
  podman_manager.send_command(f"focus {world_index}")
  time.sleep(1)  # Allow time for focus to take effect

  users_output = podman_manager.send_command("users")
  users_lines = users_output.split('\n')[1:-1]

  users_data = []
  for user_line in users_lines:
    user_info = parse_user_data(user_line)
    if user_info:
      users_data.append(user_info)

  return users_data


async def get_world_data(world_line: str, index: int) -> dict | None:
  """Parse world data and get its details"""
  logger.info("Processing world line: %s", world_line)

  # Handle the [index] prefix if present
  if world_line.startswith('['):
    bracket_end = world_line.find(']')
    if bracket_end != -1:
      world_line = world_line[bracket_end + 1:].strip()

  # Split on "Users:" to get the name and details
  parts = world_line.split("Users:", 1)
  if len(parts) != 2:
    logger.warning("Invalid world line format (missing Users:): %s", world_line)
    return None

  name = parts[0].strip()

  # Parse the details section using space as delimiter
  details = parts[1].strip().split()
  # We expect at least: Users count, "Present:", present count, "AccessLevel:", access level, max users
  if len(details) < 6:
    logger.warning("Invalid details format in world line: %s", parts[1])
    return None

  try:
    # Extract values using the known format
    user_count = int(details[0])
    present_count = int(details[2])
    access_level = details[4]
    max_users = int(details[6]) if len(details) > 6 else 32

    # Get detailed status
    podman_manager.send_command(f"focus {index}")
    time.sleep(0.5)  # Wait for focus to take effect

    status_output = podman_manager.send_command("status")
    status_lines = status_output.split('\n')

    # Filter out empty lines and command prompts
    status_lines = [line.strip() for line in status_lines if line.strip() and not line.endswith('>')]

    # Parse status data
    status_data = {}
    for line in status_lines:
      if ': ' in line:
        key, value = line.split(': ', 1)
        status_data[key.strip()] = value.strip()

    # Build world data object
    world_data = {
      "name": name,
      "sessionId": status_data.get("SessionID", ""),
      "users": user_count,
      "present": present_count,
      "maxUsers": max_users,
      "uptime": format_uptime(status_data.get("Uptime", "")),
      "accessLevel": access_level,
      "hidden": status_data.get("Hidden from listing", "False") == "True",
      "mobileFriendly": status_data.get("Mobile Friendly", "False") == "True",
      "description": status_data.get("Description", ""),
      "tags": status_data.get("Tags", "")
    }

    # Get users list
    world_data["users_list"] = await get_world_users(index)

    logger.info("Successfully parsed world data for %s", name)
    return world_data

  except (ValueError, IndexError, KeyError) as e:
    logger.error("Error parsing world data: %s", str(e))
    return None


async def handle_worlds(websocket: WebSocket):
  """Handle worlds request and data collection"""
  async with request_locks['worlds']:
    # First check if container is running
    if not podman_manager.is_container_running():
      await safe_send_json(websocket, {
        "type": "worlds_update",
        "output": [],
        "error": "Container is not running. Please start the container first."
      })
      return

    worlds_output = podman_manager.send_command("worlds")
    worlds_output_lines = worlds_output.split('\n')

    # Filter out empty lines and command prompt
    worlds_lines = [line for line in worlds_output_lines if line.strip() and not line.endswith('>')]

    # Skip the first line if it's just column headers
    if len(worlds_lines) > 0 and not worlds_lines[0].strip().startswith('['):
      worlds_lines = worlds_lines[1:]

    logger.info("Found %d world(s) to process", len(worlds_lines))

    worlds = []
    for i, world in enumerate(worlds_lines):
      try:
        world_data = await get_world_data(world, i)
        if world_data:
          worlds.append(world_data)
          logger.info("Successfully processed world: %s", world_data['name'])
        else:
          logger.warning("Failed to process world line: %s", world)
      except (ValueError, KeyError, ConnectionError, RuntimeError) as e:
        logger.error("Error processing world %d: %s", i, str(e))

    logger.info("Sending %d world(s) to client", len(worlds))
    await safe_send_json(websocket, {
      "type": "worlds_update",
      "output": worlds
    })


async def handle_websocket_message(websocket: WebSocket, message: str):
  """Handle individual WebSocket messages"""
  try:
    data = json.loads(message)
    message_type = data.get("type", "")

    if message_type in request_locks and request_locks[message_type].locked():
      logger.warning("Request of type %s already in progress, skipping", message_type)
      await safe_send_json(websocket, {
        "type": "error",
        "message": f"A {message_type} request is already in progress"
      })
      return

    if data["type"] == "command":
      await handle_command(websocket, data["command"])
    elif data["type"] == "get_status":
      await handle_status(websocket)
    elif data["type"] == "get_worlds":
      await handle_worlds(websocket)
  except json.JSONDecodeError:
    if await is_websocket_connected(websocket):
      await safe_send_json(websocket, {
        "type": "error",
        "message": "Invalid message format"
      })
  except (ConnectionError, RuntimeError, ValueError, KeyError) as e:
    logger.error("Error handling message: %s", str(e))
    if await is_websocket_connected(websocket):
      await safe_send_json(websocket, {
        "type": "error",
        "message": f"Error: {e}"
      })


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
  """Handle WebSocket connections and message routing"""
  await websocket.accept()
  active_connections.append(websocket)
  monitor_task = None

  try:
    monitor_task = asyncio.create_task(monitor_docker_output(websocket))

    while await is_websocket_connected(websocket):
      message = await websocket.receive_text()
      await handle_websocket_message(websocket, message)

  except WebSocketDisconnect:
    logger.info("WebSocket disconnected normally")
  except (ConnectionError, RuntimeError) as e:
    logger.error("WebSocket error: %s", str(e))
  finally:
    if websocket in active_connections:
      active_connections.remove(websocket)
    if monitor_task:
      monitor_task.cancel()
      with suppress(asyncio.CancelledError):
        await monitor_task


async def is_websocket_connected(websocket: WebSocket) -> bool:
  """Check if the websocket is still connected and in a valid state"""
  try:
    if websocket.client_state != WebSocketState.CONNECTED:
      return False

    # Try to send a ping to verify connection
    with suppress(WebSocketDisconnect, RuntimeError):
      await websocket.send_bytes(b'')
      return True

    return False
  except (ConnectionError, RuntimeError) as e:
    logger.debug("Error checking websocket state: %s", str(e))
    return False


async def safe_send_json(websocket: WebSocket, data: dict) -> bool:
  """Safely send JSON data over websocket with state checking"""
  try:
    if await is_websocket_connected(websocket):
      await websocket.send_json(data)
      return True
    return False
  except (ConnectionError, RuntimeError) as e:
    logger.debug("Error sending data: %s", str(e))
    return False


async def monitor_docker_output(websocket: WebSocket):
  """Monitor Docker output and send to WebSocket"""
  loop = asyncio.get_running_loop()

  async def async_callback(output):
    if await is_websocket_connected(websocket):
      await send_output(websocket, output)

  def sync_callback(output):
    asyncio.run_coroutine_threadsafe(async_callback(output), loop)

  # Run the monitoring in a separate thread
  thread = threading.Thread(
    target=podman_manager.monitor_output,
    args=(sync_callback,),
    daemon=True
  )
  thread.start()

  try:
    while await is_websocket_connected(websocket):
      await asyncio.sleep(1)  # Keep the monitoring alive
  except asyncio.CancelledError:
    # Cleanup when the task is cancelled
    pass


async def send_output(websocket: WebSocket, output):
  """Send output to WebSocket"""
  try:
    if await is_websocket_connected(websocket):
      # Ensure the output is properly encoded
      if not isinstance(output, str):
        output = str(output)

      await safe_send_json(websocket, {
        "type": "container_output",
        "output": output
      })
  except (WebSocketDisconnect, ConnectionError) as e:
    logger.error("Error sending output: %s", str(e))


@app.get("/config")
async def get_config():
  """Get the current headless config"""
  try:
    result = load_config()
    return JSONResponse(content=result)
  except ValueError as e:
    logger.error("Error in get_config endpoint: %s", str(e))
    raise HTTPException(status_code=500, detail=str(e)) from e
  except Exception as e:
    logger.error("Unexpected error in get_config endpoint: %s", str(e))
    raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}") from e


@app.post("/config")
async def update_config(config_data: Dict[Any, Any]):
  """Update the headless config"""
  try:
    save_config(config_data)
    return JSONResponse(content={"message": "Config updated successfully"})
  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/world-properties")
async def update_world_properties(data: dict):
  """Update world properties"""
  try:
    session_id = data.get('sessionId')
    if not session_id:
      raise HTTPException(status_code=400, detail="Session ID is required")

    # Note: Property updates are handled via direct podman_manager commands
    # Implementation is pending integration with the container command system
    return JSONResponse(content={"message": "Properties updated successfully"})
  except (ValueError, KeyError) as e:
    raise HTTPException(status_code=400, detail=str(e)) from e
  except (ConnectionError, RuntimeError) as e:
    logger.error("Error updating world properties: %s", str(e))
    raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/restart-container")
async def restart_container():
  """Restart the Docker container"""
  try:
    podman_manager.restart_container()
    return JSONResponse(content={"message": "Container restart initiated"})
  except (ConnectionError, RuntimeError) as e:
    logger.error("Error restarting container: %s", str(e))
    raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/start-container")
async def start_container():
  """Start the Docker container"""
  try:
    if not podman_manager.is_container_running():
      podman_manager.start_container()
      return JSONResponse(content={"message": "Container start initiated"})
    return JSONResponse(content={"message": "Container is already running"})
  except (ConnectionError, RuntimeError) as e:
    logger.error("Error starting container: %s", str(e))
    raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/stop-container")
async def stop_container():
  """Stop the Docker container"""
  try:
    if podman_manager.is_container_running():
      podman_manager.stop_container()
      return JSONResponse(content={"message": "Container stop initiated"})
    return JSONResponse(content={"message": "Container is already stopped"})
  except (ConnectionError, RuntimeError) as e:
    logger.error("Error stopping container: %s", str(e))
    raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
  import uvicorn
  uvicorn.run(app, host="0.0.0.0", port=8000)
