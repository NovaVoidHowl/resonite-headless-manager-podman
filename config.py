"""
Configuration management for Resonite Headless Manager.

This module provides configuration settings for cache refresh intervals
and other application settings.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from typing import Dict

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
  """Represents cache configuration settings"""
  worlds_interval: int = 10
  status_interval: int = 10
  sessionurl_interval: int = 30
  sessionid_interval: int = 30
  users_interval: int = 5
  listbans_interval: int = 60


class Config:
  """
  Application configuration management.
  """
  def __init__(self, config_file: str = "config.json"):
    """
    Initialize configuration.

    Args:
        config_file (str, optional): Configuration file path. Defaults to "config.json".
    """
    self.config_file = config_file
    self.cache_config = CacheConfig()
    self.load_config()

  def load_config(self) -> None:
    """Load configuration from file"""
    try:
      if os.path.exists(self.config_file):
        with open(self.config_file, 'r', encoding='utf-8') as f:
          data = json.load(f)
          if 'cache' in data:
            self.cache_config = CacheConfig(**data['cache'])
          logger.info("Loaded configuration from %s", self.config_file)
      else:
        self.save_config()  # Create default config
        logger.info("Created default configuration in %s", self.config_file)
    except json.JSONDecodeError as e:
      logger.error("JSON decode error loading config: %s", str(e))
    except OSError as e:
      logger.error("OS error loading config: %s", str(e))
    except TypeError as e:
      logger.error("Type error loading config: %s", str(e))

  def save_config(self) -> None:
    """Save current configuration to file"""
    try:
      config_data = {
        'cache': asdict(self.cache_config)
      }
      with open(self.config_file, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2)
      logger.info("Saved configuration to %s", self.config_file)
    except (OSError, TypeError) as e:
      logger.error("Error saving config: %s", str(e))

  def get_command_polling_intervals(self) -> Dict[str, Dict]:
    """
    Get command polling intervals configuration.

    Returns:
        Dict[str, Dict]: Command polling configurations
    """
    return {
      "worlds": {"polling_interval": self.cache_config.worlds_interval},
      "status": {"polling_interval": self.cache_config.status_interval},
      "sessionUrl": {"polling_interval": self.cache_config.sessionurl_interval},
      "sessionID": {"polling_interval": self.cache_config.sessionid_interval},
      "users": {"polling_interval": self.cache_config.users_interval},
      "listbans": {
        "polling_interval": self.cache_config.listbans_interval,
        "invalidate_on_commands": ["ban", "unban"]
      }
    }

  def is_using_config_file(self) -> bool:
    """Check if using config file or builtin defaults"""
    return os.path.exists(self.config_file)

  def get_current_settings(self) -> Dict:
    """Get current configuration settings"""
    return {
      "using_config_file": self.is_using_config_file(),
      "config_file_path": self.config_file if self.is_using_config_file() else None,
      "settings": {
        "cache": asdict(self.cache_config)
      }
    }

  def generate_config_file(self) -> Dict[str, str]:
    """Generate config file if not exists and return status"""
    if self.is_using_config_file():
      return {
        "status": "unchanged",
        "message": "Config file already exists and is being used"
      }
    
    self.save_config()
    return {
      "status": "created",
      "message": f"Generated new config file at {self.config_file}"
    }
