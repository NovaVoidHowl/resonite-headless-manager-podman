import asyncio
import json
import logging
import os
import re
import threading
import time
from typing import Any, Dict

import psutil  # Add this import
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from podman_manager import PodmanManager

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Serve static files (if you have any CSS/JS files)
app.mount("/static", StaticFiles(directory="static"), name="static")

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
  """Parse the ban list output into structured data"""
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


@app.get("/")
async def get():
  with open("templates/index.html", encoding='utf-8') as f:
    return HTMLResponse(f.read())


async def handle_command(websocket: WebSocket, command: str):
  """Handle command execution and response"""
  output = podman_manager.send_command(command)

  if command == "listbans":
    bans = parse_bans(output)
    await websocket.send_json({
      "type": "bans_update",
      "bans": bans
    })
  else:
    await websocket.send_json({
      "type": "command_response",
      "command": command,
      "output": output
    })


async def handle_status(websocket: WebSocket):
  """Handle status request and system metrics"""
  status = podman_manager.get_container_status()
  status_dict = dict(status)  # Convert to dictionary if it's not already

  cpu_percent = psutil.cpu_percent(interval=1)
  memory = psutil.virtual_memory()
  memory_percent = memory.percent
  memory_used = f"{memory.used / (1024 * 1024 * 1024):.1f}GB"
  memory_total = f"{memory.total / (1024 * 1024 * 1024):.1f}GB"

  # Create a new dictionary with all status data
  full_status = {
    **status_dict,
    "cpu_usage": str(cpu_percent),  # Convert to string to match expected type
    "memory_percent": str(memory_percent),
    "memory_used": memory_used,
    "memory_total": memory_total
  }

  await websocket.send_json({
    "type": "status_update",
    "status": full_status
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
  for i in range(len(parts)):
    if parts[i].endswith(":") and i + 1 < len(parts):
      key = parts[i][:-1].lower()
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


async def get_world_data(world_line: str, index: int) -> dict:
  """Parse world data and get its details"""
  podman_manager.send_command(f"focus {index}")
  time.sleep(1)

  status_output = podman_manager.send_command("status")
  status_lines = status_output.split('\n')[1:-1]

  status_data = {}
  for line in status_lines:
    if ': ' in line:
      key, value = line.split(': ', 1)
      status_data[key] = value

  parts = world_line.split('\t')
  name_part = parts[0]
  users_index = name_part.find("Users:")
  name = name_part[name_part.find(']') + 2:users_index].strip()

  world_data = {
    "name": name,
    "sessionId": status_data.get("SessionID", ""),
    "users": int(status_data.get("Current Users", 0)),
    "present": int(status_data.get("Present Users", 0)),
    "maxUsers": int(status_data.get("Max Users", 0)),
    "uptime": format_uptime(status_data.get("Uptime", "")),
    "accessLevel": status_data.get("Access Level", ""),
    "hidden": status_data.get("Hidden from listing", "False") == "True",
    "mobileFriendly": status_data.get("Mobile Friendly", "False") == "True",
    "description": status_data.get("Description", ""),
    "tags": status_data.get("Tags", "")
  }

  world_data["users_list"] = await get_world_users(index)
  return world_data


async def handle_worlds(websocket: WebSocket):
  """Handle worlds request and data collection"""
  worlds_output = podman_manager.send_command("worlds")
  worlds_output = worlds_output.split('\n')[1:-1]

  worlds = []
  for i, world in enumerate(worlds_output):
    world_data = await get_world_data(world, i)
    worlds.append(world_data)

  await websocket.send_json({
    "type": "worlds_update",
    "output": worlds
  })


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
  """Handle WebSocket connections and message routing"""
  await websocket.accept()
  active_connections.append(websocket)
  monitor_task = None

  try:
    monitor_task = asyncio.create_task(monitor_docker_output(websocket))

    while True:
      message = await websocket.receive_text()
      try:
        data = json.loads(message)

        if data["type"] == "command":
          await handle_command(websocket, data["command"])
        elif data["type"] == "get_status":
          await handle_status(websocket)
        elif data["type"] == "get_worlds":
          await handle_worlds(websocket)
      except json.JSONDecodeError:
        await websocket.send_json({
          "type": "error",
          "message": "Invalid message format"
        })

  except WebSocketDisconnect:
    logger.info("WebSocket disconnected normally")
  except (ConnectionError, TimeoutError) as e:
    logger.error("WebSocket connection error: %s", str(e))
  finally:
    active_connections.remove(websocket)
    if monitor_task:
      monitor_task.cancel()


async def is_websocket_connected(websocket: WebSocket) -> bool:
  """Check if the websocket is still connected"""
  try:
    await websocket.send_bytes(b'')
    return True
  except WebSocketDisconnect:  # Specify the exact exception we expect
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

      await websocket.send_json({
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

    # TODO: Implement the actual property updates using podman_manager
    # You'll need to send the appropriate commands to update each property

    return JSONResponse(content={"message": "Properties updated successfully"})
  except (ValueError, KeyError) as e:
    raise HTTPException(status_code=400, detail=str(e)) from e
  except Exception as e:
    logger.error("Error updating world properties: %s", str(e))
    raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/restart-container")
async def restart_container():
  """Restart the Docker container"""
  try:
    podman_manager.restart_container()
    return JSONResponse(content={"message": "Container restart initiated"})
  except Exception as e:
    logger.error("Error restarting container: %s", str(e))
    raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
  import uvicorn
  uvicorn.run(app, host="0.0.0.0", port=8000)
