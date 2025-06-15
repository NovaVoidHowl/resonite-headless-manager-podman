"""
External system interface factory for creating appropriate interface instances.

This module provides a factory pattern for creating external system interface instances
based on configuration or environment settings. Supports various container and
infrastructure management systems.
"""

import logging
import os
import sys
import subprocess
import shutil
from typing import Any, Dict, Optional, List

from .base_interface import ExternalSystemInterface  # noqa: E402 pylint: disable=relative-beyond-top-level

logger = logging.getLogger(__name__)


class ExternalSystemInterfaceFactory:
  """
  Factory class for creating external system interface instances.

  This factory determines which interface implementation to use
  based on configuration settings, environment variables, or explicit parameters.
  Supports container systems (Podman, Docker), cloud platforms, and stub interfaces.
  """

  @staticmethod
  def create_interface(
      interface_type: Optional[str] = None,
      **kwargs
  ) -> ExternalSystemInterface:
    """
    Create an external system interface instance based on the specified type.

    Args:
        interface_type: Type of interface ("podman", "docker", "stub" or None for auto-detection)
        **kwargs: Additional arguments passed to interface constructor

    Returns:
        ExternalSystemInterface: Configured interface instance

    Raises:
        ValueError: If interface_type is invalid or required dependencies are missing
        ImportError: If required modules for the interface type are not available
    """
    # Auto-detect interface type if not specified
    if interface_type is None:
      interface_type = ExternalSystemInterfaceFactory._auto_detect_interface_type()

    # Normalize interface type
    interface_type = interface_type.lower().strip()

    logger.info("Creating external system interface: type=%s", interface_type)

    # Create appropriate interface instance
    if interface_type in ["podman"]:
      return ExternalSystemInterfaceFactory._create_podman_interface(**kwargs)
    elif interface_type in ["docker"]:
      return ExternalSystemInterfaceFactory._create_docker_interface(**kwargs)
    elif interface_type in ["stub"]:
      return ExternalSystemInterfaceFactory._create_stub_interface(**kwargs)
    else:
      available_types = ExternalSystemInterfaceFactory.get_available_types()
      raise ValueError(f"Unknown interface type: {interface_type}. "
                       f"Supported types: {', '.join(available_types)}")

  @staticmethod
  def _create_podman_interface(**kwargs) -> ExternalSystemInterface:
    """Create a Podman interface instance."""
    try:
      # pylint: disable=import-outside-toplevel
      from .podman.podman_interface import PodmanInterface
      return PodmanInterface(**kwargs)
    except ImportError as e:
      logger.error("Failed to import PodmanInterface: %s", str(e))
      raise ImportError(
          "Podman interface requires the 'podman' Python package. "
          "Install it with: pip install podman"
      ) from e

  @staticmethod
  def _create_docker_interface(**kwargs) -> ExternalSystemInterface:
    """Create a Docker interface instance."""
    try:
      # pylint: disable=import-outside-toplevel
      from .docker.docker_interface import DockerInterface
      return DockerInterface(**kwargs)
    except ImportError as e:
      logger.error("Failed to import DockerInterface: %s", str(e))
      raise ImportError(
          "Docker interface requires the 'docker' Python package. "
          "Install it with: pip install docker"
      ) from e

  @staticmethod
  def _create_stub_interface(**kwargs) -> ExternalSystemInterface:
    """Create a stub interface instance."""
    try:
      # pylint: disable=import-outside-toplevel
      from .stub_interface.stub_interface import StubInterface
      return StubInterface(**kwargs)
    except ImportError as e:
      logger.error("Failed to import StubInterface: %s", str(e))
      raise ImportError("Failed to load StubInterface") from e

  @staticmethod
  def _auto_detect_interface_type() -> str:
    """
    Auto-detect the appropriate interface type based on environment.

    Returns:
        str: Detected interface type ("podman", "docker", or "stub")
    """
    # Check for explicit environment variable
    interface_env = os.getenv('EXTERNAL_INTERFACE_TYPE', '').lower()
    if interface_env:
      logger.info("Interface type from environment: %s", interface_env)
      return interface_env

    # Check for test mode indicators
    test_mode_indicators = [
        'TEST_MODE',
        'TESTING',
        'CI',
        'PYTEST_CURRENT_TEST',
        'UNITTEST_MODE'
    ]

    for indicator in test_mode_indicators:
      if os.getenv(indicator):
        logger.info("Test mode detected via %s environment variable", indicator)
        return "stub"

    # Check if we're in a test server context
    if 'test_server.py' in ' '.join(sys.argv if hasattr(sys, 'argv') else []):
      logger.info("Test server detected from command line")
      return "stub"

    # Try to detect available container systems
    detected_system = ExternalSystemInterfaceFactory._detect_container_system()
    if detected_system:
      logger.info("Detected container system: %s", detected_system)
      return detected_system

    # Default to stub if nothing else is detected
    logger.info("No container system detected, defaulting to stub interface")
    return "stub"

  @staticmethod
  def _detect_container_system() -> Optional[str]:
    """
    Detect which container system is available on the current system.

    Returns:
        Optional[str]: Detected container system ("podman", "docker") or None
    """

    # Check for Podman first (often preferred in rootless environments)
    if shutil.which("podman"):
      try:
        result = subprocess.run(
            ["podman", "version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )
        if result.returncode == 0:
          logger.debug("Podman detected and responding")
          return "podman"
      except (subprocess.TimeoutExpired, OSError):
        logger.debug("Podman found but not responding")

    # Check for Docker
    if shutil.which("docker"):
      try:
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )
        if result.returncode == 0:
          logger.debug("Docker detected and responding")
          return "docker"
      except (subprocess.TimeoutExpired, OSError):
        logger.debug("Docker found but not responding")

    return None

  @staticmethod
  def check_interface_availability(interface_type: str) -> Dict[str, Any]:
    """
    Check if an interface type is available and working.

    Args:
        interface_type: Interface type to check

    Returns:
        Dict[str, Any]: Status information including availability and any errors
    """
    interface_type = interface_type.lower().strip()

    try:
      # Try to create the interface
      interface = ExternalSystemInterfaceFactory.create_interface(interface_type)

      # For container interfaces, try to list instances to verify connectivity
      if interface_type in ["podman", "docker"]:
        try:
          instances = interface.list_instances()
          return {
              "available": True,
              "interface_type": interface_type,
              "instances_found": len(instances),
              "error": None
          }
        except (OSError, AttributeError, RuntimeError) as e:
          return {
              "available": False,
              "interface_type": interface_type,
              "error": f"Interface created but failed connectivity test: {str(e)}"
          }
      else:
        # For stub interface, just check if it was created successfully
        return {
            "available": True,
            "interface_type": interface_type,
            "error": None
        }

    except (ImportError, ValueError, OSError, AttributeError) as e:
      return {
          "available": False,
          "interface_type": interface_type,
          "error": str(e)
      }

  @staticmethod
  def create_from_config(config: Dict[str, Any]) -> ExternalSystemInterface:
    """
    Create an interface from configuration dictionary.

    Args:
        config: Configuration dictionary containing interface settings

    Returns:
        ExternalSystemInterface: Configured interface instance
    """
    interface_type = config.get('interface_type', 'auto')

    # Extract any additional parameters
    additional_params = {
        k: v for k, v in config.items()
        if k not in ['interface_type']
    }

    # Handle 'auto' as None for auto-detection
    if interface_type == 'auto':
      interface_type = None

    return ExternalSystemInterfaceFactory.create_interface(
        interface_type=interface_type,
        **additional_params
    )

  @staticmethod
  def get_available_types() -> List[str]:
    """
    Get list of available interface types.

    Returns:
        List[str]: Available interface types
    """
    return ["podman", "docker", "stub", "test", "auto"]

  @staticmethod
  def get_system_info() -> Dict[str, Any]:
    """
    Get information about the current system and available interfaces.

    Returns:
        Dict[str, Any]: System information including detected interfaces
    """
    detected_system = ExternalSystemInterfaceFactory._detect_container_system()
    info = {
        "detected_container_system": detected_system,
        "available_interfaces": {},
        "environment_variables": {
            "EXTERNAL_INTERFACE_TYPE": os.getenv('EXTERNAL_INTERFACE_TYPE'),
            "TEST_MODE": os.getenv('TEST_MODE'),
            "CI": os.getenv('CI')
        }
    }

    # Check availability of each interface type
    for interface_type in ["podman", "docker", "stub"]:
      availability_info = ExternalSystemInterfaceFactory.check_interface_availability(
          interface_type
      )
      info["available_interfaces"][interface_type] = availability_info

    return info


def create_interface(**kwargs) -> ExternalSystemInterface:
  """
  Convenience function for creating interface instances.

  Args:
      **kwargs: Arguments passed to ExternalSystemInterfaceFactory.create_interface()

  Returns:
      ExternalSystemInterface: Configured interface instance
  """
  return ExternalSystemInterfaceFactory.create_interface(**kwargs)


def get_best_available_interface() -> ExternalSystemInterface:
  """
  Get the best available interface for the current system.

  This function tries to detect and return the most suitable interface
  based on what's available on the system.

  Returns:
      ExternalSystemInterface: The best available interface instance
  """
  return ExternalSystemInterfaceFactory.create_interface()
