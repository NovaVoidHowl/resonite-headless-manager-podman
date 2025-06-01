"""
Command caching system for Resonite Headless Manager.

This module provides caching functionality for container commands to reduce load
on the container by implementing a polling-based cache update mechanism.
"""

import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
  """Represents a cached command result"""
  data: Any
  timestamp: datetime
  last_updated: datetime


@dataclass
class CommandConfig:
  """Configuration for a cached command"""
  polling_interval: int  # seconds
  invalidate_on_commands: Optional[list[str]] = None  # list of commands that should invalidate this cache


class CommandCache:
  """
  Manages caching of container commands with configurable polling intervals.
  """

  def __init__(self, command_executor: Callable[[str], str]):
    """
    Initialize the command cache.

    Args:
      command_executor (Callable[[str], str]): Function to execute container commands
    """
    self.command_executor = command_executor
    self._cache: Dict[str, CacheEntry] = {}
    self._polling_threads: Dict[str, threading.Thread] = {}
    self._stop_events: Dict[str, threading.Event] = {}
    self._command_configs: Dict[str, CommandConfig] = {}
    self._setup_default_configs()

  def _setup_default_configs(self) -> None:
    """Set up default polling configurations for commands"""
    self._command_configs = {
      "worlds": CommandConfig(10),  # Poll every 10 seconds
      "status": CommandConfig(10),
      "sessionUrl": CommandConfig(30),  # Less frequent as it rarely changes
      "sessionID": CommandConfig(30),
      "users": CommandConfig(5),  # More frequent as users come and go
      "listbans": CommandConfig(
        60,  # Longer interval for bans
        invalidate_on_commands=["ban", "unban"]  # Invalidate on ban/unban commands
      )
    }

  def start(self) -> None:
    """Start polling threads for all configured commands"""
    for command in self._command_configs:
      self._start_polling(command)

  def stop(self) -> None:
    """Stop all polling threads"""
    for command in list(self._stop_events.keys()):
      self._stop_polling(command)

  def _start_polling(self, command: str) -> None:
    """
    Start polling thread for a specific command.

    Args:
      command (str): The command to poll
    """
    if command in self._polling_threads:
      return

    stop_event = threading.Event()
    self._stop_events[command] = stop_event

    def poll_command():
      cmd = command  # Capture command in local scope
      while not stop_event.is_set():
        try:
          result = self.command_executor(cmd)
          now = datetime.now()
          self._cache[cmd] = CacheEntry(
            data=result,
            timestamp=now,
            last_updated=now
          )
          logger.info("Updated cache for command: %s", cmd)
        except (ConnectionError, RuntimeError) as e:
          logger.error("Error polling command %s: %s", cmd, e)
        except (IOError, OSError, ValueError) as e:
          logger.error("IO or value error in command %s: %s", cmd, e)
        except Exception as e:
          logger.critical("Critical error in command %s: %s", cmd, e)
          logger.exception("Full traceback for critical error:")
        # Sleep for the configured interval or until stopped
        stop_event.wait(self._command_configs[cmd].polling_interval)

    thread = threading.Thread(
      target=poll_command,
      name=f"poll_{command}",
      daemon=True
    )
    self._polling_threads[command] = thread
    thread.start()

  def _stop_polling(self, command: str) -> None:
    """
    Stop polling thread for a specific command.

    Args:
      command (str): The command to stop polling
    """
    if command in self._stop_events:
      self._stop_events[command].set()
      if command in self._polling_threads:
        self._polling_threads[command].join(timeout=1)
        del self._polling_threads[command]
      del self._stop_events[command]

  def invalidate(self, command: str) -> None:
    """
    Invalidate cache for a specific command.

    Args:
      command (str): The command whose cache should be invalidated
    """
    if command in self._cache:
      del self._cache[command]

    # Check if this command should invalidate other caches
    for cmd, config in self._command_configs.items():
      if (
        config.invalidate_on_commands and
        command in config.invalidate_on_commands and
        cmd in self._cache
      ):
        del self._cache[cmd]

  def get(self, command: str, max_age: Optional[int] = None) -> Optional[str]:
    """
    Get cached result for a command.

    Args:
      command (str): The command to get results for
      max_age (Optional[int]): Maximum age of cache in seconds

    Returns:
      Optional[str]: Cached command result or None if not cached
    """
    if command not in self._cache:
      return None

    cache_entry = self._cache[command]
    age = (datetime.now() - cache_entry.timestamp).total_seconds()

    if max_age and age > max_age:
      return None

    return cache_entry.data

  def get_with_timestamp(self, command: str, max_age: Optional[int] = None) -> Optional[tuple[Any, datetime]]:
    """
    Get cached result with its timestamp.

    Args:
      command (str): The command to get results for
      max_age (Optional[int]): Maximum age of cache in seconds

    Returns:
      Optional[tuple[Any, datetime]]: Tuple of (cached result, last_updated timestamp) or None if not cached
    """
    if command not in self._cache:
      return None

    cache_entry = self._cache[command]
    age = (datetime.now() - cache_entry.timestamp).total_seconds()

    if max_age and age > max_age:
      return None

    return (cache_entry.data, cache_entry.last_updated)

  def get_status(self) -> Dict[str, Any]:
    """
    Get status information about the cache.

    Returns:
      Dict[str, Any]: Cache statistics and status
    """
    return {
      "cached_commands": list(self._cache.keys()),
      "active_pollers": list(self._polling_threads.keys()),
      "cache_entries": {
        cmd: {
          "age": (datetime.now() - entry.timestamp).total_seconds(),
          "last_updated": entry.last_updated.isoformat(),
          "polling_interval": self._command_configs[cmd].polling_interval
        }
        for cmd, entry in self._cache.items()
      }
    }

  def is_cacheable(self, command: str) -> bool:
    """
    Check if a command is configured for caching.

    Args:
      command (str): The command to check

    Returns:
      bool: True if the command is configured for caching, False otherwise
    """
    return command in self._command_configs

  def set(self, command: str, entry: CacheEntry) -> None:
    """
    Set a cache entry for a command.

    Args:
      command (str): The command to cache
      entry (CacheEntry): The cache entry to store
    """
    self._cache[command] = entry
    if command not in self._polling_threads:
      self._start_polling(command)
