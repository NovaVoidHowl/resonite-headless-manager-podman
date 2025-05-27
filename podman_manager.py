"""
Podman container management module for the Resonite Headless Manager.

This module provides functionality to:
- Control and monitor Podman containers
- Execute commands within containers
- Stream and process container logs
- Handle container lifecycle (start/stop/restart)
- Monitor container health and status
"""

import logging
import os
import re
import subprocess
import tempfile
import threading
import time
from collections import deque
from threading import Lock
from typing import Any, Dict, List, Optional

import podman
from podman import errors as podman_errors
from podman.domain.containers import Container
import urllib3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
ERROR_CLIENT_NOT_INITIALIZED = "Podman client not initialized"
ERROR_CONTAINER_NOT_RUNNING = "Container is not running"


class PodmanManager:
  """
  Manages Podman container operations and monitoring.

  This class provides a high-level interface for:
  - Container lifecycle management (start/stop/restart)
  - Command execution within containers
  - Log streaming and monitoring
  - Container status checking
  - Output buffering and processing
  """

  def __init__(self, container_name: str):
    """
    Initialize the PodmanManager instance.

    Args:
        container_name (str): The name of the container to manage
    """
    self.container_name = container_name
    self.output_buffer: deque = deque(maxlen=25)
    self.buffer_lock: Lock = Lock()
    self.ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]|\x1B[()][AB012]')
    self._monitor_running: bool = False
    self.client: Optional[podman.PodmanClient] = None
    # Create a custom connection pool with higher max size
    self.pool_manager = urllib3.PoolManager(maxsize=25)
    self._init_client()

  def _init_client(self) -> None:
    """
    Initialize the podman client.
    """
    connection_error = None
    connection_methods = [
      {"uri": "http+unix:///run/podman/podman.sock", "desc": "Unix socket"},
      {"uri": "http+unix:///run/user/0/podman/podman.sock", "desc": "User Unix socket"},
      {"uri": "tcp://localhost:8888", "desc": "TCP localhost:8888"},
    ]

    for method in connection_methods:
      try:
        logger.info("Trying to connect using %s", method['desc'])
        client = podman.PodmanClient(
          base_url=method["uri"],
          pool_manager=self.pool_manager
        )
        client.ping()
        container = client.containers.get(self.container_name)
        logger.info("Container found: %s (ID: %s)", container.name, container.id)
        self.client = client
        return
      except (ConnectionError, RuntimeError) as e:
        connection_error = e
        logger.warning("Connection failed with %s: %s", method['desc'], str(e))

    logger.critical("All connection attempts failed. Last error: %s", str(connection_error))
    self.client = None

  def clean_output(self, text: str) -> List[str]:
    """
    Clean and format output text by removing ANSI sequences and handling line breaks.

    Args:
        text (str): The text to clean

    Returns:
        List[str]: List of cleaned lines
    """
    clean_text = self.ansi_escape.sub('', text)
    lines = [line.strip() for line in clean_text.replace('\r\n', '\n').split('\n')]
    return [line for line in lines if line]

  def add_to_buffer(self, text: str) -> None:
    """
    Add processed text to the output buffer.

    Args:
        text (str): The text to be added to the buffer after cleaning
    """
    with self.buffer_lock:
      clean_lines = self.clean_output(text)
      for line in clean_lines:
        self.output_buffer.append(line)

  def get_recent_lines(self, count: int = 50) -> List[str]:
    """
    Retrieve the most recent lines from the output buffer.

    Args:
        count (int, optional): Number of recent lines to retrieve. Defaults to 50.

    Returns:
        List[str]: List of the most recent output lines
    """
    with self.buffer_lock:
      return list(self.output_buffer)[-count:]

  def is_container_running(self) -> bool:
    """
    Check if the container is currently running.

    Returns:
        bool: True if the container is running, False otherwise
    """
    try:
      if not self.client:
        return False
      container = self.client.containers.get(self.container_name)
      return container.status == 'running'
    except (ConnectionError, RuntimeError) as e:
      logger.error("Error checking container status: %s", str(e))
      return False

  def _execute_command_process(self, command: str, output_path: str) -> subprocess.Popen:
    """
    Execute the podman attach process and send command.

    Args:
        command (str): The command to execute
        output_path (str): Path to the output file

    Returns:
        subprocess.Popen: The process object
    """
    attach_cmd = [
      "script", "-q", output_path, "-c",
      f"podman attach --detach-keys='ctrl-d' {self.container_name}"
    ]

    logger.info("Starting podman attach process with command: %s", ' '.join(attach_cmd))
    process = subprocess.Popen(
      attach_cmd,
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True
    )

    time.sleep(1)
    if process.stdin:
      process.stdin.write(f"{command}\n")
      process.stdin.flush()
      time.sleep(2)
      process.stdin.write("\x04")
      process.stdin.flush()

    return process

  def _process_users_command(self, clean_lines: List[str]) -> List[str]:
    """
    Process output specifically for the users command.

    Args:
        clean_lines (List[str]): Cleaned lines of output

    Returns:
        List[str]: Processed lines specific to the users command
    """
    response_lines = []
    start_idx = 1 if len(clean_lines) > 0 and 'Username' in clean_lines[0] else 0
    for line in clean_lines[start_idx:]:
      if not line or '>' in line:
        break
      if line.strip():  # Only add non-empty lines
        response_lines.append(line)
    return response_lines

  def _process_generic_command(self, clean_lines: List[str], command: str) -> List[str]:
    """
    Process output for general commands.

    Args:
        clean_lines (List[str]): Cleaned lines of output
        command (str): The command that was executed

    Returns:
        List[str]: Processed lines for the command
    """
    response_lines = []
    capture_started = False
    for line in clean_lines:
      if not capture_started and command.strip() in line:
        capture_started = True
      elif capture_started and '>' in line:
        break
      elif capture_started:
        response_lines.append(line)
    return response_lines

  def _process_command_output(self, output: str, command: str) -> str:
    """
    Process and parse command output.

    Args:
        output (str): Raw output from the command
        command (str): The command that was executed

    Returns:
        str: Processed output
    """
    clean_lines = self.clean_output(output)
    logger.info("Captured %d lines of output", len(clean_lines))

    response_lines = []
    if command.strip() == 'users':
      response_lines = self._process_users_command(clean_lines)
    else:
      response_lines = self._process_generic_command(clean_lines, command)

    if response_lines:
      logger.info("Found %d response lines", len(response_lines))
      return '\n'.join(response_lines)

    logger.warning("No response lines found")
    return ""

  def send_command(self, command: str, timeout: int = 10) -> str:
    """
    Send a command to the container's console.

    Args:
        command (str): The command to send
        timeout (int, optional): Timeout for the command execution. Defaults to 10.

    Returns:
        str: The output of the command
    """
    logger.info("Sending command to container: %s", command)

    try:
      if not self.is_container_running():
        logger.error("Container is not running, cannot send command: %s", command)
        return f"Error: {ERROR_CONTAINER_NOT_RUNNING}"

      if not self.client:
        logger.error(ERROR_CLIENT_NOT_INITIALIZED)
        return f"Error: {ERROR_CLIENT_NOT_INITIALIZED}"

      container = self.client.containers.get(self.container_name)
      logger.info("Container verified: %s", container.name)

      with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as cmd_file:
        cmd_path = cmd_file.name
        cmd_file.write(command)

      output_path = os.path.join(os.path.dirname(cmd_path), f"output_{os.getpid()}.txt")

      try:
        process = self._execute_command_process(command, output_path)

        try:
          process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
          logger.warning("Process timed out after %d seconds, sending SIGTERM", timeout)
          process.terminate()
          try:
            process.wait(timeout=2)
          except subprocess.TimeoutExpired:
            logger.warning("Termination timed out, sending SIGKILL")
            process.kill()

        with open(output_path, 'r', encoding='utf-8') as output_file:
          output = output_file.read()
          return self._process_command_output(output, command)

      finally:
        for path in [cmd_path, output_path]:
          try:
            if os.path.exists(path):
              os.unlink(path)
          except OSError as e:
            logger.warning("Error cleaning up temporary file %s: %s", path, str(e))

    except (ConnectionError, RuntimeError) as e:
      error_msg = str(e).strip() or "Unknown error"
      logger.error("Error sending command to container: %s", error_msg)
      return f"Error: {error_msg}"

  def _process_logs(self, container: Container, callback) -> None:
    """
    Process container logs.

    Args:
        container (Container): The container object
        callback (function): Callback function to handle log lines
    """
    try:
      for log_line in container.logs(
        stdout=True,
        stderr=True,
        follow=True,
        stream=True,
        since=0
      ):
        if not self._monitor_running or not self.is_container_running():
          if not self.is_container_running():
            callback("Container stopped\n")
          break

        decoded_line = log_line.decode('utf-8').strip() if isinstance(log_line, bytes) else str(log_line).strip()
        if decoded_line:
          self.add_to_buffer(decoded_line)
          callback(decoded_line + '\n')
    except (ConnectionError, RuntimeError) as e:
      logger.error("Error in log monitoring: %s", str(e))

  def monitor_output(self, callback) -> None:
    """
    Monitor container output continuously.

    Args:
        callback (function): Callback function to handle log lines
    """
    self._monitor_running = True
    logger.info("Starting container log monitoring")

    try:
      if not self.is_container_running():
        logger.error("Cannot monitor output: %s", ERROR_CONTAINER_NOT_RUNNING)
        callback(f"Error: {ERROR_CONTAINER_NOT_RUNNING}\n")
        return

      if not self.client:
        logger.error(ERROR_CLIENT_NOT_INITIALIZED)
        return

      container = self.client.containers.get(self.container_name)
      log_thread = threading.Thread(
        target=self._process_logs,
        args=(container, callback),
        daemon=True
      )
      log_thread.start()

      while self._monitor_running and log_thread.is_alive():
        time.sleep(0.5)
        if not self.is_container_running():
          self._monitor_running = False

      logger.info("Log monitoring stopped")

    except (ConnectionError, RuntimeError) as e:
      logger.error("Failed to start log monitoring: %s", str(e))
      self._monitor_running = False

  def get_container_status(self) -> Dict[str, Any]:
    """
    Get container status information.

    Returns:
        Dict[str, Any]: Dictionary containing container status information
    """
    try:
      if not self.client:
        return {'error': ERROR_CLIENT_NOT_INITIALIZED, 'status': 'unknown'}

      container = self.client.containers.get(self.container_name)
      inspect_data = container.inspect()

      return {
        'status': container.status,
        'name': container.name,
        'id': container.id,
        'image': inspect_data.get('ImageName', container.image)
      }
    except (ConnectionError, RuntimeError, podman_errors.ContainerNotFound) as e:
      logger.error("Error getting container status: %s", str(e))
      return {'error': str(e), 'status': 'unknown'}

  def restart_container(self) -> bool:
    """
    Safely restart the Podman container.

    Returns:
        bool: True if the container was successfully restarted, False otherwise
    """
    try:
      if not self.client:
        raise RuntimeError(ERROR_CLIENT_NOT_INITIALIZED)

      container = self.client.containers.get(self.container_name)
      self._monitor_running = False

      logger.info("Restarting container: %s", self.container_name)
      container.restart(timeout=30)

      retries = 0
      max_retries = 10
      while retries < max_retries:
        container.reload()
        if container.status == 'running':
          logger.info("Container successfully restarted")
          return True
        time.sleep(1)
        retries += 1

      logger.warning("Container restart took longer than expected")
      return False

    except (ConnectionError, RuntimeError, podman_errors.ContainerNotFound) as e:
      logger.error("Failed to restart container: %s", str(e))
      raise RuntimeError(f"Failed to restart container: {str(e)}") from e

  def start_container(self) -> None:
    """
    Start the Podman container.
    """
    try:
      if not self.client:
        raise RuntimeError(ERROR_CLIENT_NOT_INITIALIZED)

      container = self.client.containers.get(self.container_name)
      container.start()

      # Wait for container to be running
      retries = 0
      max_retries = 10
      while retries < max_retries:
        container.reload()
        if container.status == 'running':
          logger.info("Container successfully started")
          return
        time.sleep(1)
        retries += 1

      logger.warning("Container start took longer than expected")

    except (ConnectionError, RuntimeError, podman_errors.ContainerNotFound) as e:
      logger.error("Failed to start container: %s", str(e))
      raise RuntimeError(f"Failed to start container: {str(e)}") from e

  def stop_container(self) -> None:
    """
    Stop the Podman container.
    """
    try:
      if not self.client:
        raise RuntimeError(ERROR_CLIENT_NOT_INITIALIZED)

      container = self.client.containers.get(self.container_name)

      # Stop monitoring if it's running
      self._monitor_running = False

      container.stop()

      # Wait for container to be stopped
      retries = 0
      max_retries = 10
      while retries < max_retries:
        container.reload()
        if container.status != 'running':
          logger.info("Container successfully stopped")
          return
        time.sleep(1)
        retries += 1

      logger.warning("Container stop took longer than expected")

    except (ConnectionError, RuntimeError, podman_errors.ContainerNotFound) as e:
      logger.error("Failed to stop container: %s", str(e))
      raise RuntimeError(f"Failed to stop container: {str(e)}") from e

  def get_container_logs(self) -> str:
    """
    Get container logs.

    Returns:
        str: The logs of the container
    """
    try:
      if not self.is_container_running():
        return "Container is not running"

      if not self.client:
        return f"Error: {ERROR_CLIENT_NOT_INITIALIZED}"

      container = self.client.containers.get(self.container_name)
      logs = container.logs()

      # Handle generator object case
      if hasattr(logs, '__next__'):
        return ''.join([line.decode('utf-8') if isinstance(line, bytes) else str(line) for line in logs])

      return logs.decode('utf-8') if isinstance(logs, bytes) else str(logs)
    except (ConnectionError, RuntimeError, podman_errors.ContainerNotFound) as e:
      logger.error("Error getting container logs: %s", str(e))
      return f"Error getting logs: {str(e)}"
