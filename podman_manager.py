import time
import re
from collections import deque
from threading import Lock
import logging
import threading
import podman

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PodmanManager:
  def __init__(self, container_name):
    self.container_name = container_name
    self.output_buffer = deque(maxlen=25)  # Rolling buffer of last 25 lines
    self.buffer_lock = Lock()  # Thread-safe access to buffer
    # Regex pattern for ANSI escape sequences
    self.ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]|\x1B[()][AB012]')
    self._monitor_running = False
    self.client = None

    # Initialize podman client
    self._init_client()

  def _init_client(self):
    """Initialize the podman client"""
    connection_error = None

    # URI schemes according to Podman Python API docs
    connection_methods = [
      {"uri": "http+unix:///run/podman/podman.sock", "desc": "Unix socket"},
      {"uri": "http+unix:///run/user/0/podman/podman.sock", "desc": "User Unix socket"},
      {"uri": "tcp://localhost:8888", "desc": "TCP localhost:8888"},
    ]

    # Try each connection method
    for method in connection_methods:
      try:
        logger.info("Trying to connect using %s", method['desc'])
        logger.info("Creating PodmanClient with base_url: %s", method['uri'])

        self.client = podman.PodmanClient(base_url=method["uri"])

        # Test connection with ping and get container
        logger.info("Testing connection to %s", method['uri'])
        self.client.ping()
        logger.info("Ping successful, trying to get container: %s", self.container_name)

        # Check if container exists and is accessible
        container = self.client.containers.get(self.container_name)
        logger.info("Container found: %s (ID: %s)", container.name, container.id)
        logger.info("Container status: %s", container.status)

        # If we got here, connection is successful
        logger.info("Successfully connected to container '%s' using %s", self.container_name, method['desc'])
        return
      except Exception as e:
        connection_error = e
        logger.warning("Connection failed with %s: %s", method['desc'], str(e))

    # If we get here, all connection attempts failed
    logger.critical("All connection attempts failed. Last error: %s", str(connection_error))

    # Set a default client so the app doesn't crash completely
    self.client = podman.PodmanClient(base_url="http+unix:///run/podman/podman.sock")

  def clean_output(self, text):
    """Clean and format output text by removing ANSI sequences and handling line breaks"""
    # Remove all ANSI escape sequences
    clean_text = self.ansi_escape.sub('', text)

    # Split on both \r\n and \n, and filter out empty lines
    lines = [line.strip() for line in clean_text.replace('\r\n', '\n').split('\n')]
    return [line for line in lines if line]  # Return only non-empty lines

  def add_to_buffer(self, text):
    with self.buffer_lock:
      clean_lines = self.clean_output(text)
      for line in clean_lines:
        self.output_buffer.append(line)

  def get_recent_lines(self, count=50):
    with self.buffer_lock:
      return list(self.output_buffer)[-count:]

  def send_command(self, command, timeout=5):
    """Send a command to the container and return the output"""
    logger.info("Sending command to container: %s", command)

    try:
      # Get container instance
      container = self.client.containers.get(self.container_name)
      logger.info("Container verified: %s", container.name)

      # Use exec_run to execute the command inside the container
      logger.info("Using exec_run to execute command: %s", command)

      # Format command properly - either as string or list depending on what it contains
      cmd_to_run = ['bash', '-c', command]

      # Use the API as described in the documentation
      result = container.exec_run(
        cmd=cmd_to_run,
        stdout=True,
        stderr=True,
        tty=True
      )

      # Process the result based on return type
      if isinstance(result, tuple) and len(result) >= 2:
        exit_code, output = result
        logger.info("exec_run returned exit_code: %s", exit_code)

        # Decode output if it's bytes
        if isinstance(output, bytes):
          decoded_output = output.decode('utf-8').strip()
        else:
          decoded_output = str(output).strip()

        return decoded_output
      else:
        # Handle case where the result is not a tuple
        logger.warning("exec_run returned unexpected format: %s", str(result))

        # Try to extract output from the result
        if hasattr(result, 'output'):
          output = result.output
          if isinstance(output, bytes):
            return output.decode('utf-8').strip()
          return str(output).strip()

        # Last resort - convert the whole result to string
        return str(result).strip()

    except Exception as e:
      error_msg = str(e).strip() or "Unknown error"
      logger.error("Error sending command to container: %s", error_msg)
      return f"Error: {error_msg}"

  def monitor_output(self, callback):
    """Monitor container output continuously using the Podman Python API logs method"""
    self._monitor_running = True
    logger.info("Starting container log monitoring")

    try:
      container = self.client.containers.get(self.container_name)

      # Define a function to handle log processing in a separate thread
      def process_logs():
        try:
          # Use the logs method with follow=True to stream logs continuously
          for log_line in container.logs(
            stdout=True,
            stderr=True,
            follow=True,
            stream=True,
            since=0  # Get all logs from the start
          ):
            if not self._monitor_running:
              break

            if isinstance(log_line, bytes):
              decoded_line = log_line.decode('utf-8').strip()
            else:
              decoded_line = str(log_line).strip()

            if decoded_line:
              self.add_to_buffer(decoded_line)
              callback(decoded_line + '\n')
        except Exception as log_error:
          logger.error("Error in log monitoring: %s", str(log_error))

      # Start log processing in a separate thread
      log_thread = threading.Thread(target=process_logs, daemon=True)
      log_thread.start()

      # Wait for the monitoring to be stopped
      while self._monitor_running and log_thread.is_alive():
        time.sleep(0.5)

      logger.info("Log monitoring stopped")

    except Exception as e:
      logger.error("Failed to start log monitoring: %s", str(e))
      self._monitor_running = False

  def get_container_status(self):
    """Get container status information"""
    try:
      container = self.client.containers.get(self.container_name)

      # Get detailed inspection data
      inspect_data = container.inspect()

      return {
        'status': container.status,
        'name': container.name,
        'id': container.id,
        'image': inspect_data.get('ImageName', container.image)
      }
    except Exception as e:
      logger.error("Error getting container status: %s", str(e))
      return {'error': str(e), 'status': 'unknown'}

  def restart_container(self):
    """Safely restart the Podman container"""
    try:
      container = self.client.containers.get(self.container_name)

      # Stop monitoring if it's running
      self._monitor_running = False

      # Use the container's restart method with timeout
      logger.info("Restarting container: %s", self.container_name)
      container.restart(timeout=30)

      # Wait for container to be running again
      retries = 0
      max_retries = 10
      while retries < max_retries:
        container.reload()
        if container.status == 'running':
          logger.info("Container successfully restarted")
          break
        time.sleep(1)
        retries += 1

      if retries >= max_retries:
        logger.warning("Container restart took longer than expected")

      return True

    except Exception as e:
      logger.error("Failed to restart container: %s", str(e))
      raise Exception(f"Failed to restart container: {str(e)}")
