# Cache Manager

The Cache Manager provides a thread-safe caching system for storing data with timestamps, allowing other modules to
determine data freshness without repeatedly requesting information through the command queue.

## Features

- **Thread-Safe Operations**: Safe for use across multiple threads and WebSocket connections
- **TTL Support**: Automatic expiration of cached data based on Time-To-Live
- **Data Freshness Tracking**: Store data with timestamps to track age and freshness
- **Cache Status Tracking**: Entries can be FRESH, STALE, EXPIRED, or INVALID
- **Category/Namespace Support**: Organize cached data into categories for bulk operations
- **Statistics and Monitoring**: Track cache performance, hit rates, and usage patterns
- **Automatic Cleanup**: Background thread removes expired entries at configurable intervals
- **Flexible Data Storage**: Store any JSON-serializable data with optional metadata
- **Memory Management**: Configurable maximum entries with LRU-style eviction
- **Global Cache Instance**: Singleton pattern for application-wide cache usage

## Installation

No additional installation is required beyond the base project dependencies. The cache manager uses only Python standard
library modules.

## Quick Start

```python
import json
import time
from datetime import datetime
from cacheing.cache_manager import get_global_cache, CacheStatus

# Get the global cache instance
cache = get_global_cache()

# Store some data
cache.set("my_key", {"message": "Hello World"}, ttl=300)

# Retrieve the data
data = cache.get_data("my_key")
print(f"Cached data: {data}")

# Check cache statistics
stats = cache.get_stats()
print(f"Cache entries: {stats.total_entries}")
print(f"Hit rate: {stats.get_hit_rate():.1f}%")
```

## Basic Usage

### Setting up the Cache Manager

```python
from cacheing.cache_manager import CacheManager, get_global_cache, CacheStatus

# Use the global cache instance (recommended for most cases)
cache = get_global_cache()

# Or create a custom cache manager instance
cache = CacheManager(
    default_ttl=300,      # 5 minutes default TTL
    max_entries=1000,     # Maximum cache entries
    cleanup_interval=60   # Cleanup every 60 seconds
)
```

### Storing Data

```python
# Store simple data
cache.set("user_count", 42, ttl=120)  # 2 minute TTL

# Store complex data with metadata
user_data = {
    "users": [{"name": "Alice", "id": "U-123"}],
    "total": 1
}

cache.set(
    key="current_users",
    data=user_data,
    ttl=180,  # 3 minutes
    category="resonite_data",
    metadata={"command": "users", "world_id": "world-1"}
)
```

### Retrieving Data

```python
# Get fresh data only
entry = cache.get("current_users")
if entry:
    data = entry.data
    age = entry.get_age_seconds()
    print(f"Data is {age:.1f} seconds old")

# Get data (including slightly stale data)
entry = cache.get("current_users", include_stale=True)

# Get just the data (convenience method)
user_data = cache.get_data("current_users")
```

### Checking Data Freshness

```python
entry = cache.get("current_users", include_stale=True)
if entry:
    print(f"Data age: {entry.get_age_seconds():.1f} seconds")
    print(f"Remaining TTL: {entry.get_remaining_ttl():.1f} seconds")
    print(f"Is fresh: {entry.is_fresh()}")
    print(f"Is expired: {entry.is_expired()}")
    print(f"Status: {entry.status.value}")  # FRESH, STALE, EXPIRED, or INVALID
    print(f"Access count: {entry.access_count}")
    print(f"Last accessed: {entry.last_accessed}")
```

### Cache Management

```python
# Check if key exists
if cache.has_key("current_users"):
    print("Data is cached and fresh")

# Invalidate specific entry
cache.invalidate("current_users")

# Invalidate all entries in a category
cache.invalidate_category("resonite_data")

# Delete entry completely
cache.delete("old_data")

# Clear all cache or specific category
cache.clear()  # Clear all
cache.clear(category="temp_data")  # Clear category only
```

## Cache Status System

The cache uses a sophisticated status system to track data validity:

