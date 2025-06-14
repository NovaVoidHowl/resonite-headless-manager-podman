"""
Comprehensive Cache Manager Test Suite

This script provides thorough testing of the cache manager functionality,
including data storage, retrieval, TTL handling, categories, statistics,
cleanup, and thread safety. Uses mock data to test all cache operations
without requiring external dependencies.
"""

import asyncio
import json
import logging
import random
import threading
import time
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add the parent directories to the path to import modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "cacheing"))

try:
  from cache_manager import (  # pylint: disable=import-error
      CacheManager,
      get_global_cache,
      cleanup_global_cache,
      CacheStatus
  )
except ImportError as e:
  print(f"Import error: {e}")
  print("Make sure you're running this script from the correct directory")
  sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockDataGenerator:
  """
  Mock data generator for testing cache operations.

  Generates realistic test data for various cache scenarios.
  """

  def __init__(self):
    """Initialize the mock data generator."""
    self.users = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    self.worlds = ["Main Hall", "Workshop", "Lobby", "Testing Area", "Private Room"]
    self.commands = ["users", "worlds", "status", "bans", "focus", "restart"]

  def generate_user_data(self, count: int = None) -> Dict[str, Any]:
    """Generate mock user data."""
    if count is None:
      count = random.randint(1, len(self.users))

    selected_users = random.sample(self.users, min(count, len(self.users)))
    return {
        "users": [
            {
                "name": user,
                "id": f"U-{user.lower()}{random.randint(100, 999)}",
                "ping": random.randint(20, 150),
                "fps": random.randint(60, 120)
            }
            for user in selected_users
        ],
        "total_count": len(selected_users),
        "timestamp": datetime.now().isoformat()
    }

  def generate_world_data(self) -> Dict[str, Any]:
    """Generate mock world data."""
    worlds = []
    for i, world_name in enumerate(self.worlds[:random.randint(1, 3)]):
      worlds.append({
          "index": i,
          "name": world_name,
          "users": random.randint(0, 8),
          "status": random.choice(["running", "starting", "idle"])
      })

    return {
        "worlds": worlds,
        "active_worlds": len(worlds),
        "total_users": sum(w["users"] for w in worlds)
    }

  def generate_status_data(self) -> Dict[str, Any]:
    """Generate mock status data."""
    return {
        "status": random.choice(["running", "starting", "stopping"]),
        "uptime": f"{random.randint(0, 48)}h {random.randint(0, 59)}m",
        "memory_usage": f"{random.uniform(1.0, 4.0):.1f}GB",
        "cpu_usage": f"{random.uniform(5.0, 50.0):.1f}%",
        "container_id": f"resonite-{random.randint(1, 5)}"
    }

  def generate_metrics_data(self) -> Dict[str, Any]:
    """Generate mock system metrics."""
    return {
        "cpu_percent": random.uniform(10.0, 80.0),
        "memory_percent": random.uniform(30.0, 90.0),
        "disk_usage": random.uniform(20.0, 95.0),
        "network_rx": random.randint(1000, 50000),
        "network_tx": random.randint(500, 25000)
    }


# Global mock data generator
mock_data = MockDataGenerator()


def test_basic_operations():
  """Test basic cache operations (set, get, delete)."""
  print("\n=== Basic Operations Test ===")

  # Create a dedicated cache for this test
  cache = CacheManager(default_ttl=60, max_entries=100)

  try:
    # Test data storage
    user_data = mock_data.generate_user_data(3)
    success = cache.set("test_users", user_data, ttl=30, category="test_data")
    assert success, "Failed to store user data"
    print("✓ Data storage successful")

    # Test data retrieval
    entry = cache.get("test_users")
    assert entry is not None, "Failed to retrieve stored data"
    assert entry.data == user_data, "Retrieved data doesn't match stored data"
    assert entry.category == "test_data", "Category doesn't match"
    print("✓ Data retrieval successful")

    # Test data existence check
    assert cache.has_key("test_users"), "Key should exist"
    assert not cache.has_key("nonexistent"), "Nonexistent key should not exist"
    print("✓ Key existence checks successful")

    # Test convenience method
    retrieved_data = cache.get_data("test_users")
    assert retrieved_data == user_data, "Convenience method failed"
    print("✓ Convenience method works")

    # Test data deletion
    success = cache.delete("test_users")
    assert success, "Failed to delete data"
    assert not cache.has_key("test_users"), "Key should not exist after deletion"
    print("✓ Data deletion successful")

    # Test invalid operations
    assert not cache.set("", {"data": "test"}), "Empty key should fail"
    assert not cache.set("key", lambda x: x), "Non-serializable data should fail"
    print("✓ Invalid operations properly rejected")

  finally:
    cache.shutdown()


