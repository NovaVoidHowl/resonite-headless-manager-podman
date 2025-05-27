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
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Set

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

# Initialize PodmanManager with container name from .env
podman_manager = PodmanManager(
  os.getenv('CONTAINER_NAME', 'resonite-headless')  # Fallback to 'resonite-headless' if not set
)


@dataclass
class ConnectionManager:
  """Manage WebSocket connections for a specific type"""
  active_connections: Set[WebSocket]

  def __init__(self):
    self.active_connections = set()

  async def connect(self, websocket: WebSocket):
    """
    Accept and add a new WebSocket connection.

    Args:
        websocket (WebSocket): The WebSocket connection to add
    """
    await websocket.accept()
    self.active_connections.add(websocket)

  async def disconnect(self, websocket: WebSocket):
    """
    Remove a WebSocket connection from active connections.

    Args:
        websocket (WebSocket): The WebSocket connection to remove
    """
    self.active_connections.remove(websocket)

  async def broadcast(self, message: dict):
    """
    Broadcast a message to all active WebSocket connections.

    Args:
        message (dict): The message to broadcast to all connections
    """
    for connection in self.active_connections.copy():
      try:
        await safe_send_json(connection, message)
      except (ConnectionError, RuntimeError):
        await self.disconnect(connection)


# Create connection managers for different types of connections
logs_manager = ConnectionManager()
status_manager = ConnectionManager()
worlds_manager = ConnectionManager()
commands_manager = ConnectionManager()


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
  """Parse the friend requests output into a list of usernames."""
  logger.info("Raw friend requests output (before parsing): %s", repr(output))  # Use repr to show whitespace/newlines
  requests = []

  # Remove empty lines and command prompts
  lines = [line.strip() for line in output.split('\n') if line.strip() and not line.endswith('>')]
  logger.info("Lines after initial filtering: %s", repr(lines))

  # Skip the header line if it exists
  if lines and lines[0].lower().startswith('friend request'):
    lines = lines[1:]

  for line in lines:
    # Directly add any non-empty line that isn't a system message
    if line and not line.startswith('==='):
      requests.append(line)
      logger.info("Added friend request: %s", line)

  logger.info("Final parsed requests: %s", requests)
  return requests


@app.get("/")
async def get():
  """Serve the main web interface HTML page.

  Returns:
      HTMLResponse: The rendered index.html template
  """
  with open("templates/index.html", encoding='utf-8') as f:
    return HTMLResponse(f.read())


def parse_user_field(parts: list, index: int, field_name: str) -> tuple[Any, bool]:
  """Parse a specific field from user data parts"""
  if index + 1 >= len(parts):
    return None, False

  if field_name == "Present":
    return parts[index + 1].lower() == "true", True
  elif field_name == "Ping":
    try:
      return int(parts[index + 1]), True
    except ValueError:
      return 0, True
  elif field_name == "FPS":
    try:
      return float(parts[index + 1]), True
    except ValueError:
      return 0.0, True
  elif field_name == "Silenced":
    return parts[index + 1].lower() == "true", True
  else:  # ID, Role
    return parts[index + 1], True


def parse_user_data(line: str) -> dict | None:
  """Parse a single user line into structured data"""
  line = line.strip()
  if not line or line.endswith('>'):
    return None

  parts = line.split()
  if len(parts) < 7:
    return None

  user_data = {
    "username": parts[0],
    "id": None,
    "role": None,
    "present": False,
    "ping": 0,
    "fps": 0.0,
    "silenced": False
  }

  field_markers = {
    "ID": "id",
    "Role": "role",
    "Present": "present",
    "Ping": "ping",
    "FPS": "fps",
    "Silenced": "silenced"
  }

  for i, part in enumerate(parts):
    if part.endswith(':') and part[:-1] in field_markers:
      field = field_markers[part[:-1]]
      value, success = parse_user_field(parts, i, part[:-1])
      if success:
        user_data[field] = value

  if user_data["id"] and user_data["role"] is not None:
    return user_data
  return None