- **FRESH**: Data is within TTL and completely valid
- **STALE**: Data has exceeded TTL but is still usable (less than 2x TTL)
- **EXPIRED**: Data is older than 2x TTL and should be refreshed
- **INVALID**: Data has been manually invalidated

```python
from cacheing.cache_manager import CacheStatus

# Check specific status
entry = cache.get("my_key", include_stale=True)
if entry:
    if entry.status == CacheStatus.FRESH:
        print("Data is fresh and up-to-date")
    elif entry.status == CacheStatus.STALE:
        print("Data is stale but still usable")
    elif entry.status == CacheStatus.EXPIRED:
        print("Data is expired and should be refreshed")
    elif entry.status == CacheStatus.INVALID:
        print("Data has been manually invalidated")
```

## Data Categories

Organize your cached data into logical categories for easier management:

- `"resonite_data"` - Data from Resonite commands (users, worlds, bans)
- `"container_status"` - Container health and status information
- `"system_metrics"` - CPU, memory, and system data
- `"user_sessions"` - User authentication and session data
- `"temp_data"` - Short-lived temporary data

## Cache Entry Structure

Each cached item is stored as a `CacheEntry` with the following information:

```python
@dataclass
class CacheEntry:
    data: Any                    # The actual cached data
    timestamp: datetime          # When data was cached
    ttl_seconds: int            # Time-to-live in seconds (default: 300)
    category: str               # Data category/namespace (default: "default")
    metadata: Dict[str, Any]    # Additional metadata dictionary

    # Internal tracking fields
    access_count: int           # How many times accessed
    last_accessed: datetime     # When last accessed
    status: CacheStatus         # Current status (FRESH, STALE, EXPIRED, INVALID)
```

### CacheEntry Methods

```python
entry = cache.get("my_key")
if entry:
    # Age and TTL information
    age = entry.get_age_seconds()           # Age in seconds
    remaining = entry.get_remaining_ttl()   # Remaining TTL (can be negative)

    # Status checks
    is_fresh = entry.is_fresh()             # True if within TTL
    is_expired = entry.is_expired()         # True if older than 2x TTL

    # Update tracking
    entry.mark_accessed()                   # Increment access count
    entry.invalidate()                      # Mark as invalid

    # Export to dictionary
    entry_dict = entry.to_dict()            # Full entry as dict for JSON
```

## Cache Statistics

Monitor cache performance with detailed statistics:

```python
stats = cache.get_stats()

# Basic metrics
print(f"Total entries: {stats.total_entries}")
print(f"Fresh entries: {stats.fresh_entries}")
print(f"Stale entries: {stats.stale_entries}")
print(f"Expired entries: {stats.expired_entries}")
print(f"Invalid entries: {stats.invalid_entries}")

# Performance metrics
print(f"Cache hits: {stats.total_hits}")
print(f"Cache misses: {stats.total_misses}")
print(f"Hit rate: {stats.get_hit_rate():.1f}%")

# Operations tracking
print(f"Total sets: {stats.total_sets}")
print(f"Total invalidations: {stats.total_invalidations}")
print(f"Total cleanups: {stats.total_cleanups}")

# Category breakdown
print(f"Categories: {stats.categories}")

# Age information
print(f"Oldest entry: {stats.oldest_entry_age:.1f}s")
print(f"Newest entry: {stats.newest_entry_age:.1f}s")

# Convert to dictionary for JSON serialization
stats_dict = stats.to_dict()
json_stats = json.dumps(stats_dict, indent=2)
```

### CacheStats Structure

```python
@dataclass
class CacheStats:
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
```

## Integration Examples

### With Command Queue Results

```python
import json  # For JSON serialization in examples
from command_queue.command_queue import CommandQueue, ExecutionResult
from cacheing.cache_manager import get_global_cache

cache = get_global_cache()

# After getting result from command queue
def handle_command_result(command: str, result: ExecutionResult):
    if result.success:
        # Cache the result data
        cache.set(
            key=f"command_result_{command}",
            data={
                "output": result.output,
                "execution_time": result.execution_time,
                "timestamp": result.timestamp.isoformat()
            },
            ttl=300,  # 5 minutes
            category="command_results",
            metadata={
                "command": command,
                "container": "resonite-headless"
            }
        )
```

