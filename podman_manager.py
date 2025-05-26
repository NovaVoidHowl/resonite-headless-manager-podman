import time
import re
from collections import deque
from threading import Lock
import logging
import threading
import podman
import io

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
    """
    Send a command to the container's console using the attach method
    as recommended in the Resonite Headless Server documentation
    """
    logger.info("Sending command to container: %s", command)

    try:
      # Get container instance
      container = self.client.containers.get(self.container_name)
      logger.info("Container verified: %s", container.name)

      # Try using the attach method as recommended in Resonite docs
      try:
        logger.info("Attempting to attach to container console")

        # Try to attach to the console
        # Note: The API docs indicate this might raise NotImplementedError
        output = container.attach(
          stdout=True,
          stderr=True,
          stream=False,
          logs=False  # Don't include previous logs
        )

        # If we got here, attach is implemented
        logger.info("Successfully attached to container console")

        # Send the command and capture output
        # This is where we would write to stdin and read from stdout
        # But since the API might not support bidirectional communication,
        # we'll need a different approach if we get here

        # For now, fall back to our tty=True approach if attach works but
        # doesn't allow us to send commands
        logger.info("Attach worked but bidirectional communication not implemented")
        logger.info("Falling back to tty=True approach")

      except NotImplementedError:
        logger.info("Container attach method not implemented, falling back to tty=True approach")
      except Exception as attach_error:
        logger.warning("Error attaching to container: %s", str(attach_error))
        logger.info("Falling back to tty=True approach")

      # Fall back to our tty=True approach
      # Create a command to send to the container's console
      stdin_cmd = ["bash", "-c", f"echo '{command}\\n' > /dev/tty"]
      logger.info("Using exec_run with tty=True and command: %s", stdin_cmd)

      # Execute with tty=True to allocate a pseudo-TTY
      result = container.exec_run(
        cmd=stdin_cmd,
        stdout=True,
        stderr=True,
        tty=True  # This is key for proper terminal interaction
      )

      # Check if the command was sent successfully
      if isinstance(result, tuple) and len(result) >= 2:
        exit_code, output = result
        logger.info("exec_run returned exit_code: %s", exit_code)

        if exit_code != 0:
          logger.error("Error sending command to container: %r",
                       output.decode('utf-8').strip() if isinstance(output, bytes) else output)
          return f"Error sending command: {output.decode('utf-8').strip() if isinstance(output, bytes) else output}"

      # Wait for the command to be processed
      time.sleep(1.5)

      # Now get the logs to capture the output
      try:
        # Get the recent logs
        logs = container.logs(
          stdout=True,
          stderr=True,
          tail=100,  # Get enough lines to capture the full response
          timestamps=False
        )

        if isinstance(logs, bytes):
          logs_text = logs.decode('utf-8')
        else:
          logs_text = str(logs)

        # Process the logs to extract the command response
        clean_lines = self.clean_output(logs_text)
        logger.debug("Raw log lines: %r", clean_lines)

        # Look for the most recent occurrence of our command
        output_lines = []
        command_index = -1

        # Find the last occurrence of our command
        for i in range(len(clean_lines) - 1, -1, -1):
          if clean_lines[i].strip() == command.strip():
            command_index = i
            break

        if command_index != -1 and command_index < len(clean_lines) - 1:
          # Start collecting lines after the command
          start_collect = command_index + 1
          end_collect = len(clean_lines)

          # Find where the output ends (next prompt or empty line)
          for i in range(start_collect, len(clean_lines)):
            if '>' in clean_lines[i] or clean_lines[i].strip() == '':
              end_collect = i
              break

          # Collect the output lines
          output_lines = clean_lines[start_collect:end_collect]

        # If we still don't have output, try a different approach
        if not output_lines:
          # Try to find output based on proximity to the command
          for i in range(len(clean_lines)):
            if clean_lines[i].strip() and command.strip().lower() in clean_lines[i].strip().lower():
              # Found something that might be our command, check what follows
              j = i + 1
              while j < len(clean_lines) and not ('>' in clean_lines[j] or clean_lines[j].strip() == ''):
                output_lines.append(clean_lines[j])
                j += 1
              if output_lines:  # If we found some output, stop looking
                break

        # Log status of output parsing
        if output_lines:
          logger.info("Parsed %d output lines for command '%s'", len(output_lines), command)
        else:
          logger.warning("No output lines found for command '%s'", command)

        output = '\n'.join(output_lines)
        return output

      except Exception as log_error:
        logger.error("Error retrieving command output: %s", str(log_error))
        return "Command sent, but could not retrieve output"

    except Exception as e:
      error_msg = str(e).strip() or "Unknown error"
      logger.error("Error sending command to container: %s", error_msg)
      return f"Error: {error_msg}"

  # Let's also try implementing a direct attach-based approach as an alternative method
  def send_command_attach(self, command, timeout=5):
    """
    Alternative method: Try to send a command using direct podman CLI attach
    This is a backup method if the API-based approach doesn't work
    """
    # Note: This method is not currently used, but kept for reference
    # and possible future implementation
    pass

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
