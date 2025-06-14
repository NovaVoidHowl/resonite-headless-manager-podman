"""
Command Queue System for Resonite Headless Manager

This module provides a thread-safe command queue system for managing sequential
command execution to Resonite headless containers. It ensures that only one
command or command block can be executed at a time.

Key Features:
- Sequential command execution (FIFO with priority support)
- Command blocks for multi-command sequences
- Thread-safe operations
- Timeout handling
- Result tracking and history
- Integration with existing Podman interface
"""

import asyncio
import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from concurrent.futures import Future, ThreadPoolExecutor

# Configure logging
logger = logging.getLogger(__name__)


class Priority(Enum):
  """Command execution priority levels."""
  HIGH = 1    # Emergency commands (shutdown, critical operations)
  NORMAL = 2  # Regular commands
  LOW = 3     # Background/maintenance commands


class CommandStatus(Enum):
  """Status of commands in the queue."""
  QUEUED = "queued"
  EXECUTING = "executing"
  COMPLETED = "completed"
  FAILED = "failed"
  TIMEOUT = "timeout"
  CANCELLED = "cancelled"


@dataclass
class Command:
  """Represents a single command to be executed."""
  command_text: str
  timeout: int = 30
  metadata: Dict[str, Any] = field(default_factory=dict)

  def __post_init__(self):
    """Validate command after initialization."""
    if not self.command_text or not self.command_text.strip():
      raise ValueError("Command cannot be empty")
    if self.timeout <= 0:
      raise ValueError("Timeout must be positive")


@dataclass
class CommandBlock:
  """Represents a block of commands that must be executed sequentially."""
  commands: List[Command]
  description: str = ""
  block_timeout: Optional[int] = None
  metadata: Dict[str, Any] = field(default_factory=dict)

  def __post_init__(self):
    """Validate command block after initialization."""
    if not self.commands:
      raise ValueError("Command block cannot be empty")

    # Set default block timeout to sum of individual timeouts
    if self.block_timeout is None:
      self.block_timeout = sum(cmd.timeout for cmd in self.commands)

  def add_command(self, command: Union[str, Command], timeout: int = 30) -> None:
    """Add a command to the block."""
    if isinstance(command, str):
      command = Command(command_text=command, timeout=timeout)
    self.commands.append(command)

    # Update block timeout
    if self.block_timeout is not None:
      self.block_timeout += command.timeout

  def get_total_timeout(self) -> int:
    """Get the total timeout for all commands in the block."""
    return self.block_timeout or sum(cmd.timeout for cmd in self.commands)


@dataclass
class ExecutionResult:
  """Result of command execution."""
  success: bool
  output: str = ""
  error: str = ""
  execution_time: float = 0.0
  timestamp: datetime = field(default_factory=datetime.now)
  command_executed: str = ""

  def to_dict(self) -> Dict[str, Any]:
    """Convert result to dictionary."""
    return {
        'success': self.success,
        'output': self.output,
        'error': self.error,
        'execution_time': self.execution_time,
        'timestamp': self.timestamp.isoformat(),
        'command_executed': self.command_executed
    }


@dataclass
class QueueItem:
  """Internal representation of an item in the command queue."""
  queue_id: str
  priority: Priority
  timestamp: datetime
  timeout: int
  description: str = ""

  # Union type for either single command or command block
  command: Optional[Command] = None
  command_block: Optional[CommandBlock] = None

  # Execution tracking
  status: CommandStatus = CommandStatus.QUEUED
  result: Optional[ExecutionResult] = None
  future: Optional[Future] = None

  def __post_init__(self):
    """Validate queue item after initialization."""
    if self.command is None and self.command_block is None:
      raise ValueError("QueueItem must have either command or command_block")
    if self.command is not None and self.command_block is not None:
      raise ValueError("QueueItem cannot have both command and command_block")

  def is_command_block(self) -> bool:
    """Check if this item is a command block."""
    return self.command_block is not None

  def get_description(self) -> str:
    """Get a description of the queue item."""
    if self.description:
      return self.description
    elif self.command:
      return f"Command: {self.command.command_text}"
    elif self.command_block:
      return self.command_block.description or f"Block with {len(self.command_block.commands)} commands"
    return "Unknown item"