### With WebSocket Responses

```python
async def get_cached_or_fresh_data(websocket, command: str, force_refresh: bool = False):
    cache = get_global_cache()
    cache_key = f"ws_data_{command}"

    # Try to get cached data first
    if not force_refresh:
        cached_data = cache.get_data(cache_key, include_stale=True)
        if cached_data:
            # Send cached data with freshness info
            entry = cache.get(cache_key, include_stale=True)
            await websocket.send_json({
                "type": "command_response",
                "command": command,
                "output": cached_data,
                "timestamp": entry.timestamp.isoformat(),
                "cached": True,
                "age_seconds": entry.get_age_seconds()
            })
            return

    # Get fresh data and cache it
    # ... execute command through queue ...
    # cache.set(cache_key, fresh_data, ...)
```

### Pre-warming Cache

```python
async def prewarm_cache():
    """Pre-warm frequently accessed data."""
    cache = get_global_cache()

    # Pre-load common data
    common_commands = ["users", "worlds", "status"]

    for command in common_commands:
        # Execute command and cache result
        # This would be done through your request handler
        pass
```

## Configuration

### TTL Guidelines

- **User/World Data**: 60-180 seconds (changes frequently)
- **Container Status**: 30-60 seconds (for health monitoring)
- **System Metrics**: 15-30 seconds (for real-time monitoring)
- **Configuration Data**: 300-600 seconds (changes rarely)
- **Static Data**: 3600+ seconds (rarely changes)

### Memory Management

The cache automatically manages memory through several mechanisms:

1. **Maximum Entries**: When `max_entries` is reached, oldest entries are evicted (LRU-style)
2. **TTL Expiration**: Entries past their TTL are marked as stale but kept temporarily
3. **Automatic Cleanup**: Background thread removes expired entries (older than 2x TTL)
4. **Manual Cleanup**: Call `cache.cleanup()` to force immediate cleanup

```python
# Create cache with memory limits
cache = CacheManager(
    max_entries=500,      # Evict oldest when this limit is reached
    cleanup_interval=30   # Clean expired entries every 30 seconds
)

# Manual cleanup
cleaned_count = cache.cleanup()
print(f"Cleaned up {cleaned_count} expired entries")

# Check memory usage
stats = cache.get_stats()
print(f"Memory usage: {stats.total_entries}/{cache.max_entries} entries")
```

## Thread Safety

The cache manager is fully thread-safe and can be used safely from:

- Multiple WebSocket connections
- Background cleanup threads
- Command queue workers
- Web server request handlers

## Error Handling

The cache manager handles errors gracefully and provides clear feedback:

### Data Validation

```python
# Non-serializable data will be rejected
class ComplexObject:
    def __init__(self):
        self.func = lambda x: x  # Functions are not JSON serializable

obj = ComplexObject()
success = cache.set("bad_key", obj)  # Returns False
if not success:
    print("Failed to cache non-serializable data")

# Empty keys are rejected
success = cache.set("", {"data": "value"})  # Returns False
success = cache.set(None, {"data": "value"})  # Returns False

# Invalid TTL values are rejected
try:
    cache.set("key", "data", ttl=-1)  # Raises ValueError
except ValueError as e:
    print(f"Invalid TTL: {e}")
```

### Safe Data Access

```python
# Always check if data exists before using
data = cache.get_data("might_not_exist")
if data is None:
    print("Cache miss - data not found or expired")
    # Handle cache miss by fetching fresh data
else:
    print(f"Cache hit: {data}")

# Handle specific cache entry states
entry = cache.get("my_key", include_stale=True)
if entry is None:
    print("No data available (not cached or expired)")
elif entry.status == CacheStatus.INVALID:
    print("Data was invalidated - fetch fresh data")
elif entry.status == CacheStatus.EXPIRED:
    print("Data is very old - should refresh")
elif entry.status == CacheStatus.STALE:
    print("Data is slightly old but usable")
else:  # FRESH
    print("Data is fresh and current")
```

