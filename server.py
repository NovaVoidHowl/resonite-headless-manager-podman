from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import asyncio
from podman_manager import PodmanManager
import json
import threading
from dotenv import load_dotenv
import os
from typing import Dict, Any
import psutil
import re
import logging


# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Serve static files (if you have any CSS/JS files)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Store active WebSocket connections
active_connections = []

# prove env data set
print("printing env vars")
print("CONTAINER_NAME: " + os.getenv('CONTAINER_NAME', 'resonite-headless'))
print("CONFIG_PATH:" + os.getenv('CONFIG_PATH', 'resonite-headless'))
print("-------------------------------")

# Initialize PodmanManager with container name from .env
podman_manager = PodmanManager(
  os.getenv('CONTAINER_NAME', 'resonite-headless')
)  # Fallback to 'resonite-headless' if not set


# Add config file handling
def load_config() -> Dict[Any, Any]:
  """Load the headless config file"""
  config_path = os.getenv('CONFIG_PATH')
  if not config_path:
    logger.error("CONFIG_PATH environment variable is not set")
    raise ValueError("CONFIG_PATH not set in environment variables")

  logger.info("Attempting to load config from: %s", config_path)

  try:
    with open(config_path, 'r') as f:
      raw_content = f.read()
      return {
        "content": raw_content
      }
  except FileNotFoundError:
    logger.error("Config file not found at path: %s", config_path)
    raise ValueError(f"Config file not found at {config_path}")
  except Exception as e:
    logger.error("Unexpected error loading config: %s", str(e))
    raise ValueError(f"Error loading config: {str(e)}")


def save_config(config_data: Dict[Any, Any]) -> None:
  """Save the headless config file"""
  config_path = os.getenv('CONFIG_PATH')
  if not config_path:
    raise ValueError("CONFIG_PATH not set in environment variables")

  # Validate JSON before saving
  try:
    # Test if the data can be serialized
    json.dumps(config_data)
  except (TypeError, json.JSONDecodeError):
    raise ValueError("Invalid JSON data")

  with open(config_path, 'w') as f:
    json.dump(config_data, f, indent=2)


def format_uptime(uptime_str):
  """Convert .NET TimeSpan format to human readable format"""
  try:
    # Split into days, hours, minutes, seconds
    parts = uptime_str.split('.')
    if len(parts) != 2:
      return uptime_str

    days = 0
    time_parts = parts[0].split(':')
    if len(time_parts) != 3:
      return uptime_str

    hours, minutes, seconds = map(int, time_parts)

    # Handle days if present
    if hours >= 24:
      days = hours // 24
      hours = hours % 24

    # Build readable string
    components = []
    if days > 0:
      components.append(f"{days} {'day' if days == 1 else 'days'}")
    if hours > 0:
      components.append(f"{hours} {'hour' if hours == 1 else 'hours'}")
    if not days and minutes > 0:  # Only show minutes if less than a day
      components.append(f"{minutes} {'minute' if minutes == 1 else 'minutes'}")

    return ' '.join(components) if components else "just started"
  except Exception:
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


