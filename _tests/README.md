# Tests Directory

This directory contains all test scripts and test-related files for the Resonite Headless Manager project, keeping them
 separate from the main codebase.

## Directory Structure

```shell
_tests/
├── README.md                              # This file
└── test_instance-stub_and_command-queue/  # Integration tests
    ├── README.md                          # Test-specific documentation
    └── test_integration.py                # Main integration test script
```

## Test Categories

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