def test_ttl_and_freshness():
  """Test TTL handling and data freshness."""
  print("\n=== TTL and Freshness Test ===")

  cache = CacheManager(default_ttl=2, cleanup_interval=1)  # Short TTL for testing

  try:
    # Store data with short TTL
    test_data = {"message": "test", "timestamp": time.time()}
    cache.set("fresh_test", test_data, ttl=2)

    # Immediately check - should be fresh
    entry = cache.get("fresh_test")
    assert entry is not None, "Fresh data should be available"
    assert entry.is_fresh(), "Data should be fresh"
    assert entry.status == CacheStatus.FRESH, "Status should be FRESH"
    print("✓ Fresh data retrieval works")

    # Wait until stale
    print("Waiting for data to become stale...")
    time.sleep(2.5)

    # Check stale data
    entry = cache.get("fresh_test", include_stale=True)
    assert entry is not None, "Stale data should be available with include_stale=True"
    assert not entry.is_fresh(), "Data should not be fresh"
    assert entry.status == CacheStatus.STALE, "Status should be STALE"
    print("✓ Stale data handling works")

    # Check fresh-only retrieval
    entry = cache.get("fresh_test", include_stale=False)
    assert entry is None, "Stale data should not be available with include_stale=False"
    print("✓ Fresh-only retrieval works")

    # Wait until expired
    print("Waiting for data to expire...")
    time.sleep(3)

    # Check expired data
    entry = cache.get("fresh_test", include_stale=True)
    assert entry is None, "Expired data should not be available"
    print("✓ Expired data handling works")

    # Test TTL calculations
    cache.set("ttl_test", {"data": "test"}, ttl=10)
    entry = cache.get("ttl_test")
    assert entry.get_remaining_ttl() > 8, "TTL calculation incorrect"
    assert entry.get_age_seconds() < 2, "Age calculation incorrect"
    print("✓ TTL calculations work")

  finally:
    cache.shutdown()


def test_categories():
  """Test category-based cache management."""
  print("\n=== Categories Test ===")

  cache = CacheManager(default_ttl=300)

  try:
    # Store data in different categories
    cache.set("users", mock_data.generate_user_data(), category="resonite_data")
    cache.set("worlds", mock_data.generate_world_data(), category="resonite_data")
    cache.set("status", mock_data.generate_status_data(), category="container_info")
    cache.set("metrics", mock_data.generate_metrics_data(), category="system_metrics")
    cache.set("temp1", {"data": "temp"}, category="temp_data")
    cache.set("temp2", {"data": "temp"}, category="temp_data")

    # Test category key listing
    resonite_keys = cache.get_keys(category="resonite_data")
    assert len(resonite_keys) == 2, f"Expected 2 resonite keys, got {len(resonite_keys)}"
    assert "users" in resonite_keys and "worlds" in resonite_keys, "Wrong resonite keys"
    print("✓ Category key listing works")

    temp_keys = cache.get_keys(category="temp_data")
    assert len(temp_keys) == 2, f"Expected 2 temp keys, got {len(temp_keys)}"
    print("✓ Multiple entries per category work")

    # Test category entry retrieval
    resonite_entries = cache.get_all_entries(category="resonite_data")
    assert len(resonite_entries) == 2, "Wrong number of resonite entries"
    print("✓ Category entry retrieval works")        # Test category invalidation
    invalidated = cache.invalidate_category("resonite_data")
    assert invalidated == 2, f"Expected to invalidate 2 entries, got {invalidated}"

    # Check that invalidated entries are not fresh
    entry = cache.get("users")
    assert entry is None, "Invalidated entry should not be retrievable"

    # Invalidated entries are considered expired, so they're not available even with include_stale=True
    # This is the correct behavior - invalidated data should not be used
    print("✓ Category invalidation works")

    # Test category clearing
    cleared = cache.clear(category="temp_data")
    assert cleared == 2, f"Expected to clear 2 entries, got {cleared}"
    assert len(cache.get_keys(category="temp_data")) == 0, "Temp category should be empty"
    print("✓ Category clearing works")

    # Test that other categories are unaffected
    assert cache.get_data("status") is not None, "Other categories should be unaffected"
    assert cache.get_data("metrics") is not None, "Other categories should be unaffected"
    print("✓ Category isolation works")

  finally:
    cache.shutdown()


