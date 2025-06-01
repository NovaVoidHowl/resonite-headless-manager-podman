#!/usr/bin/env python3
"""
Example usage of the Cache Manager for Resonite Headless Manager

This example demonstrates how to use the caching system to store and retrieve
data with timestamps, avoiding repeated requests to the command queue.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Dict

from cache_manager import CacheManager, get_global_cache, CacheStatus


def example_basic_usage():
  """Demonstrate basic cache operations."""
  print("=== Basic Cache Usage ===")

  # Get the global cache instance
  cache = get_global_cache()

  # Store some sample data
  user_data = {
      "users": [
          {"name": "Alice", "id": "U-alice123"},
          {"name": "Bob", "id": "U-bob456"}
      ],
      "total_count": 2
  }

  # Cache the data with a 30-second TTL
  success = cache.set(
      key="current_users",
      data=user_data,
      ttl=30,
      category="resonite_data",
      metadata={"source_command": "users", "world": "main"}
  )
  print(f"Data cached successfully: {success}")

  # Retrieve the data
  entry = cache.get("current_users")
  if entry:
    print(f"Retrieved data: {entry.data}")
    print(f"Data age: {entry.get_age_seconds():.1f} seconds")
    print(f"TTL remaining: {entry.get_remaining_ttl():.1f} seconds")
    print(f"Access count: {entry.access_count}")
    print(f"Category: {entry.category}")
    print(f"Metadata: {entry.metadata}")

  # Get just the data (convenience method)
  users = cache.get_data("current_users")
  print(f"User count from cache: {users['total_count'] if users else 'Not found'}")

  print()


def example_data_freshness():
  """Demonstrate data freshness and TTL handling."""
  print("=== Data Freshness Example ===")

  cache = get_global_cache()

  # Store data with a very short TTL for demonstration
  cache.set("temp_data", {"value": 42}, ttl=3)  # 3 seconds

  # Check freshness immediately
  entry = cache.get("temp_data")
  if entry:
    print(f"Fresh data: {entry.data} (status: {entry.status.value})")

  # Wait 2 seconds
  print("Waiting 2 seconds...")
  time.sleep(2)

  # Check again - should still be fresh
  entry = cache.get("temp_data")
  if entry:
    print(f"Still fresh: {entry.data} (age: {entry.get_age_seconds():.1f}s)")

  # Wait 2 more seconds (total 4 seconds, past TTL)
  print("Waiting 2 more seconds...")
  time.sleep(2)

  # Try to get fresh data only - should fail
  entry = cache.get("temp_data", include_stale=False)
  print(f"Fresh data available: {entry is not None}")

  # Try to get stale data - should succeed
  entry = cache.get("temp_data", include_stale=True)
  if entry:
    print(f"Stale data: {entry.data} (status: {entry.status.value}, age: {entry.get_age_seconds():.1f}s)")

  print()


def example_categories():
  """Demonstrate category-based cache management."""
  print("=== Category Management Example ===")

  cache = get_global_cache()

  # Store data in different categories
  cache.set("users", {"count": 5}, category="resonite_data")
  cache.set("worlds", {"active": 3}, category="resonite_data")
  cache.set("cpu_usage", {"percent": 25.5}, category="system_metrics")
  cache.set("memory_usage", {"percent": 60.2}, category="system_metrics")
  cache.set("session_123", {"user": "Alice"}, category="user_sessions")

  # Get keys by category
  resonite_keys = cache.get_keys(category="resonite_data")
  metrics_keys = cache.get_keys(category="system_metrics")

  print(f"Resonite data keys: {resonite_keys}")
  print(f"System metrics keys: {metrics_keys}")

  # Invalidate all resonite data
  invalidated = cache.invalidate_category("resonite_data")
  print(f"Invalidated {invalidated} resonite data entries")

  # Check if resonite data is still available
  users = cache.get_data("users")
  cpu = cache.get_data("cpu_usage")
  print(f"Users data after invalidation: {users}")
  print(f"CPU data after invalidation: {cpu}")

  # Clear specific category
  cleared = cache.clear(category="system_metrics")
  print(f"Cleared {cleared} system metrics entries")

  print()


def example_cache_statistics():
  """Demonstrate cache statistics and monitoring."""
  print("=== Cache Statistics Example ===")

  cache = get_global_cache()

  # Add some data and access it
  for i in range(5):
    cache.set(f"test_data_{i}", {"value": i * 10}, category="test_data")

  # Access some entries multiple times
  for _ in range(3):
    cache.get_data("test_data_1")
    cache.get_data("test_data_2")

  # Try to access non-existent data (cache misses)
  cache.get_data("nonexistent_1")
  cache.get_data("nonexistent_2")

  # Get statistics
  stats = cache.get_stats()

  print(f"Total entries: {stats.total_entries}")
  print(f"Fresh entries: {stats.fresh_entries}")
  print(f"Cache hits: {stats.total_hits}")
  print(f"Cache misses: {stats.total_misses}")
  print(f"Hit rate: {stats.get_hit_rate():.1f}%")
  print(f"Categories: {stats.categories}")
  print(f"Oldest entry age: {stats.oldest_entry_age:.1f}s")

  # Convert to dict for JSON serialization
  stats_dict = stats.to_dict()
  print("Stats as JSON:")
  print(json.dumps(stats_dict, indent=2))

  print()


def example_resonite_integration():
  """Demonstrate integration with Resonite command patterns."""
  print("=== Resonite Integration Example ===")

  cache = get_global_cache()

  # Simulate caching results from common Resonite commands

  # Users command result
  users_data = {
      "users": [
          {
              "username": "Alice",
              "userId": "U-alice123",
              "ping": 45,
              "fps": 90
          },
          {
              "username": "Bob",
              "userId": "U-bob456",
              "ping": 67,
              "fps": 72
          }
      ],
      "total": 2
  }

  cache.set(
      key="resonite_users",
      data=users_data,
      ttl=120,  # 2 minutes for user data
      category="resonite_data",
      metadata={
          "command": "users",
          "container": "resonite-headless-1"
      }
  )

  # Worlds command result
  worlds_data = {
      "worlds": [
          {
              "index": 0,
              "name": "Main World",
              "users": 2,
              "status": "running"
          }
      ],
      "active_worlds": 1
  }

  cache.set(
      key="resonite_worlds",
      data=worlds_data,
      ttl=180,  # 3 minutes for world data
      category="resonite_data",
      metadata={
          "command": "worlds",
          "container": "resonite-headless-1"
      }
  )

  # Container status
  status_data = {
      "status": "running",
      "uptime": "2h 15m",
      "memory_usage": "2.1GB",
      "cpu_usage": "15.5%"
  }

  cache.set(
      key="container_status",
      data=status_data,
      ttl=60,  # 1 minute for status data
      category="container_info",
      metadata={
          "source": "podman_interface",
          "container": "resonite-headless-1"
      }
  )

  # Simulate a web request checking for cached data
  print("Simulating web request for user data...")

  def get_users_data(force_refresh=False):
    if not force_refresh:
      # Try cache first
      cached_users = cache.get("resonite_users", include_stale=True)
      if cached_users:
        return {
            "data": cached_users.data,
            "cached": True,
            "age_seconds": cached_users.get_age_seconds(),
            "is_fresh": cached_users.is_fresh()
        }

    # Would normally execute command here
    print("Would execute 'users' command via queue...")
    return {"data": None, "cached": False}

  # Get cached data
  result = get_users_data()
  if result["cached"]:
    print(f"Using cached user data (age: {result['age_seconds']:.1f}s, fresh: {result['is_fresh']})")
    print(f"User count: {result['data']['total']}")

  # Show all resonite data
  resonite_entries = cache.get_all_entries(category="resonite_data")
  print(f"\nAll cached Resonite data ({len(resonite_entries)} entries):")
  for key, entry in resonite_entries.items():
    print(f"  {key}: {entry.get_age_seconds():.1f}s old, {len(str(entry.data))} chars")

  print()


async def example_async_usage():
  """Demonstrate async-compatible usage patterns."""
  print("=== Async Usage Example ===")

  cache = get_global_cache()

  # Simulate async data fetching and caching
  async def fetch_and_cache_user_data():
    # Simulate async command execution
    await asyncio.sleep(0.1)  # Simulate command delay

    user_data = {"users": ["Alice", "Bob"], "count": 2}
    cache.set("async_users", user_data, ttl=60)
    return user_data

  async def get_user_data_with_cache():
    # Check cache first
    cached_data = cache.get_data("async_users")
    if cached_data:
      print("Returning cached user data")
      return cached_data

    print("Cache miss - fetching fresh data")
    return await fetch_and_cache_user_data()

  # First call - cache miss
  data1 = await get_user_data_with_cache()
  print(f"First call result: {data1}")

  # Second call - cache hit
  data2 = await get_user_data_with_cache()
  print(f"Second call result: {data2}")

  print()


def example_cleanup_and_memory():
  """Demonstrate cleanup and memory management."""
  print("=== Cleanup and Memory Management ===")

  # Create a cache with small limits for demonstration
  cache = CacheManager(
      default_ttl=5,      # 5 seconds
      max_entries=3,      # Only 3 entries max
      cleanup_interval=2  # Cleanup every 2 seconds
  )

  # Add more entries than the limit
  for i in range(5):
    cache.set(f"item_{i}", {"value": i})
    time.sleep(0.1)  # Small delay to ensure different timestamps

  print(f"Added 5 items, cache has {cache.get_stats().total_entries} entries")

  # Show which items remain (oldest should be evicted)
  all_keys = cache.get_keys()
  print(f"Remaining keys: {all_keys}")

  # Wait for TTL to expire
  print("Waiting 6 seconds for TTL expiration...")
  time.sleep(6)

  # Manual cleanup
  cleaned = cache.cleanup()
  print(f"Manually cleaned up {cleaned} expired entries")
  print(f"Cache now has {cache.get_stats().total_entries} entries")

  # Cleanup
  cache.shutdown()
  print()


def main():
  """Run all examples."""
  print("Cache Manager Examples")
  print("=" * 50)

  try:
    example_basic_usage()
    example_data_freshness()
    example_categories()
    example_cache_statistics()
    example_resonite_integration()

    # Run async example
    asyncio.run(example_async_usage())

    example_cleanup_and_memory()

  except KeyboardInterrupt:
    print("\nExamples interrupted by user")
  finally:
    # Clean up global cache
    from cache_manager import cleanup_global_cache
    cleanup_global_cache()
    print("Cleaned up global cache")


if __name__ == "__main__":
  main()
