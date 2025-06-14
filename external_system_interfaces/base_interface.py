"""
Abstract base class for external system interfaces in the Resonite Headless Manager.

This module defines the standard interface that all external system implementations
must follow, whether they manage containers (Podman, Docker), virtual machines,
cloud instances (EC2, Azure), or physical hosts.

The interface is generic and uses "instance" terminology to encompass all types
of managed resources.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ExternalSystemInterface(ABC):
  """
  Abstract base class for external system interfaces.

  This class defines the standard API that all external system implementations
  must implement. It uses generic "instance" terminology to support various
  infrastructure types including:
  - Container systems (Podman, Docker, etc.)
  - Virtual machines (VMware, VirtualBox, etc.)
  - Cloud instances (EC2, Azure VMs, Google Compute, etc.)
  - Physical hosts with process managers
  - Kubernetes pods
  - Any other managed compute resources
  """
  @abstractmethod
  def is_instance_running(self, instance_name: str) -> bool:
    """
    Check if an instance is currently running.

    Args:
        instance_name (str): Name/identifier of the instance to check

    Returns:
        bool: True if the instance is running, False otherwise
    """
    raise NotImplementedError()

  @abstractmethod
  def get_instance_status(self, instance_name: str) -> Dict[str, Any]:
    """
    Get detailed status information for an instance.

    Args:
        instance_name (str): Name/identifier of the instance

    Returns:
        Dict[str, Any]: Dictionary containing instance status information.
                       Should include at minimum:
                       - 'name': instance name
                       - 'status': current status (running, stopped, etc.)
                       - 'id': unique identifier
    """
    raise NotImplementedError()

  @abstractmethod
  def start_instance(self, instance_name: str) -> bool:
    """
    Start an instance.

    Args:
        instance_name (str): Name/identifier of the instance to start

    Returns:
        bool: True if successful, False otherwise
    """
    raise NotImplementedError()

  @abstractmethod
  def stop_instance(self, instance_name: str) -> bool:
    """
    Stop an instance.

    Args:
        instance_name (str): Name/identifier of the instance to stop

    Returns:
        bool: True if successful, False otherwise
    """
    raise NotImplementedError()

  @abstractmethod
  def restart_instance(self, instance_name: str) -> bool:
    """
    Restart an instance.

    Args:
        instance_name (str): Name/identifier of the instance to restart

    Returns:
        bool: True if successful, False otherwise
    """
    raise NotImplementedError()

  @abstractmethod
  def execute_command(self, instance_name: str, command: str, timeout: int = 10) -> str:
    """
    Execute a command on/in an instance.

    Args:
        instance_name (str): Name/identifier of the instance
        command (str): Command to execute
        timeout (int): Timeout for command execution in seconds

    Returns:
        str: Output from the command execution
    """
    raise NotImplementedError()

  @abstractmethod
  def get_instance_logs(self, instance_name: str, tail: int = 100) -> str:
    """
    Get logs from an instance.

    Args:
        instance_name (str): Name/identifier of the instance
        tail (int): Number of lines to retrieve from the end

    Returns:
        str: Instance logs
    """
    raise NotImplementedError()

  @abstractmethod
  def list_instances(self) -> List[Dict[str, Any]]:
    """
    List all managed instances.

    Returns:
        List[Dict[str, Any]]: List of instance information dictionaries.
                             Each dict should include at minimum:
                             - 'name': instance name
                             - 'status': current status
                             - 'id': unique identifier
    """
    raise NotImplementedError()

  @abstractmethod
  def instance_exists(self, instance_name: str) -> bool:
    """
    Check if an instance exists (regardless of running state).

    Args:
        instance_name (str): Name/identifier of the instance to check

    Returns:
        bool: True if instance exists, False otherwise
    """
    raise NotImplementedError()

  @abstractmethod
  def cleanup(self) -> None:
    """
    Clean up any resources used by the interface.

    This method should be called when the interface is no longer needed
    to properly clean up connections, temporary files, or other resources.
    """
    raise NotImplementedError()

  # Optional helper methods that implementations can override
  def get_interface_type(self) -> str:
    """
    Get a string identifying the type of interface.

    Returns:
        str: Interface type identifier (e.g., 'podman', 'docker', 'ec2', 'stub')
    """
    return self.__class__.__name__.lower().replace('interface', '')

  def validate_instance_name(self, instance_name: str) -> bool:
    """
    Validate that an instance name is acceptable.

    Args:
        instance_name (str): Name to validate

    Returns:
        bool: True if name is valid, False otherwise
    """
    if not instance_name or not isinstance(instance_name, str):
      return False
    return len(instance_name.strip()) > 0

  def get_supported_commands(self) -> List[str]:
    """
    Get a list of commands supported by execute_command.

    Returns:
        List[str]: List of supported command names
    """
    return []  # Base implementation returns empty list