class QueueResult:
  """Result object returned when adding items to the queue."""
  def __init__(self, queue_id: str, position: int, queue_item: QueueItem):
    self.queue_id = queue_id
    self.position = position
    self._queue_item = queue_item

  async def wait_for_completion(self, timeout: Optional[float] = None) -> ExecutionResult:
    """Wait for the command to complete execution."""
    if self._queue_item.future is None:
      raise RuntimeError("Command execution not started")

    try:
      # Use asyncio to wait for the future
      loop = asyncio.get_event_loop()

      def get_result():
        future = self._queue_item.future
        if future is not None:
          return future.result(timeout=timeout)
        else:
          raise RuntimeError("Future is None")

      result = await loop.run_in_executor(None, get_result)
      return result
    except (RuntimeError, ValueError, TimeoutError, AttributeError) as e:
      logger.error("Error waiting for command completion: %s", str(e))
      return ExecutionResult(
          success=False,
          error=f"Error waiting for completion: {str(e)}",
          command_executed=str(self._queue_item.command or self._queue_item.command_block)
      )
    except Exception as e:  # pylint: disable=broad-exception-caught
      # Catch any other unexpected exceptions to ensure we return a result
      logger.error("Unexpected error waiting for command completion: %s", str(e))
      return ExecutionResult(
          success=False,
          error=f"Unexpected error waiting for completion: {str(e)}",
          command_executed=str(self._queue_item.command or self._queue_item.command_block)
      )

  def is_completed(self) -> bool:
    """Check if the command has completed."""
    return self._queue_item.status in [
        CommandStatus.COMPLETED,
        CommandStatus.FAILED,
        CommandStatus.TIMEOUT,
        CommandStatus.CANCELLED
    ]

  def get_status(self) -> CommandStatus:
    """Get current status of the queued item."""
    return self._queue_item.status