def parse_users(output):
  """Parse the users command output into structured data"""
  users = []
  # Remove the first line if it contains the command
  lines = output.split('\n')
  if lines and "users" in lines[0]:
    lines = lines[1:]

  # Filter out empty lines and command prompt
  lines = [line for line in lines if line.strip() and not line.strip().endswith('>')]

  for line in lines:
    line = line.strip()
    if not line:
      continue

    user_info = {}
    # Split by spaces, but need to be careful as usernames might contain spaces
    parts = line.split()

    # First get the username (everything before ID:)
    name_parts = []
    id_index = -1
    for i, part in enumerate(parts):
      if part == "ID:":
        id_index = i
        break
      name_parts.append(part)

    if id_index >= 0:
      # We found the ID: marker
      user_info["name"] = " ".join(name_parts).strip()

      # Extract User ID - get the next part after "ID:"
      if id_index + 1 < len(parts):
        user_id = parts[id_index + 1]
        user_info["user_id"] = user_id if user_id != "" else None

      # Extract Role
      role_index = -1
      for i, part in enumerate(parts):
        if part == "Role:":
          role_index = i
          break

      if role_index >= 0 and role_index + 1 < len(parts):
        user_info["role"] = parts[role_index + 1]

      # Extract Present status
      present_index = -1
      for i, part in enumerate(parts):
        if part == "Present:":
          present_index = i
          break

      if present_index >= 0 and present_index + 1 < len(parts):
        user_info["present"] = parts[present_index + 1].lower() == "true"

      # Extract Ping
      ping_index = -1
      for i, part in enumerate(parts):
        if part == "Ping:":
          ping_index = i
          break

      if ping_index >= 0 and ping_index + 1 < len(parts):
        try:
          # Handle the "ms" suffix if present
          ping = parts[ping_index + 1]
          if parts[ping_index + 2] == "ms":
            ping += " ms"
          user_info["ping"] = ping
        except IndexError:
          user_info["ping"] = "0 ms"

      # Extract FPS
      fps_index = -1
      for i, part in enumerate(parts):
        if part == "FPS:":
          fps_index = i
          break

      if fps_index >= 0 and fps_index + 1 < len(parts):
        try:
          fps = float(parts[fps_index + 1])
          user_info["fps"] = round(fps, 2)  # Round to 2 decimal places
        except (ValueError, IndexError):
          user_info["fps"] = 0

      # Extract Silenced status
      silenced_index = -1
      for i, part in enumerate(parts):
        if part == "Silenced:":
          silenced_index = i
          break

      if silenced_index >= 0 and silenced_index + 1 < len(parts):
        user_info["silenced"] = parts[silenced_index + 1].lower() == "true"

      # Add the user if we have at least a name
      if "name" in user_info:
        users.append(user_info)

  return users


def parse_worlds(output):
  """Parse the worlds command output into structured data"""
  worlds = []
  # Remove the first line if it contains the command
  lines = output.split('\n')
  if lines and "worlds" in lines[0]:
    lines = lines[1:]

  # Filter out empty lines and command prompt
  lines = [line for line in lines if line.strip() and not line.strip().endswith('>')]

  # If no worlds, return empty array
  if not lines or "No worlds running" in output:
    return []

  # Process each world line
  for line in lines:
    line = line.strip()
    if not line:
      continue

    world_info = {}

    # Parse the index from within brackets [0]
    index_match = re.match(r'\[(\d+)\]', line)
    if index_match:
      world_info["index"] = int(index_match.group(1))

      # Remove the index part to make parsing easier
      line = line[line.find(']') + 1:].strip()
    else:
      # If no index found, assign a placeholder
      world_info["index"] = -1

    # Split remaining into parts by common separators
    parts = re.split(r'\s+', line)

    # First part is world name until we find "Users:"
    name_parts = []
    user_index = -1
    for i, part in enumerate(parts):
      if part == "Users:":
        user_index = i
        break
      name_parts.append(part)

    # Store the name
    if name_parts:
      world_info["name"] = " ".join(name_parts).strip()
    else:
      world_info["name"] = f"World {world_info['index']}"

    # Extract users count
    if user_index >= 0 and user_index + 1 < len(parts):
      try:
        world_info["users"] = int(parts[user_index + 1])
      except ValueError:
        world_info["users"] = 0

    # Extract present users count
    present_index = -1
    for i, part in enumerate(parts):
      if part == "Present:":
        present_index = i
        break

    if present_index >= 0 and present_index + 1 < len(parts):
      try:
        world_info["present"] = int(parts[present_index + 1])
      except ValueError:
        world_info["present"] = 0

    # Extract access level
    access_index = -1
    for i, part in enumerate(parts):
      if part == "AccessLevel:":
        access_index = i
        break

    if access_index >= 0 and access_index + 1 < len(parts):
      world_info["accessLevel"] = parts[access_index + 1]

    # Extract max users
    max_users_index = -1
    for i, part in enumerate(parts):
      if part == "MaxUsers:":
        max_users_index = i
        break

    if max_users_index >= 0 and max_users_index + 1 < len(parts):
      try:
        world_info["maxUsers"] = int(parts[max_users_index + 1])
      except ValueError:
        world_info["maxUsers"] = 0

    # Add to worlds list
    worlds.append(world_info)

  return worlds


