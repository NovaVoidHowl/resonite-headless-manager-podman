"""
Stub data source implementation for testing and development.

This module provides a data source that generates realistic dummy data
without requiring actual container infrastructure, perfect for testing
and frontend development.
"""

import logging
import random
import time
import threading
import re
from datetime import datetime
from typing import Any, Dict, List, Callable, Optional

from data_sources.base_data_source import BaseDataSource  # noqa: E402
# pylint: disable=wrong-import-position,import-error

logger = logging.getLogger(__name__)


class StubDataSource(BaseDataSource):
  """
  Stub data source implementation that provides realistic dummy data.

  This data source simulates container operations and generates believable
  test data for development and testing purposes.
  """

  def __init__(self, container_name: str = "resonite-headless", config_file: str = "config.json"):
    """
    Initialize the stub data source.

    Args:
        container_name: Name of the simulated container
        config_file: Path to configuration file (for compatibility)
    """
    self.container_name = container_name
    self.config_file = config_file
    self._container_running = True
    self._log_buffer = []
    self._monitoring_callback: Optional[Callable[[str], None]] = None
    self._monitor_running = False
    self.start_time = datetime.now()

    # Test data that matches the test server format
    self.user_names = [
        "Alice_VR", "Bob_Builder", "Charlie_Explorer", "Diana_Crafter",
        "Eve_Artist", "Frank_Scientist", "Grace_Designer", "Henry_Musician",
        "Iris_Developer", "Jack_Gamer", "Kate_Educator", "Leo_Architect"
    ]
    self.world_names = [
        "Crystal Caverns", "Neon Nexus", "Forest Haven", "Sky Palace",
        "Underground Labs", "Mystic Gardens", "Cyber City", "Ocean Depths",
        "Desert Oasis", "Arctic Station", "Volcano Base", "Cloud Kingdom"
    ]
    self.banned_users = [
        "[0]   Username: SpamUser123   UserID: U-spam123   MachineIds: 668flj393ao9sh8wj9my",
        "[BBdEEDS]   Username: Spam User 123   UserID: U-spam123   MachineIds: 668flj393ao9sh8wj9my",
        "[1]   Username: TrollUser456  UserID: U-troll456  MachineIds: b67d23f456a789c123e4",
        "[2]   Username: HackerUser789  UserID: U-hacker789  MachineIds: c89d45f678b012d345f6"
    ]
    self.friend_requests = ["NewUser789", "AnotherUser321"]

    # info on global commands
    self.native_headless_global_commands = [
      {"saveConfig": "Saves the current settings into the original config file"},
      {"login": "Login to an account - requires username and password"},
      {"logout": "Logout from the current account"},
      {"message": "Message user in friends list - requires username and message"},
      {"friendRequests": "Get list of friend requests"},
      {"acceptFriendRequest": "Accept a friend request - requires username"},
      {"worlds": "Lists all active worlds"},
      {"focus": "Focus on a specific world - requires world world name or number"},
      {"startWorldURL": "Start a world by URL - requires world URL"},
      {"startWorldTemplate": "Start a world by template - requires template name"},
      {"ban": "Bans the user from all sessions hosted by server - requires username"},
      {"unban": "Unbans the user from all sessions hosted by server - requires username"},
      {"listbans": "Lists all active bans"},
      {"banByName": "Bans the user by name from all sessions hosted by server - requires username"},
      {"unbanByName": "Unbans the user by name from all sessions hosted by server - requires username"},
      {"banByID": "Bans the user by ID from all sessions hosted by server - requires user ID"},
      {"unbanByID": "Unbans the user by ID from all sessions hosted by server - requires user ID"},
      {"gc": "Forces full garbage collection"},
      {"debugWorldState": "Prints out diagnostic information for all worlds which can be used for debugging purposes"},
      {"shutdown": "Shuts down the headless client - note if in container this will NOT stop the container"},
      {"tickRate": "Sets the maximum simulation rate for the servers - requires rate in seconds"},
      {"log": (
        "Switches the interactive shell to logging output. Press enter again to restore interactive shell. "
        "- Should not be used, reject command"
      )},
    ]
    self.native_headless_world_specific_commands = [
      {"invite": "Invite user to a world - requires username (must be in friends list)"},
      {"status": "Get status of the current world"},
      {"sessionUrl": "Get session URL of the current world"},
      {"sessionID": "Get session ID of the current world"},
      {"copySessionURL": "Copy session URL to clipboard - NOT SUPPORTED"},
      {"copySessionID": "Copy session ID to clipboard - NOT SUPPORTED"},
      {"users": "Get list of users in the current world"},
      {"close": "Close the current world"},
      {"save": "Save the current world"},
      {"restart": "Restart the current world"},
      {"kick": "Kick a user from the current world - requires username"},
      {"silence": "Silence a user in the current world - requires username"},
      {"unsilence": "Unsilence a user in the current world - requires username"},
      {"respawn": "Respawn a user in the current world - requires username"},
      {"name": "Change the name of the current world - requires new name"},
      {"accessLevel": "Change the access level of the current world - requires new access level"},
      {"hideFromListing": "Hide the current world from public listing - requires boolean value"},
      {"description": "Change the description of the current world - requires new description"},
      {
        "maxUsers": (
          "Change the maximum number of users in the current world - "
          "requires new max users"
        )
      },
      {"awayKickInterval": "Sets the away kick interval for the current world - requires minutes"},
      {"import": "Import an asset into the focused world - requires asset URL or path"},
      {
        "importMinecraft": (
          "Import a Minecraft world. Requires Mineways to be installed. - folder containing Minecraft "
          "world with the level.dat file - NOT SUPPORTED"
        )
      },
      {"dynamicImpulse": "Sends a dynamic impulse with given tag to the scene root - requires tag"},
      {
        "dynamicImpulseString": (
          "Sends a dynamic impulse with given tag and string value to the scene root - "
          "requires tag and string value"
        )
      },
      {
        "dynamicImpulseInt": (
          "Sends a dynamic impulse with given tag and integer value to the scene root - "
          "requires tag and integer value"
        )
      },
      {
        "dynamicImpulseFloat": (
          "Sends a dynamic impulse with given tag and float value to the scene root - "
          "requires tag and float value"
        )
      },
      {
        "spawn": (
          "Spawns an item from a record URL into the world's root - "
          "requires url, state (bool), persistence (bool)"
        )
      },
    ]

    self.custom_global_commands = [
      {"server_status": "global info command - custom command merging worlds and server status"}
    ]
    self.custom_world_specific_commands = [
    ]

    # Initialize with some sample log entries
    self._generate_initial_logs()
    logger.info("StubDataSource initialized with container: %s", container_name)

  def _generate_initial_logs(self) -> None:
    """Generate some initial log entries for realistic behavior."""
    sample_logs = [
        "Starting Resonite headless server...",
        "Loading world data...",
        "Initializing physics engine...",
        "Starting network services...",
        "Server ready for connections",
        f"{datetime.now().isoformat()}: User connected: Alice_VR",
        f"{datetime.now().isoformat()}: World loaded: Crystal Caverns",
        f"{datetime.now().isoformat()}: Network sync established",
        f"{datetime.now().isoformat()}: Asset cache updated",
        f"{datetime.now().isoformat()}: User activity detected"
    ]
    self._log_buffer.extend(sample_logs)

  def _generate_log_entry(self) -> str:
    """Generate a realistic log entry."""
    log_types = [
        f"[{datetime.now().strftime('%H:%M:%S')}] User joined: {random.choice(self.user_names)}",
        f"[{datetime.now().strftime('%H:%M:%S')}] User left: {random.choice(self.user_names)}",
        f"[{datetime.now().strftime('%H:%M:%S')}] World save completed",
        f"[{datetime.now().strftime('%H:%M:%S')}] Network sync update",
        f"[{datetime.now().strftime('%H:%M:%S')}] Asset cache refreshed"
    ]
    return random.choice(log_types)

  # Container Management Operations
  def is_container_running(self) -> bool:
    """Check if the container is currently running."""
    return self._container_running

  def start_container(self) -> None:
    """Start the container."""
    if self._container_running:
      logger.info("Container is already running")
      return

    logger.info("Starting container (simulated)")
    self._container_running = True

    # Simulate startup delay
    time.sleep(0.5)

    # Add startup log entry
    startup_log = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [INFO] Container started successfully"
    self._log_buffer.append(startup_log)

    if self._monitoring_callback:
      self._monitoring_callback(startup_log)

  def stop_container(self) -> None:
    """Stop the container."""
    if not self._container_running:
      logger.info("Container is already stopped")
      return

    logger.info("Stopping container (simulated)")

    # Add shutdown log entry
    shutdown_log = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [INFO] Container shutting down gracefully"
    self._log_buffer.append(shutdown_log)

    if self._monitoring_callback:
      self._monitoring_callback(shutdown_log)

    self._container_running = False
    self._monitor_running = False

  def restart_container(self) -> bool:
    """Restart the container."""
    logger.info("Restarting container (simulated)")

    try:
      self.stop_container()
      time.sleep(1)  # Simulate restart delay
      self.start_container()
      return True
    except (OSError, RuntimeError) as e:
      logger.error("Failed to restart container: %s", e)
      return False

  def get_container_status(self) -> Dict[str, Any]:
    """Get container status information."""
    if self._container_running:
      return {
          "status": "running",
          "name": self.container_name,
          "id": "abc123def456",
          "image": "registry.resonite.io/resonite-headless:latest"
      }
    else:
      return {
          "status": "stopped",
          "name": self.container_name,
          "id": "abc123def456",
          "image": "registry.resonite.io/resonite-headless:latest"
      }

  # Command Operations
  def _is_valid_command(self, command: str) -> tuple[bool, str, str]:
    """
    Check if a command is valid and return command type information.

    Args:
        command: The full command string (e.g., "focus 0" or "ban user123")

    Returns:
        Tuple of (is_valid, command_type, base_command)
        - is_valid: Whether the command is recognized
        - command_type: "global" or "world_specific"
        - base_command: The base command without parameters
    """
    # Extract the base command (first word)
    base_command = command.split()[0] if command.strip() else ""

    # Check global commands
    for cmd_dict in self.native_headless_global_commands:
      if base_command in cmd_dict:
        return True, "global", base_command

    # Check world-specific commands
    for cmd_dict in self.native_headless_world_specific_commands:
      if base_command in cmd_dict:
        return True, "world_specific", base_command

    # Check custom global commands
    for cmd_dict in self.custom_global_commands:
      if base_command in cmd_dict:
        return True, "custom_global", base_command

    # Check custom world-specific commands
    for cmd_dict in self.custom_world_specific_commands:
      if base_command in cmd_dict:
        return True, "custom_world_specific", base_command

    return False, "unknown", base_command

  def get_structured_command_response(self, command: str, target_world_instance: str,
                                      command_mode: str, _timeout: int = 10) -> Dict[str, Any]:
    """Get a structured response for a command with appropriate formatting and type."""
    # Check the container status before executing commands, no point in executing if not running
    if not self._container_running:
      return {
        "type": "error",
        "message": "Container is not running"
      }

    # split command flow based on command mode
    if command_mode == "direct":
      # Direct command execution, no prefix handling
      logger.info("Executing direct command: %s", command)
      # Simulate command processing delay
      time.sleep(random.uniform(0.1, 0.5))

      # direct commands do not have structured responses, just return the output
      # this is more intended for use on the console,
      # We return a base64 encoded blob of the output (to guard against odd characters)

      # for this stub we create a random string of 20 characters then base64 encode it
      output = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=20))
      output = output.encode('utf-8').hex()  # Simulate base64 encoding
      # Return structured response for direct command
      logger.info("Direct command output: %s", output)

      return {
        "type": "command_response",
        "command": command,
        "output": output,
        "timestamp": datetime.now().isoformat()
      }
    elif command_mode == "default":
      # Default command execution with structured response
      logger.info("Executing structured command (simulated): %s", command)

      # Simulate command processing delay
      time.sleep(random.uniform(0.1, 0.5))

      # Use current timestamp for all responses
      current_timestamp = datetime.now().isoformat()

      # Check if provided command is valid
      is_valid, command_type, base_command = self._is_valid_command(command)
      if not is_valid:
        return {
          "type": "error",
          "command": command,
          "message": f"Unknown command: {base_command}",
          "timestamp": current_timestamp
        }

      # Log the command type for debugging
      logger.info("Command '%s' recognized as %s command", base_command, command_type)

      # Handle special commands that need structured responses
      if command == "listbans":  # global info command
        return {
          "type": "bans_update",
          "bans": self.get_banned_users(),
          "timestamp": current_timestamp
        }
      elif command == "friendRequests":  # global info command
        return {
          "type": "command_response",
          "command": command,
          "output": self.get_friend_requests(),
          "timestamp": current_timestamp
        }
      elif command == "users":  # specific to a world
        return {
          "type": "command_response",
          "command": command,
          "world": target_world_instance,
          "output": self.get_users_data(),
          "timestamp": current_timestamp
        }
      elif command == "server_status":  # global info command (custom command merging worlds and server status)
        return {
          "type": "command_response",
          "command": command,
          "output": self.get_server_status(),
          "timestamp": current_timestamp
        }
      else:
        # commands that have not been implemented yet
        logger.warning("Command '%s' is currently not supported", base_command)
        return {
          "type": "command_response",
          "command": command,
          "output": "Currently not supported - no interface defined for this command",
          "timestamp": current_timestamp
        }
    else:
      # Handle unknown command modes - should not happen as there is a check in the API manager
      return {
        "type": "error",
        "message": f"Unknown command mode: {command_mode}",
        "timestamp": datetime.now().isoformat()
      }

  # Log Operations
  def get_container_logs(self) -> str:
    """Get container logs."""
    if not self._container_running:
      return "Container is not running"

    return "\n".join(self._log_buffer[-100:])  # Return last 100 lines

  def get_recent_logs(self) -> List[str]:
    """Get recent log lines from buffer."""
    return self._log_buffer[-20:]  # Return last 20 lines

  def monitor_output(self, callback: Callable[[str], None]) -> None:
    """Monitor container output continuously."""
    self._monitoring_callback = callback
    self._monitor_running = True

    # Start background task to generate periodic log entries
    def log_generator():
      while self._monitor_running and self._container_running:
        time.sleep(random.uniform(2, 8))  # Random interval between logs
        if self._monitor_running and self._container_running:
          log_entry = self._generate_log_entry()
          self._log_buffer.append(log_entry)
          if callback:
            callback(log_entry)

    thread = threading.Thread(target=log_generator, daemon=True)
    thread.start()

  # Configuration Operations
  def get_config_status(self) -> Dict[str, Any]:
    """Get configuration status."""
    return {
        "using_config_file": True  # Simulate config file usage
    }

  def get_manger_config_settings(self) -> Dict[str, Any]:
    """Get current configuration settings."""
    return {
      "cache": {
        "worlds_interval": 10,
        "status_interval": 10,
        "sessionurl_interval": 30,
        "sessionid_interval": 30,
        "users_interval": 5,
        "listbans_interval": 60
      },
      "headless_server": {
        "config_folder": "../../_stub_headless/"
      }
    }

  def update_manager_config_settings(self, settings_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update manager configuration settings."""
    # In a real implementation, this would save to a configuration file
    # For the stub, we'll just simulate a successful update
    logger.info("Updating manager config settings (stub mode): %s", settings_data)
    return {
        "message": "Manager configuration updated successfully (test mode)",
        "updated_settings": settings_data,
        "test_mode": True
    }

  def generate_config(self) -> Dict[str, Any]:
    """Generate configuration file."""
    return {
        "message": "Config file generated successfully (test mode)",
        "config_file": self.config_file,
        "test_mode": True
    }

  def get_cpu_usage(self) -> float:
    """Get current CPU usage percentage."""
    # Generate realistic CPU usage between 20-80% like test server
    base = 35.0
    variation = random.uniform(-15.0, 25.0)
    return max(5.0, min(95.0, base + variation))

  def get_memory_usage(self) -> Dict[str, Any]:
    """Get current memory usage information."""
    # Generate realistic memory usage like test server
    total_gb = 16.0
    used_percent = random.uniform(30.0, 75.0)
    used_gb = (total_gb * used_percent) / 100.0

    return {
        "percent": round(used_percent, 1),
        "used": f"{used_gb:.1f}GB",
        "total": f"{total_gb:.1f}GB"
    }

  def get_worlds_data(self) -> List[Dict[str, Any]]:
    """Generate realistic worlds data matching test server format."""
    num_worlds = random.randint(1, 4)
    worlds = []

    for _ in range(num_worlds):
      world_name = random.choice(self.world_names)
      users_count = random.randint(1, 8)
      max_users = random.randint(max(users_count, 5), 20)
      present_users = random.randint(1, users_count)

      # Generate session ID
      session_id = f"S-{random.randint(100000, 999999)}"

      # Calculate uptime
      uptime_minutes = random.randint(5, 240)
      uptime = f"{uptime_minutes // 60}h {uptime_minutes % 60}m" if uptime_minutes >= 60 else f"{uptime_minutes}m"

      world = {
          "name": world_name,
          "sessionId": session_id,
          "users": users_count,
          "present": present_users,
          "maxUsers": max_users,
          "uptime": uptime,
          "accessLevel": random.choice(["Private", "Friends", "FriendsOfFriends", "RegisteredUsers", "Anyone"]),
          "mobileFriendly": random.choice([True, False]),
          "description": f"A beautiful {world_name.lower()} world for exploration and creativity",
          "tags": random.sample(["Creative", "Social", "Educational", "Gaming", "Art", "Music"], 2),
          "user_count": {
              "connected_to_instance": users_count,
              "present": present_users,
              "max_users": max_users
          },
          "access_level": random.choice(["Private", "Friends", "FriendsOfFriends", "RegisteredUsers", "Anyone"]),
          "mobile_friendly": random.choice([True, False])
      }
      worlds.append(world)

    return worlds

  def get_users_data(self) -> List[Dict[str, Any]]:
    """Generate users data for a world matching test server format."""
    num_users = random.randint(2, 6)
    users = []

    for _ in range(num_users):
      username = random.choice(self.user_names)
      user = {
          "username": username,
          "id": f"U-{random.randint(100000, 999999)}",
          "role": random.choice(["Guest", "Builder", "Moderator", "Admin"]),
          "sessionTime": f"{random.randint(5, 120)}m",
          "isPresent": random.choice([True, False]),
          "platform": random.choice(["Desktop", "VR", "Mobile"])
      }
      users.append(user)

    return users

  def get_server_status(self) -> Dict[str, Any]:
    """Generate server status matching test server format."""
    uptime = datetime.now() - self.start_time
    uptime_str = str(uptime).split('.', maxsplit=1)[0]  # Remove microseconds

    worlds_data = self.get_worlds_data()
    return {
        "status": "running",
        "uptime": uptime_str,
        "version": "2024.3.28",
        "worlds_active": len(worlds_data),
        "total_users": sum(world["users"] for world in worlds_data),
        "server_time": datetime.now().isoformat()
    }

  def get_headless_config(self) -> Dict[str, Any]:
    """Generate realistic headless config matching test server format."""
    return {
        "startWorlds": [
            {
                "sessionName": "Test World 1",
                "description": "A test world for API testing",
                "maxUsers": 16,
                "accessLevel": "RegisteredUsers",
                "mobileFriendly": True,
                "tags": ["test", "api", "development"],
                "parentSessionIds": [],
                "awayKickMinutes": 60,
                "hideFromListing": False,
                "autoRecover": True
            }
        ],
        "dataFolder": "/app/data",
        "cacheFolder": "/app/cache",
        "logFolder": "/app/logs",
        "enableGCOptimization": True,
        "backgroundWorkers": 4,
        "autoSaveInterval": 300,
        "maxConcurrentAssetTransfers": 8,
        "useBinaryTransport": True,
        "maxUploadSpeed": 10000000
    }

  def get_banned_users(self) -> List[Dict[str, Any]]:
    """Get banned users list matching test server format."""
    # Parse the banned users using regex to handle spaces in usernames
    formatted_bans = []

    for ban_string in self.banned_users:
      # Regex pattern to match: [anything] Username: value UserID: value MachineIds: value
      pattern = r'\[.*?\]\s+Username:\s*(.+?)\s+UserID:\s*(.+?)\s+MachineIds:\s*(.+)$'
      match = re.match(pattern, ban_string)

      if match:
        username = match.group(1).strip()
        user_id = match.group(2).strip()
        machine_ids = match.group(3).strip()

        user_info = {
          "username": username,
          "userId": user_id,
          "machineIds": machine_ids
        }
        formatted_bans.append(user_info)
      else:
        # Fallback for malformed strings - log and skip
        logger.warning("Could not parse ban string: %s", ban_string)

    return formatted_bans

  def get_friend_requests(self) -> List[str]:
    """Get friend requests list matching test server format."""
    return self.friend_requests.copy()

  def get_random_log_line(self) -> str:
    """Generate a random log line matching test server format."""
    return self._generate_log_entry()

  # Resource Management
  def cleanup(self) -> None:
    """Clean up resources when data source is being shut down."""
    logger.info("Cleaning up stub data source")
    self._monitor_running = False
    self._monitoring_callback = None

  # Data source metadata
  def get_data_source_info(self) -> Dict[str, Any]:
    """Get information about this data source."""
    return {
        "type": "StubDataSource",
        "description": "Test data source providing dummy data for development",
        "is_live": False,
        "container_name": self.container_name,
        "test_mode": True
    }
