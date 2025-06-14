# Command Queue + Stub Interface Integration Test

This test script demonstrates how to use the command queue system in conjunction with the stub interface to test
 sequential command execution to a simulated Resonite headless container.

## Location

This test is located in `_tests/test_instance-stub_and_command-queue/` to keep test files separate from the main codebase.

## Purpose

The integration test shows:

1. **Queue Management**: How commands are queued and executed sequentially
2. **Priority Handling**: Commands with different priorities (HIGH, NORMAL, LOW)  
3. **Command Blocks**: Executing multiple related commands as a block
4. **Direct Interface Operations**: Instance management operations that bypass the queue
5. **Error Handling**: How the system handles failures and recovers
6. **Monitoring**: Queue status monitoring during execution

## Key Concepts

- **Command Queue**: Manages sequential execution of `execute_command` operations only
- **Direct Operations**: Instance management (start/stop/restart) bypasses the queue
- **Stub Interface**: Provides realistic mock responses for all Resonite headless commands

## Test Scenarios

### 1. Basic Command Execution

Tests individual Resonite commands through the queue:

- `status` - Get server status
- `users` - List connected users  
- `worlds` - List active worlds
- `sessionurl` - Get session URL
- `sessionid` - Get session ID

### 2. Command Blocks

Tests sequential execution of related commands:

- World management block (status, worlds, users, session info)
- User management block (users, friend requests, ban list)

### 3. Priority Testing

Demonstrates priority-based execution:

- HIGH priority commands execute first
- NORMAL priority commands execute in order
- LOW priority commands execute last

### 4. Direct Interface Operations

Tests operations that bypass the queue:

- `instance_exists()` - Check if instance exists
- `get_instance_status()` - Get detailed status
- `is_instance_running()` - Check running state
- `start_instance()` - Start instance
- `get_instance_logs()` - Retrieve logs
- `list_instances()` - List all instances
- `restart_instance()` - Restart instance

### 5. Error Handling

Tests system resilience:

- Commands that fail with exceptions
- Recovery after failures
- Command blocks with failures

### 6. Queue Monitoring

Demonstrates status monitoring:

- Queue length tracking
- Execution status monitoring
- Completed item history

## Running the Test

```bash
cd _tests/test_instance-stub_and_command-queue
python test_integration.py
```

## Expected Output

The test will show:

- Command execution logs
- Queue status updates
- Realistic Resonite headless responses
- Error handling demonstrations
- Performance timing information

## Architecture

```text
[Test Script] 
    ↓
[StubCommandExecutor] ← Adapts interface for queue
    ↓
[CommandQueue] ← Manages sequential execution
    ↓
[StubInterface] ← Provides mock Resonite responses
```

The `StubCommandExecutor` class acts as an adapter between the command queue system and the stub interface,
 ensuring that the queue's `execute_command` calls are properly routed to the stub interface's implementation.

## Integration Points

1. **Queue → Interface**: Commands flow from queue to stub interface
2. **Direct Operations**: Instance management bypasses queue entirely
3. **Error Propagation**: Failures in stub interface bubble up through queue
4. **Result Formatting**: Queue wraps interface responses in ExecutionResult objects

This test demonstrates the complete integration pattern that will be used with real container interfaces
 (Podman, Docker) in production deployments.

## Files in this Test

- `test_integration.py` - Main integration test script
- `README.md` - This documentation file
