"""
Data source factory for creating appropriate data source instances.

This module provides a factory pattern for creating data source instances
based on configuration or environment settings.
"""

import logging
import os
import sys
from typing import Any, Dict, Optional, List

from .base_data_source import BaseDataSource  # noqa: E402 pylint: disable=relative-beyond-top-level
from .stub_data_source import StubDataSource  # noqa: E402 pylint: disable=relative-beyond-top-level

logger = logging.getLogger(__name__)


class DataSourceFactory:
  """
  Factory class for creating data source instances.

  This factory determines which data source implementation to use
  based on configuration settings, environment variables, or explicit parameters.
  """

  @staticmethod
  def create_data_source(
      source_type: Optional[str] = None,
      container_name: Optional[str] = None,
      config_file: str = "config.json",
      **kwargs
  ) -> BaseDataSource:
    """
    Create a data source instance based on the specified type.

    Args:
        source_type: Type of data source ("live", "stub", "test", or None for auto-detection)
        container_name: Name of the container (uses env var if not provided)
        config_file: Path to configuration file
        **kwargs: Additional arguments passed to data source constructor

    Returns:
        BaseDataSource: Configured data source instance

    Raises:
        ValueError: If source_type is invalid or required parameters are missing
    """
    # Auto-detect source type if not specified
    if source_type is None:
      source_type = DataSourceFactory._auto_detect_source_type()

    # Normalize source type
    source_type = source_type.lower().strip()

    # Get container name from environment if not provided
    if container_name is None:
      container_name = os.getenv('CONTAINER_NAME', 'resonite-headless')

    logger.info("Creating data source: type=%s, container=%s", source_type, container_name)

    # Create appropriate data source instance
    if source_type in ["live", "production", "prod"]:
      # return LiveDataSource(container_name, config_file, **kwargs) # Uncomment when LiveDataSource is implemented
      raise NotImplementedError("LiveDataSource is not implemented yet.")
    elif source_type in ["stub", "test", "testing", "dummy", "mock"]:
      return StubDataSource(container_name, config_file, **kwargs)
    else:
      raise ValueError(f"Unknown data source type: {source_type}. "
                       f"Supported types: live, stub, test, production")

  @staticmethod
  def _auto_detect_source_type() -> str:
    """
    Auto-detect the appropriate data source type based on environment.

    Returns:
        str: Detected source type ("live" or "stub")
    """
    # Check for explicit environment variable
    data_source_env = os.getenv('DATA_SOURCE_TYPE', '').lower()
    if data_source_env:
      logger.info("Data source type from environment: %s", data_source_env)
      return data_source_env

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
        return "stub"    # Check if we're in a test server context
    if 'test_server.py' in ' '.join(sys.argv if hasattr(sys, 'argv') else []):
      logger.info("Test server detected from command line")
      return "stub"

    # Default to live for production
    logger.info("No test mode indicators found, defaulting to live data source")
    return "live"

  @staticmethod
  def create_from_config(config: Dict[str, Any]) -> BaseDataSource:
    """
    Create a data source from configuration dictionary.

    Args:
        config: Configuration dictionary containing data source settings

    Returns:
        BaseDataSource: Configured data source instance
    """
    source_type = config.get('data_source_type', 'live')
    container_name = config.get('container_name')
    config_file = config.get('config_file', 'config.json')

    # Extract any additional parameters
    additional_params = {
        k: v for k, v in config.items()
        if k not in ['data_source_type', 'container_name', 'config_file']
    }

    return DataSourceFactory.create_data_source(
        source_type=source_type,
        container_name=container_name,
        config_file=config_file,
        **additional_params
    )

  @staticmethod
  def get_available_types() -> List[str]:
    """
    Get list of available data source types.

    Returns:
        List[str]: Available data source types
    """
    return ["live", "stub", "test", "production", "dummy", "mock"]


def create_data_source(**kwargs) -> BaseDataSource:
  """
  Convenience function for creating data source instances.

  Args:
      **kwargs: Arguments passed to DataSourceFactory.create_data_source()

  Returns:
      BaseDataSource: Configured data source instance
  """
  return DataSourceFactory.create_data_source(**kwargs)