async def handle_command(websocket: WebSocket, command: str):
  """Handle command execution and response"""
  async with request_locks['command']:
    logger.info("Executing command: %s", command)
    output = podman_manager.send_command(command)
    logger.info("Raw command output: %s", output)

    # Check if the output indicates container is not running
    if output.startswith("Error: Container is not running"):
      await safe_send_json(websocket, {
        "type": "error",
        "message": "Container is not running. Please start the container first."
      })
      return

    # Handle specific command types
    if command == "listbans":
      bans = parse_bans(output) if output.strip() else []
      await safe_send_json(websocket, {
        "type": "bans_update",
        "bans": bans
      })
    elif command == "friendRequests":
      requests = parse_friend_requests(output) if output.strip() else []
      await safe_send_json(websocket, {
          "type": "command_response",
          "command": command,
          "output": requests
      })
    elif command == "users":
      users = []
      lines = output.split('\n')
      # Process each line that isn't empty and isn't a prompt
      for line in [line_str for line_str in lines if line_str.strip() and not line_str.endswith('>')]:
        user_data = parse_user_data(line)
        if user_data:
          users.append(user_data)

      await safe_send_json(websocket, {
        "type": "command_response",
        "command": command,
        "output": users
      })
    else:
      # For other commands, just return the raw output
      await safe_send_json(websocket, {
        "type": "command_response",
        "command": command,
        "output": output.strip() if output.strip() else ""
      })


async def handle_status(websocket: WebSocket):
  """Handle status request and system metrics"""
  try:
    # Get container status first
    status = podman_manager.get_container_status()
    status_dict = dict(status)

    # Add system metrics
    cpu_percent = psutil.cpu_percent(interval=None)  # Changed to not block
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    memory_used = f"{memory.used / (1024 * 1024 * 1024):.1f}GB"
    memory_total = f"{memory.total / (1024 * 1024 * 1024):.1f}GB"

    # Parse status data from container status command if container is running
    if podman_manager.is_container_running():
      status_output = podman_manager.send_command("status")
      for line in [
        status_line.strip()
        for status_line in status_output.split('\n')
        if status_line.strip() and not status_line.endswith('>')
      ]:
        if ': ' in line:
          key, value = line.split(': ', 1)
          status_dict[key.strip()] = value.strip()

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


async def get_world_users(world_index: int) -> list:
  """Get users data for a specific world"""
  # Send focus command and wait for it to take effect
  focus_output = podman_manager.send_command(f"focus {world_index}")
  if "Error" in focus_output:
    logger.error("Failed to focus world %d: %s", world_index, focus_output)
    return []

  # Wait for focus to take effect
  time.sleep(1)

  # Get users and parse output
  users_output = podman_manager.send_command("users")
  if "Error" in users_output:
    logger.error("Failed to get users for world %d: %s", world_index, users_output)
    return []

  # Split output into lines and remove first line (header) and last line (prompt)
  users_lines = [line.strip() for line in users_output.split('\n') if line.strip()]
  if len(users_lines) > 1:  # Check if we have any lines besides the header
    users_lines = users_lines[1:-1]
  else:
    return []

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


async def send_json_message(websocket: WebSocket, data: dict):
  """Send JSON message, ensuring it's properly typed"""
  if await is_websocket_connected(websocket):
    await websocket.send_json({
      "type": "json",
      "data": data
    })


async def monitor_websocket(websocket: WebSocket, callback):
  """Monitor a WebSocket connection and handle messages"""
  try:
    while await is_websocket_connected(websocket):
      data = await websocket.receive()
      if data["type"] == "websocket.receive":
        if "text" in data:
          await callback(websocket, json.loads(data["text"]))
        elif "bytes" in data:
          # Ignore binary messages - they are handled separately
          pass
  except WebSocketDisconnect:
    logger.info("WebSocket disconnected normally")
  except json.JSONDecodeError:
    logger.error("Invalid JSON received")
  except (ConnectionError, RuntimeError) as e:
    logger.error("Error in WebSocket monitoring: %s", str(e))


