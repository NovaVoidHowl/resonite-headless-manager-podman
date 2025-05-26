import select
import time
import re
from collections import deque
from threading import Lock
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import podman-py, fall back to docker-py with podman socket
try:
  import podman
  USE_PODMAN_PY = True
  logger.info("Using native podman-py library")
except ImportError:
  import docker
  USE_PODMAN_PY = False
  logger.info("Using docker-py library with podman socket")


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
    """Initialize the podman client based on available libraries"""
    if USE_PODMAN_PY:
      # Use native podman python library
      # Determine socket URI based on OS platform
      if os.name == 'nt':  # Windows
        socket_uri = "tcp://localhost:8080"  # Default for podman machine
      else:  # Linux/macOS
        socket_uri = "unix:///run/podman/podman.sock"

      self.client = podman.PodmanClient(base_url=socket_uri)
    else:
      # Use docker-py with podman socket
      if os.name == 'nt':  # Windows
        socket_url = "tcp://localhost:8080"  # Default for podman machine
      else:  # Linux/macOS
        socket_url = "unix:///run/podman/podman.sock"

      if 'docker' in globals():
        self.client = docker.DockerClient(base_url=socket_url)
      else:
        raise ImportError("docker module is not available. Ensure it is installed and accessible.")

    logger.info(f"Podman client initialized with container name: {self.container_name}")

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

  def send_command(self, command, timeout=1):
    """Send a command to the container and return the output"""
    try:
      container = self.client.containers.get(self.container_name)

      # Get raw connection to container without logs
      conn_socket = container.attach_socket(params={
        'stdin': True,
        'stdout': True,
        'stderr': True,
        'stream': True,
        'logs': False
      })

      # Send the command with a carriage return
      cmd_bytes = f"{command}\r".encode('utf-8')
      conn_socket._sock.send(cmd_bytes)

      # Read the response with timeout
      output = []
      start_time = time.time()
      no_data_count = 0  # Counter for consecutive no-data readings

      while True:
        ready = select.select([conn_socket._sock], [], [], 0.1)
        if ready[0]:
          chunk = conn_socket._sock.recv(4096).decode('utf-8')
          if chunk:
            output.append(chunk)
            no_data_count = 0  # Reset counter when we get data
            continue

        no_data_count += 1
        # Break if we've had no data for 3 consecutive reads or exceeded timeout
        if no_data_count >= 3 or (time.time() - start_time > timeout):
          break

      conn_socket.close()
      result = ''.join(output).strip()
      # Use clean_output instead of direct ANSI escape removal
      clean_lines = self.clean_output(result)
      return '\n'.join(clean_lines)

    except Exception as e:
      logger.error(f"Error sending command to container: {str(e)}")
      return f"Error: {str(e)}"

  def monitor_output(self, callback):
    """Monitor container output continuously"""
    self._monitor_running = True
    buffer = ""
    try:
      container = self.client.containers.get(self.container_name)
      # Completely disable historical logs and only get new output
      output_socket = container.attach_socket(params={
        'stdin': False,
        'stdout': True,
        'stderr': True,
        'stream': True,
        'logs': False,  # Disable historical logs
        'since': 0,     # Ignore any historical logs
      })

      # Send initial carriage returns to get prompt
      cmd_socket = container.attach_socket(params={
        'stdin': True,
        'stdout': True,
        'stderr': True,
        'stream': True,
        'logs': False  # Also disable logs for command socket
      })
      cmd_socket._sock.send(b'\r')
      cmd_socket.close()

      while self._monitor_running:
        ready = select.select([output_socket._sock], [], [], 0.1)
        if ready[0]:
          try:
            chunk = output_socket._sock.recv(2048).decode('utf-8')
            if chunk:
              # Append chunk to buffer
              buffer += chunk

              # Process complete lines
              while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                if line:
                  # Use clean_output for single line
                  clean_lines = self.clean_output(line)
                  for clean_line in clean_lines:
                    self.add_to_buffer(clean_line)
                    callback(clean_line + '\n')

              # If buffer gets too large, clear it
              if len(buffer) > 2048:
                buffer = buffer[-1024:]

          except Exception as e:
            logger.error(f"Error reading from socket: {e}")
            break

    except Exception as e:
      logger.error(f"Error monitoring container: {str(e)}")
    finally:
      self._monitor_running = False
      try:
        output_socket.close()
      except Exception:
        pass

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
      logger.error(f"Error getting container status: {str(e)}")
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
        logger.warning(f"Failed to stop container gracefully: {e}")
        # Try to force kill if graceful stop fails
        container.kill()

      # Wait for container to fully stop
      try:
        container.wait(timeout=35)
      except Exception as e:
        logger.warning(f"Container wait timeout: {e}")

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
      logger.error(f"Failed to restart container: {str(e)}")
      raise Exception(f"Failed to restart container: {str(e)}")
