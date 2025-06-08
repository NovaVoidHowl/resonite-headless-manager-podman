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
      except (ConnectionError, RuntimeError, ValueError) as e:
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
      if data["type"] == "websocket.receive" and "text" in data:
        await callback(websocket, data["text"])
  except WebSocketDisconnect:
    logger.info("WebSocket disconnected normally")
  except json.JSONDecodeError:
    logger.error("Invalid JSON received")
  except (ConnectionError, RuntimeError) as e:
    logger.error("Error in WebSocket monitoring: %s", str(e))


async def _handle_logs_websocket(websocket: WebSocket, data_source):
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


async def _handle_message_based_websocket(websocket: WebSocket, manager: ConnectionManager,
                                          request_locks: dict, command_handlers: dict,
                                          handler_key: str, endpoint_name: str):
  """Handle WebSocket connections that process messages with handlers"""
  await manager.connect(websocket)

  try:
    while await is_websocket_connected(websocket):
      async def message_handler(ws, msg):
        return await handle_websocket_message(
            ws, msg, request_locks, {handler_key: command_handlers[handler_key]}
        )
      await monitor_websocket(websocket, message_handler)

  except WebSocketDisconnect:
    logger.info("%s WebSocket disconnected normally", endpoint_name)
  except (ConnectionError, RuntimeError, json.JSONDecodeError) as e:
    logger.error("%s WebSocket error: %s", endpoint_name, str(e))
  finally:
    await manager.disconnect(websocket)


async def _handle_heartbeat_websocket(websocket: WebSocket):
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


async def _handle_monitoring_websocket(websocket: WebSocket, manager: ConnectionManager,
                                       data_source, update_type: str, data_getter,
                                       endpoint_name: str):
  """Handle WebSocket connections that monitor and send periodic updates"""
  await manager.connect(websocket)

  try:
    while await is_websocket_connected(websocket):
      # Get data and send update
      data = data_getter(data_source)

      if update_type == "cpu":
        message = {
            "type": "cpu_update",
            "cpu_usage": data
        }
      else:  # memory
        message = {
            "type": "memory_update",
            "memory_percent": data.get("percent", 0),
            "memory_used": data.get("used", "0GB"),
            "memory_total": data.get("total", "0GB")
        }

      await safe_send_json(websocket, message)
      await asyncio.sleep(1)  # Update every second

  except WebSocketDisconnect:
    logger.info("%s WebSocket disconnected normally", endpoint_name)
  except (ConnectionError, RuntimeError) as e:
    logger.error("%s WebSocket error: %s", endpoint_name, str(e))
  finally:
    await manager.disconnect(websocket)


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
    await _handle_logs_websocket(websocket, data_source)

  @app.websocket("/ws/status")
  async def status_endpoint(websocket: WebSocket):
    """Handle status monitoring WebSocket connections"""
    await _handle_message_based_websocket(
        websocket, status_manager, request_locks, command_handlers,
        "get_status", "Status"
    )

  @app.websocket("/ws/worlds")
  async def worlds_endpoint(websocket: WebSocket):
    """Handle worlds list WebSocket connections"""
    await _handle_message_based_websocket(
        websocket, worlds_manager, request_locks, command_handlers,
        "get_worlds", "Worlds"
    )

  @app.websocket("/ws/command")
  async def command_endpoint(websocket: WebSocket):
    """Handle command WebSocket connections"""
    await _handle_message_based_websocket(
        websocket, commands_manager, request_locks, command_handlers,
        "command", "Command"
    )

  @app.websocket("/ws/heartbeat")
  async def heartbeat_endpoint(websocket: WebSocket):
    """Handle heartbeat connections to keep other WebSockets alive"""
    await _handle_heartbeat_websocket(websocket)

  @app.websocket("/ws/cpu")
  async def cpu_endpoint(websocket: WebSocket):
    """Handle CPU monitoring WebSocket connections"""
    await _handle_monitoring_websocket(
        websocket, cpu_manager, data_source, "cpu",
        lambda ds: ds.get_cpu_usage(), "CPU"
    )

  @app.websocket("/ws/memory")
  async def memory_endpoint(websocket: WebSocket):
    """Handle memory monitoring WebSocket connections"""
    await _handle_monitoring_websocket(
        websocket, memory_manager, data_source, "memory",
        lambda ds: ds.get_memory_usage(), "Memory"
    )

  @app.websocket("/ws/container_status")
  async def container_status_endpoint(websocket: WebSocket):
    """Handle container status WebSocket connections"""
    await _handle_message_based_websocket(
        websocket, container_status_manager, request_locks, command_handlers,
        "get_container_status", "Container Status"
    )


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
