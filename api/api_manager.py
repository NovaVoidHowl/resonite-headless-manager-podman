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

  def __init__(self, data_source, templates_path="templates"):
    """
    Initialize the API Manager.

    Args:
        data_source: The data source implementation (BaseDataSource)
        templates_path: Path to templates directory (default: "templates")    """
    self.data_source = data_source
    self.templates_path = templates_path
    self.app = FastAPI(
        title="Resonite Headless Manager API",
        description="WebSocket and REST API for managing Resonite headless servers",
        version="0.0.1-dev",
        redoc_url=None,  # Disable ReDoc endpoint
        docs_url=None  # Disable Swagger UI endpoint
    )
    # set default server IP
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
    create_rest_endpoints(self.app, self.data_source, self.templates_path)    # Create WebSocket endpoints
    create_websocket_endpoints(
        self.app,
        self.data_source,
        self.request_locks,
        self.command_handlers
    )

    logger.info("API endpoints configured with data source: %s",
                self.data_source.__class__.__name__)

  async def _handle_status_command(self, websocket, _data):
    """Handle status command via WebSocket."""
    try:
      # Get server status from data source
      server_status = self.data_source.get_server_status()
      status_data = {
          "type": "status_update",
          "status": server_status,
          "timestamp": server_status.get("server_time", "2025-06-08T12:00:00Z")
      }
      await websocket.send_json(status_data)
    except (RuntimeError, AttributeError, KeyError, ValueError, OSError) as e:
      logger.error("Error handling status command: %s", str(e))
      await websocket.send_json({
          "type": "error",
          "message": f"Status command failed: {e}"
      })

  async def _handle_worlds_command(self, websocket, _data):
    """Handle worlds command via WebSocket."""
    try:
      # Get worlds data from data source
      worlds_data = self.data_source.get_worlds_data()
      response_data = {
          "type": "worlds_update",
          "worlds_data": worlds_data,
          "timestamp": "2025-06-08T12:00:00Z",
          "cached": False
      }
      await websocket.send_json(response_data)
    except (RuntimeError, AttributeError, KeyError, ValueError, OSError) as e:
      logger.error("Error handling worlds command: %s", str(e))
      await websocket.send_json({
          "type": "error",
          "message": f"Worlds command failed: {e}"
      })

  async def _handle_container_status_command(self, websocket, _data):
    """Handle container status command via WebSocket."""
    try:
      status = self.data_source.get_container_status()
      await websocket.send_json({
          "type": "container_status_update",
          "status": status
      })
    except (RuntimeError, AttributeError, KeyError, ValueError, OSError) as e:
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

      target_world_instance = data.get("target_world_instance", None)
      if not target_world_instance:
        await websocket.send_json({
            "type": "error",
            "message": "No target world instance specified"
        })
        return

      command_mode = data.get("command_mode", "default")
      if command_mode not in ["default", "direct"]:
        await websocket.send_json({
            "type": "error",
            "message": f"Invalid command mode: {command_mode}"
        })
        return

      # Use data source to get structured command response
      response = self.data_source.get_structured_command_response(command, target_world_instance, command_mode)
      await websocket.send_json(response)
    except (RuntimeError, AttributeError, KeyError, ValueError, OSError) as e:
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
    except (RuntimeError, AttributeError, OSError) as e:
      logger.error("Error during API Manager shutdown: %s", str(e))
