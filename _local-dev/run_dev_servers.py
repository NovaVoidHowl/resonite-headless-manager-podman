#!/usr/bin/env python3
"""
Development server launcher for Resonite Headless Manager.

This script runs both the API test server and the web UI server simultaneously
with separate console outputs for easy local development and testing.

Features:
- Runs API test server on port 8000 (with stub data)
- Runs web UI server on port 8080
- Shows separate logs for each server in split console view
- Graceful shutdown when Ctrl+C is pressed
- Cross-platform compatible

Usage:
    python run_dev_servers.py

The servers will be available at:
- API Server: http://localhost:8000
- Web UI: http://localhost:8080
"""

import os
import sys
import time
import signal
import threading
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional


class ColoredOutput:
  """Handle colored console output for different servers."""

  # ANSI color codes
  COLORS = {
      'reset': '\033[0m',
      'bold': '\033[1m',
      'red': '\033[91m',
      'green': '\033[92m',
      'yellow': '\033[93m',
      'blue': '\033[94m',
      'magenta': '\033[95m',
      'cyan': '\033[96m',
      'white': '\033[97m',
  }

  @classmethod
  def colorize(cls, text: str, color: str) -> str:
    """Colorize text with ANSI codes."""
    if os.name == 'nt':  # Windows may not support colors in all terminals
      return text
    return f"{cls.COLORS.get(color, '')}{text}{cls.COLORS['reset']}"


class ServerRunner:
  """Manages running multiple servers with separate logging."""

  def __init__(self):
    self.processes = []
    self.running = True
    self.lock = threading.Lock()

  def setup_signal_handlers(self):
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(_signum, _frame):
      print(f"\n{ColoredOutput.colorize('🛑 Shutdown signal received...', 'yellow')}")
      self.stop_all_servers()
      sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
      signal.signal(signal.SIGTERM, signal_handler)

  def log_with_prefix(self, process_name: str, line: str, color: str = 'white'):
    """Log a line with server prefix and timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = f"[{timestamp}] [{process_name}]"
    colored_prefix = ColoredOutput.colorize(prefix, color)

    with self.lock:
      print(f"{colored_prefix} {line.strip()}")

  def run_server_with_logging(self, command: list, process_name: str, color: str, cwd: Optional[str] = None):
    """Run a server process and handle its output logging."""
    try:
      # Set environment to use UTF-8 encoding for Windows
      env = os.environ.copy()
      env['PYTHONIOENCODING'] = 'utf-8'

      # Start the process
      process = subprocess.Popen(
          command,
          stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT,
          universal_newlines=True,
          bufsize=1,
          cwd=cwd,
          env=env,
          encoding='utf-8',
          errors='replace'
      )

      self.processes.append(process)
      self.log_with_prefix(process_name, f"Starting server: {' '.join(command)}", color)

      # Read output line by line
      while self.running and process.poll() is None:
        assert process.stdout is not None  # stdout is guaranteed to be a pipe due to stdout=subprocess.PIPE
        line = process.stdout.readline()
        if line:
          self.log_with_prefix(process_name, line, color)

      # Handle process termination
      if process.poll() is not None:
        return_code = process.returncode
        if return_code == 0:
          self.log_with_prefix(process_name, "Server stopped normally", color)
        else:
          self.log_with_prefix(process_name, f"Server stopped with exit code: {return_code}", 'red')

    except (subprocess.SubprocessError, OSError) as e:
      self.log_with_prefix(process_name, f"Error running server: {e}", 'red')

  def start_api_server(self):
    """Start the API test server."""
    api_path = Path(__file__).parent / ".." / "api" / "local-test"
    command = [sys.executable, "test_server.py"]

    thread = threading.Thread(
        target=self.run_server_with_logging,
        args=(command, "API-SERVER", "cyan", str(api_path)),
        daemon=True
    )
    thread.start()
    return thread

  def start_web_server(self):
    """Start the web UI server."""
    web_path = Path(__file__).parent / ".."
    command = [sys.executable, "webserver.py"]

    thread = threading.Thread(
        target=self.run_server_with_logging,
        args=(command, "WEB-SERVER", "green", str(web_path)),
        daemon=True
    )
    thread.start()
    return thread

  def stop_all_servers(self):
    """Stop all running server processes."""
    self.running = False

    for process in self.processes:
      try:
        if process.poll() is None:  # Process is still running          process.terminate()
          # Give it a moment to terminate gracefully
          try:
            process.wait(timeout=5)
          except subprocess.TimeoutExpired:
            process.kill()
      except (subprocess.SubprocessError, OSError, AttributeError) as e:
        print(f"Error stopping process: {e}")

  def print_startup_banner(self):
    """Print the startup banner with server information."""
    banner = f"""
{ColoredOutput.colorize('=' * 80, 'bold')}
{ColoredOutput.colorize('🚀 Resonite Headless Manager - Development Servers', 'bold')}
{ColoredOutput.colorize('=' * 80, 'bold')}

