# Docker Interface for Resonite Headless Manager

> [!warning]
> Note this interface is untested and may not work as expected
>

This module provides a Docker implementation of the `ExternalSystemInterface` for managing Docker containers running
 Resonite headless instances.

## Overview

The `DockerInterface` class provides comprehensive container management capabilities using the official Docker Python
 SDK, implementing all methods from the base `ExternalSystemInterface`.

## Features

- **Container Lifecycle Management**: Start, stop, restart Docker containers
- **Command Execution**: Execute commands inside running containers using `docker exec`
- **Status Monitoring**: Check container status and health
- **Log Management**: Retrieve container logs with configurable tail length
- **Container Discovery**: List and check existence of containers
- **Multiple Connection Methods**: Supports various Docker daemon connection methods

## Requirements

- Docker installed and running
- Python `docker` package: `pip install docker`
- Appropriate permissions to access Docker daemon

## Connection Methods

The interface automatically tries multiple connection methods in order:

1. **Unix Socket**: `unix://var/run/docker.sock` (Linux/macOS)
2. **TCP with TLS**: `tcp://localhost:2376` (secure)
3. **TCP without TLS**: `tcp://localhost:2375` (insecure)
4. **Environment Configuration**: Uses `DOCKER_HOST`, `DOCKER_TLS_VERIFY`, etc.

## Usage

### Basic Usage

```python
from docker_interface import DockerInterface

# Create interface instance
interface = DockerInterface()

# Check if container exists and is running
if interface.instance_exists("my-resonite-headless"):
    if interface.is_instance_running("my-resonite-headless"):
        print("Container is running")
    else:
        # Start the container
        interface.start_instance("my-resonite-headless")

# Execute Resonite headless commands
result = interface.execute_command("my-resonite-headless", "status")
print(f"Resonite status: {result}")

# Get container logs
logs = interface.get_instance_logs("my-resonite-headless", tail=50)
print(f"Recent logs:\n{logs}")

# Clean up when done
interface.cleanup()
```

### Container Management

```python
interface = DockerInterface()

# Get detailed container status
status = interface.get_instance_status("my-container")
print(f"Status: {status['status']}")
print(f"Image: {status['image']}")

# Container lifecycle operations
interface.start_instance("my-container")
interface.restart_instance("my-container")
interface.stop_instance("my-container")

# List all containers
containers = interface.list_instances()
for container in containers:
    print(f"{container['name']}: {container['status']}")
```

### Resonite Command Execution

The interface supports all standard Resonite headless commands:

```python
interface = DockerInterface()

# Check Resonite status
status = interface.execute_command("resonite-headless", "status")

# List users
users = interface.execute_command("resonite-headless", "users")

# Get session information
session_id = interface.execute_command("resonite-headless", "sessionid")
session_url = interface.execute_command("resonite-headless", "sessionurl")

# Administrative commands
interface.execute_command("resonite-headless", "kick username")
interface.execute_command("resonite-headless", "ban username")
interface.execute_command("resonite-headless", "save")
```

## Supported Resonite Commands

The interface supports all standard Resonite headless commands including:

- **Status Commands**: `status`, `users`, `worlds`, `sessionurl`, `sessionid`
- **User Management**: `kick`, `ban`, `unban`, `silence`, `unsilence`, `respawn`
- **Session Management**: `invite`, `acceptfriendrequest`, `message`
- **World Management**: `save`, `close`, `restart`, `name`, `description`
- **Administrative**: `gc`, `login`, `logout`, `saveconfig`, `shutdown`

## Error Handling

The interface provides comprehensive error handling:

```python
interface = DockerInterface()

# Check connection
if not interface._get_client():
    print("Failed to connect to Docker daemon")

# Graceful error handling in operations
if not interface.start_instance("nonexistent-container"):
    print("Failed to start container")

# Get detailed error information
status = interface.get_instance_status("container")
if 'error' in status:
    print(f"Error: {status['error']}")
```

## Docker Daemon Configuration

### Linux/macOS

Ensure Docker daemon is running and accessible:

```bash
# Start Docker daemon (if not already running)
sudo systemctl start docker

# Add user to docker group (to avoid sudo)
sudo usermod -aG docker $USER
```

### Windows

- Docker Desktop should be running
- Expose daemon on tcp://localhost:2375 or tcp://localhost:2376

### Environment Variables

Set these environment variables for custom Docker configurations:

- `DOCKER_HOST`: Docker daemon URL
- `DOCKER_TLS_VERIFY`: Enable TLS verification
- `DOCKER_CERT_PATH`: Path to TLS certificates

## Comparison with Podman Interface

| Feature | Docker Interface | Podman Interface |
|---------|------------------|------------------|
| Command Execution | `docker exec` | `podman attach` |
| Connection Methods | TCP, Unix socket, Environment | Unix socket, TCP |
| TLS Support | Yes | Limited |
| Rootless Support | Limited | Native |
| API Compatibility | Docker API | Podman API |

## Troubleshooting

### Connection Issues

- Verify Docker daemon is running: `docker version`
- Check permissions: `docker ps`
- Test connectivity: `docker info`

### Container Issues

- Verify container exists: `docker ps -a`
- Check container logs: `docker logs container-name`
- Ensure container is running before executing commands

### Command Execution Issues

- Verify Resonite headless is properly initialized in container
- Check container has interactive terminal support
- Ensure sufficient timeout for long-running commands

## Examples

See `example_usage.py` for comprehensive usage examples including:

- Basic container operations
- Log monitoring
- Health checks
- Resonite-specific command execution

## Dependencies

```bash
pip install docker
```

## License

This module is part of the Resonite Headless Manager project.
