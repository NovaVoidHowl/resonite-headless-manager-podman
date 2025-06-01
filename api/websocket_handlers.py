"""
WebSocket handlers and connection management for Resonite headless server manager.

This module provides:
- WebSocket connection management
- WebSocket endpoint handlers for different services
- Message routing and broadcasting
- Connection state management
"""

import asyncio
import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Set

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


@dataclass
class ConnectionManager:
  """Manage WebSocket connections for a specific type"""
  active_connections: Set[WebSocket]

  def __init__(self):
    self.active_connections = set()

  async def connect(self, websocket: WebSocket):
    """
    Accept and add a new WebSocket connection.

    Args:
        websocket (WebSocket): The WebSocket connection to add
    """
    await websocket.accept()
    self.active_connections.add(websocket)

  async def disconnect(self, websocket: WebSocket):
    """
    Remove a WebSocket connection from active connections.

    Args:
        websocket (WebSocket): The WebSocket connection to remove
    """
    self.active_connections.discard(websocket)

  async def broadcast(self, message: dict):
    """
    Broadcast a message to all active WebSocket connections.

    Args:
        message (dict): The message to broadcast to all connections
    """
    for connection in self.active_connections.copy():
      try:
        if await is_websocket_connected(connection):
          await connection.send_json(message)
        else:
          self.active_connections.discard(connection)
      except Exception as e:
        logger.error("Error broadcasting to connection: %s", str(e))
        self.active_connections.discard(connection)


# Create connection managers for different types of connections
logs_manager = ConnectionManager()
status_manager = ConnectionManager()
worlds_manager = ConnectionManager()
commands_manager = ConnectionManager()
cpu_manager = ConnectionManager()
memory_manager = ConnectionManager()
container_status_manager = ConnectionManager()


async def is_websocket_connected(websocket: WebSocket) -> bool:
  """Check if the websocket is still connected and in a valid state"""
  try:
    return websocket.client_state == WebSocketState.CONNECTED
  except (ConnectionError, RuntimeError) as e:
    logger.debug("Error checking websocket state: %s", str(e))
    return False


async def safe_send_json(websocket: WebSocket, data: dict) -> bool:
  """Safely send JSON data over websocket with state checking"""
  try:
    if await is_websocket_connected(websocket):
      # Add timestamp if not already present
      if "timestamp" not in data:
        data["timestamp"] = datetime.now().isoformat()

      await websocket.send_json(data)
      return True
    return False
  except (ConnectionError, RuntimeError) as e:
    logger.debug("Error sending data: %s", str(e))
    return False


async def handle_websocket_message(websocket: WebSocket, message: str, request_locks: dict, handlers: dict):
  """
  Handle individual WebSocket messages

  Args:
      websocket: The WebSocket connection
      message: The raw message string
      request_locks: Dictionary of locks for different request types
      handlers: Dictionary of handler functions for different message types
  """
  try:
    data = json.loads(message)
    message_type = data.get("type", "")

    if message_type in request_locks and request_locks[message_type].locked():
      logger.warning("Request of type %s already in progress, skipping", message_type)
      await safe_send_json(websocket, {
          "type": "error",
          "message": f"A {message_type} request is already in progress"
      })
      return

    # Route to appropriate handler
    if message_type in handlers:
      await handlers[message_type](websocket, data)
    else:
      await safe_send_json(websocket, {
          "type": "error",
          "message": f"Unknown message type: {message_type}"
      })

  except json.JSONDecodeError:
    if await is_websocket_connected(websocket):
      await safe_send_json(websocket, {
          "type": "error",
          "message": "Invalid message format"
      })
  except (ConnectionError, RuntimeError, ValueError, KeyError) as e:
    logger.error("Error handling message: %s", str(e))
    if await is_websocket_connected(websocket):
      await safe_send_json(websocket, {
          "type": "error",
          "message": f"Error: {e}"
      })


