"""
Podman container interface module for the Resonite Headless Manager.

This module provides simple functions to:
- Control Podman containers (start/stop/restart)
- Execute commands within containers
- Get container status and logs
- Check container health
"""

import logging
import os
import re
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional

import podman
from podman import errors as podman_errors

# Configure logging
logger = logging.getLogger(__name__)

# Constants
ERROR_CLIENT_NOT_INITIALIZED = "Podman client not initialized"
ERROR_CONTAINER_NOT_RUNNING = "Container is not running"
ERROR_CONTAINER_NOT_FOUND = "Container not found"

# Global client instance
_client: Optional[podman.PodmanClient] = None


def _get_client() -> Optional[podman.PodmanClient]:
  """
  Get or initialize the Podman client.

  Returns:
      Optional[podman.PodmanClient]: The Podman client or None if connection fails
  """
  global _client
  if _client is not None:
    try:
      _client.ping()
      return _client
    except (podman_errors.APIError, OSError):
      _client = None

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
      _client = client
      logger.info("Successfully connected using %s", method['desc'])
      return _client
    except (podman_errors.APIError, OSError) as e:
      logger.warning("Connection failed with %s: %s", method['desc'], str(e))

  logger.error("All connection attempts failed")
  return None


def _clean_output(text: str) -> List[str]:
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


def _process_command_output(output: str, command: str) -> str:
  """
  Process and parse command output.

  Args:
      output (str): Raw output from the command
      command (str): The command that was executed

  Returns:
      str: Processed output
  """
  clean_lines = _clean_output(output)

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


def is_container_running(container_name: str) -> bool:
  """
  Check if a container is currently running.

  Args:
      container_name (str): Name of the container to check

  Returns:
      bool: True if the container is running, False otherwise
  """
  try:
    client = _get_client()
    if not client:
      return False

    container = client.containers.get(container_name)
    return container.status == 'running'
  except (podman_errors.APIError, podman_errors.ContainerNotFound, OSError) as e:
    logger.error("Error checking container status: %s", str(e))
    return False


def get_container_status(container_name: str) -> Dict[str, Any]:
  """
  Get container status information.

  Args:
      container_name (str): Name of the container

  Returns:
      Dict[str, Any]: Dictionary containing container status information
  """
  try:
    client = _get_client()
    if not client:
      return {'error': ERROR_CLIENT_NOT_INITIALIZED, 'status': 'unknown'}

    container = client.containers.get(container_name)
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


def start_container(container_name: str) -> bool:
  """
  Start a Podman container.

  Args:
      container_name (str): Name of the container to start

  Returns:
      bool: True if successful, False otherwise
  """
  try:
    client = _get_client()
    if not client:
      logger.error(ERROR_CLIENT_NOT_INITIALIZED)
      return False

    container = client.containers.get(container_name)
    container.start()

    # Wait for container to be running
    for _ in range(10):
      container.reload()
      if container.status == 'running':
        logger.info("Container '%s' successfully started", container_name)
        return True
      time.sleep(1)

    logger.warning("Container start took longer than expected")
    return False

  except (podman_errors.APIError, podman_errors.ContainerNotFound, OSError) as e:
    logger.error("Failed to start container '%s': %s", container_name, str(e))
    return False


def stop_container(container_name: str) -> bool:
  """
  Stop a Podman container.

  Args:
      container_name (str): Name of the container to stop

  Returns:
      bool: True if successful, False otherwise
  """
  try:
    client = _get_client()
    if not client:
      logger.error(ERROR_CLIENT_NOT_INITIALIZED)
      return False

    container = client.containers.get(container_name)
    container.stop()

    # Wait for container to be stopped
    for _ in range(10):
      container.reload()
      if container.status != 'running':
        logger.info("Container '%s' successfully stopped", container_name)
        return True
      time.sleep(1)

    logger.warning("Container stop took longer than expected")
    return False

  except (podman_errors.APIError, podman_errors.ContainerNotFound, OSError) as e:
    logger.error("Failed to stop container '%s': %s", container_name, str(e))
    return False


def restart_container(container_name: str) -> bool:
  """
  Restart a Podman container.

  Args:
      container_name (str): Name of the container to restart

  Returns:
      bool: True if successful, False otherwise
  """
  try:
    client = _get_client()
    if not client:
      logger.error(ERROR_CLIENT_NOT_INITIALIZED)
      return False

    container = client.containers.get(container_name)
    logger.info("Restarting container: %s", container_name)
    container.restart(timeout=30)

    # Wait for container to be running
    for _ in range(10):
      container.reload()
      if container.status == 'running':
        logger.info("Container '%s' successfully restarted", container_name)
        return True
      time.sleep(1)

    logger.warning("Container restart took longer than expected")
    return False

  except (podman_errors.APIError, podman_errors.ContainerNotFound, OSError) as e:
    logger.error("Failed to restart container '%s': %s", container_name, str(e))
    return False


def execute_command(container_name: str, command: str, timeout: int = 10) -> str:
  """
  Execute a command in a container via podman attach.

  Args:
    container_name (str): Name of the container
    command (str): Command to execute
    timeout (int): Timeout for command execution in seconds

  Returns:
    str: Output from the command
  """
  logger.info("Executing command in container '%s': %s", container_name, command)

  try:
    if not is_container_running(container_name):
      logger.error("Container '%s' is not running", container_name)
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
        f"podman attach --detach-keys='ctrl-d' {container_name}"
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
          return _process_command_output(output, command)
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
    logger.error("Error executing command in container '%s': %s", container_name, error_msg)
    return f"Error: {error_msg}"


def get_container_logs(container_name: str, tail: int = 100) -> str:
  """
  Get logs from a container.

  Args:
    container_name (str): Name of the container
    tail (int): Number of lines to retrieve from the end

  Returns:
    str: Container logs
  """
  try:
    client = _get_client()
    if not client:
      return f"Error: {ERROR_CLIENT_NOT_INITIALIZED}"

    container = client.containers.get(container_name)
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
    logger.error("Error getting logs for container '%s': %s", container_name, str(e))
    return f"Error getting logs: {str(e)}"


def list_containers() -> List[Dict[str, Any]]:
  """
  List all containers.

  Returns:
    List[Dict[str, Any]]: List of container information
  """
  try:
    client = _get_client()
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


def container_exists(container_name: str) -> bool:
  """
  Check if a container exists.

  Args:
    container_name (str): Name of the container to check

  Returns:
    bool: True if container exists, False otherwise
  """
  try:
    client = _get_client()
    if not client:
      return False

    client.containers.get(container_name)
    return True

  except podman_errors.ContainerNotFound:
    return False
  except (podman_errors.APIError, OSError) as e:
    logger.error("Error checking if container '%s' exists: %s", container_name, str(e))
    return False


def cleanup():
  """Clean up the Podman client connection."""
  global _client
  if _client:
    try:
      _client.close()
    except (podman_errors.APIError, OSError, AttributeError) as e:
      logger.warning("Error closing Podman client: %s", str(e))
    finally:
      _client = None
