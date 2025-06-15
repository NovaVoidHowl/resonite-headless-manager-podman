"""
Example usage of the External System Interface Factory

This example demonstrates how to use the factory to create and manage
different interface types based on configuration.
"""

import json
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from external_system_interfaces.factory import (  # noqa:E402  pylint: disable=wrong-import-position
    ExternalSystemInterfaceFactory,
    create_interface,
    get_best_available_interface
)


def example_basic_usage():
  """Basic factory usage examples."""
  print("=== Basic Factory Usage Examples ===\n")

  # 1. Create specific interface types
  print("1. Creating specific interface types:")

  # Always works - stub interface for testing/development
  stub = create_interface(interface_type="stub")
  print(f"   Stub interface: {type(stub).__name__}")
  stub.cleanup()
  # Would work if Podman is installed and configured
  try:
    podman = create_interface(interface_type="podman")
    print(f"   Podman interface: {type(podman).__name__}")
    podman.cleanup()
  except (ImportError, ValueError, OSError, RuntimeError) as e:
    print(f"   Podman interface: Not available - {e}")
  # Would work if Docker is installed and configured
  try:
    docker = create_interface(interface_type="docker")
    print(f"   Docker interface: {type(docker).__name__}")
    docker.cleanup()
  except (ImportError, ValueError, OSError, RuntimeError) as e:
    print(f"   Docker interface: Not available - {e}")


def example_auto_detection():
  """Auto-detection example."""
  print("\n2. Auto-detection (best available interface):")

  # Let the factory choose the best available interface
  auto_interface = get_best_available_interface()
  print(f"   Auto-detected: {type(auto_interface).__name__}")

  # Test basic functionality
  instances = auto_interface.list_instances()
  print(f"   Found {len(instances)} instances")

  auto_interface.cleanup()


def example_config_based():
  """Configuration-based interface creation."""
  print("\n3. Configuration-based interface creation:")

  # Example configurations that might come from config files
  configs = [
    {
      "interface_type": "stub",
      "description": "Development/testing configuration"
    },
    {
      "interface_type": "auto",
      "description": "Auto-detect best available"
    },
    {
      "interface_type": "podman",
      "description": "Podman container management"
    }
  ]
  for config in configs:
    print(f"   Config: {config['description']}")
    try:
      interface = ExternalSystemInterfaceFactory.create_from_config(config)
      print(f"     Created: {type(interface).__name__}")

      # Quick functionality test
      status = interface.get_instance_status("test-instance")
      print(f"     Test status: {status.get('status', 'N/A')}")

      interface.cleanup()
    except (ImportError, ValueError, OSError, RuntimeError, AttributeError) as e:
      print(f"     Failed: {e}")


def example_system_info():
  """System information and interface availability."""
  print("\n4. System information and interface availability:")

  system_info = ExternalSystemInterfaceFactory.get_system_info()

  print(f"   Detected container system: {system_info['detected_container_system']}")
  print("   Environment variables:")
  for key, value in system_info['environment_variables'].items():
    print(f"     {key}: {value}")
    print("   Interface availability:")
  for interface_type, info in system_info['available_interfaces'].items():
    status = "✓" if info['available'] else "✗"
    instances_found = info.get('instances_found')
    instance_count = f" ({instances_found} instances)" if instances_found is not None else ""
    error_msg = f" - {info['error']}" if info.get('error') else ""
    print(f"     {status} {interface_type}{instance_count}{error_msg}")


def example_json_config():
  """Example with JSON configuration file."""
  print("\n5. JSON configuration file example:")

  # Example JSON config that might be loaded from a file
  json_config = {
    "external_interface": {
      "interface_type": "auto",  # or "stub", "podman", "docker"
      "fallback_to_stub": True
    },
    "container_settings": {
      "default_timeout": 30,
      "max_retries": 3
    }
  }

  print("   Example config.json:")
  print(f"   {json.dumps(json_config, indent=4)}")
  # Use the configuration
  interface_config = json_config["external_interface"]
  try:
    interface = ExternalSystemInterfaceFactory.create_from_config(interface_config)
    print(f"   Successfully created: {type(interface).__name__}")
    interface.cleanup()
  except (ImportError, ValueError, OSError, RuntimeError, AttributeError) as e:
    print(f"   Failed to create interface: {e}")


def example_environment_override():
  """Example showing environment variable override."""
  print("\n6. Environment variable override:")
  print("   Set environment variables to override auto-detection:")
  print("   - EXTERNAL_INTERFACE_TYPE=podman  # Force Podman interface")
  print("   - EXTERNAL_INTERFACE_TYPE=docker  # Force Docker interface")
  print("   - EXTERNAL_INTERFACE_TYPE=stub    # Force stub interface")
  print("   - TEST_MODE=1                     # Force test mode (stub)")


if __name__ == "__main__":
  print("External System Interface Factory Usage Examples")
  print("=" * 60)

  try:
    example_basic_usage()
    example_auto_detection()
    example_config_based()
    example_system_info()
    example_json_config()
    example_environment_override()

    print(f"\n{'=' * 60}")
    print("All examples completed successfully!")

  except Exception as e:
    print(f"Example execution failed: {e}")
    raise