### Logging

The cache manager provides detailed logging for debugging:

```python
import logging

# Enable cache manager logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('cacheing.cache_manager')

# Now cache operations will be logged
cache.set("debug_key", {"test": "data"})
# DEBUG - Cached data for key 'debug_key' (TTL: 300s, Category: default)

cache.get("debug_key")
# DEBUG - Cache hit for key 'debug_key' (age: 1.2s, status: fresh)
```

## Performance Tips

1. **Use Categories**: Organize data for easier bulk operations
2. **Check TTL**: Use appropriate TTL values for your data types
3. **Monitor Stats**: Use cache statistics to optimize performance
4. **Batch Operations**: Invalidate categories instead of individual keys
5. **Include Stale**: Allow stale data when appropriate to reduce load
6. **JSON Serializable**: Ensure all cached data is JSON serializable
7. **Key Naming**: Use consistent, descriptive key naming conventions
8. **Memory Monitoring**: Monitor cache size and cleanup frequency

## Best Practices

### Key Naming Conventions

```python
# Use descriptive, hierarchical key names
cache.set("resonite:users:world_1", user_data)
cache.set("container:status:resonite-headless-1", status_data)
cache.set("metrics:cpu:container_1", cpu_metrics)

# Include version numbers for data schemas
cache.set("api:user_data:v2:alice123", user_profile)
```

### Category Organization

```python
# Organize by data type and update frequency
CATEGORIES = {
    "resonite_realtime": 30,    # 30s TTL - users, worlds
    "resonite_status": 60,      # 1m TTL - server status
    "container_health": 45,     # 45s TTL - health checks
    "user_sessions": 300,       # 5m TTL - auth data
    "static_config": 3600,      # 1h TTL - configuration
}

for category, ttl in CATEGORIES.items():
    cache.set(f"{category}:example", data, ttl=ttl, category=category)
```

### Memory Management Strategy

```python
# Monitor and manage cache size
def monitor_cache_health():
    stats = cache.get_stats()

    # Check memory usage
    usage_percent = (stats.total_entries / cache.max_entries) * 100
    if usage_percent > 80:
        print(f"Cache usage high: {usage_percent:.1f}%")

    # Check hit rate
    hit_rate = stats.get_hit_rate()
    if hit_rate < 50:
        print(f"Low hit rate: {hit_rate:.1f}% - consider adjusting TTLs")

    # Check for too many stale entries
    stale_percent = (stats.stale_entries / stats.total_entries) * 100
    if stale_percent > 25:
        print(f"Many stale entries: {stale_percent:.1f}% - consider cleanup")
        cache.cleanup()
```

## Troubleshooting

### Common Issues

1. **Cache Miss on Fresh Data**

   - Check if TTL is too short
   - Verify key spelling and case sensitivity
   - Check if data was invalidated

2. **Memory Usage Growing**

   - Increase cleanup frequency
   - Reduce max_entries limit
   - Check for data that never expires

3. **Poor Hit Rate**

   - Review TTL settings (may be too short)
   - Check if data is being invalidated too often
   - Verify cache keys are consistent

4. **Thread Safety Issues**

   - Use the global cache instance
   - Avoid modifying cache entries directly
   - Let the cache manager handle thread synchronization

### Debug Mode

```python
# Enable detailed logging for troubleshooting
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Monitor cache operations
cache = get_global_cache()
cache.set("debug_test", {"data": "test"})
# Will log: "Cached data for key 'debug_test' (TTL: 300s, Category: default)"
```

## API Reference

### CacheManager Methods