def test_statistics():
  """Test cache statistics and monitoring."""
  print("\n=== Statistics Test ===")

  cache = CacheManager(default_ttl=60)

  try:
    # Add some data
    for i in range(5):
      cache.set(f"item_{i}", {"value": i}, category="test_stats")

    # Access some entries multiple times
    for _ in range(3):
      cache.get_data("item_1")
      cache.get_data("item_2")

    # Try to access non-existent data (cache misses)
    cache.get_data("nonexistent_1")
    cache.get_data("nonexistent_2")

    # Invalidate some entries
    cache.invalidate("item_3")
    cache.invalidate("item_4")

    # Get statistics
    stats = cache.get_stats()

    # Verify statistics
    assert stats.total_entries == 5, f"Expected 5 entries, got {stats.total_entries}"
    assert stats.fresh_entries == 3, f"Expected 3 fresh entries, got {stats.fresh_entries}"
    assert stats.invalid_entries == 2, f"Expected 2 invalid entries, got {stats.invalid_entries}"
    assert stats.total_hits >= 6, f"Expected at least 6 hits, got {stats.total_hits}"
    assert stats.total_misses >= 2, f"Expected at least 2 misses, got {stats.total_misses}"
    assert stats.total_sets == 5, f"Expected 5 sets, got {stats.total_sets}"
    assert stats.total_invalidations == 2, f"Expected 2 invalidations, got {stats.total_invalidations}"

    print(f"✓ Statistics tracking works (Hit rate: {stats.get_hit_rate():.1f}%)")

    # Test category statistics
    assert "test_stats" in stats.categories, "Category should be in stats"
    assert stats.categories["test_stats"] == 5, "Category count should be 5"
    print("✓ Category statistics work")

    # Test statistics serialization
    stats_dict = stats.to_dict()
    assert isinstance(stats_dict, dict), "Stats should convert to dict"
    assert "hit_rate_percent" in stats_dict, "Hit rate should be in dict"
    json_str = json.dumps(stats_dict, indent=2)
    assert len(json_str) > 100, "JSON should be substantial"
    print("✓ Statistics serialization works")

  finally:
    cache.shutdown()


def test_cleanup_and_memory():
  """Test cleanup and memory management."""
  print("\n=== Cleanup and Memory Test ===")

  # Create cache with small limits for testing
  cache = CacheManager(default_ttl=1, max_entries=3, cleanup_interval=0.5)

  try:
    # Fill beyond capacity
    for i in range(5):
      cache.set(f"item_{i}", {"value": i})
      time.sleep(0.1)  # Small delay for different timestamps

    stats = cache.get_stats()
    assert stats.total_entries <= 3, f"Cache should have max 3 entries, has {stats.total_entries}"
    print("✓ Maximum entries limit enforced")

    # Check which items remain (should be most recent)
    remaining_keys = cache.get_keys()
    assert len(remaining_keys) <= 3, "Should have at most 3 keys"
    print(f"✓ LRU eviction works (remaining keys: {remaining_keys})")

    # Wait for data to expire
    print("Waiting for data to expire...")
    time.sleep(2.5)

    # Manual cleanup
    cleaned = cache.cleanup()
    print(f"✓ Manual cleanup removed {cleaned} entries")

    # Check final state
    final_stats = cache.get_stats()
    assert final_stats.total_entries == 0, "All entries should be cleaned up"
    print("✓ All expired entries cleaned up")

    # Test automatic cleanup (add data and wait)
    cache.set("auto_cleanup", {"test": "data"}, ttl=1)
    time.sleep(2)  # Wait for automatic cleanup

    # The cleanup thread should have removed the expired entry
    assert cache.get_data("auto_cleanup") is None, "Automatic cleanup should have worked"
    print("✓ Automatic cleanup works")

  finally:
    cache.shutdown()