def parse_status(output):
  """Parse the status command output into structured data"""
  # Remove the first line if it contains the command
  lines = output.split('\n')
  if lines and "status" in lines[0]:
    lines = lines[1:]

  # Filter out empty lines and command prompt
  lines = [line for line in lines if line.strip() and not line.strip().endswith('>')]

  # Initialize result dict
  status_data = {}

  # Extract key-value pairs
  for line in lines:
    line = line.strip()
    if not line or ":" not in line:
      continue

    parts = line.split(":", 1)
    if len(parts) == 2:
      key = parts[0].strip()
      value = parts[1].strip()

      # Convert certain fields to appropriate types
      if key == "Current Users" or key == "Present Users" or key == "Max Users":
        try:
          value = int(value)
        except ValueError:
          # Keep as string if parsing fails
          pass
      elif key == "Hidden from listing" or key == "Mobile Friendly":
        value = value.lower() == "true"
      elif key == "Uptime":
        # Keep as string but could be further processed
        pass

      # Use camelCase keys for JSON consistency
      key_mapping = {
        "Name": "name",
        "SessionID": "sessionId",
        "Current Users": "users",
        "Present Users": "present",
        "Max Users": "maxUsers",
        "Uptime": "uptime",
        "Access Level": "accessLevel",
        "Hidden from listing": "hidden",
        "Mobile Friendly": "mobileFriendly",
        "Description": "description",
        "Tags": "tags"
      }

      # Add to status data
      if key in key_mapping:
        status_data[key_mapping[key]] = value
      else:
        # For any keys not in the mapping, convert to camelCase
        camel_key = key.lower().replace(" ", "_")
        status_data[camel_key] = value

      # Parse Users list if present
      if key == "Users":
        users = [u.strip() for u in value.split(",") if u.strip()]
        status_data["usersList"] = users

  return status_data


def clean_terminal_output(output):
  """Remove ANSI escape sequences and other terminal control characters from output"""
  import re

  # Remove ANSI escape sequences
  ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
  output = ansi_escape.sub('', output)

  # Remove common prompt text
  output = re.sub(r'Headless Software Debug do not join>', '', output)

  # Strip leading/trailing whitespace
  output = output.strip()

  return output


