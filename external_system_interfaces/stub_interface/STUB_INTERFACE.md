# Stub Interface Documentation

## Overview

The Stub Interface provides a complete mock implementation of container management functionality for the  
Resonite Headless Manager. This interface simulates all container operations and Resonite headless  
application commands without requiring actual container infrastructure, making it perfect for development,  
testing, and demonstration purposes.

The stub returns realistic responses that closely mimic what would be returned from actual Resonite  
headless containers, including detailed status information, user management responses, and world  
management outputs.

## Requirements

- Python 3.10+ (requires `match-case` syntax)
- Python packages: `typing`, `logging`, `time`, `random`, `string` (all standard library)

## Architecture

- **`stub_interface.py`** - Core functional interface with simple functions that provide stubbed responses
- **`STUB_INTERFACE.md`** - This documentation file

## Functional Interface

### Basic Functions

The interface provides simple functions that return predefined responses mimicking real container behavior.  
All functions include appropriate logging and simulated delays to make the behavior realistic.

### Container Management

```python
# Start a container (returns True after 1 second delay)
if start_container("resonite-headless-1"):
    print("Container started successfully")

# Stop a container (returns True after 1 second delay)
if stop_container("resonite-headless-1"):
    print("Container stopped successfully")

# Restart a container (returns True after 1 second delay)
if restart_container("resonite-headless-1"):
    print("Container restarted successfully")

# Check if container is running (always returns True in stub)
if is_container_running("resonite-headless-1"):
    print("Container is running")
```

### Information Gathering

```python
# Get container status (returns mock data with random container ID)
status = get_container_status("resonite-headless-1")
print(f"Container: {status['name']}, Status: {status['status']}, ID: {status['id']}")

# Get container logs (returns realistic Resonite headless log entries)
logs = get_container_logs("resonite-headless-1", tail=10)
print(logs)

# List all containers (returns two example containers)
containers = list_containers()
for container in containers:
    print(f"{container['name']}: {container['status']}")

# Check if container exists (always returns True in stub)
if container_exists("resonite-headless-1"):
    print("Container exists")
```

### Resonite Command Execution

The `execute_command` function supports all major Resonite headless commands and returns realistic responses:

```python
# World status information
result = execute_command("resonite-headless-1", "status")
print(result)  # Returns detailed world status

# List users in the world
result = execute_command("resonite-headless-1", "users")
print(result)  # Returns formatted user list with IDs, roles, etc.

# User management commands
result = execute_command("resonite-headless-1", "kick TestUser")
print(result)  # Returns kick confirmation with user details

result = execute_command("resonite-headless-1", "ban TestUser")
print(result)  # Returns ban confirmation with detailed logs

# World management
result = execute_command("resonite-headless-1", "save")
print(result)  # Returns "World saved successfully!"

result = execute_command("resonite-headless-1", "restart")
print(result)  # Returns "World restarted successfully!"
```

## Available Functions

### Container Management Functions

- `start_container(container_name: str) -> bool` - Start a container (1 second delay, always returns True)
- `stop_container(container_name: str) -> bool` - Stop a container (1 second delay, always returns True)
- `restart_container(container_name: str) -> bool` - Restart a container (1 second delay, always returns True)

### Information Functions

- `is_container_running(container_name: str) -> bool` - Check if container is running (always returns True)
- `get_container_status(container_name: str) -> Dict[str, Any]` - Get detailed status with random container ID
- `container_exists(container_name: str) -> bool` - Check if container exists (always returns True)
- `list_containers() -> List[Dict[str, Any]]` - List all containers (returns 2 example containers)

### Command and Log Functions

- `execute_command(container_name: str, command: str, timeout: int = 10) -> str` - Execute Resonite command
- `get_container_logs(container_name: str, tail: int = 100) -> str` - Get realistic container logs

### Utility Functions

- `cleanup()` - Clean up resources (stub implementation does nothing but logs)

## Supported Resonite Commands

The `execute_command` function supports all major Resonite headless application commands:

### World Information Commands

- `status` - Returns detailed world status information
- `users` - Lists all users with IDs, roles, presence, and statistics
- `worlds` - Lists all active worlds
- `sessionurl` - Returns the session URL
- `sessionid` - Returns the session ID

