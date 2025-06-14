# Command Queue Test Suite

This directory contains comprehensive tests for the Command Queue system component.

## Overview

The Command Queue system manages sequential execution of commands to Resonite headless containers.
 This test suite validates all aspects of the command queue functionality without requiring external dependencies.

## Test Structure

### `test.py` - Comprehensive Test Suite

A standalone test script that thoroughly exercises the command queue system with the following test categories:

#### Test Categories

1. **Basic Usage** - Single commands, priority handling, and basic command blocks
2. **Command Blocks** - Sequential command execution with detailed results
3. **Queue Status** - Monitoring queue state, processing status, and completion tracking
4. **Custom Command Blocks** - Different types of command sequences for various scenarios
5. **Error Handling** - Command failures, recovery, and error propagation
6. **Priority Handling** - Testing high, normal, and low priority command execution
7. **Performance** - Testing multiple commands and execution timing

#### Mock Components

- **MockCommandExecutor**: Configurable mock that simulates command execution with:
  - Variable execution times
  - Configurable failure rates
  - Specific command failure simulation
  - Realistic command responses
  - Execution statistics tracking

## Running the Tests

### Prerequisites

Ensure the Command Queue module is available:

```bash
# From the project root
python -m pip install -e .
```

### Execute Tests

```bash
# From this directory
python test.py

# Or from project root
python _tests/test_command-queue/test.py
```

## Expected Output

The test suite will output detailed logging showing:

- Command queue initialization and shutdown
- Individual command execution with timing
- Command block processing with results
- Error handling and recovery
- Priority queue ordering
- Performance metrics and statistics

## Test Features

### Validated Functionality

- ✅ Single command execution
- ✅ Command blocks (sequential execution)
- ✅ Priority handling (HIGH, NORMAL, LOW)
- ✅ Error handling and recovery
- ✅ Queue status monitoring
- ✅ Performance characteristics
- ✅ Command timeout handling
- ✅ Graceful shutdown and cleanup

### Mock Behaviors

- Realistic command responses (status, users, worlds, etc.)
- Variable execution times
- Configurable failure scenarios
- Statistical tracking
- Command history logging

## Integration

This test complements the integration test in `_tests/test_instance-stub_and_command-queue/` which tests the command
 queue working with the stub interface.

## Maintenance

When modifying the Command Queue system:

1. Run this test suite to ensure core functionality remains intact
2. Add new test cases for new features
3. Update the MockCommandExecutor if new command behaviors are needed
4. Verify performance characteristics haven't regressed

## Architecture

```shell
test.py
├── MockCommandExecutor (configurable mock executor)
├── Basic Usage Tests (single commands, priorities)
├── Command Block Tests (sequential execution)
├── Queue Status Tests (monitoring)
├── Error Handling Tests (failures, recovery)
├── Priority Tests (queue ordering)
└── Performance Tests (timing, throughput)
```

The test suite is designed to be completely self-contained and can run without any external dependencies or containers.
