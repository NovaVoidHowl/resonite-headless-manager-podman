# Cache Manager Test Suite

This directory contains comprehensive tests for the Cache Manager system component.

## Overview

The Cache Manager provides thread-safe caching functionality for the Resonite Headless Manager, allowing data to be
 stored with timestamps and TTL (Time To Live) values. This test suite validates all aspects of the cache manager
 functionality without requiring external dependencies.

## Test Structure

### `test.py` - Comprehensive Test Suite

A standalone test script that thoroughly exercises the cache manager system with the following test categories:

#### Test Categories

1. **Basic Operations** - Set, get, delete, key existence checks, and data validation
2. **TTL and Freshness** - Time-to-live handling, fresh/stale/expired status transitions
3. **Categories** - Category-based organization, bulk operations, and isolation
4. **Statistics** - Performance metrics, hit rates, and monitoring data
5. **Cleanup and Memory** - Automatic cleanup, memory limits, and LRU eviction
6. **Thread Safety** - Concurrent operations from multiple threads
7. **Resonite Integration** - Realistic usage patterns for Resonite command caching  
8. **Async Compatibility** - Async/await patterns and concurrent operations
9. **Error Handling** - Invalid inputs, edge cases, and graceful failure handling
10. **Global Cache** - Singleton pattern and global instance management

#### Mock Components

- **MockDataGenerator**: Generates realistic test data including:
  - User data with names, IDs, ping, and FPS
  - World data with names, user counts, and status
  - Container status with uptime, memory, and CPU usage
  - System metrics with CPU, memory, disk, and network stats

## Running the Tests

### Prerequisites

Ensure the Cache Manager module is available:

```bash
# From the project root
python -m pip install -e .
```

### Execute Tests

```bash
# From this directory
python test.py

# Or from project root
python _tests/test_cache-manager/test.py
```

## Expected Output

The test suite will output detailed information showing:

- Test category progress with checkmarks (✓) for passed tests
- Cache operation logging with timestamps and details
- Thread safety validation across concurrent operations
- TTL transitions from fresh to stale to expired
- Memory management and cleanup operations
- Performance metrics and statistics tracking
- Error handling for invalid operations

## Test Features

### Validated Functionality

- ✅ **Data Storage**: JSON-serializable data with TTL and metadata
- ✅ **Data Retrieval**: Fresh and stale data handling with status tracking
- ✅ **TTL Management**: Automatic expiration and status transitions
- ✅ **Categories**: Namespace-based organization and bulk operations
- ✅ **Statistics**: Hit rates, access counts, and performance metrics
- ✅ **Thread Safety**: Concurrent access from multiple threads
- ✅ **Memory Management**: Maximum entry limits with LRU eviction
- ✅ **Cleanup**: Automatic and manual expired entry removal
- ✅ **Error Handling**: Graceful handling of invalid inputs
- ✅ **Global Instance**: Singleton pattern for app-wide usage

### Mock Data Types

The test suite generates realistic mock data for:

- **User Lists**: Names, IDs, ping times, FPS data
- **World Information**: World names, user counts, status
- **Container Status**: Uptime, memory usage, CPU usage
- **System Metrics**: CPU, memory, disk, network statistics
- **Metadata**: Command sources, timestamps, container IDs

### Thread Safety Testing

The test suite validates thread safety by:

- Running 5 concurrent threads performing cache operations
- Each thread performs 10 set and 10 get operations
- Verifying no race conditions or data corruption
- Checking category isolation across threads
- Validating final statistics accuracy

### Performance Characteristics

The tests validate:

- Sub-millisecond cache operations for small data
- Proper TTL calculations and aging
- Memory usage within configured limits
- Cleanup efficiency and timing
- Hit rate calculations and optimization

## Integration

This test complements other test suites:

- **Command Queue Tests**: Cache integration with command results
- **Integration Tests**: End-to-end cache usage patterns
- **Container Interface Tests**: Caching container status and metrics

## Configuration Testing

The test suite validates configuration options:

- **default_ttl**: Default time-to-live for cache entries (60-3600 seconds)
- **max_entries**: Maximum cache size with automatic eviction (100-10000 entries)
- **cleanup_interval**: Automatic cleanup frequency (10-300 seconds)

## Cache Status System Testing

Validates the four-state cache status system:

- **FRESH**: Data within TTL, completely valid
- **STALE**: Past TTL but still usable (< 2x TTL)
- **EXPIRED**: Very old data (> 2x TTL), should be refreshed
- **INVALID**: Manually invalidated data

## Async Pattern Testing

Tests async/await compatibility:

- Cache operations within async functions
- Concurrent cache access from multiple async tasks
- Integration with async command execution patterns
- Thread-safe operations across async contexts

## Error Scenarios

The test suite validates proper handling of:

- Non-serializable data (functions, complex objects)
- Invalid TTL values (negative numbers)
- Empty or None cache keys
- Operations on non-existent keys
- Category operations on empty categories
- Memory exhaustion and cleanup failures

## Maintenance

When modifying the Cache Manager system:

1. Run this test suite to ensure core functionality remains intact
2. Add new test cases for new features or edge cases
3. Update the MockDataGenerator for new data types
4. Verify thread safety for any new operations
5. Check performance impact and adjust limits if needed
6. Update documentation for new configuration options

## Architecture

```shell
test.py
├── MockDataGenerator (realistic test data generation)
├── Basic Operations Tests (core CRUD operations)
├── TTL and Freshness Tests (time-based behavior)
├── Categories Tests (namespace organization)
├── Statistics Tests (performance monitoring)
├── Cleanup Tests (memory management)
├── Thread Safety Tests (concurrent access)
├── Resonite Integration Tests (real-world patterns)
├── Async Compatibility Tests (async/await patterns)
├── Error Handling Tests (invalid inputs)
└── Global Cache Tests (singleton management)
```

The test suite is designed to be:

- **Completely standalone** - no external dependencies
- **Deterministic** - consistent results across runs
- **Comprehensive** - covers all cache manager features
- **Realistic** - uses patterns from actual Resonite integration
- **Performance-aware** - validates efficiency characteristics

## Troubleshooting

### Common Test Issues

1. **Import Errors**: Ensure the cache manager module is in the Python path
2. **Thread Safety Failures**: May indicate race conditions in cache operations
3. **TTL Test Failures**: System clock changes can affect timing-based tests
4. **Memory Test Failures**: Insufficient system resources or memory limits

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show detailed cache operation logs during test execution.

## Performance Benchmarks

Expected performance characteristics:

- **Set Operations**: < 1ms for small data (< 1KB)
- **Get Operations**: < 0.5ms for cached data
- **Category Operations**: < 10ms for 100 entries
- **Thread Contention**: Minimal blocking under normal load
- **Memory Usage**: ~100 bytes overhead per cache entry
- **Cleanup Time**: < 50ms for 1000 expired entries