### User Management Commands

- `kick <username>` - Kicks a user from the session
- `silence <username>` - Silences a user in the session
- `unsilence <username>` - Removes silence from a user
- `ban <username>` - Bans a user from all sessions
- `unban <username>` - Removes ban for a user
- `respawn <username>` - Respawns a user
- `role <username> <role>` - Assigns a role to a user

### Communication Commands

- `message <username> <message>` - Sends a message to a user
- `invite <username>` - Invites a user to the current world
- `friendrequests` - Lists incoming friend requests
- `acceptfriendrequest <username>` - Accepts a friend request

### World Management Commands

- `save` - Saves the current world
- `close` - Closes the current world
- `restart` - Restarts the current world
- `name <new_name>` - Sets a new world name
- `description <description>` - Sets world description
- `accesslevel <level>` - Sets world access level
- `maxusers <number>` - Sets maximum user limit

### Administrative Commands

- `login <credentials>` - Login to an account
- `logout` - Logout from current account
- `saveconfig` - Saves current configuration
- `listbans` - Lists all active bans
- `debugworldstate` - Returns detailed world state information
- `gc` - Forces garbage collection
- `shutdown` - Shuts down the headless client

### Dynamic Commands

- `dynamicimpulse*` - Dynamic impulse commands
- `spawn <url>` - Spawns items from URLs
- `import <path>` - Imports assets

All commands return realistic responses that closely match actual Resonite headless application output.

## Example Usage

Here's a complete example of using the stub interface:

```python
from stub_interface import (
    start_container, execute_command, get_container_logs, 
    get_container_status, list_containers, cleanup
)

# Start a container
container_name = "resonite-headless-test"
if start_container(container_name):
    print(f"✓ Container {container_name} started")

# Get container status
status = get_container_status(container_name)
print(f"Container ID: {status['id']}, Status: {status['status']}")

# Execute some Resonite commands
print("\n--- World Status ---")
world_status = execute_command(container_name, "status")
print(world_status)

print("\n--- User List ---")
users = execute_command(container_name, "users")
print(users)

print("\n--- Kick User ---")
kick_result = execute_command(container_name, "kick TestUser")
print(kick_result)

# Get container logs
print("\n--- Container Logs ---")
logs = get_container_logs(container_name, tail=5)
print(logs)

# List all containers
print("\n--- All Containers ---")
containers = list_containers()
for container in containers:
    print(f"  {container['name']}: {container['status']}")

# Cleanup
cleanup()
```

## Error Handling

All functions return appropriate indicators for success/failure:

- **Boolean functions** (start_container, stop_container, etc.): Return `True` for success, `False` for failure
- **String functions** (execute_command, get_container_logs): Return response strings or error messages
- **Dictionary functions** (get_container_status): Return status dictionaries with mock data
- **List functions** (list_containers): Return lists of container information

In this stub implementation:

- Container management functions always return `True`
- Status functions return realistic mock data
- Command execution returns appropriate Resonite headless responses
- No actual errors are simulated (all operations succeed)

## Stub Behavior

### Realistic Simulation

- **Timing delays**: Container operations include 1-second delays, command execution includes 0.5-second delays
- **Logging**: All operations are logged using Python's logging module
- **Dynamic data**: Container IDs are randomly generated for each status request
- **Realistic responses**: All Resonite command responses closely match actual application output

### Limitations

- No actual container management (all operations are mocked)
- No persistent state (each function call is independent)
- No error conditions simulated (all operations succeed)
- No network connectivity required

## Usage Recommendations

1. **Development**: Use for developing and testing application logic without container dependencies
2. **Testing**: Perfect for unit tests and integration tests
3. **Demonstration**: Great for demos and presentations
4. **Error handling**: Always check return values even though this stub always succeeds
5. **Cleanup**: Call `cleanup()` when done (logs cleanup but no actual resources to clean)
6. **Logging**: Configure logging to see detailed operation information

## Implementation Details

The stub interface uses modern Python features:

- **Match-case statements**: Uses Python 3.10+ `match-case` for command routing
- **Helper functions**: Modular design with separate functions for different command types
- **Type hints**: Full type annotations for better IDE support
- **Logging**: Comprehensive logging for debugging and monitoring