# Function to handle worlds command
async def process_worlds_command(podman_manager):
    logger.info("Starting process_worlds_command")
    try:
        worlds_output = podman_manager.send_command("worlds")
        logger.info(f"Raw worlds output: {worlds_output}")

        # If no worlds are running, bail early
        if "No worlds running" in worlds_output:
            logger.info("No worlds running")
            return []

        # Remove the command and the command prompt
        worlds_output = worlds_output.split('\n')
        # Filter out empty lines and command prompts
        worlds_output = [line for line in worlds_output if line.strip() and not line.strip().endswith('>')]

        # Remove the first line if it contains the command itself
        if worlds_output and "worlds" in worlds_output[0]:
            worlds_output = worlds_output[1:]

        logger.info(f"Parsed worlds output lines: {len(worlds_output)}")
        logger.info(f"Worlds output: {worlds_output}")

        # Double check - if we have no worlds after parsing, return empty list
        if not worlds_output:
            logger.warning("No worlds found after parsing output")
            return []

        worlds = []
        for i, world in enumerate(worlds_output):
            logger.info(f"Processing world {i}: {world}")
            try:
                # First focus on this world
                focus_result = podman_manager.send_command(f"focus {i}")
                logger.info(f"Focus result: {focus_result}")

                # Add delay to prevent overwhelming the container
                await asyncio.sleep(0.5)

                # Get detailed status
                status_output = podman_manager.send_command("status")
                logger.info(f"Status output for world {i}: {status_output}")

                # Skip if status command failed or returned nothing useful
                if not status_output or "Unknown command" in status_output:
                    logger.warning(f"Failed to get status for world {i}")
                    continue

                # Split the output into lines and remove empty lines and prompts
                status_lines = [line for line in status_output.split('\n')
                                if line.strip() and not line.strip().endswith('>')]

                # Remove the command line if present
                if status_lines and "status" in status_lines[0]:
                    status_lines = status_lines[1:]

                # Parse status output
                status_data = {}
                for line in status_lines:
                    if ': ' in line:
                        key, value = line.split(': ', 1)
                        status_data[key.strip()] = value.strip()

                logger.info(f"Parsed status data: {status_data}")

                # If status_data is empty, create minimal data to avoid skipping
                if not status_data:
                    logger.warning(f"Empty status data for world {i}, using minimal data")
                    status_data = {
                        "SessionID": f"world-{i}",  # Generate a placeholder ID
                        "Current Users": "0",
                        "Present Users": "0",
                        "Max Users": "0",
                        "Uptime": "0.00:00:00",
                        "Access Level": "Unknown",
                        "Hidden from listing": "False",
                        "Mobile Friendly": "False"
                    }

                # Split by tabs to separate the main sections (from original worlds command)
                parts = world.split('\t')

                # Extract name and index from the first part
                name_part = parts[0] if parts else world
                users_index = name_part.find("Users:")

                # Handle case where "Users:" is not found
                if users_index == -1:
                    name = name_part.strip()
                else:
                    name = name_part[name_part.find(']') + 1:users_index].strip()
                    # Clean up any remaining brackets
                    if name.startswith('['):
                        name = name[name.find(']') + 1:].strip()

                # Ensure we have a name even if parsing failed
                if not name:
                    name = f"World {i}"

                logger.info(f"Extracted name: '{name}'")

                # Create world data combining both outputs
                world_data = {
                    "name": name,
                    "sessionId": status_data.get("SessionID", f"world-{i}"),  # Ensure we have an ID
                    "users": int(status_data.get("Current Users", "0").strip()),
                    "present": int(status_data.get("Present Users", "0").strip()),
                    "maxUsers": int(status_data.get("Max Users", "0").strip()),
                    "uptime": format_uptime(status_data.get("Uptime", "")),
                    "accessLevel": status_data.get("Access Level", ""),
                    "hidden": status_data.get("Hidden from listing", "False").strip() == "True",
                    "mobileFriendly": status_data.get("Mobile Friendly", "False").strip() == "True",
                    "description": status_data.get("Description", ""),
                    "tags": status_data.get("Tags", ""),
                    "index": i  # Store the original world index
                }
                logger.info(f"Created world data: {world_data}")

                # Send the users command to the focused world
                users_output = podman_manager.send_command("users")
                logger.info(f"Users output for world {i}: {users_output}")

                # Remove command and prompt lines
                users_lines = [line for line in users_output.split('\n')
                              if line.strip() and not line.strip().endswith('>')]

                # Remove the command line if present
                if users_lines and "users" in users_lines[0]:
                    users_lines = users_lines[1:]

                logger.info(f"Parsed users lines: {users_lines}")

                # Parse users
                users_data = []
                for user_line in users_lines:
                    if user_line.strip():  # Skip empty lines
                        user_info = {}

                        # Split the line by spaces but handle the special case of ID field
                        parts = user_line.split()

                        # First part is always the username
                        user_info["username"] = parts[0] if parts else ""

                        # Look for "ID:" and get the next part
                        for i, part in enumerate(parts):
                            if part == "ID:":
                                if i + 1 < len(parts):
                                    user_info["userId"] = parts[i + 1]
                                break

                        # Parse the rest of the key-value pairs
                        for i in range(len(parts)):
                            if parts[i].endswith(":") and i + 1 < len(parts):
                                key = parts[i][:-1].lower()  # Remove colon and convert to lowercase
                                value = parts[i + 1]
                                if key == "present":
                                    value = value.lower() == "true"
                                elif key == "ping":
                                    try:
                                        value = int(value)
                                    except ValueError:
                                        # Handle case where ping has "ms" suffix
                                        value = int(value.replace("ms", "")) if "ms" in value else 0
                                elif key == "fps":
                                    try:
                                        value = float(value)
                                    except ValueError:
                                        value = 0.0
                                elif key == "silenced":
                                    value = value.lower() == "true"
                                user_info[key] = value

                        users_data.append(user_info)

                # Add users data to world_data
                world_data["users_list"] = users_data
                logger.info(f"Added {len(users_data)} users to world")

                worlds.append(world_data)
            except Exception as world_error:
                logger.error(f"Error processing world {i}: {str(world_error)}", exc_info=True)
                # Still try to add minimal world info
                try:
                    worlds.append({
                        "name": f"World {i}",
                        "sessionId": f"world-{i}",
                        "users": 0,
                        "present": 0,
                        "maxUsers": 0,
                        "uptime": "unknown",
                        "accessLevel": "Unknown",
                        "hidden": False,
                        "mobileFriendly": False,
                        "index": i,
                        "users_list": []
                    })
                except:
                    pass

        logger.info(f"Final worlds list: {len(worlds)} worlds")
        for i, world in enumerate(worlds):
            logger.info(f"World {i}: {world['name']} (sessionId: {world['sessionId']})")
        return worlds
    except Exception as e:
        logger.error(f"Error in process_worlds_command: {str(e)}", exc_info=True)
        return []


