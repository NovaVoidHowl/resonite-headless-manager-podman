"""
API Manager for Resonite Headless Manager.

This module coordinates REST and WebSocket endpoints, providing a unified
interface for API management with pluggable data sources.
"""

import asyncio
import json
import logging
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rest_handlers import create_rest_endpoints
from websocket_handlers import create_websocket_endpoints

logger = logging.getLogger(__name__)
default_server_ip = "127.0.0.1"

class APIManager:
  """
  Manages the FastAPI application with REST and WebSocket endpoints.

  This class coordinates all API endpoints and provides a clean interface
  for starting/stopping the API with different data sources.
  """

  def __init__(self, data_source):
    """
    Initialize the API Manager.

    Args:
        data_source: The data source implementation (BaseDataSource)
    """
    self.data_source = data_source
    self.app = FastAPI(
        title="Resonite Headless Manager API",
        description="WebSocket and REST API for managing Resonite headless servers",
        version="1.0.0"
    )    # set default server IP
    self.server_ip = default_server_ip
    # get server ip from config.json file
    # open config.json and read the server_ip field
    try:
      with open("config.json", "r", encoding="utf-8") as f:
        config = f.read()
        # Assuming config is a JSON string, parse it
        config_data = json.loads(config)
        self.server_ip = config_data.get("server_ip", default_server_ip)
    except FileNotFoundError:
      logger.info("config.json not found, using default server IP")
    except json.JSONDecodeError:
      logger.error("Invalid JSON in config.json, using default server IP")

    # Add CORS middleware
    self.app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://" + self.server_ip + ":8000"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    self.request_locks = {}
    self.command_handlers = {}

    self._setup_locks()
    self._setup_command_handlers()
    self._setup_endpoints()

  def _setup_locks(self):
    """Set up request locks for different operations."""
    self.request_locks = {
        "get_status": asyncio.Lock(),
        "get_worlds": asyncio.Lock(),
        "get_container_status": asyncio.Lock(),
        "command": asyncio.Lock()
    }

  def _setup_command_handlers(self):
    """Set up command handlers for WebSocket operations."""
    self.command_handlers = {
        "get_status": self._handle_status_command,
        "get_worlds": self._handle_worlds_command,
        "get_container_status": self._handle_container_status_command,
        "command": self._handle_general_command
    }

  def _setup_endpoints(self):
    """Set up all REST and WebSocket endpoints."""
    # Create REST endpoints
    create_rest_endpoints(self.app, self.data_source)

    # Create WebSocket endpoints
    create_websocket_endpoints(
        self.app,
        self.data_source,
        self.request_locks,
        self.command_handlers
    )

    logger.info("API endpoints configured with data source: %s",
                self.data_source.__class__.__name__)

  async def _handle_status_command(self, websocket, data):
    """Handle status command via WebSocket."""
    try:
      # For stub data source, this would return mock status
      status_data = {
          "type": "status_update",
          "status": "Server running normally",
          "timestamp": "2025-06-01T12:00:00Z"
      }
      await websocket.send_json(status_data)
    except Exception as e:
      logger.error("Error handling status command: %s", str(e))
      await websocket.send_json({
          "type": "error",
          "message": f"Status command failed: {e}"
      })

  async def _handle_worlds_command(self, websocket, data):
    """Handle worlds command via WebSocket."""
    try:
      # This would use data_source.send_command("worlds") in the future
      worlds_data = {
          "type": "worlds_update",
          "worlds_data": [],
          "timestamp": "2025-06-01T12:00:00Z",
          "cached": False
      }
      await websocket.send_json(worlds_data)
    except Exception as e:
      logger.error("Error handling worlds command: %s", str(e))
      await websocket.send_json({
          "type": "error",
          "message": f"Worlds command failed: {e}"
      })

  async def _handle_container_status_command(self, websocket, data):
    """Handle container status command via WebSocket."""
    try:
      status = self.data_source.get_container_status()
      await websocket.send_json({
          "type": "container_status_update",
          "status": status
      })
    except Exception as e:
      logger.error("Error handling container status command: %s", str(e))
      await websocket.send_json({
          "type": "error",
          "message": f"Container status command failed: {e}"
      })

  async def _handle_general_command(self, websocket, data):
    """Handle general commands via WebSocket."""
    try:
      command = data.get("command", "")
      if not command:
        await websocket.send_json({
            "type": "error",
            "message": "No command specified"
        })
        return

      # Send command through data source
      output = self.data_source.send_command(command)

      await websocket.send_json({
          "type": "command_response",
          "command": command,
          "output": output,
          "timestamp": "2025-06-01T12:00:00Z"
      })
    except Exception as e:
      logger.error("Error handling command: %s", str(e))
      await websocket.send_json({
          "type": "error",
          "message": f"Command failed: {e}"
      })

  def get_app(self) -> FastAPI:
    """
    Get the FastAPI application instance.

    Returns:
        FastAPI: The configured FastAPI application
    """
    return self.app

  def get_data_source_info(self) -> Dict[str, Any]:
    """
    Get information about the current data source.

    Returns:
        Dict[str, Any]: Data source information
    """
    return self.data_source.get_data_source_info()

  async def shutdown(self):
    """Clean up resources when shutting down."""
    try:
      logger.info("Shutting down API Manager...")
      self.data_source.cleanup()
      logger.info("API Manager shutdown complete")
    except Exception as e:
      logger.error("Error during API Manager shutdown: %s", str(e))
