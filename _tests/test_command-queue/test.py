"""
Comprehensive Command Queue System Test

This script provides thorough testing of the command queue system functionality,
including command execution, priority handling, command blocks, error handling,
monitoring, and performance characteristics. Uses mock executors to simulate
various scenarios without requiring external dependencies.
"""

import asyncio
import logging
import random
import time
import sys
from pathlib import Path
from typing import Dict, List

# Add the parent directories to the path to import modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "command_queue"))

try:
  from command_queue import (  # pylint: disable=import-error
      Command,
      CommandBlock,
      CommandQueue,
      Priority
  )
except ImportError as e:
  print(f"Import error: {e}")
  print("Make sure you're running this script from the correct directory")
  sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Constants for common commands
FOCUS_WORLD_1 = "focus 1"
FOCUS_WORLD_0 = "focus 0"


class MockCommandExecutor:
  """
  Mock command executor with configurable behavior for testing.

  This class simulates command execution with various scenarios including
  successes, failures, timeouts, and variable execution times.
  """

  def __init__(self, base_delay: float = 0.1, failure_rate: float = 0.0):
    """
    Initialize the mock executor.

    Args:
        base_delay: Base execution time for commands
        failure_rate: Probability of command failure (0.0 to 1.0)
    """
    self.base_delay = base_delay
    self.failure_rate = failure_rate
    self.execution_count = 0
    self.failed_commands: Dict[str, str] = {}
    self.command_history: List[str] = []

  def add_failing_command(self, command: str, error_message: str = "Mock failure"):
    """Mark a specific command to always fail."""
    self.failed_commands[command] = error_message

  def execute_command(self, container_name: str, command: str, timeout: int) -> str:
    """
    Mock command execution with configurable behavior.

    Args:
        container_name: Name of the container
        command: Command to execute
        timeout: Timeout in seconds

    Returns:
        str: Mock command output

    Raises:
        Various exceptions based on command and configuration
    """
    self.execution_count += 1
    self.command_history.append(command)

    logger.info("Mock executing '%s' on container '%s' (timeout: %ds, execution #%d)",
                command, container_name, timeout, self.execution_count)

    # Check for specifically failing commands
    if command in self.failed_commands:
      raise RuntimeError(self.failed_commands[command])

    # Random failures based on failure rate
    if self.failure_rate > 0 and random.random() < self.failure_rate:
      raise ConnectionError(f"Random failure for command: {command}")

    # Simulate execution time
    execution_time = self.base_delay + random.uniform(0, self.base_delay)
    time.sleep(execution_time)

    # Return different responses based on command
    return self._generate_mock_response(command, container_name)

  def _generate_mock_response(self, command: str, container_name: str) -> str:
    """Generate realistic mock responses for different commands."""
    command_lower = command.lower().strip()

    if command_lower == "status":
      return (f"Container: {container_name}\nStatus: Running\n"
              f"Users: {random.randint(1, 10)}\nUptime: 02:30:15")
    elif command_lower == "users":
      users = ["TestUser1", "TestUser2", "TestUser3", "AdminBot"]
      selected_users = random.sample(users, random.randint(1, len(users)))
      return "\n".join(f"User: {user} (Active)" for user in selected_users)
    elif command_lower == "worlds":
      world_info = (f"World 0: Main Hall ({random.randint(0, 5)} users)\n"
                    f"World 1: Workshop ({random.randint(0, 3)} users)")
      return world_info
    elif command_lower.startswith("focus"):
      world_num = command_lower.split()[-1] if len(command_lower.split()) > 1 else "0"
      return f"Focused on world {world_num}"
    elif command_lower == "shutdown":
      return "Shutdown initiated successfully"
    elif command_lower == "restart":
      return "Restart completed successfully"
    elif command_lower.startswith("ban"):
      username = command_lower.split()[-1] if len(command_lower.split()) > 1 else "user"
      return f"User '{username}' has been banned"
    elif command_lower == "listbans":
      return "Banned users:\n- troublemaker123\n- spammer456"
    elif command_lower == "gc":
      return "Garbage collection completed"
    elif command_lower == "debugworldstate":
      return "World debug info:\nWorld 0: 1024MB memory\nWorld 1: 512MB memory"
    else:
      return f"Command '{command}' executed successfully (execution #{self.execution_count})"

  def get_stats(self) -> Dict[str, int]:
    """Get execution statistics."""
    return {
        'total_executions': self.execution_count,
        'unique_commands': len(set(self.command_history)),
        'command_history_length': len(self.command_history)
    }


