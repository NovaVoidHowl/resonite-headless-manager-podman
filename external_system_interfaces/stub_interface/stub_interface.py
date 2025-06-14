"""
Podman container interface module for the Resonite Headless Manager.

This module provides simple functions to:
- Control Podman containers (start/stop/restart)
- Execute commands within containers
- Get container status and logs
- Check container health
"""

import logging
import random
import string
import time
from typing import Any, Dict, List

# Configure logging
logger = logging.getLogger(__name__)

# Constants
ERROR_CLIENT_NOT_INITIALIZED = "Podman client not initialized"
ERROR_CONTAINER_NOT_RUNNING = "Container is not running"
ERROR_CONTAINER_NOT_FOUND = "Container not found"


def is_container_running(_container_name: str) -> bool:
  """
  Check if a container is currently running.

  Args:
      container_name (str): Name of the container to check

  Returns:
      bool: True if the container is running, False otherwise
  """
 # this is a stub so just return True
  return True


def get_container_status(container_name: str) -> Dict[str, Any]:
  """
  Get container status information.

  Args:
      container_name (str): Name of the container

  Returns:
      Dict[str, Any]: Dictionary containing container status information
  """

  # makeup a container id, random string of length 8
  container_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

  return {
    'status': "running",  # Stubbed status
    'name': container_name,

    'id': container_id,
    'image': "example/image:latest",  # Stubbed image name
  }


def start_container(container_name: str) -> bool:
  """
  Start a Podman container.

  Args:
      container_name (str): Name of the container to start

  Returns:
      bool: True if successful, False otherwise
  """
  # stub so wait a bit and return True
  time.sleep(1)
  logger.info("Container '%s' started successfully", container_name)
  return True


def stop_container(container_name: str) -> bool:
  """
  Stop a Podman container.

  Args:
      container_name (str): Name of the container to stop

  Returns:
      bool: True if successful, False otherwise
  """
  # stub so wait a bit and return True
  time.sleep(1)
  logger.info("Container '%s' stopped successfully", container_name)
  return True


def restart_container(container_name: str) -> bool:
  """
  Restart a Podman container.

  Args:
      container_name (str): Name of the container to restart

  Returns:
      bool: True if successful, False otherwise
  """
  # stub so wait a bit and return True
  time.sleep(1)
  logger.info("Container '%s' restarted successfully", container_name)
  return True


def _handle_user_action_command(command_lower: str, action: str) -> str:
  """Helper function to handle user action commands (kick, silence, etc.)"""
  username = command_lower.split(" ", 1)[1] if " " in command_lower else "user"

  match action:
    case "kick":
      return (f"KickRequest: True for User ID3632F00 (Alloc: 1) - UserName: {username}, "
              f"UserId: U-1e0baHzIF4i, MachineId: 66m********bmy, Role: Guest. "
              f"Changing User: , ScheduledForValidation: True\n"
              f"{username} kicked!")
    case "silence":
      return (f"Silence: True for User ID417D100 (Alloc: 1) - UserName: {username}, "
              f"UserId: U-1e0baHzIF4i, MachineId: 66*********bmy, Role: Guest. "
              f"Changing User:\n"
              f"{username} silenced!")
    case "unsilence":
      return (f"Silence: False for User ID417D100 (Alloc: 1) - UserName: {username}, "
              f"UserId: U-1e0baHzIF4i, MachineId: 66***bmy, Role: Guest. "
              f"Changing User: User ID2E00 (Alloc: 0) - UserName: TWC-Headless-Bot, "
              f"UserId: U-1diPwgYpBhY, MachineId: du***g5y, Role: Admin\n"
              f"{username} unsilenced!")
    case "ban":
      return (f"BanRequest: True for User ID296C700 (Alloc: 1) - UserName: {username}, "
              f"UserId: U-1e0baHzIF4i, MachineId: 66*****bmy, Role: Guest. "
              f"Changing User: , ScheduledForValidation: True\n"
              f"{username} banned!\n"
              f"Banning user User ID296C700 (Alloc: 1) - UserName: {username}, "
              f"UserId: U-1e0baHzIF4i, MachineId: 66*****************bby, "
              f"Role: Guest. Last Changing User:")
    case "respawn":
      return (f"Destroying User: User ID4CC3C00 (Alloc: 1) - UserName: {username}, "
              f"UserId: U-1e0baHzIF4i, MachineId: 66******bmy, Role: Builder\n"
              f"Currently updating user: User ID2E00 (Alloc: 0) - UserName: TWC-Headless-Bot, "
              f"UserId: U-1diPwgYpBhY, MachineId: du****6g5y, Role: Admin\n"
              f"{username} respawned!")
    case _:
      return f"Unknown user action: {action}"