async def monitor_websocket(websocket: WebSocket, callback):
  """Monitor a WebSocket connection and handle messages"""
  try:
    while await is_websocket_connected(websocket):
      data = await websocket.receive()
      if data["type"] == "websocket.receive":
        if "text" in data:
          await callback(websocket, data["text"])
  except WebSocketDisconnect:
    logger.info("WebSocket disconnected normally")
  except json.JSONDecodeError:
    logger.error("Invalid JSON received")
  except (ConnectionError, RuntimeError) as e:
    logger.error("Error in WebSocket monitoring: %s", str(e))


def create_websocket_endpoints(app, data_source, request_locks, command_handlers):
  """
  Create all WebSocket endpoints for the FastAPI app

  Args:
      app: FastAPI application instance
      data_source: Data source instance for container operations (BaseDataSource)
      request_locks: Dictionary of locks for different request types
      command_handlers: Dictionary of command handler functions
  """
  @app.websocket("/ws/logs")
  async def logs_endpoint(websocket: WebSocket):
    """Handle container logs WebSocket connections"""
    await logs_manager.connect(websocket)

    try:
      recent_logs = data_source.get_recent_logs()
      for log_line in recent_logs:
        await safe_send_json(websocket, {
            "type": "container_output",
            "output": log_line,
            "timestamp": datetime.now().isoformat()
        })

      async def stream_callback(output):
        await logs_manager.broadcast({
            "type": "container_output",
            "output": output,
            "timestamp": datetime.now().isoformat()
        })

      loop = asyncio.get_running_loop()

      def sync_callback(output):
        asyncio.run_coroutine_threadsafe(stream_callback(output), loop)

      thread = threading.Thread(
          target=data_source.monitor_output,
          args=(sync_callback,),
          daemon=True
      )
      thread.start()

      while await is_websocket_connected(websocket):
        await asyncio.sleep(1)

    except WebSocketDisconnect:
      logger.info("Logs WebSocket disconnected normally")
    except (ConnectionError, RuntimeError) as e:
      logger.error("Logs WebSocket error: %s", str(e))
    finally:
      await logs_manager.disconnect(websocket)

  @app.websocket("/ws/status")
  async def status_endpoint(websocket: WebSocket):
    """Handle status monitoring WebSocket connections"""
    await status_manager.connect(websocket)

    try:
      while await is_websocket_connected(websocket):
        def message_handler(ws, msg): return handle_websocket_message(
            ws, msg, request_locks, {"get_status": command_handlers["get_status"]}
        )
        await monitor_websocket(websocket, message_handler)

    except WebSocketDisconnect:
      logger.info("Status WebSocket disconnected normally")
    except (ConnectionError, RuntimeError, json.JSONDecodeError) as e:
      logger.error("Status WebSocket error: %s", str(e))
    finally:
      await status_manager.disconnect(websocket)

  @app.websocket("/ws/worlds")
  async def worlds_endpoint(websocket: WebSocket):
    """Handle worlds list WebSocket connections"""
    await worlds_manager.connect(websocket)

    try:
      while await is_websocket_connected(websocket):
        def message_handler(ws, msg): return handle_websocket_message(
            ws, msg, request_locks, {"get_worlds": command_handlers["get_worlds"]}
        )
        await monitor_websocket(websocket, message_handler)

    except WebSocketDisconnect:
      logger.info("Worlds WebSocket disconnected normally")
    except (ConnectionError, RuntimeError, json.JSONDecodeError) as e:
      logger.error("Worlds WebSocket error: %s", str(e))
    finally:
      await worlds_manager.disconnect(websocket)

  @app.websocket("/ws/command")
  async def command_endpoint(websocket: WebSocket):
    """Handle command WebSocket connections"""
    await commands_manager.connect(websocket)

    try:
      while await is_websocket_connected(websocket):
        def message_handler(ws, msg): return handle_websocket_message(
            ws, msg, request_locks, {"command": command_handlers["command"]}
        )
        await monitor_websocket(websocket, message_handler)

    except WebSocketDisconnect:
      logger.info("Command WebSocket disconnected normally")
    except (ConnectionError, RuntimeError, json.JSONDecodeError, KeyError) as e:
      logger.error("Command WebSocket error: %s", str(e))
    finally:
      await commands_manager.disconnect(websocket)

  @app.websocket("/ws/heartbeat")
  async def heartbeat_endpoint(websocket: WebSocket):
    """Handle heartbeat connections to keep other WebSockets alive"""
    await websocket.accept()
    try:
      while True:
        await asyncio.sleep(30)  # Send heartbeat every 30 seconds
        if await is_websocket_connected(websocket):
          await websocket.send_json({
              "type": "heartbeat",
              "timestamp": datetime.now().isoformat()
          })
        else:
          break
    except WebSocketDisconnect:
      logger.info("Heartbeat WebSocket disconnected normally")
    except (ConnectionError, RuntimeError) as e:
      logger.error("Heartbeat WebSocket error: %s", str(e))
  @app.websocket("/ws/cpu")
  async def cpu_endpoint(websocket: WebSocket):
    """Handle CPU monitoring WebSocket connections"""
    await cpu_manager.connect(websocket)

    try:
      while await is_websocket_connected(websocket):
        # Get CPU usage and send update
        cpu_usage = data_source.get_cpu_usage()
        await safe_send_json(websocket, {
            "type": "cpu_update",
            "cpu_usage": cpu_usage
        })
        await asyncio.sleep(1)  # Update every second

    except WebSocketDisconnect:
      logger.info("CPU WebSocket disconnected normally")
    except (ConnectionError, RuntimeError) as e:
      logger.error("CPU WebSocket error: %s", str(e))
    finally:
      await cpu_manager.disconnect(websocket)
  @app.websocket("/ws/memory")
  async def memory_endpoint(websocket: WebSocket):
    """Handle memory monitoring WebSocket connections"""
    await memory_manager.connect(websocket)

    try:
      while await is_websocket_connected(websocket):
        # Get memory usage and send update
        memory_info = data_source.get_memory_usage()
        await safe_send_json(websocket, {
            "type": "memory_update",
            "memory_percent": memory_info.get("percent", 0),
            "memory_used": memory_info.get("used", "0GB"),
            "memory_total": memory_info.get("total", "0GB")
        })
        await asyncio.sleep(1)  # Update every second

    except WebSocketDisconnect:
      logger.info("Memory WebSocket disconnected normally")
    except (ConnectionError, RuntimeError) as e:
      logger.error("Memory WebSocket error: %s", str(e))
    finally:
      await memory_manager.disconnect(websocket)

  @app.websocket("/ws/container_status")
  async def container_status_endpoint(websocket: WebSocket):
    """Handle container status WebSocket connections"""
    await container_status_manager.connect(websocket)

    try:
      while await is_websocket_connected(websocket):
        def message_handler(ws, msg): return handle_websocket_message(
            ws, msg, request_locks, {"get_container_status": command_handlers["get_container_status"]}
        )
        await monitor_websocket(websocket, message_handler)

    except WebSocketDisconnect:
      logger.info("Container Status WebSocket disconnected normally")
    except (ConnectionError, RuntimeError, json.JSONDecodeError) as e:
      logger.error("Container Status WebSocket error: %s", str(e))
    finally:
      await container_status_manager.disconnect(websocket)


async def send_output(output):
  """Send output to WebSocket logs"""
  try:
    if not isinstance(output, str):
      output = str(output)

    await logs_manager.broadcast({
        "type": "container_output",
        "output": output,
        "timestamp": datetime.now().isoformat()
    })
  except (ConnectionError, RuntimeError) as e:
    logger.error("Error broadcasting output: %s", str(e))