# Create a global mock executor instance for use in examples
mock_executor = MockCommandExecutor(base_delay=0.2)


async def basic_usage_example():
  """Demonstrate basic command queue usage."""
  print("\n=== Basic Usage Example ===")

  # Create command queue directly
  queue = CommandQueue(
      container_name="resonite-headless",
      command_executor=mock_executor.execute_command
  )

  try:
    # Execute single command
    print("1. Executing single command...")
    result = queue.add_command("status")
    execution_result = await result.wait_for_completion()
    print(f"Result: {execution_result.output}")

    # Execute command with high priority
    print("\n2. Executing high priority command...")
    result = queue.add_command("shutdown", priority=Priority.HIGH)
    execution_result = await result.wait_for_completion()
    print(f"High priority result: {execution_result.output}")

    # Execute command block
    print("\n3. Executing command block...")
    command_block = CommandBlock([
        Command("focus 1", timeout=10),
        Command("users", timeout=15)
    ], description="Get users in world 1")

    result = queue.add_command_block(command_block)
    execution_result = await result.wait_for_completion()
    print(f"Block result: {execution_result.output}")

  finally:
    queue.shutdown()


async def command_block_example():
  """Demonstrate command block usage."""
  print("\n=== Command Block Example ===")

  queue = CommandQueue(
      container_name="resonite-headless",
      command_executor=mock_executor.execute_command
  )

  try:
    # Create a command block manually
    print("1. Creating and executing command block...")
    commands = [
        Command(FOCUS_WORLD_1, timeout=10),
        Command("users", timeout=15),
        Command("status", timeout=10)
    ]

    command_block = CommandBlock(
        commands=commands,
        description="Get detailed world 1 information"
    )

    result = queue.add_command_block(command_block)
    execution_result = await result.wait_for_completion()
    print(f"Block result: {execution_result.output}")

    # Create another command block for administration
    print("\n2. Creating administrative command block...")
    admin_commands = [
        Command("listbans", timeout=10),
        Command("status", timeout=10)
    ]

    admin_block = CommandBlock(
        commands=admin_commands,
        description="Administrative status check"
    )

    result = queue.add_command_block(admin_block, priority=Priority.HIGH)
    execution_result = await result.wait_for_completion()
    print(f"Admin block result: {execution_result.output}")

  finally:
    queue.shutdown()


async def queue_status_example():
  """Demonstrate queue status monitoring."""
  print("\n=== Queue Status Example ===")

  queue = CommandQueue(
      container_name="resonite-headless",
      command_executor=mock_executor.execute_command
  )

  try:
    # Add several commands without waiting
    print("1. Adding commands to queue...")

    # Add commands with different priorities
    queue.add_command("status", priority=Priority.LOW)
    queue.add_command("worlds", priority=Priority.NORMAL)
    commands = [
        Command(FOCUS_WORLD_1, timeout=10),
        Command("users", timeout=15)
    ]
    world_block = CommandBlock(commands=commands, description="Get world 1 info")
    queue.add_command_block(world_block, priority=Priority.NORMAL)

    # Check status
    status = queue.get_status()
    print(f"Queue length: {status['queue_length']}")
    print(f"Is processing: {status['is_processing']}")
    print(f"Completed count: {status['completed_count']}")

    # Wait a bit for processing
    await asyncio.sleep(3)

    # Check status again
    status = queue.get_status()
    print(f"\nAfter processing - Queue length: {status['queue_length']}")
    print(f"Completed items: {status['completed_count']}")

  finally:
    queue.shutdown()


