"""
Example usage of the Command Queue System

This script demonstrates how to use the command queue system for managing
sequential command execution to Resonite headless containers.
"""

import asyncio
import logging
import time

# Import directly from the command_queue module file in the same directory
from command_queue import Command, CommandBlock, CommandQueue, Priority


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Command constants
FOCUS_WORLD_1 = "focus 1"


# Mock executor for demonstration (replace with actual podman interface)
def mock_command_executor(container_name: str, command: str, timeout: int) -> str:
  """Mock command executor for demonstration purposes."""
  # Use the container_name parameter to avoid unused parameter warning
  logger.info("Executing on %s: %s (timeout: %ds)", container_name, command, timeout)

  # Simulate command execution time
  time.sleep(0.5)

  # Simulate different command responses
  if command == "status":
    return "Server Status: Running\nUsers: 5\nWorlds: 3"
  elif command == "worlds":
    return "World 0: Main Hall (5 users)\nWorld 1: Workshop (2 users)\nWorld 2: Private Room (0 users)"
  elif command.startswith("focus"):
    world_num = command.split()[1]
    return f"Focused on world {world_num}"
  elif command == "users":
    return "Username: Alice\nUsername: Bob\nUsername: Charlie"
  elif command == "shutdown":
    return "Server shutdown initiated"
  elif command.startswith("ban"):
    username = command.split()[1]
    return f"User {username} has been banned"
  elif command == "listbans":
    return "Banned Users:\n- troublemaker123\n- spammer456"
  else:
    return f"Command executed: {command}"


async def basic_usage_example():
  """Demonstrate basic command queue usage."""
  print("\n=== Basic Usage Example ===")

  # Create command queue directly
  queue = CommandQueue(
      container_name="resonite-headless",
      command_executor=mock_command_executor
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
      command_executor=mock_command_executor
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
      command_executor=mock_command_executor
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
          Command("sessionUrl"),
          Command("sessionID"),
          Command("users"),
          Command("sessionUrl"),
          Command("sessionID")
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
          Command("sessionUrl")
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

  # Mock executor that sometimes fails
  def failing_executor(container_name: str, command: str, timeout: int) -> str:
    if command == "fail_command":
      raise ConnectionError("Container not responding")
    elif command == "timeout_command":
      time.sleep(timeout + 1)  # This will cause a timeout
      return "This should timeout"
    else:
      return mock_command_executor(container_name, command, timeout)

  queue = CommandQueue(
      container_name="resonite-headless",
      command_executor=failing_executor
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


async def main():
  """Run all examples."""
  print("Command Queue System Examples")
  print("=" * 50)

  # Run all examples
  await basic_usage_example()
  await command_block_example()
  await queue_status_example()
  create_custom_command_blocks()
  await error_handling_example()

  print("\n" + "=" * 50)
  print("All examples completed!")


if __name__ == "__main__":
  asyncio.run(main())