@app.get("/")
async def get():
  with open("templates/index.html") as f:
    return HTMLResponse(f.read())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
  await websocket.accept()
  logger.info("connection open")
  active_connections.append(websocket)

  monitor_task = None
  try:
    # Start monitoring Podman output in a separate task
    logger.info("Starting container log monitoring")
    monitor_task = asyncio.create_task(monitor_podman_output(websocket))

    # Handle incoming messages
    while True:
      try:
        # Receive the message with a timeout to handle stalled connections
        message = await asyncio.wait_for(websocket.receive(), timeout=30.0)

        # Check if we got text or bytes (binary) data
        if "text" in message:
            data_str = message["text"]
            is_binary = False
        elif "bytes" in message:
            data_str = message["bytes"].decode("utf-8")
            is_binary = True
        else:
            # Unrecognized message format
            logger.warning("Unrecognized WebSocket message format")
            continue

        # Skip empty messages
        if not data_str or not data_str.strip():
            logger.debug("Received empty WebSocket message, skipping")
            continue

        try:
          # Parse the message as JSON
          data = json.loads(data_str)

          # Validate message structure
          if not isinstance(data, dict) or "type" not in data:
              await websocket.send_json({
                  "type": "error",
                  "message": "Invalid message format: missing 'type' field"
              })
              continue

          if data["type"] == "command":
            # Execute command and send response
            output = podman_manager.send_command(data["command"])

            # Special handling for listbans command
            if data["command"] == "listbans":
              bans = parse_bans(output)
              await websocket.send_json({
                "type": "bans_update",
                "bans": bans
              })
            else:
              await websocket.send_json({
                "type": "command_response",
                "command": data["command"],
                "output": output
              })
          elif data["type"] == "get_status":
            # Get container status and system metrics
            status = podman_manager.get_container_status()

            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = f"{memory.used / (1024 * 1024 * 1024):.1f}GB"
            memory_total = f"{memory.total / (1024 * 1024 * 1024):.1f}GB"

            # Add metrics to status response
            status.update({
              "cpu_usage": cpu_percent,
              "memory_percent": memory_percent,
              "memory_used": memory_used,
              "memory_total": memory_total
            })

            await websocket.send_json({
              "type": "status_update",
              "status": status
            })
          elif data["type"] == "get_worlds":
            try:
              worlds = await process_worlds_command(podman_manager)
              logger.info(f"Sending worlds update with {len(worlds)} worlds")
              # Send the worlds data with a clearer structure
              await websocket.send_json({
                "type": "worlds_update",
                "worlds": worlds  # Changed from "output" to "worlds" for clarity
              })
            except Exception as world_error:
              logger.error("Error processing worlds: %s", str(world_error))
              await websocket.send_json({
                "type": "error",
                "message": f"Error processing worlds: {str(world_error)}"
              })
          else:
              # Unknown message type
              logger.warning(f"Received unknown message type: {data['type']}")
              await websocket.send_json({
                  "type": "error",
                  "message": f"Unknown message type: {data['type']}"
              })
        except json.JSONDecodeError as json_err:
          logger.error(f"JSON parsing error: {json_err}, data: {data_str[:100]}")
          await websocket.send_json({
            "type": "error",
            "message": "Invalid JSON format in message"
          })
        except KeyError as key_err:
          logger.error(f"Missing required field in message: {key_err}")
          await websocket.send_json({
            "type": "error",
            "message": f"Missing required field in message: {key_err}"
          })
      except asyncio.TimeoutError:
        # Just a regular timeout, no need to log or send error
        continue
      except Exception as recv_error:
        logger.error("Error receiving websocket message: %s", str(recv_error))
        # Check if websocket is still connected before trying to continue
        if not await is_websocket_connected(websocket):
          logger.info("WebSocket connection closed")
          break
  except Exception as e:
    logger.error(f"WebSocket error: {e}", exc_info=True)
  finally:
    if websocket in active_connections:
      active_connections.remove(websocket)

    if monitor_task:
      monitor_task.cancel()

    logger.info("connection closed")