def _handle_role_command(command_lower: str) -> str:
  """Helper function to handle role assignment command"""
  parts = command_lower.split(" ", 2)
  username = parts[1] if len(parts) > 1 else "user"
  role = parts[2].capitalize() if len(parts) > 2 else "Guest"
  return f"{username} now has role {role}!"


def _get_invite_response() -> str:
  """Helper function to return the complex invite response"""
  return ("Updated: 01/01/0001 00:00:00 -> 07/06/2025 14:25:53\n"
          "Updated:  -> TWC Debug - do not join\n"
          "Updated:  -> Instance to test out headless management interface\n"
          "Updated:  -> S-87fe7d8f-6571-4c6a-938b-21c0757afab8\n"
          "Updated: Private -> RegisteredUsers\n"
          "Updated: False -> True\n"
          "Updated: 0 -> 5\n"
          "Updated:  -> U-1diPwgYpBhY\n"
          "Updated:  -> ad8f0e9c-4051-4c2c-8db8-f2d520239d32\n"
          "Updated:  -> TWC-Headless-Bot\n"
          "Updated:  -> du7zuugh11mh1kha6kne6c1qfybha6ms41i6e3p5fcbca8as6g5y\n"
          "Updated: False -> True\n"
          "Updated:  -> https://skyfrost-archive.resonite.com/thumbnails/"
          "72802320-f872-4005-ab64-0f036521c198.webp\n"
          "SIGNALR: SendMessage - Id: MSG-65ebc6b6-4ead-4ea4-bfac-59841500e35e, "
          "OwnerId: U-1diPwgYpBhY, RecipientId: U-1e0baHzIF4i, "
          "SenderId: U-1diPwgYpBhY, Type: SessionInvite\n"
          "SIGNALR: BroadcastSession SessionInfo. Id: S-87fe7d8f-6571-4c6a-938b-21c0757afab8, "
          "Name: TWC Debug - do not join, Host: TWC-Headless-Bot, CorrespondingWorldId: , "
          "URLs: lnl-nat://6a95325a-dbe2-4397-afda-f735285b5000/"
          "S-87fe7d8f-6571-4c6a-938b-21c0757afab8, IsExpired: False to Public\n"
          "Invite sent!")


def execute_command(container_name: str, command: str, _timeout: int = 10) -> str:
  """
  Execute a command in a container.

  Args:
    container_name (str): Name of the container
    command (str): Command to execute
    timeout (int): Timeout for command execution in seconds

  Returns:
    str: Output from the command
  """
  logger.info("Executing command in container '%s': %s", container_name, command)

  # Simulate command execution delay
  time.sleep(0.5)

  # Parse command and return appropriate stub responses based on Resonite headless commands
  command_lower = command.lower().strip()
  command_parts = command_lower.split(" ", 1)
  base_command = command_parts[0]

  # Use match-case for better readability and reduced cognitive complexity
  match base_command:
    case "status":
      return """Name: TWC Debug - do not join
SessionID: S-87fe7d8f-6571-4c6a-938b-21c0757afab8
Current Users: 1
Present Users: 0
Max Users: 6
Uptime: 01:12:35.4423964
Access Level: RegisteredUsers
Hidden from listing: False
Mobile Friendly: False
Description: Instance to test out headless management interface
Tags: debug, test, TheWorldCore
Users: TWC-Headless-Bot"""

    case "users":
      return ("TWC-Headless-Bot        ID: U-1diPwgYpBhY       "
              "Role: Admin     Present: False  Ping: 0 ms      FPS: 60.00322   Silenced: False\n"
              "TWC-Test-User1  ID: U-1e0baHzIF4i       "
              "Role: Builder   Present: True   Ping: 0 ms      FPS: 59.999996  Silenced: False")

    case "worlds":
      return ("[0] TWC Debug - do not join         Users: 2    Present: 1      "
              "AccessLevel: RegisteredUsers    MaxUsers: 6")

    case "sessionurl":
      return "https://go.resonite.com/session/S-87fe7d8f-6571-4c6a-938b-21c0757afab8"

    case "sessionid":
      return "S-87fe7d8f-6571-4c6a-938b-21c0757afab8"

    case "friendrequests":
      return "TWC-Test-User1"

    case "listbans":
      return "[0]     Username: TWC-Test-User1        UserID: U-1e0baHzIF4i   MachineIds: 668************bmy"

    case "debugworldstate":
      return """World: Userspace, Handle: 1
  WorldStage: RefreshBegin
  SyncTick: 1
  WorldSessionState:
  WorldSessionStopProcessing:
  WorldMessagesToProcess:
  WorldTotalProcessedMessages:
  WorldMessagesToTransmit:
  ProcessingSyncMessage:
  CurrentlyDecodingStream:
World: TWC Debug - do not join, Handle: 2
  WorldStage: RefreshBegin
  SyncTick: 191540
  WorldSessionState: WaitingForSyncThreadEvent
  WorldSessionStopProcessing: False
  WorldMessagesToProcess: 0
  WorldTotalProcessedMessages: 128420
  WorldMessagesToTransmit: 0
  ProcessingSyncMessage:
  CurrentlyDecodingStream:"""

    case "gc":
      return "GC finished"

    case "login":
      return "Login successful!"

    case "logout":
      return "Logged out successfully!"

    case "message":
      return ("SIGNALR: SendMessage - Id: MSG-2fc37ac0-8e99-44de-a2a7-1ab1ae0098f4, "
              "OwnerId: U-1diPwgYpBhY, RecipientId: U-1e0baHzIF4i, "
              "SenderId: U-1diPwgYpBhY, Type: Text\n"
              "Message sent!")

    case "invite":
      return _get_invite_response()

    case "acceptfriendrequest":
      return "Request accepted!"

    case "kick":
      return _handle_user_action_command(command_lower, "kick")

    case "silence":
      return _handle_user_action_command(command_lower, "silence")

    case "unsilence":
      return _handle_user_action_command(command_lower, "unsilence")

    case "ban":
      return _handle_user_action_command(command_lower, "ban")

    case "unban":
      return "Removed 1 matching bans"

    case "respawn":
      return _handle_user_action_command(command_lower, "respawn")

    case "role":
      return _handle_role_command(command_lower)

    case "saveconfig":
      return "Configuration saved successfully!"

    case "save":
      return "World saved successfully!"

    case "close":
      return "World closed successfully!"

    case "restart":
      return "World restarted successfully!"

    case "shutdown":
      return "Shutting down headless client..."

    case "name" | "description" | "accesslevel" | "maxusers" | "tickrate":
      return "Setting updated successfully!"

    case "hidefromlisting" | "awaykickinterval":
      return "Setting updated successfully!"

    case cmd if cmd.startswith(("dynamicimpulse", "spawn", "import")):
      return "Command executed successfully!"

    case _:
      return f"Command '{command}' executed successfully (stub response)"