def _perform_cache_operations(cache, thread_id: int, operation_count: int, results: list):
  """Perform cache operations for a single thread."""
  for i in range(operation_count):
    key = f"thread_{thread_id}_item_{i}"
    data = {
        "thread_id": thread_id,
        "item_id": i,
        "timestamp": time.time(),
        "data": f"test_data_{thread_id}_{i}"
    }

    # Store data
    success = cache.set(key, data, category=f"thread_{thread_id}")
    if success:
      results.append(f"SET:{thread_id}:{i}")

    # Retrieve data
    retrieved = cache.get_data(key)
    if retrieved and retrieved["thread_id"] == thread_id:
      results.append(f"GET:{thread_id}:{i}")

    # Small random delay
    time.sleep(random.uniform(0.001, 0.005))


def _create_worker_thread(cache, thread_id: int, operation_count: int, results: list, errors: list):
  """Create a worker thread that performs cache operations."""
  def worker_thread():
    """Worker thread that performs cache operations."""
    try:
      _perform_cache_operations(cache, thread_id, operation_count, results)
    except (ValueError, TypeError, KeyError, RuntimeError) as e:
      errors.append(f"Thread {thread_id}: {str(e)}")
    except Exception as e:  # pylint: disable=broad-exception-caught
      # In thread safety tests, we need to catch all exceptions to avoid breaking the test
      errors.append(f"Thread {thread_id}: Unexpected error: {str(e)}")

  return threading.Thread(target=worker_thread)


def _validate_thread_results(results: list, errors: list, thread_count: int, operations_per_thread: int, cache):
  """Validate the results of thread safety testing."""
  # Check for errors
  assert len(errors) == 0, f"Errors occurred: {errors}"

  # Check operation count
  expected_operations = thread_count * operations_per_thread * 2  # SET + GET
  assert len(results) == expected_operations, f"Expected {expected_operations} operations, got {len(results)}"

  # Check final cache state
  stats = cache.get_stats()
  assert stats.total_entries == thread_count * operations_per_thread, "Wrong number of entries"
  assert stats.total_sets == thread_count * operations_per_thread, "Wrong number of sets"

  print(f"✓ Thread safety test passed ({len(results)} operations, {stats.total_entries} entries)")


def _validate_category_separation(cache, thread_count: int, operations_per_thread: int):
  """Validate that thread operations are properly separated by category."""
  for thread_id in range(thread_count):
    category_keys = cache.get_keys(category=f"thread_{thread_id}")
    assert len(category_keys) == operations_per_thread, f"Thread {thread_id} should have {operations_per_thread} keys"

  print("✓ Thread-safe category operations work")


def test_thread_safety():
  """Test thread safety of cache operations."""
  print("\n=== Thread Safety Test ===")

  cache = CacheManager(default_ttl=60, max_entries=100)
  results = []
  errors = []

  try:
    # Configuration
    thread_count = 5
    operations_per_thread = 10

    # Create and start threads
    threads = []
    for thread_id in range(thread_count):
      thread = _create_worker_thread(cache, thread_id, operations_per_thread, results, errors)
      threads.append(thread)
      thread.start()

    # Wait for completion
    for thread in threads:
      thread.join()

    # Validate results
    _validate_thread_results(results, errors, thread_count, operations_per_thread, cache)
    _validate_category_separation(cache, thread_count, operations_per_thread)

  finally:
    cache.shutdown()