@app.websocket("/ws/logs")
async def logs_endpoint(websocket: WebSocket):
    """Handle container logs WebSocket connections"""
    await logs_manager.connect(websocket)

    try:
        # Send initial recent logs
        recent_logs = podman_manager.get_recent_logs()
        for log_line in recent_logs:
            await safe_send_json(websocket, {
                "type": "container_output",
                "output": log_line,
                "timestamp": datetime.now().isoformat()
            })

        # Set up streaming
        async def stream_callback(output):
            if await is_websocket_connected(websocket):
                await safe_send_json(websocket, {
                    "type": "container_output",
                    "output": output,
                    "timestamp": datetime.now().isoformat()
                })

        # Start monitoring in a separate thread
        loop = asyncio.get_running_loop()
        def sync_callback(output):
            asyncio.run_coroutine_threadsafe(stream_callback(output), loop)

        thread = threading.Thread(
            target=podman_manager.monitor_output,
            args=(sync_callback,),
            daemon=True
        )
        thread.start()

        # Keep the connection alive
        while await is_websocket_connected(websocket):
            try:
                message = await websocket.receive()
                # Handle any incoming messages if needed
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.info("Logs WebSocket disconnected normally")
    except (ConnectionError, RuntimeError) as e:
        logger.error("Logs WebSocket error: %s", str(e))
    finally:
        await logs_manager.disconnect(websocket)


@app.websocket("/ws/status")
async def status_endpoint(websocket: WebSocket):
    """Handle status monitoring WebSocket connections"""
    await status_manager.connect(websocket)

    try:
        while await is_websocket_connected(websocket):
            message = await websocket.receive_text()
            data = json.loads(message)
            if data.get("type") == "get_status":
                async with request_locks['status']:
                    await handle_status(websocket)

    except WebSocketDisconnect:
        logger.info("Status WebSocket disconnected normally")
    except (ConnectionError, RuntimeError, json.JSONDecodeError) as e:
        logger.error("Status WebSocket error: %s", str(e))
    finally:
        await status_manager.disconnect(websocket)


@app.websocket("/ws/worlds")
async def worlds_endpoint(websocket: WebSocket):
  """Handle worlds list WebSocket connections"""
  await worlds_manager.connect(websocket)

  try:
    while await is_websocket_connected(websocket):
      message = await websocket.receive_text()
      data = json.loads(message)
      if data.get("type") == "get_worlds":
        await handle_worlds(websocket)

  except WebSocketDisconnect:
    logger.info("Worlds WebSocket disconnected normally")
  except (ConnectionError, RuntimeError, json.JSONDecodeError) as e:
    logger.error("Worlds WebSocket error: %s", str(e))
  finally:
    await worlds_manager.disconnect(websocket)


@app.websocket("/ws/command")
async def command_endpoint(websocket: WebSocket):
  """Handle command WebSocket connections"""
  await commands_manager.connect(websocket)

  try:
    while await is_websocket_connected(websocket):
      message = await websocket.receive_text()
      data = json.loads(message)
      if data.get("type") == "command":
        await handle_command(websocket, data["command"])

  except WebSocketDisconnect:
    logger.info("Command WebSocket disconnected normally")
  except (ConnectionError, RuntimeError, json.JSONDecodeError, KeyError) as e:
    logger.error("Command WebSocket error: %s", str(e))
  finally:
    await commands_manager.disconnect(websocket)


@app.websocket("/ws/heartbeat")
async def heartbeat_endpoint(websocket: WebSocket):
  """Handle heartbeat connections to keep other WebSockets alive"""
  await websocket.accept()
  try:
    while True:
      await websocket.send_bytes(b'')
      await asyncio.sleep(1)
  except WebSocketDisconnect:
    logger.info("Heartbeat WebSocket disconnected normally")
  except (ConnectionError, RuntimeError) as e:
    logger.error("Heartbeat WebSocket error: %s", str(e))


async def is_websocket_connected(websocket: WebSocket) -> bool:
  """Check if the websocket is still connected and in a valid state"""
  try:
    return websocket.client_state == WebSocketState.CONNECTED
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
      await send_output(output)

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


async def send_output(output):
  """Send output to WebSocket"""
  try:
    if not isinstance(output, str):
      output = str(output)

    await logs_manager.broadcast({
      "type": "container_output",
      "output": output,
      "timestamp": datetime.now().isoformat()
    })
  except (ConnectionError, RuntimeError) as e:
    logger.error("Error broadcasting output: %s", str(e))


@app.get("/config")
async def get_config():
  """Get the current headless config"""
  try:
    result = load_config()
    return JSONResponse(content=result)
  except ValueError as e:
    logger.error("Error in get_config endpoint: %s", str(e))
    raise HTTPException(status_code=500, detail=str(e)) from e
  except (ConnectionError, RuntimeError) as e:
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
