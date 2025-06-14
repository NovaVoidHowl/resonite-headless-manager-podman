"""
Test script demonstrating Command Queue integration with Stub Interface

This script shows how to use the command queue system in conjunction with the
stub interface to test sequential command execution to a simulated Resonite
headless container. The queue manages only execute_command operations, while
other operations (start/stop/restart) are called directly on the interface.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the parent directories to the path to import modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "external_system_interfaces"))
sys.path.insert(0, str(project_root / "external_system_interfaces" / "stub_interface"))
sys.path.insert(0, str(project_root / "command_queue"))

try:
  from stub_interface import StubInterface  # pylint: disable=import-error
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


class StubCommandExecutor:
  """
  Wrapper that connects the command queue to the stub interface.

  This class adapts the stub interface's execute_command method to work
  with the command queue system.
  """

  def __init__(self, stub_interface: StubInterface, instance_name: str):
    """
    Initialize the executor.

    Args:
        stub_interface: The stub interface instance
        instance_name: Name of the instance to execute commands on
    """
    self.stub_interface = stub_interface
    self.instance_name = instance_name

  def execute_command(self, container_name: str, command: str, timeout: int) -> str:
    """
    Execute a command through the stub interface.

    Args:
        container_name: Name of the container (matches instance_name)
        command: Command to execute
        timeout: Timeout in seconds

    Returns:
        str: Command output
    """
    logger.info("Executing command '%s' on instance '%s' (timeout: %ds)",
                command, container_name, timeout)

    # Verify we're targeting the correct instance
    if container_name != self.instance_name:
      raise ValueError(f"Container name mismatch: expected {self.instance_name}, got {container_name}")

    return self.stub_interface.execute_command(self.instance_name, command, timeout)


async def test_basic_command_execution():
  """Test basic command execution through the queue."""
  print("\n=== Basic Command Execution Test ===")

  # Create stub interface and executor
  stub = StubInterface()
  instance_name = "resonite-headless-test"
  executor = StubCommandExecutor(stub, instance_name)

  # Create command queue
  queue = CommandQueue(
      container_name=instance_name,
      command_executor=executor.execute_command,
      max_queue_size=50
  )

  try:
    # Test basic Resonite commands
    commands_to_test = [
        "status",
        "users",
        "worlds",
        "sessionurl",
        "sessionid"
    ]

    print(f"Testing {len(commands_to_test)} basic commands...")

    for cmd in commands_to_test:
      print(f"\nExecuting: {cmd}")
      result = queue.add_command(cmd, timeout=10)
      execution_result = await result.wait_for_completion()

      print(f"Success: {execution_result.success}")
      if execution_result.success:
        # Truncate long outputs for readability
        output = execution_result.output
        if len(output) > 100:
          output = output[:100] + "..."
        print(f"Output: {output}")
      else:
        print(f"Error: {execution_result.error}")

  finally:
    queue.shutdown()


async def test_command_blocks():
  """Test command blocks with related Resonite commands."""
  print("\n=== Command Blocks Test ===")

  stub = StubInterface()
  instance_name = "resonite-headless-test"
  executor = StubCommandExecutor(stub, instance_name)

  queue = CommandQueue(
      container_name=instance_name,
      command_executor=executor.execute_command
  )

  try:
    # Create a world management command block
    world_mgmt_commands = [
        Command("status", timeout=10),
        Command("worlds", timeout=10),
        Command("users", timeout=10),
        Command("sessionurl", timeout=5),
        Command("sessionid", timeout=5)
    ]

    world_mgmt_block = CommandBlock(
        commands=world_mgmt_commands,
        description="World management information gathering"
    )

    print("Executing world management command block...")
    result = queue.add_command_block(world_mgmt_block)
    execution_result = await result.wait_for_completion()

    print(f"Block execution success: {execution_result.success}")
    print(f"Execution time: {execution_result.execution_time:.2f} seconds")

    # Print each command's output section
    outputs = execution_result.output.split('\n')
    current_section = []
    for line in outputs:
      if line.startswith("=== Command:"):
        if current_section:
          print("".join(current_section))
        current_section = [f"\n{line}\n"]
      else:
        current_section.append(f"{line}\n")

    if current_section:
      print("".join(current_section))

    # Create a user management command block
    user_mgmt_commands = [
        Command("users", timeout=10),
        Command("friendrequests", timeout=10),
        Command("listbans", timeout=10)
    ]

    user_mgmt_block = CommandBlock(
        commands=user_mgmt_commands,
        description="User management information"
    )

    print("\nExecuting user management command block...")
    result = queue.add_command_block(user_mgmt_block, priority=Priority.HIGH)
    execution_result = await result.wait_for_completion()

    print(f"User mgmt block success: {execution_result.success}")

  finally:
    queue.shutdown()


async def test_mixed_priorities():
  """Test commands with different priorities."""
  print("\n=== Mixed Priorities Test ===")

  stub = StubInterface()
  instance_name = "resonite-headless-test"
  executor = StubCommandExecutor(stub, instance_name)

  queue = CommandQueue(
      container_name=instance_name,
      command_executor=executor.execute_command
  )

  try:
    # Add commands with different priorities
    print("Adding commands with different priorities...")

    # Add low priority commands first
    low1 = queue.add_command("debugworldstate", priority=Priority.LOW,
                             description="Debug info (low priority)")
    low2 = queue.add_command("gc", priority=Priority.LOW,
                             description="Garbage collection (low priority)")

    # Add normal priority command
    normal = queue.add_command("status", priority=Priority.NORMAL,
                               description="Status check (normal priority)")

    # Add high priority command (should execute first)
    high = queue.add_command("users", priority=Priority.HIGH,
                             description="User list (high priority)")

    # Check queue status
    status = queue.get_status()
    print(f"Queue length: {status['queue_length']}")
    print("Queue items:")
    for item in status['queue_items']:
      print(f"  - {item['description']} (Priority: {item['priority']})")

    # Wait for all to complete
    print("\nWaiting for command execution...")
    results = await asyncio.gather(
        high.wait_for_completion(),
        normal.wait_for_completion(),
        low1.wait_for_completion(),
        low2.wait_for_completion()
    )

    print("\nExecution order and results:")
    for i, result in enumerate(results):
      cmd_name = ["High priority", "Normal priority", "Low priority 1", "Low priority 2"][i]
      print(f"{cmd_name}: Success={result.success}, Time={result.execution_time:.2f}s")

  finally:
    queue.shutdown()


async def test_direct_interface_operations():
  """Test direct interface operations (not through queue)."""
  print("\n=== Direct Interface Operations Test ===")

  stub = StubInterface()
  instance_name = "resonite-headless-test"

  print("Testing direct interface operations (bypassing queue)...")

  # Test instance management operations
  print(f"\n1. Checking if instance '{instance_name}' exists...")
  exists = stub.instance_exists(instance_name)
  print(f"   Instance exists: {exists}")

  print("\n2. Getting instance status...")
  status = stub.get_instance_status(instance_name)
  print(f"   Status: {status}")

  print("\n3. Checking if instance is running...")
  is_running = stub.is_instance_running(instance_name)
  print(f"   Is running: {is_running}")

  if not is_running:
    print("\n4. Starting instance...")
    started = stub.start_instance(instance_name)
    print(f"   Start successful: {started}")

  print("\n5. Getting instance logs...")
  logs = stub.get_instance_logs(instance_name, tail=5)
  print(f"   Recent logs:\n{logs}")

  print("\n6. Listing all instances...")
  instances = stub.list_instances()
  print(f"   Found {len(instances)} instances:")
  for instance in instances:
    print(f"   - {instance['name']}: {instance['status']}")

  print("\n7. Restarting instance...")
  restarted = stub.restart_instance(instance_name)
  print(f"   Restart successful: {restarted}")


async def test_error_handling():
  """Test error handling in the queue system."""
  print("\n=== Error Handling Test ===")

  stub = StubInterface()
  instance_name = "resonite-headless-test"  # Create a custom executor that can simulate failures

  class FaultInjectionExecutor(StubCommandExecutor):
    """
    Custom executor that can simulate command failures for testing error handling.

    This class extends StubCommandExecutor to add the ability to mark specific
    commands as failing, allowing us to test error handling and recovery scenarios.
    """

    def __init__(self, stub_interface, instance_name):
      super().__init__(stub_interface, instance_name)
      self.fail_commands = set()

    def add_failing_command(self, command):
      """Mark a command to fail."""
      self.fail_commands.add(command)

    def execute_command(self, container_name: str, command: str, timeout: int) -> str:
      if command in self.fail_commands:
        raise ConnectionError(f"Simulated failure for command: {command}")
      return super().execute_command(container_name, command, timeout)

  executor = FaultInjectionExecutor(stub, instance_name)
  executor.add_failing_command("fail_test")

  queue = CommandQueue(
      container_name=instance_name,
      command_executor=executor.execute_command
  )

  try:
    print("Testing error handling...")

    # Test successful command
    print("\n1. Executing successful command...")
    success_result = queue.add_command("status")
    result = await success_result.wait_for_completion()
    print(f"   Success: {result.success}")

    # Test failing command
    print("\n2. Executing command that will fail...")
    fail_result = queue.add_command("fail_test")
    result = await fail_result.wait_for_completion()
    print(f"   Success: {result.success}")
    print(f"   Error: {result.error}")

    # Test recovery with another successful command
    print("\n3. Testing recovery with another successful command...")
    recovery_result = queue.add_command("users")
    result = await recovery_result.wait_for_completion()
    print(f"   Recovery success: {result.success}")

    # Test command block with failure
    print("\n4. Testing command block with failure...")
    commands = [
        Command("status"),
        Command("fail_test"),  # This will fail
        Command("users")       # This should still execute in stub
    ]

    block = CommandBlock(commands, description="Block with failure")
    block_result = queue.add_command_block(block)
    result = await block_result.wait_for_completion()
    print(f"   Block success: {result.success}")
    print(f"   Block error: {result.error}")

  finally:
    queue.shutdown()


async def test_queue_monitoring():
  """Test queue status monitoring capabilities."""
  print("\n=== Queue Monitoring Test ===")

  stub = StubInterface()
  instance_name = "resonite-headless-test"
  executor = StubCommandExecutor(stub, instance_name)

  queue = CommandQueue(
      container_name=instance_name,
      command_executor=executor.execute_command,
      max_queue_size=20
  )

  try:
    print("Adding multiple commands to demonstrate monitoring...")

    # Add several commands without waiting
    commands = [
        ("status", Priority.NORMAL),
        ("users", Priority.HIGH),
        ("worlds", Priority.LOW),
        ("sessionurl", Priority.NORMAL),
        ("listbans", Priority.HIGH),
        ("debugworldstate", Priority.LOW)
    ]

    results = []
    for cmd, priority in commands:
      result = queue.add_command(cmd, priority=priority, description=f"Test {cmd}")
      results.append(result)

    # Monitor queue status during execution
    print("\nMonitoring queue during execution...")
    for i in range(3):
      status = queue.get_status()
      print(f"\nStatus check {i+1}:")
      print(f"  Queue length: {status['queue_length']}")
      print(f"  Is processing: {status['is_processing']}")
      print(f"  Completed count: {status['completed_count']}")

      if status['queue_items']:
        print("  Pending items:")
        for item in status['queue_items']:
          print(f"    - {item['description']} ({item['status']})")

      await asyncio.sleep(1)

    # Wait for all commands to complete
    print("\nWaiting for all commands to complete...")
    await asyncio.gather(*[r.wait_for_completion() for r in results])

    # Final status
    final_status = queue.get_status()
    print("\nFinal status:")
    print(f"  Queue length: {final_status['queue_length']}")
    print(f"  Total completed: {final_status['completed_count']}")

    if final_status['recent_completed']:
      print("  Recent completed items:")
      for item in final_status['recent_completed']:
        print(f"    - {item['description']} -> {item['status']}")

  finally:
    queue.shutdown()


async def main():
  """Run all tests."""
  print("Command Queue + Stub Interface Integration Tests")
  print("=" * 60)

  try:
    # Run all test scenarios
    await test_basic_command_execution()
    await test_command_blocks()
    await test_mixed_priorities()
    await test_direct_interface_operations()
    await test_error_handling()
    await test_queue_monitoring()

    print("\n" + "=" * 60)
    print("All tests completed successfully!")

  except Exception as e:
    logger.error("Test execution failed: %s", str(e))
    raise


if __name__ == "__main__":
  asyncio.run(main())
