# Tests Directory

This directory contains all test scripts and test-related files for the Resonite Headless Manager project, keeping them
 separate from the main codebase.

## Directory Structure

```shell
_tests/
├── README.md                              # This file
├── test_cache-manager/                    # Cache Manager tests
│   ├── README.md                          # Cache manager test documentation
│   └── test.py                            # Comprehensive cache manager test suite
├── test_command-queue/                    # Command Queue tests
│   ├── README.md                          # Command queue test documentation
│   └── test.py                            # Comprehensive command queue test suite
└── test_instance-stub_and_command-queue/ # Integration tests
    ├── README.md                          # Integration test documentation
    └── test_integration.py                # Command queue + stub interface integration
```

## Test Categories

### Cache Manager Tests

**Location**: `test_cache-manager/`

Tests the cache manager system functionality, including:

- Basic cache operations (set, get, delete, exists)
- TTL (Time To Live) handling and data freshness
- Category-based organization and bulk operations
- Cache statistics and performance monitoring
- Thread safety and concurrent access
- Memory management and automatic cleanup
- Async compatibility and integration patterns
- Error handling and edge cases
- Global cache instance management

**How to run**:

```bash
cd _tests/test_cache-manager
python test.py
```

### Command Queue Tests

**Location**: `test_command-queue/`

Tests the command queue system functionality, including:

- Single command execution with various priorities
- Command blocks for sequential execution
- Queue status monitoring and tracking
- Error handling and recovery mechanisms
- Priority queue ordering (HIGH, NORMAL, LOW)
- Performance characteristics and timing
- Mock command execution with realistic responses

**How to run**:

```bash
cd _tests/test_command-queue
python test.py
```

### Integration Tests

**Location**: `test_instance-stub_and_command-queue/`

Tests the integration between the command queue system and the stub interface, demonstrating:

- Sequential command execution through the queue
- Priority handling (HIGH, NORMAL, LOW)
- Command blocks for related operations
- Direct interface operations (bypassing queue)
- Error handling and recovery
- Queue monitoring and status tracking

**How to run**:

```bash
cd _tests/test_instance-stub_and_command-queue
python test_integration.py
```

## Adding New Tests

When adding new test scripts:

1. **Create a descriptive directory** under `_tests/` for your test category
2. **Include a README.md** explaining what the test does and how to run it
3. **Use clear, descriptive filenames** for test scripts
4. **Update this main README** to document the new test category

## Test Naming Conventions

- **Directories**: Use descriptive names with hyphens: `test_category-name_and-scope`
- **Files**: Use clear names indicating the test purpose: `test_integration.py`, `test_performance.py`
- **Functions**: Use descriptive test function names: `test_basic_command_execution()`

## Path Management

Test scripts should handle module imports properly by adding the project root to the Python path:

```python
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / "module_directory"))
```

This ensures tests can import modules from the main codebase regardless of where they're run from.

## Test Dependencies

Tests should minimize external dependencies and use the existing project modules where possible. Mock objects and stub
 implementations are preferred over real infrastructure dependencies for unit and integration testing.
