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
from datetime import datetime
from typing import Any, Dict, List, Callable, Optional

from .base_data_source import BaseDataSource

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
        {"[0]   username: SpamUser123   UserID: U-spam123   MachineIds: 668flj393ao9sh8wj9my"},
        {"[0]   username: TrollUser456  UserID: U-troll456  MachineIds: b67d23f456a789c123e4"}
    ]
    self.friend_requests = ["NewUser789", "AnotherUser321"]

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
        f"[{datetime.now().strftime('%H:%M:%S')}] Asset cache refreshed",
        f"[{datetime.now().strftime('%H:%M:%S')}] Physics step: 60 FPS",
        f"[{datetime.now().strftime('%H:%M:%S')}] Memory usage: {self.get_memory_usage()['percent']}%",
        f"[{datetime.now().strftime('%H:%M:%S')}] CPU usage: {self.get_cpu_usage():.1f}%"
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
    except Exception as e:
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
  def send_command(self, command: str, timeout: int = 10, use_cache: bool = True) -> str:
    """Send a command to the container with responses matching test server format."""
    if not self._container_running:
      return "Error: Container is not running"

    logger.info("Executing command (simulated): %s", command)

    # Simulate command processing delay
    time.sleep(random.uniform(0.1, 0.5))

    # Generate realistic responses based on command matching test server
    if command == "status":
      return ("Server Status: Running\n"
              "Uptime: 2h 30m\n"
              "Active Users: 3\n"
              "World: Crystal Caverns")
    elif command == "users":
      return ("Connected Users:\n"
              "1. Alice_VR (Admin) - 45m\n"
              "2. Bob_Builder (Builder) - 32m\n"
              "3. Charlie_Explorer (Guest) - 15m")
    elif command == "listbans":
      return ("[0]\tUsername: SpamUser123\tUserID: U-spam123\tMachineIds: a45f8d9e334c9b7a99d1\n"
              "[1]\tUsername: TrollUser456\tUserID: U-troll456\tMachineIds: b67d23f456a789c123e4")
    elif command == "friendRequests":
      return "NewUser789\nAnotherUser321"
    elif command.startswith("save"):
      return "World saved successfully"
    elif command.startswith("kick"):
      user = command.split(' ', 1)[1] if ' ' in command else 'unknown'
      return f"User kicked successfully: {user}"
    elif command.startswith("ban"):
      user = command.split(' ', 1)[1] if ' ' in command else 'unknown'
      return f"User banned successfully: {user}"
    elif command.startswith("unban"):
      user = command.split(' ', 1)[1] if ' ' in command else 'unknown'
      return f"User unbanned successfully: {user}"
    else:
      return f"Unexpected Command: {command}"

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

  def get_config_settings(self) -> Dict[str, Any]:
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
        "config_folder": "../_stub_headless/"
      }
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
    uptime_str = str(uptime).split('.')[0]  # Remove microseconds

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
    return self.banned_users.copy()

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
