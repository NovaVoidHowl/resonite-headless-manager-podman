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
    connection_error = None
    
    # For Linux systems, prioritize Unix socket connection
    if USE_PODMAN_PY:
      # We know we're running on Linux servers only
      connection_methods = [
        {"type": "podman", "uri": "unix:///run/podman/podman.sock", "desc": "Unix socket"},
        {"type": "podman", "uri": "unix:///run/user/0/podman/podman.sock", "desc": "User Unix socket"},
        {"type": "podman", "uri": "tcp://localhost:8080", "desc": "TCP localhost:8080"},
      ]
    else:
      connection_methods = [
        {"type": "docker", "uri": "unix:///run/podman/podman.sock", "desc": "Unix socket with docker-py"},
        {"type": "docker", "uri": "unix:///run/user/0/podman/podman.sock", "desc": "User Unix socket with docker-py"},
        {"type": "docker", "uri": "tcp://localhost:8080", "desc": "TCP localhost:8080 with docker-py"},
      ]
    
    # Try each connection method
    for method in connection_methods:
      try:
        logger.info(f"Trying to connect using {method['desc']}")
        
        if method["type"] == "podman" and USE_PODMAN_PY:
          self.client = podman.PodmanClient(base_url=method["uri"])
        elif method["type"] == "docker" and 'docker' in globals():
          self.client = docker.DockerClient(base_url=method["uri"])
        else:
          continue
          
        # Test connection with ping and get container
        logger.info(f"Testing connection to {method['uri']}")
        self.client.ping()
        logger.info(f"Ping successful, trying to get container: {self.container_name}")
        
        # Check if container exists and is accessible
        container = self.client.containers.get(self.container_name)
        logger.info(f"Container found: {container.name} (ID: {container.id})")
        logger.info(f"Container status: {container.status}")
        
        # Try a basic socket operation to verify socket functionality
        try:
          logger.info("Testing socket operations...")
          test_socket = self._safe_attach_socket(container, params={
            'stdin': True,
            'stdout': True,
            'stderr': True,
            'stream': True,
            'logs': False
          })
          test_socket.close()
          logger.info("Socket test successful")
        except Exception as socket_error:
          logger.warning(f"Socket operation test failed: {str(socket_error)}")
          # Continue anyway since we have container access
        
        # If we got here, connection is successful
        logger.info(f"Successfully connected to container '{self.container_name}' using {method['desc']}")
        return
      except Exception as e:
        connection_error = e
        logger.warning(f"Connection failed with {method['desc']}: {str(e)}")
    
    # If we get here, all connection attempts failed
    logger.critical(f"All connection attempts failed. Last error: {str(connection_error)}")
    
    # Set a default client so the app doesn't crash completely
    if USE_PODMAN_PY:
      self.client = podman.PodmanClient(base_url="unix:///run/podman/podman.sock")
    elif 'docker' in globals():
      self.client = docker.DockerClient(base_url="unix:///run/podman/podman.sock")
    else:
      raise ImportError("Neither podman-py nor docker-py available")

  def _safe_attach_socket(self, container, params):
    """Try multiple methods to attach to container socket with better error handling"""
    error = None
    
    # Method 1: Standard attach_socket method
    try:
      logger.info("Trying standard attach_socket method")
      return container.attach_socket(params=params)
    except Exception as e:
      error = e
      logger.warning(f"Standard attach_socket failed: {str(e)}")
    
    # Method 2: Try with demux=True parameter
    try:
      logger.info("Trying attach_socket with demux=True")
      modified_params = params.copy()
      modified_params['demux'] = True
      return container.attach_socket(params=modified_params)
    except Exception as e:
      error = e
      logger.warning(f"attach_socket with demux=True failed: {str(e)}")
    
    # Method 3: Try with exec instead of attach for some container runtime compatibility
    if params.get('stdin', False):
      try:
        logger.info("Trying exec_create/exec_start as fallback")
        exec_id = container.client.api.exec_create(
          container.id,
          ['sh'],
          stdin=True,
          stdout=True,
          stderr=True,
          tty=True
        )['Id']
        socket = container.client.api.exec_start(
          exec_id,
          detach=False,
          tty=True,
          stream=True,
          socket=True
        )
        logger.info("exec_create/exec_start succeeded")
        return socket
      except Exception as e:
        error = e
        logger.warning(f"exec_create/exec_start failed: {str(e)}")
    
    # If all methods failed, raise the last error
    if error:
      raise error
    else:
      raise Exception("All socket attachment methods failed")

  def _exec_attach(self, container):
    """Create an exec instance for better compatibility with other tools like Cockpit"""
    try:
      logger.info("Creating exec instance for container interaction")
      
      # Create exec instance
      if hasattr(container, 'client') and hasattr(container.client, 'api'):
        exec_id = container.client.api.exec_create(
          container.id,
          ['sh'],  # Use shell for command execution
          stdin=True, 
          stdout=True,
          stderr=True,
          tty=True
        )['Id']
        
        # Start exec instance and get socket
        socket = container.client.api.exec_start(
          exec_id,
          detach=False,
          tty=True,
          stream=True,
          socket=True
        )
        
        # Create a wrapper object that mimics the attach_socket result structure
        class ExecSocket:
          def __init__(self, sock):
            self._sock = sock
            
          def close(self):
            try:
              self._sock.close()
            except:
              pass
        
        return ExecSocket(socket)
      else:
        raise Exception("Container client doesn't support exec API")
    except Exception as e:
      logger.error(f"Failed to create exec instance: {str(e)}")
      raise

  def _direct_podman_exec(self, command):
    """Directly execute a command in the container using podman command line tool
    
    This is a fallback method that bypasses socket connections entirely
    by using the podman CLI directly, which can be more reliable when
    there are socket permission issues or other socket-related problems.
    """
    try:
      import subprocess
      import shlex
      
      logger.info(f"Executing command via direct podman exec: {command}")
      
      # Create the podman exec command
      podman_cmd = f"podman exec -it {self.container_name} bash -c {shlex.quote(command)}"
      logger.info(f"Running podman command: {podman_cmd}")
      
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
        logger.warning(f"Direct podman exec returned non-zero exit code: {process.returncode}")
        logger.warning(f"stderr: {stderr}")
        if stderr:
          return f"Error: {stderr}"
      
      return stdout
    
    except Exception as e:
      logger.error(f"Error in direct podman exec: {str(e)}")
      return f"Error: {str(e)}"

  def _direct_log_monitoring(self, callback):
    """Fallback monitoring mode using direct podman logs command
    
    This is used as a last resort when socket connections fail completely.
    It uses the podman logs command with --follow to monitor container output.
    """
    try:
      import subprocess
      import threading
      
      logger.info(f"Starting direct log monitoring for container: {self.container_name}")
      
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
      except:
        try:
          process.kill()
        except:
          pass
      
      logger.info("Direct log monitoring stopped")
      return True
      
    except Exception as e:
      logger.error(f"Error in direct log monitoring: {str(e)}")
      return False

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
    logger.info(f"Sending command to container: {command}")
    
    try:
      # Get container instance
      container = self.client.containers.get(self.container_name)
      
      # METHOD 1: Try exec attach first (works better with Cockpit)
      try:
        logger.info("Trying exec attach method for command")
        conn_socket = self._exec_attach(container)
        logger.info("Exec attach successful for command")
        
        # Send command
        cmd_bytes = f"{command}\r".encode('utf-8')
        conn_socket._sock.send(cmd_bytes)
        logger.info(f"Command sent via exec attach: {command}")
        
        # Read response with timeout
        output = []
        start_time = time.time()
        no_data_count = 0
        
        while True:
          ready = select.select([conn_socket._sock], [], [], 0.1)
          if ready[0]:
            chunk = conn_socket._sock.recv(4096).decode('utf-8')
            if chunk:
              output.append(chunk)
              no_data_count = 0
              continue
          
          no_data_count += 1
          if no_data_count >= 3 or (time.time() - start_time > timeout):
            break
        
        conn_socket.close()
        result = ''.join(output).strip()
        clean_lines = self.clean_output(result)
        return '\n'.join(clean_lines)
        
      except Exception as exec_error:
        logger.warning(f"Exec attach for command failed: {str(exec_error)}")
        logger.info("Falling back to safe_attach_socket")
        
        # METHOD 2: Try safe socket attach
        try:
          conn_socket = self._safe_attach_socket(container, params={
            'stdin': True,
            'stdout': True,
            'stderr': True,
            'stream': True,
            'logs': False
          })
          logger.info("Socket connection established via fallback")
          
          # Send command
          cmd_bytes = f"{command}\r".encode('utf-8')
          conn_socket._sock.send(cmd_bytes)
          logger.info(f"Command sent via socket attach: {command}")
          
          # Read response with timeout
          output = []
          start_time = time.time()
          no_data_count = 0
          
          while True:
            ready = select.select([conn_socket._sock], [], [], 0.1)
            if ready[0]:
              chunk = conn_socket._sock.recv(4096).decode('utf-8')
              if chunk:
                output.append(chunk)
                no_data_count = 0
                continue
            
            no_data_count += 1
            if no_data_count >= 3 or (time.time() - start_time > timeout):
              break
          
          conn_socket.close()
          result = ''.join(output).strip()
          clean_lines = self.clean_output(result)
          return '\n'.join(clean_lines)
          
        except Exception as socket_error:
          socket_error_msg = str(socket_error).strip() or "Unknown socket error"
          logger.error(f"Socket attach failed: {socket_error_msg}")
          logger.info("Falling back to direct podman exec command")
          
          # METHOD 3: Last resort - direct podman command execution
          return self._direct_podman_exec(command)
    
    except Exception as e:
      error_msg = str(e).strip() or "Unknown error"
      logger.error(f"Error sending command to container: {error_msg}")
      
      # Try direct podman exec as a complete fallback
      try:
        logger.info("Attempting direct podman exec as complete fallback")
        return self._direct_podman_exec(command)
      except Exception as direct_error:
        logger.error(f"Direct podman exec also failed: {str(direct_error)}")
        return f"Error: {error_msg}"

  def monitor_output(self, callback):
    """Monitor container output continuously"""
    self._monitor_running = True
    buffer = ""
    retry_count = 0
    max_retries = 3
    retry_delay = 5  # seconds
    
    while self._monitor_running and retry_count <= max_retries:
      try:
        logger.info(f"Attempting to connect to container: {self.container_name}")
        container = self.client.containers.get(self.container_name)
        
        # Try to use exec first since we're on Linux and this may work better with Cockpit
        try:
          logger.info("Attempting to use exec attach method...")
          output_socket = self._exec_attach(container)
          logger.info("Exec attach method successful")
        except Exception as exec_error:
          logger.warning(f"Exec attach method failed: {str(exec_error)}")
          logger.info("Falling back to standard socket attachment...")
          
          # Fallback to socket attach
          try:
            output_socket = self._safe_attach_socket(container, params={
              'stdin': False,
              'stdout': True,
              'stderr': True,
              'stream': True,
              'logs': False,
              'since': 0,
            })
            logger.info("Fallback socket connection established")
          except Exception as socket_error:
            logger.error(f"Fallback socket connection failed: {str(socket_error)}")
            raise socket_error

        # Send initial carriage returns to get prompt (using safe attach method)
        try:
          cmd_socket = self._safe_attach_socket(container, params={
            'stdin': True,
            'stdout': True,
            'stderr': True,
            'stream': True,
            'logs': False
          })
          cmd_socket._sock.send(b'\r')
          cmd_socket.close()
        except Exception as cmd_error:
          logger.warning(f"Failed to send initial carriage return: {str(cmd_error)}")
          # Continue anyway - this is just to get an initial prompt
        
        # Reset retry count on successful connection
        retry_count = 0
        logger.info("Starting monitoring loop")

        # Main monitoring loop
        while self._monitor_running:
          try:
            ready = select.select([output_socket._sock], [], [], 0.1)
            if ready[0]:
              try:
                chunk = output_socket._sock.recv(2048).decode('utf-8')
                if chunk:
                  # Process the chunk
                  buffer += chunk
                  
                  # Process complete lines
                  while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    if line:
                      clean_lines = self.clean_output(line)
                      for clean_line in clean_lines:
                        self.add_to_buffer(clean_line)
                        callback(clean_line + '\n')
                  
                  # If buffer gets too large, trim it
                  if len(buffer) > 2048:
                    buffer = buffer[-1024:]
              except Exception as recv_error:
                logger.error(f"Error receiving data from socket: {str(recv_error)}")
                break
          except Exception as select_error:
            logger.error(f"Error in select operation: {str(select_error)}")
            break

      except Exception as e:
        retry_count += 1
        error_msg = str(e).strip()
        if error_msg:
          logger.error(f"Error monitoring container (attempt {retry_count}/{max_retries}): {error_msg}")
        else:
          logger.error(f"Error monitoring container (attempt {retry_count}/{max_retries}): Unknown error (empty error message)")
          
        if retry_count <= max_retries:
          logger.info(f"Retrying in {retry_delay} seconds...")
          time.sleep(retry_delay)
        else:
          logger.error("Maximum retry attempts reached. Monitoring stopped.")
          # Last resort - try direct monitoring using podman logs
          logger.info("Trying direct log monitoring as last resort...")
          if self._direct_log_monitoring(callback):
            logger.info("Direct log monitoring successfully started")
            return  # Exit method as monitoring is now handled by _direct_log_monitoring
          else:
            logger.error("All monitoring methods failed. Output monitoring disabled.")
      finally:
        if 'output_socket' in locals():
          try:
            output_socket.close()
            logger.info("Closed output socket connection")
          except Exception as close_error:
            logger.error(f"Error closing output socket: {str(close_error)}")

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