Starting development environment with:
  {ColoredOutput.colorize('🔧 API Test Server', 'cyan')}   → http://localhost:8000
  {ColoredOutput.colorize('🌐 Web UI Server', 'green')}    → http://localhost:8080

{ColoredOutput.colorize('📋 Features:', 'yellow')}
  • API server uses stub data source (no real containers needed)
  • All REST and WebSocket endpoints available
  • Web UI connects to API server for live testing
  • Separate colored logs for each server

{ColoredOutput.colorize('⚡ Quick Start:', 'yellow')}
  1. Wait for both servers to start
  2. Open http://localhost:8080 for the web interface
  3. Press Ctrl+C to stop both servers

{ColoredOutput.colorize('=' * 80, 'bold')}
"""
    print(banner)

  def wait_for_startup(self):
    """Wait a moment for servers to start and show status."""
    time.sleep(2)
    print(f"\n{ColoredOutput.colorize('✅ Servers should be starting up...', 'green')}")
    print(f"{ColoredOutput.colorize('🌐 Web UI:', 'green')} http://localhost:8080")
    print(f"{ColoredOutput.colorize('🔧 API Server:', 'cyan')} http://localhost:8000")
    print(f"\n{ColoredOutput.colorize('📝 Server logs:', 'yellow')}")
    print("-" * 50)

  def run(self):
    """Run both servers with monitoring."""
    self.setup_signal_handlers()
    self.print_startup_banner()

    try:
      # Start both servers
      api_thread = self.start_api_server()
      web_thread = self.start_web_server()

      self.wait_for_startup()

      # Keep the main thread alive and monitor
      while self.running:
        time.sleep(1)

        # Check if any critical threads have died
        if not api_thread.is_alive() or not web_thread.is_alive():
          print(f"\n{ColoredOutput.colorize('❌ One or more servers stopped unexpectedly', 'red')}")
          break

    except KeyboardInterrupt:
      print(f"\n{ColoredOutput.colorize('🛑 Received shutdown signal', 'yellow')}")

    finally:
      self.stop_all_servers()
      print(f"{ColoredOutput.colorize('👋 All servers stopped. Goodbye!', 'green')}")


def main():
  """Main function to start the development environment."""
  # Check if we're in the right directory
  if not Path("../webserver.py").exists():
    print(f"{ColoredOutput.colorize('❌ Error: webserver.py not found in current directory', 'red')}")
    print("Please run this script from the '_local_dev' folder of the resonite-headless-manager repository")
    sys.exit(1)

  if not Path("../api/local-test/test_server.py").exists():
    print(f"{ColoredOutput.colorize('❌ Error: API test server not found', 'red')}")
    print("Expected: api/local-test/test_server.py")
    sys.exit(1)

  # Start the development environment
  runner = ServerRunner()
  runner.run()


if __name__ == "__main__":
  main()