def create_custom_command_blocks():
  """Demonstrate creating custom command blocks."""
  print("\n=== Custom Command Blocks Example ===")

  world_management = CommandBlock(
      commands=[
          Command(FOCUS_WORLD_1),
          Command("status"),
          Command("users"),
          Command("worlds"),
          Command("listbans")
      ],
      description="Complete world 1 management info"
  )

  # Create a user investigation block
  user_investigation = CommandBlock(
      commands=[
          Command("worlds"),  # See all worlds first
          Command("focus 0"),  # Focus on main world
          Command("users"),   # Get user list
          Command("listbans")  # Check ban list
      ],
      description="User investigation sequence"
  )

  # Create server maintenance block
  maintenance_block = CommandBlock(
      commands=[
          Command("status"),
          Command("worlds"),
          Command("listbans"),
          Command("gc")
      ],
      description="Server maintenance check"
  )

  print("Created custom command blocks:")
  print(f"1. {world_management.description} - {len(world_management.commands)} commands")
  print(f"2. {user_investigation.description} - {len(user_investigation.commands)} commands")
  print(f"3. {maintenance_block.description} - {len(maintenance_block.commands)} commands")

  return [world_management, user_investigation, maintenance_block]


async def error_handling_example():
  """Demonstrate error handling capabilities."""
  print("\n=== Error Handling Example ===")

  # Create a mock executor that will fail for specific commands
  failing_executor = MockCommandExecutor(base_delay=0.1)
  failing_executor.add_failing_command("fail_command", "Container not responding")

  queue = CommandQueue(
      container_name="resonite-headless",
      command_executor=failing_executor.execute_command
  )

  try:
    # Test command that fails
    print("1. Testing command that fails...")
    result = queue.add_command("fail_command")
    execution_result = await result.wait_for_completion()
    print(f"Failed command result: Success={execution_result.success}, Error={execution_result.error}")

    # Test successful command after failure
    print("\n2. Testing successful command after failure...")
    result = queue.add_command("status")
    execution_result = await result.wait_for_completion()
    print(f"Recovery result: Success={execution_result.success}")

    # Test command block with failure
    print("\n3. Testing command block with failure...")
    commands = [
        Command("status"),
        Command("fail_command"),  # This will fail
        Command("worlds")         # This won't execute due to block failure
    ]
    command_block = CommandBlock(commands=commands, description="Block with failure")
    result = queue.add_command_block(command_block)
    execution_result = await result.wait_for_completion()
    print(f"Block with failure: Success={execution_result.success}, Error={execution_result.error}")

  finally:
    queue.shutdown()


async def priority_handling_example():
  """Demonstrate priority handling in the queue."""
  print("\n=== Priority Handling Example ===")

  queue = CommandQueue(
      container_name="resonite-headless",
      command_executor=mock_executor.execute_command
  )

  try:
    # Add commands with different priorities (note: they'll be processed in priority order)
    print("1. Adding commands with different priorities...")

    low_result = queue.add_command("status", priority=Priority.LOW)
    normal_result = queue.add_command("users", priority=Priority.NORMAL)
    high_result = queue.add_command("worlds", priority=Priority.HIGH)

    # Wait for all to complete
    await asyncio.gather(
        low_result.wait_for_completion(),
        normal_result.wait_for_completion(),
        high_result.wait_for_completion()
    )

    print("All priority commands completed")

  finally:
    queue.shutdown()


async def performance_example():
  """Demonstrate performance characteristics."""
  print("\n=== Performance Example ===")

  # Create a fast executor for performance testing
  fast_executor = MockCommandExecutor(base_delay=0.01)

  queue = CommandQueue(
      container_name="resonite-headless",
      command_executor=fast_executor.execute_command
  )

  try:
    print("1. Testing multiple simultaneous commands...")
    start_time = time.time()

    # Add many commands quickly
    results = []
    for i in range(10):
      result = queue.add_command(f"test_command_{i}")
      results.append(result)

    # Wait for all to complete
    await asyncio.gather(*[r.wait_for_completion() for r in results])

    end_time = time.time()
    print(f"Completed 10 commands in {end_time - start_time:.2f} seconds")
    print(f"Executor stats: {fast_executor.get_stats()}")

  finally:
    queue.shutdown()


async def main():
  """Run all examples."""
  print("Command Queue System Comprehensive Test")
  print("=" * 50)

  # Run all examples
  await basic_usage_example()
  await command_block_example()
  await queue_status_example()
  create_custom_command_blocks()
  await error_handling_example()
  await priority_handling_example()
  await performance_example()

  print("\n" + "=" * 50)
  print("All tests completed successfully!")
  print(f"Total mock executor calls: {mock_executor.get_stats()}")


if __name__ == "__main__":
  asyncio.run(main())
