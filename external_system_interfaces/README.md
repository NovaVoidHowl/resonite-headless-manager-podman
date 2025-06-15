# External System Interfaces

This folder contains all interface modules for connecting to external systems that manage Resonite headless instances.
 The interfaces provide a standardized way to control containers, virtual machines, cloud instances,
 or other infrastructure types.

## Supported Interfaces

The following interfaces are currently supported:

### Container Systems

- **Podman** - Rootless container management (Linux/Unix)
- **Docker** - Container management platform
- **Stub** - Mock interface for testing and development

## Interface Factory

The `factory.py` module provides a factory pattern for creating interface instances at runtime.
 This allows you to easily switch between different infrastructure types through configuration.

### Basic Usage

```python
from external_system_interfaces.factory import create_interface, get_best_available_interface

# Create a specific interface type
stub_interface = create_interface(interface_type="stub")
podman_interface = create_interface(interface_type="podman")
docker_interface = create_interface(interface_type="docker")

# Auto-detect the best available interface
auto_interface = get_best_available_interface()
```

### Configuration-Based Usage

```python
from external_system_interfaces.factory import ExternalSystemInterfaceFactory

# From a configuration dictionary
config = {
    "interface_type": "auto"  # or "stub", "podman", "docker"
}
interface = ExternalSystemInterfaceFactory.create_from_config(config)

# Check system capabilities
system_info = ExternalSystemInterfaceFactory.get_system_info()
print(f"Detected container system: {system_info['detected_container_system']}")
```

## Interface Selection Methods

### 1. Explicit Configuration

Set the interface type directly in your application configuration:

```json
{
  "external_interface": {
    "interface_type": "podman"
  }
}
```

### 2. Environment Variables

Override the interface type using environment variables:

```bash
# Force a specific interface
export EXTERNAL_INTERFACE_TYPE=podman
export EXTERNAL_INTERFACE_TYPE=docker
export EXTERNAL_INTERFACE_TYPE=stub

# Force test mode (uses stub interface)
export TEST_MODE=1
```

### 3. Auto-Detection

The factory can automatically detect the best available interface:

- Checks for test mode indicators (CI, TEST_MODE, etc.)
- Detects available container systems (Podman, Docker)
- Falls back to stub interface if nothing else is available

Priority order:

1. Environment variable override
2. Test mode detection → stub
3. Podman detection
4. Docker detection
5. Fallback → stub

## Interface Types

### Stub Interface

**Purpose**: Testing, development, and demonstrations
**Requirements**: None (always available)
**Use Cases**:

- Development and testing
- CI/CD pipelines
- Demonstrations without real infrastructure
- Debugging application logic

```python
# Always works
stub = create_interface(interface_type="stub")
```

### Podman Interface

**Purpose**: Rootless container management
**Requirements**:

- Podman installed and configured
- `podman` Python package (`pip install podman`)

**Use Cases**:

- Linux/Unix production environments
- Rootless container deployments
- Security-conscious environments

```python
# Requires Podman setup
podman = create_interface(interface_type="podman")
```

### Docker Interface

**Purpose**: Container management
**Requirements**:

- Docker installed and configured
- `docker` Python package (`pip install docker`)

**Use Cases**:

- Standard container deployments
- Development environments
- Cross-platform container management

```python
# Requires Docker setup
docker = create_interface(interface_type="docker")
```

## System Requirements

### For Podman Interface

```bash
# Install Podman (Linux)
sudo apt-get install podman  # Ubuntu/Debian
sudo dnf install podman      # Fedora/RHEL

# Install Python package
pip install podman
```

### For Docker Interface

```bash
# Install Docker (varies by platform)
# See: https://docs.docker.com/get-docker/

# Install Python package
pip install docker
```

### For Stub Interface

No additional requirements - always available.

## Error Handling and Fallbacks

The factory provides robust error handling:

```python
# Check interface availability before use
availability = ExternalSystemInterfaceFactory.check_interface_availability("podman")
if availability["available"]:
    interface = create_interface(interface_type="podman")
else:
    print(f"Podman not available: {availability['error']}")
    interface = create_interface(interface_type="stub")  # Fallback
```

## Example Application Integration

```python
import os
from external_system_interfaces.factory import create_interface

def get_interface_from_config():
    """Get interface based on configuration and environment."""
    
    # Check for environment override first
    interface_type = os.getenv('EXTERNAL_INTERFACE_TYPE')
    
    if not interface_type:
        # Load from config file or use auto-detection
        interface_type = "auto"  # or load from your config
    
    try:
        return create_interface(interface_type=interface_type)
    except Exception as e:
        print(f"Failed to create {interface_type} interface: {e}")
        print("Falling back to stub interface")
        return create_interface(interface_type="stub")

# Usage
interface = get_interface_from_config()
instances = interface.list_instances()
print(f"Found {len(instances)} instances using {type(interface).__name__}")
```

## Common Interface Methods

All interfaces implement the same base methods from `ExternalSystemInterface`:

- `is_instance_running(instance_name)` - Check if instance is running
- `get_instance_status(instance_name)` - Get detailed instance status
- `start_instance(instance_name)` - Start an instance
- `stop_instance(instance_name)` - Stop an instance
- `restart_instance(instance_name)` - Restart an instance
- `execute_command(instance_name, command, timeout)` - Execute command in instance
- `get_instance_logs(instance_name, tail)` - Get instance logs
- `list_instances()` - List all instances
- `instance_exists(instance_name)` - Check if instance exists
- `cleanup()` - Clean up resources

## Testing

You can test interface functionality using the integration test:

```bash
# Run the integration test (uses factory)
cd resonite-headless-manager
python _tests/test_instance-stub_and_command-queue/test_integration.py
```

Or test the factory directly:

```bash
# Test factory functionality
cd resonite-headless-manager
python external_system_interfaces/example_usage.py
```
