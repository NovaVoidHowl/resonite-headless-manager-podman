import time
import re
from collections import deque
from threading import Lock
import logging
import subprocess
import shlex
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

  def _direct_podman_exec(self, command):
    """Directly execute a command in the container using podman command line tool

    This method bypasses socket connections entirely by using the podman CLI directly,
    which is more reliable when there are socket permission issues.
    """
    try:
      logger.info("Executing command via direct podman exec: %s", command)

      # Create the podman exec command
      podman_cmd = f"podman exec -it {self.container_name} bash -c {shlex.quote(command)}"
      logger.info("Running podman command: %s", podman_cmd)

      # Execute the command and capture output
      process = subprocess.Popen(
        podman_cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
      )

      stdout, stderr = process.communicate(timeout=5)

      if process.returncode != 0:
        logger.warning("Direct podman exec returned non-zero exit code: %d", process.returncode)
        logger.warning("stderr: %s", stderr)
        if stderr:
          return f"Error: {stderr}"

      return stdout

    except Exception as e:
      logger.error("Error in direct podman exec: %s", str(e))
      return f"Error: {str(e)}"

  def send_command(self, command, timeout=5):
    """Send a command to the container and return the output"""
    logger.info("Sending command to container: %s", command)

    try:
      # Get container instance to verify it exists
      container = self.client.containers.get(self.container_name)
      logger.info("Container verified: %s", container.name)

      # Try container.exec_run first (preferred method for podman-py)
      try:
        if hasattr(container, 'exec_run'):
          logger.info("Using exec_run to execute command: %s", command)
          result = container.exec_run(command)
          if result.exit_code == 0:
            output = result.output.decode('utf-8').strip()
            return output
          else:
            logger.warning("exec_run returned non-zero exit code: %d", result.exit_code)
      except Exception as exec_error:
        logger.warning("exec_run failed: %s", str(exec_error))

      # Fall back to direct podman exec if exec_run fails
      return self._direct_podman_exec(command)

    except Exception as e:
      error_msg = str(e).strip() or "Unknown error"
      logger.error("Error sending command to container: %s", error_msg)
      return f"Error: {error_msg}"

  def _direct_log_monitoring(self, callback):
    """Monitoring using direct podman logs command

    Uses the podman logs command with --follow to monitor container output.
    """
    try:
      logger.info("Starting direct log monitoring for container: %s", self.container_name)

      def read_stream(stream, cb):
        """Read lines from stream and call callback for each line"""
        for line in iter(stream.readline, b''):
            if not line:
                break
            decoded_line = line.decode('utf-8').strip()
            if decoded_line:
                self.add_to_buffer(decoded_line)
                cb(decoded_line + '\n')

      # Start podman logs process with --follow flag
      process = subprocess.Popen(
        ["podman", "logs", "--follow", self.container_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1  # Line buffered
      )

      # Create threads to monitor stdout and stderr
      stdout_thread = threading.Thread(
        target=read_stream,
        args=(process.stdout, callback),
        daemon=True
      )
      stderr_thread = threading.Thread(
        target=read_stream,
        args=(process.stderr, callback),
        daemon=True
      )

      # Start the threads
      stdout_thread.start()
      stderr_thread.start()

      # Monitor and keep process running while _monitor_running is True
      while self._monitor_running:
        if process.poll() is not None:
          # Process ended unexpectedly
          logger.warning("Direct log monitoring process ended unexpectedly")
          break
        time.sleep(0.5)

      # Clean up process when monitoring stops
      try:
        process.terminate()
        process.wait(timeout=2)
      except subprocess.TimeoutExpired:
        try:
          process.kill()
        except subprocess.SubprocessError:
          pass

      logger.info("Direct log monitoring stopped")
      return True

    except Exception as e:
      logger.error("Error in direct log monitoring: %s", str(e))
      return False

  def monitor_output(self, callback):
    """Monitor container output continuously"""
    self._monitor_running = True

    # Skip socket-based monitoring attempts since they're failing
    # and go directly to direct log monitoring
    logger.info("Using direct log monitoring")
    if self._direct_log_monitoring(callback):
      logger.info("Direct log monitoring successfully started")
    else:
      logger.error("Log monitoring failed")

    self._monitor_running = False
    logger.info("Monitor output stopped")

  def get_container_status(self):
    """Get container status information"""
    try:
      container = self.client.containers.get(self.container_name)
      return {
        'status': container.status,
        'name': container.name,
        'id': container.id
      }
    except Exception as e:
      logger.error("Error getting container status: %s", str(e))
      return {'error': str(e)}

  def restart_container(self):
    """Safely restart the Podman container"""
    try:
      container = self.client.containers.get(self.container_name)

      # Stop monitoring if it's running
      self._monitor_running = False

      # First try to gracefully stop the container
      try:
        container.stop(timeout=30)  # Give it 30 seconds to stop gracefully
      except Exception as e:
        logger.warning("Failed to stop container gracefully: %s", e)
        # Try to force kill if graceful stop fails
        container.kill()

      # Wait for container to fully stop
      try:
        container.wait(timeout=35)
      except Exception as e:
        logger.warning("Container wait timeout: %s", e)

      # Restart the container
      container.restart()

      # Wait for container to be running
      retries = 0
      while retries < 10:
        container.reload()
        if container.status == 'running':
          break
        time.sleep(1)
        retries += 1

      return True

    except Exception as e:
      logger.error("Failed to restart container: %s", str(e))
      raise Exception(f"Failed to restart container: {str(e)}")