async def is_websocket_connected(websocket: WebSocket) -> bool:
  """Check if the websocket is still connected"""
  try:
    # Try sending a ping frame
    await websocket.send_bytes(b'')
    return True
  except Exception:
    return False


async def monitor_podman_output(websocket: WebSocket):
  """Monitor Podman output and send to WebSocket"""
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
  """Send output to WebSocket with improved formatting and structured data"""
  try:
    if await is_websocket_connected(websocket):
      # Ensure the output is properly encoded as JSON
      if not isinstance(output, str):
        output = str(output)

      # Clean terminal output of ANSI escape sequences and prompts
      cleaned_output = clean_terminal_output(output)

      # Extract the first line to determine command type
      first_line = cleaned_output.split("\n")[0] if cleaned_output else ""

      # Check if this is a known command output that should be structured
      if "users" in first_line.lower():
        # Parse users command output
        users_data = parse_users(cleaned_output)
        await websocket.send_json({
          "type": "container_output",
          "info_type": "users",
          "user_list": users_data,
          "raw_output": cleaned_output  # Include cleaned raw output for fallback
        })
      elif "worlds" in first_line.lower():
        # Parse worlds command output
        worlds_data = parse_worlds(cleaned_output)
        await websocket.send_json({
          "type": "container_output",
          "info_type": "worlds",
          "worlds_list": worlds_data,
          "raw_output": cleaned_output  # Include cleaned raw output for fallback
        })
      elif "status" in first_line.lower():
        # Parse status command output
        status_data = parse_status(cleaned_output)
        await websocket.send_json({
          "type": "container_output",
          "info_type": "status",
          "status_data": status_data,
          "raw_output": cleaned_output  # Include cleaned raw output for fallback
        })
      else:
        # Regular terminal output
        await websocket.send_json({
          "type": "container_output",
          "output": cleaned_output
        })
  except Exception as e:
    logger.error(f"Error sending output: {e}")
    # Don't rethrow the exception to avoid crashing the WebSocket handler


@app.get("/config")
async def get_config():
  """Get the current headless config"""
  try:
    result = load_config()
    return JSONResponse(content=result)
  except ValueError as e:
    logger.error("Error in get_config endpoint: %s", str(e))
    raise HTTPException(status_code=500, detail=str(e))
  except Exception as e:
    logger.error("Unexpected error in get_config endpoint: %s", str(e))
    raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.post("/config")
async def update_config(config_data: Dict[Any, Any]):
  """Update the headless config"""
  try:
    save_config(config_data)
    return JSONResponse(content={"message": "Config updated successfully"})
  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/world-properties")
async def update_world_properties(data: dict):
  """Update world properties"""
  try:
    session_id = data.get('sessionId')
    if not session_id:
      raise HTTPException(status_code=400, detail="Session ID is required")

    # Find the world index by sessionId
    worlds = await process_worlds_command(podman_manager)
    world_index = None
    for world in worlds:
      if world.get('sessionId') == session_id:
        world_index = world.get('index')
        break

    if world_index is None:
      raise HTTPException(status_code=404, detail="World not found")

    # Focus on the specific world
    podman_manager.send_command(f"focus {world_index}")

    # Update each property if provided
    if 'name' in data:
      podman_manager.send_command(f"worldname \"{data['name']}\"")

    if 'description' in data:
      podman_manager.send_command(f"description \"{data['description']}\"")

    if 'accessLevel' in data:
      podman_manager.send_command(f"access {data['accessLevel']}")

    if 'maxUsers' in data:
      podman_manager.send_command(f"maxusers {data['maxUsers']}")

    if 'hidden' in data:
      hidden_value = "true" if data['hidden'] else "false"
      podman_manager.send_command(f"hidden {hidden_value}")

    logger.info(f"Updated properties for world with sessionId: {session_id}")
    return JSONResponse(content={"message": "Properties updated successfully"})
  except Exception as e:
    logger.error(f"Error updating world properties: {str(e)}")
    raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/restart-container")
async def restart_container():
  """Restart the Podman container"""
  try:
    podman_manager.restart_container()
    return JSONResponse(content={"message": "Container restart initiated"})
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
  import uvicorn
  uvicorn.run(app, host="0.0.0.0", port=8000)
