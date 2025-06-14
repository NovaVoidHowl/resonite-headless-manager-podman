"""
Podman container interface module for the Resonite Headless Manager.

This module provides a complete implementation of the ExternalSystemInterface
for managing Podman containers. It provides functions to:
- Control Podman containers (start/stop/restart)
- Execute commands within containers
- Get container status and logs
- Check container health
"""

import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import podman
from podman import errors as podman_errors

# Import the base interface
sys.path.append(str(Path(__file__).parent.parent))
from base_interface import ExternalSystemInterface  # noqa: E402 pylint: disable=wrong-import-position,import-error

# Configure logging
logger = logging.getLogger(__name__)

# Constants
ERROR_CLIENT_NOT_INITIALIZED = "Podman client not initialized"
ERROR_CONTAINER_NOT_RUNNING = "Container is not running"
ERROR_CONTAINER_NOT_FOUND = "Container not found"

# Global client instance
_client: Optional[podman.PodmanClient] = None


class PodmanInterface(ExternalSystemInterface):
  """
  Podman implementation of the ExternalSystemInterface.

  This class provides container management capabilities using Podman,
  implementing all methods from the base interface.
  """

  def __init__(self):
    """Initialize the Podman interface."""
    self._client: Optional[podman.PodmanClient] = None

  def is_instance_running(self, instance_name: str) -> bool:
    """
    Check if a container is currently running.

    Args:
        instance_name (str): Name of the container to check

    Returns:
        bool: True if the container is running, False otherwise
    """
    try:
      client = self._get_client()
      if not client:
        return False

      container = client.containers.get(instance_name)
      return container.status == 'running'
    except (podman_errors.APIError, podman_errors.ContainerNotFound, OSError) as e:
      logger.error("Error checking container status: %s", str(e))
      return False

  def get_instance_status(self, instance_name: str) -> Dict[str, Any]:
    """
    Get container status information.

    Args:
        instance_name (str): Name of the container

    Returns:
        Dict[str, Any]: Dictionary containing container status information
    """
    try:
      client = self._get_client()
      if not client:
        return {'error': ERROR_CLIENT_NOT_INITIALIZED, 'status': 'unknown'}

      container = client.containers.get(instance_name)
      inspect_data = container.inspect()

      return {
        'status': container.status,
        'name': container.name,
        'id': container.id,
        'image': inspect_data.get('ImageName', container.image)
      }
    except (podman_errors.APIError, podman_errors.ContainerNotFound, OSError) as e:
      logger.error("Error getting container status: %s", str(e))
      return {'error': str(e), 'status': 'unknown'}

  def start_instance(self, instance_name: str) -> bool:
    """
    Start a Podman container.

    Args:
        instance_name (str): Name of the container to start

    Returns:
        bool: True if successful, False otherwise
    """
    try:
      client = self._get_client()
      if not client:
        logger.error(ERROR_CLIENT_NOT_INITIALIZED)
        return False

      container = client.containers.get(instance_name)
      container.start()

      # Wait for container to be running
      for _ in range(10):
        container.reload()
        if container.status == 'running':
          logger.info("Container '%s' successfully started", instance_name)
          return True
        time.sleep(1)

      logger.warning("Container start took longer than expected")
      return False

    except (podman_errors.APIError, podman_errors.ContainerNotFound, OSError) as e:
      logger.error("Failed to start container '%s': %s", instance_name, str(e))
      return False

  def stop_instance(self, instance_name: str) -> bool:
    """
    Stop a Podman container.

    Args:
        instance_name (str): Name of the container to stop

    Returns:
        bool: True if successful, False otherwise
    """
    try:
      client = self._get_client()
      if not client:
        logger.error(ERROR_CLIENT_NOT_INITIALIZED)
        return False

      container = client.containers.get(instance_name)
      container.stop()

      # Wait for container to be stopped
      for _ in range(10):
        container.reload()
        if container.status != 'running':
          logger.info("Container '%s' successfully stopped", instance_name)
          return True
        time.sleep(1)

      logger.warning("Container stop took longer than expected")
      return False

    except (podman_errors.APIError, podman_errors.ContainerNotFound, OSError) as e:
      logger.error("Failed to stop container '%s': %s", instance_name, str(e))
      return False

  def restart_instance(self, instance_name: str) -> bool:
    """
    Restart a Podman container.

    Args:
        instance_name (str): Name of the container to restart

    Returns:
        bool: True if successful, False otherwise
    """
    try:
      client = self._get_client()
      if not client:
        logger.error(ERROR_CLIENT_NOT_INITIALIZED)
        return False

      container = client.containers.get(instance_name)
      logger.info("Restarting container: %s", instance_name)
      container.restart(timeout=30)

      # Wait for container to be running
      for _ in range(10):
        container.reload()
        if container.status == 'running':
          logger.info("Container '%s' successfully restarted", instance_name)
          return True
        time.sleep(1)

      logger.warning("Container restart took longer than expected")
      return False

    except (podman_errors.APIError, podman_errors.ContainerNotFound, OSError) as e:
      logger.error("Failed to restart container '%s': %s", instance_name, str(e))
      return False

  def execute_command(self, instance_name: str, command: str, timeout: int = 10) -> str:
    """
    Execute a command in a container via podman attach.

    Args:
      instance_name (str): Name of the container
      command (str): Command to execute
      timeout (int): Timeout for command execution in seconds

    Returns:
      str: Output from the command
    """
    logger.info("Executing command in container '%s': %s", instance_name, command)

    try:
      if not self.is_instance_running(instance_name):
        logger.error("Container '%s' is not running", instance_name)
        return f"Error: {ERROR_CONTAINER_NOT_RUNNING}"

      # Create temporary file for output
      with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as cmd_file:
        cmd_path = cmd_file.name
        cmd_file.write(command)

      output_path = os.path.join(os.path.dirname(cmd_path), f"output_{os.getpid()}.txt")

      try:
        # Use script and podman attach to execute the command
        attach_cmd = [
          "script", "-q", output_path, "-c",
          f"podman attach --detach-keys='ctrl-d' {instance_name}"
        ]

        process = subprocess.Popen(
          attach_cmd,
          stdin=subprocess.PIPE,
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
          text=True
        )

        # Send command and detach sequence
        time.sleep(1)
        if process.stdin:
          process.stdin.write(f"{command}\n")
          process.stdin.flush()
          time.sleep(2)
          process.stdin.write("\x04")  # Ctrl-D to detach
          process.stdin.flush()

        # Wait for process to complete
        try:
          process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
          logger.warning("Command timed out after %d seconds", timeout)
          process.terminate()
          try:
            process.wait(timeout=2)
          except subprocess.TimeoutExpired:
            process.kill()

        # Read and process output
        if os.path.exists(output_path):
          with open(output_path, 'r', encoding='utf-8') as output_file:
            output = output_file.read()
            return self._process_command_output(output, command)
        else:
          return "No output captured"

      finally:
        # Clean up temporary files
        for path in [cmd_path, output_path]:
          try:
            if os.path.exists(path):
              os.unlink(path)
          except OSError as e:
            logger.warning("Error cleaning up file %s: %s", path, str(e))

    except (OSError, podman_errors.APIError, podman_errors.ContainerNotFound) as e:
      error_msg = str(e).strip() or "Unknown error"
      logger.error("Error executing command in container '%s': %s", instance_name, error_msg)
      return f"Error: {error_msg}"

  def get_instance_logs(self, instance_name: str, tail: int = 100) -> str:
    """
    Get logs from a container.

    Args:
      instance_name (str): Name of the container
      tail (int): Number of lines to retrieve from the end

    Returns:
      str: Container logs
    """
    try:
      client = self._get_client()
      if not client:
        return f"Error: {ERROR_CLIENT_NOT_INITIALIZED}"

      container = client.containers.get(instance_name)
      logs = container.logs(tail=tail)

      # Handle different log formats
      if hasattr(logs, '__iter__'):
        log_lines = []
        for line in logs:
          if isinstance(line, bytes):
            log_lines.append(line.decode('utf-8'))
          else:
            log_lines.append(str(line))
        return ''.join(log_lines)
      else:
        return logs.decode('utf-8') if isinstance(logs, bytes) else str(logs)

    except (podman_errors.APIError, podman_errors.ContainerNotFound, OSError) as e:
      logger.error("Error getting logs for container '%s': %s", instance_name, str(e))
      return f"Error getting logs: {str(e)}"

  def list_instances(self) -> List[Dict[str, Any]]:
    """
    List all containers.

    Returns:
      List[Dict[str, Any]]: List of container information
    """
    try:
      client = self._get_client()
      if not client:
        return []

      containers = client.containers.list(all=True)
      return [
        {
          'name': container.name,
          'id': container.id,
          'status': container.status,
          'image': container.image
        }
        for container in containers
      ]

    except (podman_errors.APIError, podman_errors.ContainerNotFound, OSError) as e:
      logger.error("Error listing containers: %s", str(e))
      return []

  def instance_exists(self, instance_name: str) -> bool:
    """
    Check if a container exists.

    Args:
      instance_name (str): Name of the container to check

    Returns:
      bool: True if container exists, False otherwise
    """
    try:
      client = self._get_client()
      if not client:
        return False

      client.containers.get(instance_name)
      return True

    except podman_errors.ContainerNotFound:
      return False
    except (podman_errors.APIError, OSError) as e:
      logger.error("Error checking if container '%s' exists: %s", instance_name, str(e))
      return False

  def cleanup(self) -> None:
    """Clean up the Podman client connection."""
    if self._client:
      try:
        self._client.close()
      except (podman_errors.APIError, OSError, AttributeError) as e:
        logger.warning("Error closing Podman client: %s", str(e))
      finally:
        self._client = None

  def get_supported_commands(self) -> List[str]:
    """
    Get a list of commands supported by execute_command.

    Returns:
        List[str]: List of supported command names
    """
    # Return Resonite headless commands that can be executed
    return [
      "status", "users", "worlds", "sessionurl", "sessionid", "friendrequests",
      "listbans", "debugworldstate", "gc", "login", "logout", "message", "invite",
      "acceptfriendrequest", "kick", "silence", "unsilence", "ban", "unban",
      "respawn", "role", "saveconfig", "save", "close", "restart", "shutdown",
      "name", "description", "accesslevel", "maxusers", "tickrate",
      "hidefromlisting", "awaykickinterval", "dynamicimpulse", "spawn", "import"
    ]

  def _get_client(self) -> Optional[podman.PodmanClient]:
    """
    Get or initialize the Podman client.

    Returns:
        Optional[podman.PodmanClient]: The Podman client or None if connection fails
    """
    if self._client is not None:
      try:
        self._client.ping()
        return self._client
      except (podman_errors.APIError, OSError):
        self._client = None

    connection_methods = [
        {"uri": "http+unix:///run/podman/podman.sock", "desc": "Unix socket"},
        {"uri": "http+unix:///run/user/0/podman/podman.sock", "desc": "User Unix socket"},
        {"uri": "tcp://localhost:8888", "desc": "TCP localhost:8888"},
    ]

    for method in connection_methods:
      try:
        logger.info("Trying to connect using %s", method['desc'])
        client = podman.PodmanClient(base_url=method["uri"])
        client.ping()
        self._client = client
        logger.info("Successfully connected using %s", method['desc'])
        return self._client
      except (podman_errors.APIError, OSError) as e:
        logger.warning("Connection failed with %s: %s", method['desc'], str(e))

    logger.error("All connection attempts failed")
    return None

  def _clean_output(self, text: str) -> List[str]:
    """
    Clean and format output text by removing ANSI sequences and handling line breaks.

    Args:
        text (str): The text to clean

    Returns:
        List[str]: List of cleaned lines
    """
    ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]|\x1B[()][AB012]')
    clean_text = ansi_escape.sub('', text)
    lines = [line.strip() for line in clean_text.replace('\r\n', '\n').split('\n')]
    return [line for line in lines if line]

  def _process_command_output(self, output: str, command: str) -> str:
    """
    Process and parse command output.

    Args:
        output (str): Raw output from the command
        command (str): The command that was executed

    Returns:
        str: Processed output
    """
    clean_lines = self._clean_output(output)

    response_lines = []
    capture_started = False

    for line in clean_lines:
      if not capture_started and command.strip() in line:
        capture_started = True
      elif capture_started and '>' in line:
        break
      elif capture_started and line.strip():
        response_lines.append(line)

    return '\n'.join(response_lines) if response_lines else ""
