# Command Queue System

This module provides a thread-safe command queue system for managing sequential command execution to Resonite headless
containers.\
It ensures that only one command or command block can be executed at a time, preventing command conflicts and ensuring
proper execution order.

## Features

- **Sequential Execution**: Commands are executed one at a time in FIFO order
- **Command Blocks**: Support for multi-command sequences that must be executed together
- **Priority Support**: High-priority commands can jump to the front of the queue
- **Thread Safety**: Safe for use across multiple threads and WebSocket connections
- **Status Tracking**: Monitor queue status, pending commands, and execution progress
- **Timeout Handling**: Configurable timeouts for individual commands and command blocks
- **Error Handling**: Robust error handling with detailed error reporting

## Command Types

### Single Commands

Simple commands that execute independently:

```python
queue.add_command("shutdown")
queue.add_command("status")
```

### Command Blocks

Sequential commands that must be executed together (e.g., focus + users):

```python
# Get users in world 2
command_block = CommandBlock([
    Command("focus 2"),
    Command("users")
], description="Get users in world 2")
queue.add_command_block(command_block)
```

### Priority Commands

Commands that need immediate execution:

```python
queue.add_command("shutdown", priority=Priority.HIGH)
```

## Usage Examples

### Basic Usage

```python
import asyncio
import logging
import time
from command_queue import CommandQueue, Command, CommandBlock, Priority

# Mock executor function (replace with actual podman interface)
def mock_command_executor(container_name: str, command: str, timeout: int) -> str:
    """Mock command executor for demonstration purposes."""
    logging.info("Executing on %s: %s (timeout: %ds)", container_name, command, timeout)
    time.sleep(0.5)  # Simulate execution time
    return f"Command '{command}' executed successfully"

# Initialize queue with container name and command executor function
queue = CommandQueue(
    container_name="resonite-headless",
    command_executor=mock_command_executor
)

async def example():
    # Add single command
    result = queue.add_command("status", timeout=15)
    execution_result = await result.wait_for_completion()
    print(f"Result: {execution_result.output}")

    # Add command block for world inspection
    world_num = 2
    block = CommandBlock([
        Command(f"focus {world_num}"),
        Command("users")
    ], description=f"Get users in world {world_num}")

    result = queue.add_command_block(block)
    execution_result = await result.wait_for_completion()
    print(f"Block result: {execution_result.output}")

    # Check queue status
    status = queue.get_status()
    print(f"Queue length: {status['queue_length']}")
    print(f"Is processing: {status['is_processing']}")

    # Shutdown queue when done
    queue.shutdown()

# Run the example
asyncio.run(example())
```

### WebSocket Integration

```python
import asyncio
from command_queue import CommandQueue, Priority

# Initialize queue with your command executor
queue = CommandQueue(
    container_name="resonite-headless",
    command_executor=your_command_executor_function
)

async def handle_command_request(websocket, command_data):
    """Handle command request from WebSocket"""
    command = command_data.get('command')
    priority = Priority.HIGH if command_data.get('urgent') else Priority.NORMAL

    # Add to queue
    result = queue.add_command(command, priority=priority)

    # Send response
    await websocket.send_json({
        'type': 'command_queued',
        'queue_id': result.queue_id,
        'position': result.position
    })

    # Wait for completion (optional)
    if command_data.get('wait_for_result'):
        final_result = await result.wait_for_completion()
        await websocket.send_json({
            'type': 'command_result',
            'queue_id': result.queue_id,
            'output': final_result.output,
            'success': final_result.success
        })
```

### Advanced Command Blocks