- `set(key, data, ttl=None, category="default", metadata=None)` - Store data in cache
- `get(key, include_stale=False)` - Retrieve cache entry with full metadata
- `get_data(key, include_stale=False)` - Retrieve just the cached data
- `has_key(key, fresh_only=True)` - Check if key exists and meets freshness criteria
- `invalidate(key)` - Mark specific entry as invalid
- `invalidate_category(category)` - Mark all entries in category as invalid
- `delete(key)` - Remove entry completely from cache
- `clear(category=None)` - Clear all cache entries or specific category
- `cleanup()` - Remove expired and invalid entries manually
- `get_stats()` - Get detailed cache statistics
- `get_keys(category=None)` - Get list of all keys or keys in category
- `get_all_entries(category=None)` - Get all cache entries or entries in category
- `shutdown()` - Gracefully shutdown cache manager and cleanup thread

### CacheEntry Methods

- `is_fresh()` - Check if entry is within TTL
- `is_expired()` - Check if entry is older than 2x TTL
- `get_age_seconds()` - Get age of entry in seconds
- `get_remaining_ttl()` - Get remaining TTL (can be negative)
- `mark_accessed()` - Update access tracking
- `invalidate()` - Mark entry as invalid
- `to_dict()` - Convert entry to dictionary for JSON serialization

### CacheStats Methods

- `get_hit_rate()` - Calculate cache hit rate percentage
- `to_dict()` - Convert stats to dictionary for JSON serialization

### Global Cache Functions

- `get_global_cache()` - Get global cache instance
- `cleanup_global_cache()` - Shutdown global cache

### Cache Manager Instance Methods

```python
# Graceful shutdown
cache.shutdown()  # Stops background thread and clears cache

# Get current configuration
print(f"Default TTL: {cache.default_ttl}")
print(f"Max entries: {cache.max_entries}")
print(f"Cleanup interval: {cache.cleanup_interval}")
```

## Running the Examples

A complete working example is provided in `example_usage.py`. Run it with:

```bash
cd cacheing
python example_usage.py
```

This example demonstrates:

- Basic cache operations (set, get, delete)
- Data freshness and TTL handling
- Category-based cache management
- Cache statistics and monitoring
- Integration with Resonite command patterns
- Async-compatible usage patterns
- Cleanup and memory management
- Error handling scenarios

### Example Output

The example will show output similar to:

```text
Cache Manager Examples
==================================================
=== Basic Cache Usage ===
Data cached successfully: True
Retrieved data: {'users': [{'name': 'Alice', 'id': 'U-alice123'},
                 {'name': 'Bob', 'id': 'U-bob456'}], 'total_count': 2}
Data age: 0.0 seconds
TTL remaining: 30.0 seconds
Access count: 1
Category: resonite_data
Metadata: {'source_command': 'users', 'world': 'main'}
User count from cache: 2

=== Data Freshness Example ===
Fresh data: {'value': 42} (status: fresh)
Waiting 2 seconds...
Still fresh: {'value': 42} (age: 2.0s)
Waiting 2 more seconds...
Fresh data available: False
Stale data: {'value': 42} (status: stale, age: 4.0s)
```

## Cache Manager Implementation Details

### Cache Entry Lifecycle

1. **Creation**: Entry is created with `CacheStatus.FRESH`
2. **Access**: Each access increments `access_count` and updates `last_accessed`
3. **Aging**: Status automatically updates based on age:
   - `FRESH`: Within TTL
   - `STALE`: Past TTL but less than 2x TTL
   - `EXPIRED`: Older than 2x TTL
4. **Invalidation**: Can be manually marked as `INVALID`
5. **Cleanup**: Expired and invalid entries are automatically removed

### Thread Safety Implementation

The cache manager uses `threading.RLock()` for thread safety:

```python
# All operations are thread-safe
cache = get_global_cache()

# Safe to call from multiple threads simultaneously
cache.set("key1", data1)  # Thread A
cache.get("key2")         # Thread B
cache.cleanup()           # Background thread
```

### Background Cleanup Thread

The cache automatically starts a background daemon thread that:

- Runs every `cleanup_interval` seconds (default: 60)
- Removes entries with status `EXPIRED` or `INVALID`
- Logs cleanup statistics
- Gracefully shuts down when `cache.shutdown()` is called
