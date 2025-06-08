"""
Example usage of the Podman interface.

This script demonstrates how to use the podman_interface.py module to interact with Podman
containers for the Resonite Headless Manager.

To run this example:
    python example_usage.py

Make sure you have:
1. Podman installed and running
2. A container named 'my-resonite-headless' (or modify the container_name variable)
3. Required Python packages installed (podman, logging)
"""

import time
import logging
from podman_interface import (
    is_container_running,
    get_container_status,
    start_container,
    stop_container,
    restart_container,
    execute_command,
    get_container_logs,
    list_containers,
    container_exists,
    cleanup
)

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants for messages
MSG_CONTAINER_START_FAILED = "✗ Failed to start container"
MSG_CONTAINER_NOT_EXISTS = "✗ Container '{}' does not exist"
MSG_CONTAINER_STARTED = "✓ Container started successfully"
MSG_CONTAINER_STOPPED = "✓ Container stopped successfully"
MSG_CONTAINER_RESTARTED = "✓ Container restarted successfully"


def example_basic_container_operations():
  """Demonstrate basic container operations."""
  print("\n=== Basic Container Operations ===")

  container_name = "my-resonite-headless"

  # Check if container exists
  if container_exists(container_name):
    print(f"✓ Container '{container_name}' exists")

    # Get container status
    status = get_container_status(container_name)
    print(f"Container status: {status}")

    # Check if running
    is_running = is_container_running(container_name)
    print(f"Container running: {is_running}")

    if not is_running:
      # Start the container
      print(f"Starting container '{container_name}'...")
      if start_container(container_name):
        print(MSG_CONTAINER_STARTED)
      else:
        print(MSG_CONTAINER_START_FAILED)
        return

    # Wait a moment for container to be fully ready
    time.sleep(10)

    # Restart the container
    print(f"Restarting container '{container_name}'...")
    if restart_container(container_name):
      print(MSG_CONTAINER_RESTARTED)
    else:
      print("✗ Failed to restart container")

    # wait for a moment after restart
    time.sleep(10)

    # Stop the container
    print(f"Stopping container '{container_name}'...")
    if stop_container(container_name):
      print(MSG_CONTAINER_STOPPED)
    else:
      print("✗ Failed to stop container")
  else:
    print(f"✗ Container '{container_name}' does not exist")


def example_log_monitoring():
  """Demonstrate getting container logs."""
  print("\n=== Log Monitoring Examples ===")

  container_name = "my-resonite-headless"

  if not container_exists(container_name):
    print(f"✗ Container '{container_name}' does not exist")
    return

  # Get recent logs
  print("--- Getting last 20 lines of logs ---")
  logs = get_container_logs(container_name, tail=20)
  print("Recent logs:")
  print(logs)

  # Get more extensive logs
  print("\n--- Getting last 50 lines of logs ---")
  logs = get_container_logs(container_name, tail=50)
  print("Extended logs:")
  print(logs)


def example_container_listing():
  """Demonstrate listing all containers."""
  print("\n=== Container Listing Examples ===")

  containers = list_containers()

  if containers:
    print(f"Found {len(containers)} containers:")
    for container in containers:
      print(f"  - Name: {container['name']}")
      print(f"    ID: {container['id'][:12]}...")
      print(f"    Status: {container['status']}")
      print(f"    Image: {container['image']}")
      print()
  else:
    print("No containers found")


def example_health_check():
  """Demonstrate a simple health check routine."""
  print("\n=== Health Check Example ===")

  container_name = "my-resonite-headless"

  if not container_exists(container_name):
    print(f"✗ Container '{container_name}' does not exist")
    return

  # Check if container is running
  if is_container_running(container_name):
    print(f"✓ Container '{container_name}' is running")

    # Execute a simple health check command
    health_result = execute_command(container_name, "echo 'health check'", timeout=5)
    if "health check" in health_result:
      print("✓ Container is responsive")
    else:
      print("✗ Container may not be responsive")

    # Get current status
    status = get_container_status(container_name)
    print(f"Current status: {status}")

  else:
    print(f"✗ Container '{container_name}' is not running")

    # Try to start it
    print("Attempting to start container...")
    if start_container(container_name):
      print(MSG_CONTAINER_STARTED)
    else:
      print(MSG_CONTAINER_START_FAILED)


def example_resonite_specific_commands():
  """Demonstrate Resonite-specific command examples."""
  print("\n=== Resonite-Specific Command Examples ===")

  container_name = "my-resonite-headless"

  if not container_exists(container_name):
    print(f"✗ Container '{container_name}' does not exist")
    return

  if not is_container_running(container_name):
    print("Container not running, starting it...")
    if not start_container(container_name):
      print(MSG_CONTAINER_START_FAILED)
      return
    time.sleep(5)  # Wait for Resonite to initialize

  # Example Resonite headless commands
  resonite_commands = [
      "status",  # Check Resonite status
      "sessions",  # List active sessions
      "users",  # List connected users
      "help",  # Show available commands
  ]

  for command in resonite_commands:
    print(f"\n--- Resonite Command: {command} ---")
    result = execute_command(container_name, command, timeout=10)
    print(f"Response: {result}")


def main():
  """Run all examples."""
  print("Podman Interface Example Usage")
  print("=" * 50)

  try:
    # Run all example functions
    example_container_listing()
    example_basic_container_operations()
    example_log_monitoring()
    example_health_check()
    example_resonite_specific_commands()

  except KeyboardInterrupt:
    print("\n\nExample interrupted by user")
  except (OSError, IOError) as e:
    logger.error("I/O error during example execution: %s", e)
  except ImportError as e:
    logger.error("Import error - missing dependencies: %s", e)
  except Exception as e:  # pylint: disable=broad-exception-caught
    logger.error("Unexpected error during example execution: %s", e)
  finally:
    # Clean up the client connection
    cleanup()
    print("\nExample completed. Podman client cleaned up.")


if __name__ == "__main__":
  main()