```python
from command_queue import Command, CommandBlock, Priority

# Complex world management sequence
def get_world_info(world_number):
    return CommandBlock([
        Command(f"focus {world_number}"),
        Command("status"),
        Command("users"),
        Command("sessionUrl")
    ], description=f"Full world {world_number} information")

# Ban user sequence
def ban_user(username, reason="Violation of rules"):
    return CommandBlock([
        Command(f"ban {username} \"{reason}\""),
        Command("listbans")  # Refresh ban list
    ], description=f"Ban user {username}")

# Queue multiple operations
async def example_operations():
    queue.add_command_block(get_world_info(1))
    queue.add_command_block(ban_user("problematic_user"))
    queue.add_command("shutdown", priority=Priority.HIGH)  # Will execute before ban
```

## Running the Example

A complete working example is provided in `example_usage.py`. Run it with:

```bash
cd command_queue
python example_usage.py
```

This example demonstrates:

- Basic command execution
- Command blocks
- Priority handling
- Queue status monitoring
- Error handling scenarios

## API Reference

### CommandQueue

Main queue management class.

**Constructor:**

```python
CommandQueue(
    container_name: str,
    command_executor: Callable[[str, str, int], str],
    max_queue_size: int = 100,
    cleanup_interval: int = 60,
    max_result_history: int = 50
)
```

**Parameters:**

- `container_name` - Name of the container to execute commands in
- `command_executor` - Function that executes commands (container_name, command, timeout) → output
- `max_queue_size` - Maximum number of items that can be queued (default: 100)
- `cleanup_interval` - Interval in seconds to cleanup completed items (default: 60)
- `max_result_history` - Maximum number of completed results to keep (default: 50)

#### Methods

- `add_command(command, timeout=30, priority=Priority.NORMAL, description="")` - Add single command
- `add_command_block(command_block, priority=Priority.NORMAL, description="")` - Add command block
- `get_status()` - Get current queue status
- `clear_queue()` - Clear all pending commands
- `shutdown()` - Gracefully shutdown the queue
- `is_processing()` - Check if currently processing commands
- `get_queue_length()` - Get current number of items in queue

### CommandBlock

Container for multiple sequential commands.

**Constructor:**

```python
CommandBlock(
    commands: List[Command],
    description: str = "",
    block_timeout: Optional[int] = None,
    metadata: Dict[str, Any] = None
)
```

#### Methods

- `add_command(command, timeout=30)` - Add command to block
- `get_total_timeout()` - Get combined timeout for all commands

### QueueResult

Result object returned when adding commands to queue.

#### Properties

- `queue_id` - Unique identifier for the queued item
- `position` - Position in queue
- `wait_for_completion(timeout=None)` - Async method to wait for completion
- `is_completed()` - Check if the command has completed
- `get_status()` - Get current status of the queued item

### ExecutionResult

Result object returned after command execution.

#### Properties

- `success` - Whether execution was successful
- `output` - Command output
- `error` - Error message (if any)
- `execution_time` - Time taken to execute
- `timestamp` - When execution completed
- `command_executed` - The command that was executed

## Error Handling

The queue system provides comprehensive error handling:

- **Timeout Errors**: Commands that exceed their timeout are terminated
- **Connection Errors**: Container connection issues are handled gracefully
- **Queue Full**: Protection against queue overflow
- **Invalid Commands**: Validation of command format and parameters
- **Worker Thread Errors**: Recovery from worker thread failures

## Thread Safety

The command queue is fully thread-safe and can be used from:

- Multiple WebSocket connections
- Background monitoring tasks
- Web API endpoints
- Administrative interfaces

All operations use appropriate locking mechanisms to ensure data consistency.

## Performance Considerations

- **Single Worker Thread**: Ensures sequential execution but may create delays for multiple simultaneous requests
- **Result Caching**: Integration with existing command cache system for frequently used commands
- **Memory Management**: Automatic cleanup of completed results to prevent memory leaks
- **Timeout Management**: Prevents hanging commands from blocking the queue indefinitely

## Integration with Existing Systems

The command queue integrates with existing systems by accepting any command executor function that follows the
signature:

```python
def command_executor(container_name: str, command: str, timeout: int) -> str:
    """Execute a command and return the output"""
    # Your implementation here
    pass
```