def get_container_logs(container_name: str, tail: int = 100) -> str:
  """
  Get logs from a container.

  Args:
    container_name (str): Name of the container
    tail (int): Number of lines to retrieve from the end

  Returns:
    str: Container logs
  """
  # This is a stub implementation, return fake log data
  logger.info("Getting logs for container '%s' (last %d lines)", container_name, tail)

  # Generate realistic stub log entries
  stub_logs = [
    "2025-06-14 10:15:23 [INFO] Resonite Headless starting up...",
    "2025-06-14 10:15:24 [INFO] Loading configuration from Config.json",
    "2025-06-14 10:15:25 [INFO] Initializing world manager",
    "2025-06-14 10:15:26 [INFO] Starting world: TWC Debug - do not join",
    "2025-06-14 10:15:27 [INFO] World loaded successfully",
    "2025-06-14 10:15:28 [INFO] Session ID: S-87fe7d8f-6571-4c6a-938b-21c0757afab8",
    "2025-06-14 10:15:29 [INFO] User TWC-Headless-Bot joined the session",
    "2025-06-14 10:16:15 [INFO] User TWC-Test-User1 joined the session",
    "2025-06-14 10:16:16 [INFO] User TWC-Test-User1 role changed to Builder",
    "2025-06-14 10:17:30 [INFO] Dynamic impulse received: test_impulse",
    "2025-06-14 10:18:45 [INFO] World saved successfully",
    "2025-06-14 10:19:12 [INFO] Heartbeat: 2 users active, 1 present"
  ]

  # Return the last 'tail' number of lines
  return '\n'.join(stub_logs[-tail:]) if tail < len(stub_logs) else '\n'.join(stub_logs)


def list_containers() -> List[Dict[str, Any]]:
  """
  List all containers.

  Returns:
    List[Dict[str, Any]]: List of container information
  """
  # stub so return a list of fake containers
  return [
    {
      'name': 'example_container_1',
      'id': '12345678',
      'image': 'example/image:latest',
      'status': 'running'
    },
    {
      'name': 'example_container_2',
      'id': '87654321',
      'image': 'another/image:latest',
      'status': 'stopped'
    }
  ]


def container_exists(_container_name: str) -> bool:
  """
  Check if a container exists.

  Args:
    container_name (str): Name of the container to check

  Returns:
    bool: True if container exists, False otherwise
  """
  # stub so just return True
  return True


def cleanup():
  """
  Cleanup any resources used by the interface.

  This is a stub function for cleanup operations.
  """
  # In a real implementation, this would clean up any resources or connections
  logger.info("Cleanup called, but no resources to clean up in stub implementation.")
