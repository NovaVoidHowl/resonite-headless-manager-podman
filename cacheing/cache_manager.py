"""
Data Caching System for Resonite Headless Manager

This module provides a thread-safe caching system for storing data with timestamps
to avoid repeated requests to the command queue. It stores data alongside metadata
about when it was received, allowing other modules to determine data freshness.

Key Features:
- Thread-safe cache operations
- TTL (Time To Live) support for automatic cache expiration
- Data freshness tracking with timestamps
- Flexible data storage (any JSON-serializable data)
- Cache statistics and monitoring
- Cleanup of expired entries
- Multiple cache categories/namespaces
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# Configure logging
logger = logging.getLogger(__name__)


class CacheStatus(Enum):
  """Status of cached data."""
  FRESH = "fresh"        # Within TTL and valid
  STALE = "stale"        # Past TTL but still usable
  EXPIRED = "expired"    # Should be refreshed
  INVALID = "invalid"    # Marked as invalid


@dataclass
class CacheEntry:
  """Represents a single cached data entry."""
  data: Any
  timestamp: datetime
  ttl_seconds: int = 300  # Default 5 minutes
  category: str = "default"
  metadata: Dict[str, Any] = field(default_factory=dict)

  # Internal tracking
  access_count: int = 0
  last_accessed: datetime = field(default_factory=datetime.now)
  status: CacheStatus = CacheStatus.FRESH

  def __post_init__(self):
    """Validate cache entry after initialization."""
    if self.ttl_seconds <= 0:
      raise ValueError("TTL must be positive")
    if not self.category:
      raise ValueError("Category cannot be empty")

  def is_fresh(self) -> bool:
    """Check if the cached data is still fresh (within TTL)."""
    if self.status == CacheStatus.INVALID:
      return False

    age = datetime.now() - self.timestamp
    return age.total_seconds() < self.ttl_seconds

  def is_expired(self) -> bool:
    """Check if the cached data has expired."""
    if self.status == CacheStatus.INVALID:
      return True

    age = datetime.now() - self.timestamp
    # Consider expired if older than 2x TTL
    return age.total_seconds() > (self.ttl_seconds * 2)

  def get_age_seconds(self) -> float:
    """Get the age of the cached data in seconds."""
    return (datetime.now() - self.timestamp).total_seconds()

  def get_remaining_ttl(self) -> float:
    """Get remaining TTL in seconds (can be negative if stale)."""
    return self.ttl_seconds - self.get_age_seconds()

  def mark_accessed(self) -> None:
    """Mark this entry as accessed (updates access tracking)."""
    self.access_count += 1
    self.last_accessed = datetime.now()

  def invalidate(self) -> None:
    """Mark this entry as invalid."""
    self.status = CacheStatus.INVALID

  def to_dict(self) -> Dict[str, Any]:
    """Convert cache entry to dictionary format."""
    return {
        'data': self.data,
        'timestamp': self.timestamp.isoformat(),
        'ttl_seconds': self.ttl_seconds,
        'category': self.category,
        'metadata': self.metadata,
        'access_count': self.access_count,
        'last_accessed': self.last_accessed.isoformat(),
        'status': self.status.value,
        'age_seconds': self.get_age_seconds(),
        'remaining_ttl': self.get_remaining_ttl(),
        'is_fresh': self.is_fresh(),
        'is_expired': self.is_expired()
    }


@dataclass
class CacheStats:
  """Statistics about cache usage."""
  total_entries: int = 0
  fresh_entries: int = 0
  stale_entries: int = 0
  expired_entries: int = 0
  invalid_entries: int = 0
  total_hits: int = 0
  total_misses: int = 0
  total_sets: int = 0
  total_invalidations: int = 0
  total_cleanups: int = 0
  categories: Dict[str, int] = field(default_factory=dict)
  oldest_entry_age: float = 0.0
  newest_entry_age: float = 0.0

  def get_hit_rate(self) -> float:
    """Calculate cache hit rate."""
    total_requests = self.total_hits + self.total_misses
    if total_requests == 0:
      return 0.0
    return (self.total_hits / total_requests) * 100

  def to_dict(self) -> Dict[str, Any]:
    """Convert stats to dictionary format."""
    return {
        'total_entries': self.total_entries,
        'fresh_entries': self.fresh_entries,
        'stale_entries': self.stale_entries,
        'expired_entries': self.expired_entries,
        'invalid_entries': self.invalid_entries,
        'total_hits': self.total_hits,
        'total_misses': self.total_misses,
        'total_sets': self.total_sets,
        'total_invalidations': self.total_invalidations,
        'total_cleanups': self.total_cleanups,
        'hit_rate_percent': self.get_hit_rate(),
        'categories': dict(self.categories),
        'oldest_entry_age_seconds': self.oldest_entry_age,
        'newest_entry_age_seconds': self.newest_entry_age
    }


class CacheManager:
  """
  Thread-safe cache manager for storing data with timestamps.

  This class provides caching functionality without concern for how data
  is obtained - it simply stores and retrieves data with timing information.
  """

  def __init__(self,
               default_ttl: int = 300,
               max_entries: int = 1000,
               cleanup_interval: int = 60):
    """
    Initialize the cache manager.

    Args:
        default_ttl: Default time-to-live in seconds
        max_entries: Maximum number of cache entries
        cleanup_interval: Interval in seconds for automatic cleanup
    """
    self.default_ttl = default_ttl
    self.max_entries = max_entries
    self.cleanup_interval = cleanup_interval

    # Cache storage: {key: CacheEntry}
    self._cache: Dict[str, CacheEntry] = {}
    self._cache_lock = threading.RLock()

    # Statistics tracking
    self._stats = CacheStats()
    self._stats_lock = threading.RLock()

    # Cleanup thread management
    self._cleanup_thread: Optional[threading.Thread] = None
    self._shutdown_requested = False

    # Start automatic cleanup
    self._start_cleanup_thread()

    logger.info("CacheManager initialized (TTL: %ds, Max entries: %d)",
                default_ttl, max_entries)

  def set(self,
          key: str,
          data: Any,
          ttl: Optional[int] = None,
          category: str = "default",
          metadata: Optional[Dict[str, Any]] = None) -> bool:
    """
    Store data in the cache.

    Args:
        key: Unique identifier for the cached data
        data: Data to cache (must be JSON-serializable)
        ttl: Time-to-live in seconds (uses default if None)
        category: Category/namespace for the data
        metadata: Optional metadata to store with the data

    Returns:
        bool: True if data was successfully cached
    """
    if not key:
      logger.warning("Cannot cache data with empty key")
      return False

    # Validate data is JSON serializable
    try:
      json.dumps(data)
    except (TypeError, ValueError) as e:
      logger.error("Data for key '%s' is not JSON serializable: %s", key, str(e))
      return False

    effective_ttl = ttl if ttl is not None else self.default_ttl
    effective_metadata = metadata or {}

    # Create cache entry
    entry = CacheEntry(
        data=data,
        timestamp=datetime.now(),
        ttl_seconds=effective_ttl,
        category=category,
        metadata=effective_metadata
    )

    with self._cache_lock:
      # Check if we need to make room
      if len(self._cache) >= self.max_entries and key not in self._cache:
        self._evict_oldest_entry()

      # Store the entry
      self._cache[key] = entry

      logger.debug("Cached data for key '%s' (TTL: %ds, Category: %s)",
                   key, effective_ttl, category)

    # Update statistics
    with self._stats_lock:
      self._stats.total_sets += 1
      self._stats.categories[category] = self._stats.categories.get(category, 0) + 1

    return True

  def get(self, key: str, include_stale: bool = False) -> Optional[CacheEntry]:
    """
    Retrieve data from the cache.

    Args:
        key: Key to look up
        include_stale: Whether to return stale data (past TTL but not expired)

    Returns:
        CacheEntry if found and valid, None otherwise
    """
    if not key:
      return None

    with self._cache_lock:
      entry = self._cache.get(key)
      if entry is None:
        with self._stats_lock:
          self._stats.total_misses += 1
        return None

      # Mark as accessed
      entry.mark_accessed()

      # Check if data is usable
      if entry.is_expired():
        logger.debug("Cache entry for key '%s' is expired", key)
        with self._stats_lock:
          self._stats.total_misses += 1
        return None

      if not entry.is_fresh() and not include_stale:
        logger.debug("Cache entry for key '%s' is stale (not including stale)", key)
        with self._stats_lock:
          self._stats.total_misses += 1
        return None

      # Update entry status
      if entry.is_fresh():
        entry.status = CacheStatus.FRESH
      else:
        entry.status = CacheStatus.STALE

      with self._stats_lock:
        self._stats.total_hits += 1

      logger.debug("Cache hit for key '%s' (age: %.1fs, status: %s)",
                   key, entry.get_age_seconds(), entry.status.value)

      return entry

  def get_data(self, key: str, include_stale: bool = False) -> Optional[Any]:
    """
    Convenience method to get just the data (not the full entry).

    Args:
        key: Key to look up
        include_stale: Whether to return stale data

    Returns:
        The cached data if found and valid, None otherwise
    """
    entry = self.get(key, include_stale)
    return entry.data if entry else None

  def has_key(self, key: str, fresh_only: bool = True) -> bool:
    """
    Check if a key exists in the cache.

    Args:
        key: Key to check
        fresh_only: Only consider fresh (non-stale) entries

    Returns:
        bool: True if key exists and meets freshness criteria
    """
    entry = self.get(key, include_stale=not fresh_only)
    return entry is not None

  def invalidate(self, key: str) -> bool:
    """
    Invalidate a specific cache entry.

    Args:
        key: Key to invalidate

    Returns:
        bool: True if key was found and invalidated
    """
    with self._cache_lock:
      entry = self._cache.get(key)
      if entry:
        entry.invalidate()
        logger.debug("Invalidated cache entry for key '%s'", key)

        with self._stats_lock:
          self._stats.total_invalidations += 1
        return True

    return False

  def invalidate_category(self, category: str) -> int:
    """
    Invalidate all entries in a specific category.

    Args:
        category: Category to invalidate

    Returns:
        int: Number of entries invalidated
    """
    count = 0
    with self._cache_lock:
      for entry in self._cache.values():
        if entry.category == category:
          entry.invalidate()
          count += 1

    if count > 0:
      logger.info("Invalidated %d cache entries in category '%s'", count, category)
      with self._stats_lock:
        self._stats.total_invalidations += count

    return count

  def delete(self, key: str) -> bool:
    """
    Remove a cache entry completely.

    Args:
        key: Key to remove

    Returns:
        bool: True if key was found and removed
    """
    with self._cache_lock:
      if key in self._cache:
        del self._cache[key]
        logger.debug("Deleted cache entry for key '%s'", key)
        return True

    return False

  def clear(self, category: Optional[str] = None) -> int:
    """
    Clear cache entries.

    Args:
        category: If specified, only clear entries in this category

    Returns:
        int: Number of entries cleared
    """
    count = 0
    with self._cache_lock:
      if category is None:
        count = len(self._cache)
        self._cache.clear()
        logger.info("Cleared all %d cache entries", count)
      else:
        keys_to_remove = [
            key for key, entry in self._cache.items()
            if entry.category == category
        ]
        for key in keys_to_remove:
          del self._cache[key]
          count += 1
        logger.info("Cleared %d cache entries in category '%s'", count, category)

    return count

  def cleanup(self) -> int:
    """
    Remove expired and invalid entries.

    Returns:
        int: Number of entries cleaned up
    """
    count = 0
    with self._cache_lock:
      keys_to_remove = [
          key for key, entry in self._cache.items()
          if entry.is_expired() or entry.status == CacheStatus.INVALID
      ]

      for key in keys_to_remove:
        del self._cache[key]
        count += 1

    if count > 0:
      logger.debug("Cleaned up %d expired/invalid cache entries", count)
      with self._stats_lock:
        self._stats.total_cleanups += count

    return count

  def get_stats(self) -> CacheStats:
    """
    Get current cache statistics.

    Returns:
        CacheStats: Current cache statistics
    """
    with self._cache_lock, self._stats_lock:
      # Update current counts
      self._stats.total_entries = len(self._cache)
      self._stats.fresh_entries = 0
      self._stats.stale_entries = 0
      self._stats.expired_entries = 0
      self._stats.invalid_entries = 0

      ages = []
      for entry in self._cache.values():
        age = entry.get_age_seconds()
        ages.append(age)

        if entry.status == CacheStatus.INVALID:
          self._stats.invalid_entries += 1
        elif entry.is_expired():
          self._stats.expired_entries += 1
        elif entry.is_fresh():
          self._stats.fresh_entries += 1
        else:
          self._stats.stale_entries += 1

      if ages:
        self._stats.oldest_entry_age = max(ages)
        self._stats.newest_entry_age = min(ages)
      else:
        self._stats.oldest_entry_age = 0.0
        self._stats.newest_entry_age = 0.0

      # Return a copy of the stats
      return CacheStats(
          total_entries=self._stats.total_entries,
          fresh_entries=self._stats.fresh_entries,
          stale_entries=self._stats.stale_entries,
          expired_entries=self._stats.expired_entries,
          invalid_entries=self._stats.invalid_entries,
          total_hits=self._stats.total_hits,
          total_misses=self._stats.total_misses,
          total_sets=self._stats.total_sets,
          total_invalidations=self._stats.total_invalidations,
          total_cleanups=self._stats.total_cleanups,
          categories=dict(self._stats.categories),
          oldest_entry_age=self._stats.oldest_entry_age,
          newest_entry_age=self._stats.newest_entry_age
      )

  def get_keys(self, category: Optional[str] = None) -> List[str]:
    """
    Get all cache keys, optionally filtered by category.

    Args:
        category: If specified, only return keys in this category

    Returns:
        List[str]: List of cache keys
    """
    with self._cache_lock:
      if category is None:
        return list(self._cache.keys())
      else:
        return [
            key for key, entry in self._cache.items()
            if entry.category == category
        ]

  def get_all_entries(self, category: Optional[str] = None) -> Dict[str, CacheEntry]:
    """
    Get all cache entries, optionally filtered by category.

    Args:
        category: If specified, only return entries in this category

    Returns:
        Dict[str, CacheEntry]: Dictionary of cache entries
    """
    with self._cache_lock:
      if category is None:
        return dict(self._cache)
      else:
        return {
            key: entry for key, entry in self._cache.items()
            if entry.category == category
        }

  def _evict_oldest_entry(self) -> None:
    """Remove the oldest cache entry to make room for new ones."""
    if not self._cache:
      return    # Find the oldest entry by timestamp
    oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].timestamp)
    del self._cache[oldest_key]
    logger.debug("Evicted oldest cache entry: %s", oldest_key)

  def _start_cleanup_thread(self) -> None:
    """Start the background cleanup thread."""
    def cleanup_worker():
      logger.info("Cache cleanup thread started (interval: %ds)", self.cleanup_interval)

      while not self._shutdown_requested:
        time.sleep(self.cleanup_interval)
        if not self._shutdown_requested:
          try:
            self.cleanup()
          except (RuntimeError, KeyError, ValueError, AttributeError) as e:
            logger.error("Error during cache cleanup: %s", str(e))
          except Exception as e:  # pylint: disable=broad-exception-caught
            # Catch any other unexpected exceptions to prevent cleanup thread from dying
            logger.error("Unexpected error during cache cleanup: %s", str(e))

      logger.info("Cache cleanup thread stopped")

    self._cleanup_thread = threading.Thread(
        target=cleanup_worker,
        daemon=True,
        name="cache_cleanup"
    )
    self._cleanup_thread.start()

  def shutdown(self) -> None:
    """
    Gracefully shutdown the cache manager.
    """
    logger.info("Shutting down cache manager...")
    self._shutdown_requested = True

    # Wait for cleanup thread to finish
    if self._cleanup_thread and self._cleanup_thread.is_alive():
      self._cleanup_thread.join(timeout=5)

    # Clear all cache
    self.clear()

    logger.info("Cache manager shutdown complete")


# Global cache manager instance
_global_cache: Optional[CacheManager] = None
_global_cache_lock = threading.Lock()


def get_global_cache() -> CacheManager:
  """
  Get or create the global cache manager instance.

  Returns:
      CacheManager: The global cache manager
  """
  global _global_cache

  if _global_cache is None:
    with _global_cache_lock:
      if _global_cache is None:
        _global_cache = CacheManager()

  return _global_cache


def cleanup_global_cache() -> None:
  """Clean up the global cache manager."""
  global _global_cache

  if _global_cache is not None:
    with _global_cache_lock:
      if _global_cache is not None:
        _global_cache.shutdown()
        _global_cache = None