class CommandQueue:
  """
  Thread-safe command queue for sequential execution of container commands.

  This class manages a queue of commands and command blocks, ensuring that
  only one command is executed at a time to prevent conflicts in the container.
  """

  def __init__(self,
               container_name: str,
               command_executor: Callable[[str, str, int], str],
               max_queue_size: int = 100,
               cleanup_interval: int = 60,
               max_result_history: int = 50):
    """
    Initialize the command queue.

    Args:
        container_name: Name of the container to execute commands in
        command_executor: Function to execute commands (container_name, command, timeout) -> output
        max_queue_size: Maximum number of items that can be queued
        cleanup_interval: Interval in seconds to cleanup completed items
        max_result_history: Maximum number of completed results to keep
    """
    self.container_name = container_name
    self.command_executor = command_executor
    self.max_queue_size = max_queue_size
    self.max_result_history = max_result_history

    # Queue management
    self._queue: deque = deque()
    self._queue_lock = threading.RLock()
    self._processing_lock = threading.Lock()
    self._is_processing = False
    self._shutdown_requested = False

    # Result tracking
    self._completed_items: Dict[str, QueueItem] = {}
    self._completed_lock = threading.RLock()

    # Worker thread
    self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="command_queue")
    self._worker_future: Optional[Future] = None

    # Start worker thread
    self._start_worker()

    # Start cleanup thread
    self._cleanup_thread = threading.Thread(
        target=self._cleanup_worker,
        args=(cleanup_interval,),
        daemon=True,
        name="queue_cleanup"
    )
    self._cleanup_thread.start()

    logger.info("CommandQueue initialized for container: %s", container_name)

  def add_command(self,
                  command: Union[str, Command],
                  timeout: int = 30,
                  priority: Priority = Priority.NORMAL,
                  description: str = "") -> QueueResult:
    """
    Add a single command to the queue.

    Args:
        command: Command string or Command object
        timeout: Command timeout in seconds
        priority: Execution priority
        description: Optional description

    Returns:
        QueueResult object for tracking completion

    Raises:
        ValueError: If queue is full or command is invalid
        RuntimeError: If queue is shutting down
    """
    if self._shutdown_requested:
      raise RuntimeError("Queue is shutting down")

    # Convert string to Command object if needed
    if isinstance(command, str):
      command = Command(command_text=command, timeout=timeout)

    # Create queue item
    queue_item = QueueItem(
        queue_id=str(uuid.uuid4()),
        priority=priority,
        timestamp=datetime.now(),
        timeout=timeout,
        description=description,
        command=command
    )

    return self._add_queue_item(queue_item)

  def add_command_block(self,
                        command_block: CommandBlock,
                        priority: Priority = Priority.NORMAL,
                        description: str = "") -> QueueResult:
    """
    Add a command block to the queue.

    Args:
        command_block: CommandBlock object
        priority: Execution priority
        description: Optional description override

    Returns:
        QueueResult object for tracking completion

    Raises:
        ValueError: If queue is full or command block is invalid
        RuntimeError: If queue is shutting down
    """
    if self._shutdown_requested:
      raise RuntimeError("Queue is shutting down")

    # Use provided description or block's description
    final_description = description or command_block.description

    # Create queue item
    queue_item = QueueItem(
        queue_id=str(uuid.uuid4()),
        priority=priority,
        timestamp=datetime.now(),
        timeout=command_block.get_total_timeout(),
        description=final_description,
        command_block=command_block
    )

    return self._add_queue_item(queue_item)

  def _add_queue_item(self, queue_item: QueueItem) -> QueueResult:
    """Internal method to add a queue item."""
    with self._queue_lock:
      if len(self._queue) >= self.max_queue_size:
        raise ValueError(f"Queue is full (max size: {self.max_queue_size})")

      # Create future immediately when adding to queue
      queue_item.future = Future()

      # Insert based on priority (higher priority = lower enum value)
      inserted = False
      for i, existing_item in enumerate(self._queue):
        if queue_item.priority.value < existing_item.priority.value:
          self._queue.insert(i, queue_item)
          position = i + 1
          inserted = True
          break

      if not inserted:
        self._queue.append(queue_item)
        position = len(self._queue)

      logger.info("Added %s to queue at position %d (ID: %s)",
                  queue_item.get_description(), position, queue_item.queue_id)

      return QueueResult(queue_item.queue_id, position, queue_item)

  def get_status(self) -> Dict[str, Any]:
    """Get current queue status information."""
    with self._queue_lock:
      queue_items = []
      for item in self._queue:
        queue_items.append({
            'queue_id': item.queue_id,
            'description': item.get_description(),
            'priority': item.priority.name,
            'status': item.status.value,
            'timestamp': item.timestamp.isoformat(),
            'timeout': item.timeout
        })

    with self._completed_lock:
      completed_count = len(self._completed_items)
      recent_completed = []
      # Get 5 most recent completed items
      sorted_completed = sorted(
          self._completed_items.values(),
          key=lambda x: x.timestamp,
          reverse=True
      )
      for item in sorted_completed[:5]:
        recent_completed.append({
            'queue_id': item.queue_id,
            'description': item.get_description(),
            'status': item.status.value,
            'timestamp': item.timestamp.isoformat(),
            'success': item.result.success if item.result else False
        })

    return {
        'queue_length': len(self._queue),
        'is_processing': self._is_processing,
        'shutdown_requested': self._shutdown_requested,
        'completed_count': completed_count,
        'queue_items': queue_items,
        'recent_completed': recent_completed,
        'container_name': self.container_name
    }

  def clear_queue(self) -> int:
    """
    Clear all pending commands from the queue.

    Returns:
        Number of items removed
    """
    with self._queue_lock:
      count = len(self._queue)
      # Mark all queued items as cancelled
      for item in self._queue:
        if item.status == CommandStatus.QUEUED:
          item.status = CommandStatus.CANCELLED
          if item.future:
            item.future.cancel()

      self._queue.clear()
      logger.info("Cleared %d items from queue", count)
      return count

  def is_processing(self) -> bool:
    """Check if the queue is currently processing commands."""
    return self._is_processing

  def get_queue_length(self) -> int:
    """Get the current number of items in the queue."""
    with self._queue_lock:
      return len(self._queue)

  def shutdown(self) -> None:
    """
    Gracefully shutdown the queue system.
    """
    logger.info("Shutting down command queue...")
    self._shutdown_requested = True

    # Clear remaining queue
    self.clear_queue()    # Shutdown executor
    try:
      self._executor.shutdown(wait=True)
    except (RuntimeError, OSError, AttributeError) as e:
      logger.error("Error shutting down executor: %s", str(e))
    except Exception as e:  # pylint: disable=broad-exception-caught
      # Catch any other unexpected exceptions during shutdown
      logger.error("Unexpected error shutting down executor: %s", str(e))

    logger.info("Command queue shutdown complete")

  def _start_worker(self) -> None:
    """Start the worker thread for processing commands."""
    def worker():
      logger.info("Command queue worker started")
      while not self._shutdown_requested:
        try:
          self._process_next_item()
          time.sleep(0.1)  # Small delay to prevent busy waiting
        except (RuntimeError, ValueError, AttributeError, OSError) as e:
          logger.error("Error in queue worker: %s", str(e))
          time.sleep(1)  # Longer delay on error
        except Exception as e:  # pylint: disable=broad-exception-caught
          # Worker thread must not die from unexpected exceptions
          logger.error("Unexpected error in queue worker: %s", str(e))
          time.sleep(1)  # Longer delay on error
      logger.info("Command queue worker stopped")

    self._worker_future = self._executor.submit(worker)

  def _process_next_item(self) -> None:
    """Process the next item in the queue."""
    with self._queue_lock:
      if not self._queue or self._is_processing:
        return

      item = self._queue.popleft()    # Set processing flag
    with self._processing_lock:
      self._is_processing = True

    try:
      # Use the existing future that was created when adding to queue
      future = item.future
      if future is None:
        raise RuntimeError("Future should have been created when adding to queue")

      item.status = CommandStatus.EXECUTING

      logger.info("Executing %s (ID: %s)", item.get_description(), item.queue_id)

      # Execute the item
      start_time = time.time()
      result = self._execute_item(item)
      execution_time = time.time() - start_time

      # Update result with execution time
      result.execution_time = execution_time      # Set status based on result
      if result.success:
        item.status = CommandStatus.COMPLETED
      else:
        item.status = CommandStatus.FAILED

      item.result = result
      future.set_result(result)

      logger.info("Completed %s in %.2fs (ID: %s)",
                  item.get_description(), execution_time, item.queue_id)

    except (RuntimeError, ValueError, AttributeError, OSError) as e:
      logger.error("Error executing %s: %s", item.get_description(), str(e))
      error_result = ExecutionResult(
          success=False,
          error=str(e),
          command_executed=str(item.command or item.command_block)
      )
      item.result = error_result
    except Exception as e:  # pylint: disable=broad-exception-caught
      # Ensure we always set a result, even for unexpected exceptions
      logger.error("Unexpected error executing %s: %s", item.get_description(), str(e))
      error_result = ExecutionResult(
          success=False,
          error=f"Unexpected error: {str(e)}",
          command_executed=str(item.command or item.command_block)
      )
      item.result = error_result
      item.status = CommandStatus.FAILED

      if item.future:
        item.future.set_result(error_result)

    finally:
      # Add to completed items
      with self._completed_lock:
        self._completed_items[item.queue_id] = item

      # Clear processing flag
      with self._processing_lock:
        self._is_processing = False

  def _execute_item(self, item: QueueItem) -> ExecutionResult:
    """Execute a single queue item (command or command block)."""
    if item.command:
      return self._execute_single_command(item.command)
    elif item.command_block:
      return self._execute_command_block(item.command_block)
    else:
      raise ValueError("Queue item has neither command nor command_block")

  def _execute_single_command(self, command: Command) -> ExecutionResult:
    """Execute a single command."""
    try:
      logger.debug("Executing command: %s (timeout: %ds)", command.command_text, command.timeout)
      output = self.command_executor(self.container_name, command.command_text, command.timeout)

      return ExecutionResult(
          success=True,
          output=output,
          command_executed=command.command_text
      )
    except OSError as e:
      logger.error("Command execution failed: %s", str(e))
      return ExecutionResult(
          success=False,
          error=str(e),
          command_executed=command.command_text
      )
    except Exception as e:  # pylint: disable=broad-exception-caught
      # Catch any other unexpected exceptions during command execution
      logger.error("Unexpected error during command execution: %s", str(e))
      return ExecutionResult(
          success=False,
          error=f"Unexpected error: {str(e)}",
          command_executed=command.command_text
      )

  def _execute_command_block(self, command_block: CommandBlock) -> ExecutionResult:
    """Execute a command block (multiple sequential commands)."""
    all_outputs = []
    start_time = time.time()

    for i, command in enumerate(command_block.commands):
      try:
        logger.debug("Executing command %d/%d in block: %s",
                     i + 1, len(command_block.commands), command.command_text)

        # Check for timeout on the entire block
        elapsed = time.time() - start_time
        if command_block.block_timeout and elapsed >= command_block.block_timeout:
          return ExecutionResult(
              success=False,
              error=f"Command block timed out after {elapsed:.1f}s",
              output='\n'.join(all_outputs),
              command_executed=f"Block: {command_block.description}"
          )        # Execute individual command
        output = self.command_executor(self.container_name, command.command_text, command.timeout)
        all_outputs.append(f"[{command.command_text}] {output}")

      except (RuntimeError, ValueError, OSError) as e:
        error_msg = f"Command {i + 1} failed: {str(e)}"
        logger.error(error_msg)
        all_outputs.append(f"[{command.command_text}] ERROR: {str(e)}")

        return ExecutionResult(
            success=False,
            error=error_msg,
            output='\n'.join(all_outputs),
            command_executed=f"Block: {command_block.description}"
        )
      except Exception as e:  # pylint: disable=broad-exception-caught
        # Catch any other unexpected exceptions in command block execution
        error_msg = f"Command {i + 1} unexpected error: {str(e)}"
        logger.error(error_msg)
        all_outputs.append(f"[{command.command_text}] UNEXPECTED ERROR: {str(e)}")

        return ExecutionResult(
            success=False,
            error=error_msg,
            output='\n'.join(all_outputs),
            command_executed=f"Block: {command_block.description}"
        )

    return ExecutionResult(
        success=True,
        output='\n'.join(all_outputs),
        command_executed=f"Block: {command_block.description}"
    )

  def _cleanup_worker(self, interval: int) -> None:
    """Background worker to cleanup old completed items."""
    logger.info("Starting cleanup worker (interval: %ds)", interval)

    while not self._shutdown_requested:
      try:
        time.sleep(interval)
        if self._shutdown_requested:
          break

        self._cleanup_completed_items()
      except (RuntimeError, OSError) as e:
        logger.error("Error in cleanup worker: %s", str(e))
      except Exception as e:  # pylint: disable=broad-exception-caught
        # Cleanup worker must not die from unexpected exceptions
        logger.error("Unexpected error in cleanup worker: %s", str(e))

    logger.info("Cleanup worker stopped")

  def _cleanup_completed_items(self) -> None:
    """Remove old completed items to prevent memory leaks."""
    with self._completed_lock:
      if len(self._completed_items) <= self.max_result_history:
        return

      # Sort by timestamp and keep only the most recent
      sorted_items = sorted(
          self._completed_items.items(),
          key=lambda x: x[1].timestamp,
          reverse=True
      )
      # Keep only the most recent items
      items_to_keep = dict(sorted_items[:self.max_result_history])
      removed_count = len(self._completed_items) - len(items_to_keep)

      self._completed_items.clear()
      self._completed_items.update(items_to_keep)

      logger.debug("Cleaned up %d old completed items", removed_count)