def test_resonite_integration():
  """Test realistic Resonite integration scenarios."""
  print("\n=== Resonite Integration Test ===")

  cache = CacheManager(default_ttl=120)

  try:
    # Simulate caching results from common Resonite commands

    # Users command result
    users_data = mock_data.generate_user_data(4)
    cache.set(
        key="resonite_users",
        data=users_data,
        ttl=120,
        category="resonite_data",
        metadata={"command": "users", "container": "resonite-headless-1"}
    )

    # Worlds command result
    worlds_data = mock_data.generate_world_data()
    cache.set(
        key="resonite_worlds",
        data=worlds_data,
        ttl=180,
        category="resonite_data",
        metadata={"command": "worlds", "container": "resonite-headless-1"}
    )

    # Container status
    status_data = mock_data.generate_status_data()
    cache.set(
        key="container_status",
        data=status_data,
        ttl=60,
        category="container_info",
        metadata={"source": "container_interface", "container": "resonite-headless-1"}
    )

    # Simulate web request checking for cached data
    def get_cached_user_data(force_refresh=False):
      if not force_refresh:
        cached_users = cache.get("resonite_users", include_stale=True)
        if cached_users:
          return {
              "data": cached_users.data,
              "cached": True,
              "age_seconds": cached_users.get_age_seconds(),
              "is_fresh": cached_users.is_fresh(),
              "metadata": cached_users.metadata
          }
      return {"data": None, "cached": False}

    # Test cached data retrieval
    result = get_cached_user_data()
    assert result["cached"], "Should use cached data"
    assert result["is_fresh"], "Data should be fresh"
    assert result["data"]["total_count"] == 4, "Should have 4 users"
    assert result["metadata"]["command"] == "users", "Metadata should be preserved"
    print("✓ Cached data retrieval with metadata works")

    # Test cache warming scenario
    cache_keys = ["resonite_users", "resonite_worlds", "container_status"]
    all_cached = all(cache.has_key(key) for key in cache_keys)
    assert all_cached, "All data should be cached"
    print("✓ Cache warming scenario works")

    # Test bulk operations
    resonite_entries = cache.get_all_entries(category="resonite_data")
    assert len(resonite_entries) == 2, "Should have 2 resonite entries"        # Test category-based refresh
    cache.invalidate_category("resonite_data")
    fresh_resonite = cache.get("resonite_users", include_stale=False)

    assert fresh_resonite is None, "Invalidated data should not be fresh"
    # Note: Invalidated entries are considered expired and not retrievable even with include_stale=True
    # This is correct behavior - invalidated data should not be used
    print("✓ Category-based refresh works")

    # Test that container info is unaffected
    container_data = cache.get("container_status")
    assert container_data is not None, "Container data should be unaffected"
    assert container_data.is_fresh(), "Container data should still be fresh"
    print("✓ Category isolation during invalidation works")

  finally:
    cache.shutdown()


async def test_async_compatibility():
  """Test async compatibility and usage patterns."""
  print("\n=== Async Compatibility Test ===")

  cache = CacheManager(default_ttl=60)

  try:
    # Simulate async data fetching and caching
    async def fetch_and_cache_data(key: str, delay: float = 0.1):
      await asyncio.sleep(delay)  # Simulate async operation
      data = mock_data.generate_user_data()
      cache.set(key, data, ttl=60, category="async_test")
      return data

    async def get_data_with_cache(key: str):
      # Check cache first
      cached_data = cache.get_data(key)
      if cached_data:
        return cached_data, True  # data, was_cached

      # Fetch fresh data
      fresh_data = await fetch_and_cache_data(key)
      return fresh_data, False

    # Test async operations
    data1, cached1 = await get_data_with_cache("async_test_1")
    assert not cached1, "First call should not be cached"
    assert data1 is not None, "Should have data"

    data2, cached2 = await get_data_with_cache("async_test_1")
    assert cached2, "Second call should be cached"
    assert data2 == data1, "Cached data should match"

    print("✓ Async caching pattern works")

    # Test concurrent async operations
    async def concurrent_test():
      tasks = []
      for i in range(5):
        task = get_data_with_cache(f"concurrent_{i}")
        tasks.append(task)

      results = await asyncio.gather(*tasks)
      return results

    concurrent_results = await concurrent_test()
    assert len(concurrent_results) == 5, "Should have 5 results"

    # All should be cache misses (first time)
    cache_misses = sum(1 for _, cached in concurrent_results if not cached)
    assert cache_misses == 5, "All should be cache misses"

    print("✓ Concurrent async operations work")

  finally:
    cache.shutdown()


