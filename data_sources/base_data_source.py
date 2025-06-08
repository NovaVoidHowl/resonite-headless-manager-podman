# pylint: disable=unnecessary-ellipsis
"""
Abstract base class for data sources in the Resonite Headless Manager.

This module provides the interface that all data sources must implement,
enabling pluggable data source architecture for testing and production.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Callable


class BaseDataSource(ABC):
  """
  Abstract base class for data sources.

  This interface defines all the operations that data sources must support
  to be compatible with the API endpoints. Implementations can provide
  live data (from actual containers) or stub data (for testing).
  """

  # Container Management Operations
  @abstractmethod
  def is_container_running(self) -> bool:
    """
    Check if the container is currently running.

    Returns:
        bool: True if the container is running, False otherwise
    """
    ...

  @abstractmethod
  def start_container(self) -> None:
    """
    Start the container.

    Raises:
        RuntimeError: If container cannot be started
    """
    ...

  @abstractmethod
  def stop_container(self) -> None:
    """
    Stop the container.

    Raises:
        RuntimeError: If container cannot be stopped
    """
    ...

  @abstractmethod
  def restart_container(self) -> bool:
    """
    Restart the container.

    Returns:
        bool: True if restart was successful, False otherwise

    Raises:
        RuntimeError: If container cannot be restarted
    """
    ...

  @abstractmethod
  def get_container_status(self) -> Dict[str, Any]:
    """
    Get container status information.

    Returns:
        Dict[str, Any]: Dictionary containing container status information
            Keys: status, name, id, image, error (optional)
    """
    ...

  # Command Operations
  @abstractmethod
  def get_structured_command_response(self, command: str, target_world_instance: str,
                                      command_mode: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Get a structured response for a command with appropriate formatting and type.

    This method handles special commands that need structured responses (like listbans, users, etc.)
    and returns a dictionary containing the response type and data. For regular commands,
    it can return the raw output.

    Args:
        command: The command to execute
        timeout: Command timeout in seconds

    Returns:
        Dict[str, Any]: Structured response containing:
            - type: The response type (e.g., 'bans_update', 'command_response', etc.)
            - output/data: The structured data or raw output
            - command: The original command (for command_response type)
            - other fields as appropriate for the response type
    """
    ...

  # Log Operations
  @abstractmethod
  def get_container_logs(self) -> str:
    """
    Get container logs.

    Returns:
        str: The logs of the container
    """
    ...

  @abstractmethod
  def get_recent_logs(self) -> List[str]:
    """
    Get recent log lines from buffer.

    Returns:
        List[str]: Recent log lines
    """
    ...

  @abstractmethod
  def monitor_output(self, callback: Callable[[str], None]) -> None:
    """
    Monitor container output continuously.

    Args:
        callback: Function to call with each log line
    """
    ...

  # Configuration Operations
  @abstractmethod
  def get_config_status(self) -> Dict[str, Any]:
    """
    Get configuration status.

    Returns:
        Dict[str, Any]: Configuration status information
    """
    ...

  @abstractmethod
  def get_manger_config_settings(self) -> Dict[str, Any]:
    """
    Get current configuration settings.

    Returns:
        Dict[str, Any]: Current configuration settings
    """
    ...

  @abstractmethod
  def update_manager_config_settings(self, settings_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update manager configuration settings.

    Args:
        settings_data: Configuration settings data to update

    Returns:
        Dict[str, Any]: Result of the update operation
    """
    ...

  @abstractmethod
  def generate_config(self) -> Dict[str, Any]:
    """
    Generate configuration file.

    Returns:
        Dict[str, Any]: Result of config generation        """
    ...

  @abstractmethod
  def get_cpu_usage(self) -> float:
    """
    Get current CPU usage percentage.

    Returns:
        float: CPU usage as a percentage (0.0 to 100.0)
    """
    ...

  @abstractmethod
  def get_memory_usage(self) -> Dict[str, Any]:
    """
    Get current memory usage information.

    Returns:
        Dict[str, Any]: Memory usage information with keys:
            - percent: Memory usage percentage
            - used: Used memory (e.g. "2.1GB")
            - total: Total memory (e.g. "8.0GB")
    """
    ...

  # Data Access Operations
  @abstractmethod
  def get_worlds_data(self) -> List[Dict[str, Any]]:
    """
    Get worlds data.

    Returns:
        List[Dict[str, Any]]: List of world information dictionaries
    """
    ...

  @abstractmethod
  def get_users_data(self) -> List[Dict[str, Any]]:
    """
    Get users data.

    Returns:
        List[Dict[str, Any]]: List of user information dictionaries
    """
    ...

  @abstractmethod
  def get_server_status(self) -> Dict[str, Any]:
    """
    Get server status information.

    Returns:
        Dict[str, Any]: Server status information dictionary
    """
    ...

  @abstractmethod
  def get_headless_config(self) -> Dict[str, Any]:
    """
    Get headless configuration.

    Returns:
        Dict[str, Any]: Headless configuration dictionary
    """
    ...

  @abstractmethod
  def get_banned_users(self) -> List[Dict[str, Any]]:
    """
    Get banned users list.

    Returns:
        List[Dict[str, Any]]: List of banned user information dictionaries
    """
    ...

  @abstractmethod
  def get_friend_requests(self) -> List[str]:
    """
    Get friend requests list.

    Returns:
        List[str]: List of friend request usernames
    """
    ...

  # Resource Management
  @abstractmethod
  def cleanup(self) -> None:
    """Clean up resources when data source is being shut down."""
    ...

  # Optional: Data source metadata
  def get_data_source_info(self) -> Dict[str, Any]:
    """
    Get information about this data source.

    Returns:
        Dict[str, Any]: Metadata about the data source
    """
    return {
        "type": self.__class__.__name__,
        "description": "Base data source implementation",
        "is_live": False
    }
