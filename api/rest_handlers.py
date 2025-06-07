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


def get_config_path(data_source=None) -> str:
  """
  Get the configuration file path from data source settings or environment.
  
  Args:
      data_source: The data source instance to get settings from
      
  Returns:
      str: Path to the configuration file
      
  Raises:
      ValueError: If no config path can be determined
  """
  try:
    # First try to get config path from data source settings
    if data_source:
      try:
        settings = data_source.get_manger_config_settings()
        config_folder = settings.get("headless_server", {}).get("config_folder")
        if config_folder:
          config_path = os.path.join(config_folder, "Config.json")
          logger.info("Using config path from data source settings: %s", config_path)
          return config_path
      except Exception as e:
        logger.warning("Failed to get config path from data source: %s, falling back to environment", str(e))
  except Exception as e:
    logger.warning("Error accessing data source for config path: %s, falling back to environment", str(e))

  # Fall back to environment variable
  config_path = os.getenv('CONFIG_PATH')
  if config_path:
    logger.info("Using config path from environment: %s", config_path)
    return config_path

  # Final fallback for development/testing
  logger.warning("No config path found, using default fallback")
  raise ValueError("CONFIG_PATH not set in environment variables and no data source settings available")


def load_config(data_source=None) -> Dict[Any, Any]:
  """Load the headless config file"""
  config_path = get_config_path(data_source)
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


def save_config(config_data: Dict[Any, Any], data_source=None) -> None:
  """Save the headless config file"""
  config_path = get_config_path(data_source)

  try:
    json.dumps(config_data)
  except (TypeError, json.JSONDecodeError) as exc:
    raise ValueError("Invalid JSON data") from exc

  with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config_data, f, indent=2)


def create_rest_endpoints(app, data_source, templates_path="templates"):
  """
  Create all REST API endpoints for the FastAPI app

  Args:
      app: FastAPI application instance
      data_source: Data source instance for container operations (BaseDataSource)
      templates_path: Path to templates directory (default: "templates")
  """
  @app.get("/", include_in_schema=False)  # Main web interface, note do not add openapi metadata here
  async def get_root():
    """Serve the main web interface HTML page.

    Returns:
        HTMLResponse: The rendered api-index.html template    """
    template_path = f"{templates_path}/api-index.html"
    try:
      with open(template_path, encoding='utf-8') as f:
        return HTMLResponse(content=f.read())
    except FileNotFoundError:
      logger.error("Template not found: %s", template_path)
      return HTMLResponse(
          content=f"<html><body><h1>API Server Running</h1>"
                  f"<p>Template not found: {template_path}</p></body></html>",
          status_code=200
      )

  @app.get("/api/headless/config",
           summary="Get Configuration",
           description="Retrieve the current headless server configuration",
           tags=["Headless Instance Configuration"],
           responses={
               200: {"description": "Configuration retrieved successfully"},
               500: {"description": "Error loading configuration"}
           })
  async def get_config():
    """Get the current headless config"""
    try:
      result = load_config(data_source)
      return JSONResponse(content=result)    
    except ValueError as e:
      logger.error("Error in get_config endpoint: %s", str(e))
      raise HTTPException(status_code=500, detail=str(e)) from e
    except (ConnectionError, RuntimeError) as e:
      logger.error("Unexpected error in get_config endpoint: %s", str(e))
      raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}") from e

  @app.post("/api/headless/config",
            summary="Update Configuration",
            description="Update the headless server configuration",
            tags=["Headless Instance Configuration"],
            responses={
                200: {"description": "Configuration updated successfully"},
                400: {"description": "Invalid configuration data"}
            })
  async def update_config(config_data: Dict[Any, Any]):
    """Update the headless config"""
    try:
      save_config(config_data, data_source)
      return JSONResponse(content={"message": "Config updated successfully"})
    except ValueError as e:
      raise HTTPException(status_code=400, detail=str(e)) from e

  @app.post("/api/restart-container",
            summary="Restart Container",
            description="Restart the Docker container running the headless server",
            tags=["Container Control"],
            responses={
                200: {"description": "Container restart initiated successfully"},
                500: {"description": "Error restarting container"}
            })
  async def restart_container():
    """Restart the Docker container"""
    try:
      data_source.restart_container()
      return JSONResponse(content={"message": "Container restart initiated"})
    except (ConnectionError, RuntimeError) as e:
      logger.error("Error restarting container: %s", str(e))
      raise HTTPException(status_code=500, detail=str(e)) from e

  @app.post("/api/start-container",
            summary="Start Container",
            description="Start the Docker container running the headless server",
            tags=["Container Control"],
            responses={
                200: {"description": "Container start initiated or already running"},
                500: {"description": "Error starting container"}
            })
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

  @app.post("/api/stop-container",
            summary="Stop Container",
            description="Stop the Docker container running the headless server",
            tags=["Container Control"],
            responses={
                200: {"description": "Container stop initiated or already stopped"},
                500: {"description": "Error stopping container"}
            })
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

  @app.get("/api/manager/config/status",
           summary="Get Config Status",
           description="Get whether the app is using builtin or config file settings",
           tags=["Manager App Configuration"],
           responses={
               200: {"description": "Configuration status retrieved successfully"},
               500: {"description": "Error retrieving configuration status"}
           })
  async def get_config_status():
    """Get whether the app is using builtin or config file settings"""
    try:
      result = data_source.get_config_status()
      return JSONResponse(content=result)
    except Exception as e:
      logger.error("Error in get_config_status endpoint: %s", str(e))
      raise HTTPException(status_code=500, detail=str(e)) from e

  @app.get("/api/manager/config/settings",
           summary="Get Config Settings",
           description="Get current configuration settings",
           tags=["Manager App Configuration"],
           responses={
               200: {"description": "Configuration settings retrieved successfully"},
               500: {"description": "Error retrieving configuration settings"}
           })
  async def get_manger_config_settings():
    """Get current configuration settings"""
    try:
      result = data_source.get_manger_config_settings()
      return JSONResponse(content=result)
    except Exception as e:
      logger.error("Error in get_manger_config_settings endpoint: %s", str(e))
      raise HTTPException(status_code=500, detail=str(e)) from e

  @app.post("/api/manager/config/generate",
            summary="Generate Config File",
            description="Generate config file and switch to using it",
            tags=["Manager App Configuration"],
            responses={
                200: {"description": "Config file generated successfully"},
                500: {"description": "Error generating config file"}
            })
  async def generate_config():
    """Generate config file and switch to using it"""
    try:
      result = data_source.generate_config()
      return JSONResponse(content=result)
    except Exception as e:
      logger.error("Error generating config file: %s", str(e))
      raise HTTPException(status_code=500, detail=str(e)) from e
