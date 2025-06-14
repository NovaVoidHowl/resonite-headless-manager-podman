"""
Docker container interface module for the Resonite Headless Manager.

This module provides a complete implementation of the ExternalSystemInterface
for managing Docker containers. It provides functions to:
- Control Docker containers (start/stop/restart)
- Execute commands within containers
- Get container status and logs
- Check container health
"""

import logging
import re
import sys
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import docker
from docker import errors as docker_errors

# Import the base interface
sys.path.append(str(Path(__file__).parent.parent))
from base_interface import ExternalSystemInterface  # noqa: E402 # pylint: disable=wrong-import-position

# Configure logging
logger = logging.getLogger(__name__)

# Constants
ERROR_CLIENT_NOT_INITIALIZED = "Docker client not initialized"
ERROR_CONTAINER_NOT_RUNNING = "Container is not running"
ERROR_CONTAINER_NOT_FOUND = "Container not found"


class DockerInterface(ExternalSystemInterface):
  """
  Docker implementation of the ExternalSystemInterface.

  This class provides container management capabilities using Docker,
  implementing all methods from the base interface.
  """

  def __init__(self):
    """Initialize the Docker interface."""
    self._client: Optional[docker.DockerClient] = None

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
    except (docker_errors.APIError, docker_errors.NotFound, OSError) as e:
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

      # Get image name safely
      image_name = "unknown"
      if container.image and hasattr(container.image, 'tags') and container.image.tags:
        image_name = container.image.tags[0]
      elif container.image and hasattr(container.image, 'id'):
        image_name = str(container.image.id)
      elif hasattr(container, 'attrs') and 'Image' in container.attrs:
        image_name = container.attrs['Image']

      return {
        'status': container.status,
        'name': container.name,
        'id': container.id,
        'image': image_name
      }
    except (docker_errors.APIError, docker_errors.NotFound, OSError) as e:
      logger.error("Error getting container status: %s", str(e))
      return {'error': str(e), 'status': 'unknown'}

  def start_instance(self, instance_name: str) -> bool:
    """
    Start a Docker container.

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

    except (docker_errors.APIError, docker_errors.NotFound, OSError) as e:
      logger.error("Failed to start container '%s': %s", instance_name, str(e))
      return False

  def stop_instance(self, instance_name: str) -> bool:
    """
    Stop a Docker container.

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

    except (docker_errors.APIError, docker_errors.NotFound, OSError) as e:
      logger.error("Failed to stop container '%s': %s", instance_name, str(e))
      return False

  def restart_instance(self, instance_name: str) -> bool:
    """
    Restart a Docker container.

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

    except (docker_errors.APIError, docker_errors.NotFound, OSError) as e:
      logger.error("Failed to restart container '%s': %s", instance_name, str(e))
      return False

  def execute_command(self, instance_name: str, command: str, timeout: int = 10) -> str:
    """
    Execute a command in a container via docker exec with timeout support.

    The timeout is implemented using threading to prevent the command from hanging
    indefinitely. If the command doesn't complete within the specified timeout,
    it will return an error message indicating the timeout.

    Args:
      instance_name (str): Name of the container
      command (str): Command to execute
      timeout (int): Timeout for command execution in seconds

    Returns:
      str: Output from the command, or error message if timeout/failure occurs
    """
    logger.info("Executing command in container '%s': %s", instance_name, command)

    try:
      if not self.is_instance_running(instance_name):
        logger.error("Container '%s' is not running", instance_name)
        return f"Error: {ERROR_CONTAINER_NOT_RUNNING}"

      client = self._get_client()
      if not client:
        return f"Error: {ERROR_CLIENT_NOT_INITIALIZED}"

      container = client.containers.get(instance_name)

      # Execute command using docker exec with timeout handling
      result = self._execute_with_timeout(container, command, timeout)

      if result is None:
        logger.warning("Command timed out after %d seconds", timeout)
        return f"Error: Command timed out after {timeout} seconds"

      # Process the output
      if result.output:
        output = result.output.decode('utf-8') if isinstance(result.output, bytes) else str(result.output)
        return self._process_command_output(output, command)
      else:
        return "No output captured"

    except (OSError, docker_errors.APIError, docker_errors.NotFound) as e:
      error_msg = str(e).strip() or "Unknown error"
      logger.error("Error executing command in container '%s': %s", instance_name, error_msg)
      return f"Error: {error_msg}"

  def _execute_with_timeout(self, container, command: str, timeout: int) -> Optional[Any]:
    """
    Execute a command in a container with timeout support.

    Args:
      container: Docker container object
      command (str): Command to execute
      timeout (int): Timeout in seconds

    Returns:
      Execution result or None if timeout
    """
    result_container: List[Optional[Any]] = [None]
    exception_container: List[Optional[BaseException]] = [None]

    def execute_command():
      try:
        result = container.exec_run(
          command,
          stdout=True,
          stderr=True,
          stdin=False,
          tty=False,
          privileged=False,
          user='',
          environment=None,
          workdir=None,
          detach=False,
          stream=False,
          socket=False,
          demux=False
        )
        result_container[0] = result
      except (docker_errors.APIError, docker_errors.NotFound, OSError) as e:
        exception_container[0] = e

    # Start execution in a thread
    exec_thread = threading.Thread(target=execute_command)
    exec_thread.daemon = True
    exec_thread.start()

    # Wait for completion or timeout
    exec_thread.join(timeout)

    if exec_thread.is_alive():
      # Command is still running after timeout
      logger.warning("Command execution timed out after %d seconds", timeout)
      return None    # Check if there was an exception
    exception = exception_container[0]
    if exception is not None:
      raise exception

    return result_container[0]

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
      logs = container.logs(tail=tail, stdout=True, stderr=True, timestamps=False, follow=False)

      # Handle log output
      if isinstance(logs, bytes):
        return logs.decode('utf-8')
      else:
        return str(logs)

    except (docker_errors.APIError, docker_errors.NotFound, OSError) as e:
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

      container_list = []
      for container in containers:
        # Get image name safely
        image_name = "unknown"
        if container.image and hasattr(container.image, 'tags') and container.image.tags:
          image_name = container.image.tags[0]
        elif container.image and hasattr(container.image, 'id'):
          image_name = str(container.image.id)
        elif hasattr(container, 'attrs') and 'Image' in container.attrs:
          image_name = container.attrs['Image']

        container_list.append({
          'name': container.name,
          'id': container.id,
          'status': container.status,
          'image': image_name
        })

      return container_list

    except (docker_errors.APIError, OSError) as e:
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

    except docker_errors.NotFound:
      return False
    except (docker_errors.APIError, OSError) as e:
      logger.error("Error checking if container '%s' exists: %s", instance_name, str(e))
      return False

  def cleanup(self) -> None:
    """Clean up the Docker client connection."""
    if self._client:
      try:
        self._client.close()
      except (docker_errors.APIError, OSError, AttributeError) as e:
        logger.warning("Error closing Docker client: %s", str(e))
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

  def _get_client(self) -> Optional[docker.DockerClient]:
    """
    Get or initialize the Docker client.

    Returns:
        Optional[docker.DockerClient]: The Docker client or None if connection fails
    """
    if self._client is not None:
      try:
        self._client.ping()
        return self._client
      except (docker_errors.APIError, OSError):
        self._client = None

    connection_methods = [
        {"base_url": "unix://var/run/docker.sock", "desc": "Unix socket"},
        {"base_url": "tcp://localhost:2376", "desc": "TCP localhost:2376 (TLS)"},
        {"base_url": "tcp://localhost:2375", "desc": "TCP localhost:2375 (no TLS)"},
    ]

    for method in connection_methods:
      try:
        logger.info("Trying to connect using %s", method['desc'])
        if 'tcp' in method['base_url'] and '2376' in method['base_url']:
          # Try with TLS
          client = docker.DockerClient(base_url=method["base_url"], tls=True)
        else:
          client = docker.DockerClient(base_url=method["base_url"])

        client.ping()
        self._client = client
        logger.info("Successfully connected using %s", method['desc'])
        return self._client
      except (docker_errors.APIError, OSError) as e:
        logger.warning("Connection failed with %s: %s", method['desc'], str(e))

    # Try default client (uses environment variables)
    try:
      logger.info("Trying default Docker client from environment")
      client = docker.from_env()
      client.ping()
      self._client = client
      logger.info("Successfully connected using environment configuration")
      return self._client
    except (docker_errors.APIError, OSError) as e:
      logger.warning("Default client connection failed: %s", str(e))

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
