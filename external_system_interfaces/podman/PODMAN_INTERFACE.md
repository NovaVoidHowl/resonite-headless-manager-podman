# Podman Interface Documentation

## Overview

The Podman interface provides a clean set of functions that offer direct access to Podman container
operations.\
This interface is designed to be simple, reliable, and easy to use for managing Resonite headless containers.

## Requirements

- Python 3.7+
- Podman installed and configured
- Python packages: `podman`, `typing` (standard library)
- Podman service running (rootless or rootful)

## Architecture

- **`podman_interface.py`** - Core functional interface with simple functions
- **`example_usage.py`** - Examples of how to use the interface

## Functional Interface

### Basic Functions

```python
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

# Check if container is running
if is_container_running("my-container"):
    print("Container is running")

# Execute a command
result = execute_command("my-container", "status")
print(result)

# Get container status
status = get_container_status("my-container")
print(f"Status: {status['status']}")
```

### Container Management

```python
# Start a container
if start_container("my-container"):
    print("Container started successfully")

# Stop a container
if stop_container("my-container"):
    print("Container stopped successfully")

# Restart a container
if restart_container("my-container"):
    print("Container restarted successfully")
```

### Information Gathering

```python
# Get container logs
logs = get_container_logs("my-container", tail=50)
print(logs)

# List all containers
containers = list_containers()
for container in containers:
    print(f"{container['name']}: {container['status']}")

# Check if container exists
if container_exists("my-container"):
    print("Container exists")
```

## Available Functions

### Container Management Functions

- `start_container(container_name: str) -> bool` - Start a container
- `stop_container(container_name: str) -> bool` - Stop a container  
- `restart_container(container_name: str) -> bool` - Restart a container

### Information Functions

- `is_container_running(container_name: str) -> bool` - Check if container is running
- `get_container_status(container_name: str) -> Dict[str, Any]` - Get detailed status
- `container_exists(container_name: str) -> bool` - Check if container exists
- `list_containers() -> List[Dict[str, Any]]` - List all containers

### Command and Log Functions

- `execute_command(container_name: str, command: str, timeout: int = 10) -> str` - Execute command in container
- `get_container_logs(container_name: str, tail: int = 100) -> str` - Get container logs

### Utility Functions

- `cleanup()` - Clean up client connections

## Example Usage

Complete examples are available in `example_usage.py`, including:

- Basic container operations (start/stop/restart)
- Command execution with timeout handling
- Log monitoring and retrieval
- Health checking routines
- Container listing and status checking
- Resonite-specific command examples

## Error Handling

All functions return appropriate error indicators:

- Boolean functions return `False` on error
- String functions return error messages prefixed with "Error:"
- Status functions return dictionaries with error information

## Connection Management

The interface automatically manages Podman client connections:

- Tries multiple connection methods (Unix socket, TCP)
- Automatically reconnects on connection loss
- Proper cleanup when done

## Usage Recommendations

1. **New code**: Use the functional interface directly
2. **Error handling**: Always check return values
3. **Cleanup**: Call `cleanup()` when done (optional but recommended)
