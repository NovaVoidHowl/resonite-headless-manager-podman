"""
REST API handlers for Resonite headless server manager.

This module provides:
- Configuration management endpoints
- Container control endpoints
- World management endpoints
- Status and settings endpoints
"""

import json
import logging
import os
from typing import Any, Dict

from fastapi import HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

logger = logging.getLogger(__name__)


def load_config() -> Dict[Any, Any]:
  """Load the headless config file"""
  config_path = os.getenv('CONFIG_PATH')
  if not config_path:
    logger.error("CONFIG_PATH environment variable is not set")
    raise ValueError("CONFIG_PATH not set in environment variables")

  logger.info("Attempting to load config from: %s", config_path)

  try:
    with open(config_path, 'r', encoding='utf-8') as f:
      return json.load(f)
  except FileNotFoundError as exc:
    logger.error("Config file not found at path: %s", config_path)
    raise ValueError(f"Config file not found at {config_path}") from exc
  except Exception as e:
    logger.error("Unexpected error loading config: %s", str(e))
    raise ValueError(f"Error loading config: {str(e)}") from e


def save_config(config_data: Dict[Any, Any]) -> None:
  """Save the headless config file"""
  config_path = os.getenv('CONFIG_PATH')
  if not config_path:
    raise ValueError("CONFIG_PATH not set in environment variables")

  try:
    json.dumps(config_data)
  except (TypeError, json.JSONDecodeError) as exc:
    raise ValueError("Invalid JSON data") from exc

  with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config_data, f, indent=2)


def create_rest_endpoints(app, data_source):
  """
  Create all REST API endpoints for the FastAPI app

  Args:
      app: FastAPI application instance
      data_source: Data source instance for container operations (BaseDataSource)
  """

  @app.get("/")
  async def get_root():
    """Serve the main web interface HTML page.

    Returns:
        HTMLResponse: The rendered index.html template
    """
    with open("templates/api-index.html", encoding='utf-8') as f:
      return HTMLResponse(content=f.read())

  @app.get("/config")
  async def get_config():
    """Get the current headless config"""
    try:
      result = load_config()
      return JSONResponse(content=result)
    except ValueError as e:
      logger.error("Error in get_config endpoint: %s", str(e))
      raise HTTPException(status_code=500, detail=str(e)) from e
    except (ConnectionError, RuntimeError) as e:
      logger.error("Unexpected error in get_config endpoint: %s", str(e))
      raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}") from e

  @app.post("/config")
  async def update_config(config_data: Dict[Any, Any]):
    """Update the headless config"""
    try:
      save_config(config_data)
      return JSONResponse(content={"message": "Config updated successfully"})
    except ValueError as e:
      raise HTTPException(status_code=400, detail=str(e)) from e

  @app.post("/api/world-properties")
  async def update_world_properties(data: dict):
    """Update world properties"""
    try:
      session_id = data.get('sessionId')
      if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")

      return JSONResponse(content={"message": "Properties updated successfully"})
    except (ValueError, KeyError) as e:
      raise HTTPException(status_code=400, detail=str(e)) from e
    except (ConnectionError, RuntimeError) as e:
      logger.error("Error updating world properties: %s", str(e))
      raise HTTPException(status_code=500, detail=str(e)) from e
  @app.post("/api/restart-container")
  async def restart_container():
    """Restart the Docker container"""
    try:
      data_source.restart_container()
      return JSONResponse(content={"message": "Container restart initiated"})
    except (ConnectionError, RuntimeError) as e:
      logger.error("Error restarting container: %s", str(e))
      raise HTTPException(status_code=500, detail=str(e)) from e

  @app.post("/api/start-container")
  async def start_container():
    """Start the Docker container"""
    try:
      if not data_source.is_container_running():
        data_source.start_container()
        return JSONResponse(content={"message": "Container start initiated"})
      return JSONResponse(content={"message": "Container is already running"})
    except (ConnectionError, RuntimeError) as e:
      logger.error("Error starting container: %s", str(e))
      raise HTTPException(status_code=500, detail=str(e)) from e

  @app.post("/api/stop-container")
  async def stop_container():
    """Stop the Docker container"""
    try:
      if data_source.is_container_running():
        data_source.stop_container()
        return JSONResponse(content={"message": "Container stop initiated"})
      return JSONResponse(content={"message": "Container is already stopped"})
    except (ConnectionError, RuntimeError) as e:
      logger.error("Error stopping container: %s", str(e))
      raise HTTPException(status_code=500, detail=str(e)) from e

  @app.get("/api/config/status")
  async def get_config_status():
    """Get whether the app is using builtin or config file settings"""
    try:
      result = data_source.get_config_status()
      return JSONResponse(content=result)
    except Exception as e:
      logger.error("Error in get_config_status endpoint: %s", str(e))
      raise HTTPException(status_code=500, detail=str(e)) from e

  @app.get("/api/config/settings")
  async def get_config_settings():
    """Get current configuration settings"""
    try:
      result = data_source.get_config_settings()
      return JSONResponse(content=result)
    except Exception as e:
      logger.error("Error in get_config_settings endpoint: %s", str(e))
      raise HTTPException(status_code=500, detail=str(e)) from e

  @app.post("/api/config/generate")
  async def generate_config():
    """Generate config file and switch to using it"""
    try:
      result = data_source.generate_config()
      return JSONResponse(content=result)
    except Exception as e:
      logger.error("Error generating config file: %s", str(e))
      raise HTTPException(status_code=500, detail=str(e)) from e