def test_error_handling():
  """Test error handling and edge cases."""
  print("\n=== Error Handling Test ===")

  cache = CacheManager(default_ttl=60)

  try:
    # Test invalid TTL
    try:
      cache.set("invalid_ttl", {"data": "test"}, ttl=-1)
      assert False, "Should have raised ValueError for negative TTL"
    except ValueError:
      print("✓ Negative TTL properly rejected")

    # Test empty/None keys
    assert not cache.set("", {"data": "test"}), "Empty key should fail"
    assert not cache.set(None, {"data": "test"}), "None key should fail"
    print("✓ Invalid keys properly rejected")

    # Test non-serializable data
    class NonSerializable:
      """A test class containing non-serializable data (lambda function)."""

      def __init__(self):
        self.func = lambda x: x

    non_serializable = NonSerializable()
    assert not cache.set("bad_data", non_serializable), "Non-serializable data should fail"
    print("✓ Non-serializable data properly rejected")

    # Test operations on non-existent keys
    assert cache.get("nonexistent") is None, "Non-existent key should return None"
    assert cache.get_data("nonexistent") is None, "Non-existent key data should return None"
    assert not cache.has_key("nonexistent"), "Non-existent key should not exist"
    assert not cache.delete("nonexistent"), "Deleting non-existent key should return False"
    assert not cache.invalidate("nonexistent"), "Invalidating non-existent key should return False"
    print("✓ Operations on non-existent keys handled gracefully")

    # Test empty category operations
    assert len(cache.get_keys(category="empty_category")) == 0, "Empty category should have no keys"
    assert len(cache.get_all_entries(category="empty_category")) == 0, "Empty category should have no entries"
    assert cache.invalidate_category("empty_category") == 0, "Empty category invalidation should return 0"
    assert cache.clear(category="empty_category") == 0, "Empty category clear should return 0"
    print("✓ Empty category operations handled gracefully")

    # Test cache entry edge cases
    cache.set("edge_case", {"data": "test"}, ttl=1)
    entry = cache.get("edge_case")
    assert entry is not None, "Entry should exist"

    # Test multiple access tracking
    original_count = entry.access_count
    cache.get("edge_case")
    cache.get("edge_case")
    updated_entry = cache.get("edge_case")
    assert updated_entry.access_count > original_count, "Access count should increase"
    print("✓ Access tracking works correctly")

  finally:
    cache.shutdown()


def test_global_cache():
  """Test global cache instance management."""
  print("\n=== Global Cache Test ===")

  # Clean up any existing global cache
  cleanup_global_cache()

  # Get global cache instances
  cache1 = get_global_cache()
  cache2 = get_global_cache()

  # Should be the same instance
  assert cache1 is cache2, "Global cache should be singleton"
  print("✓ Global cache singleton works")

  # Test global cache functionality
  cache1.set("global_test", {"data": "test"}, category="global_test")
  data = cache2.get_data("global_test")
  assert data is not None, "Global cache should share data"
  assert data["data"] == "test", "Global cache data should match"
  print("✓ Global cache data sharing works")

  # Test cleanup
  cleanup_global_cache()

  # Getting cache again should create new instance
  cache3 = get_global_cache()
  assert cache3 is not cache1, "New global cache should be different instance"
  assert cache3.get_data("global_test") is None, "New global cache should not have old data"
  print("✓ Global cache cleanup works")

  # Clean up
  cleanup_global_cache()


async def main():
  """Run all tests."""
  print("Cache Manager Comprehensive Test Suite")
  print("=" * 60)

  try:
    # Run all tests
    test_basic_operations()
    test_ttl_and_freshness()
    test_categories()
    test_statistics()
    test_cleanup_and_memory()
    test_thread_safety()
    test_resonite_integration()
    await test_async_compatibility()
    test_error_handling()
    test_global_cache()

    print("\n" + "=" * 60)
    print("🎉 All tests completed successfully!")
    print("Cache Manager is working correctly across all test scenarios.")

  except Exception as e:  # pylint: disable=broad-exception-caught
    # Top-level test runner needs to catch all exceptions to provide useful error reporting
    print(f"\n❌ Test failed: {str(e)}")
    traceback.print_exc()
    sys.exit(1)

  finally:
    # Final cleanup
    cleanup_global_cache()


if __name__ == "__main__":
  asyncio.run(main())
