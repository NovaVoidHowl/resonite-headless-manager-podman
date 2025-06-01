#!/usr/bin/env python3
"""
Standalone test server for Resonite Headless Manager API testing.

This script provides a test environment for the API layer with dummy/stub data,
allowing you to test the REST and WebSocket APIs in isolation from the actual
Podman container management system.

Features:
- Serves both REST and WebSocket APIs on port 8000
- Uses dummy data for all responses
- Simulates realistic Resonite headless server behavior
- Provides all endpoints from the real system
- Useful for frontend development and API testing

Usage:
    python test_server.py

The server will start on http://localhost:8000 with the same API structure
as the production system.
"""

import asyncio
import json
import logging
import random
from datetime import datetime
from typing import Any, Dict, List

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Resonite Headless Manager API Test Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files if they exist
try:
  app.mount("/static", StaticFiles(directory="../static"), name="static")
except RuntimeError:
  logger.warning("Static directory not found, skipping static file serving")


# =============================================================================
# DUMMY DATA GENERATORS
# =============================================================================

class DummyDataGenerator:
  """Generates realistic dummy data for testing"""

  def __init__(self):
    self.start_time = datetime.now()
    self.user_names = [
        "Alice_VR", "Bob_Builder", "Charlie_Explorer", "Diana_Crafter",
        "Eve_Artist", "Frank_Scientist", "Grace_Designer", "Henry_Musician",
        "Iris_Developer", "Jack_Gamer", "Kate_Educator", "Leo_Architect"
    ]
    self.world_names = [
        "Crystal Caverns", "Neon Nexus", "Forest Haven", "Sky Palace",
        "Underground Labs", "Mystic Gardens", "Cyber City", "Ocean Depths",
        "Desert Oasis", "Arctic Station", "Volcano Base", "Cloud Kingdom"
    ]
    self.banned_users = [
        {"username": "TrollUser123", "id": "U-troll123", "reason": "Harassment"},
        {"username": "SpamBot", "id": "U-spam456", "reason": "Spamming"},
        {"username": "BadActor", "id": "U-bad789", "reason": "Inappropriate content"}
    ]
    self.friend_requests = [
        {"username": "NewFriend1", "id": "U-friend001"},
        {"username": "BestBuddy", "id": "U-friend002"},
        {"username": "CoolPlayer", "id": "U-friend003"}
    ]
    self.container_logs = [
        "Starting Resonite headless server...",
        "Loading world data...",
        "Initializing physics engine...",
        "Starting network services...",
        "Server ready for connections",
        f"{datetime.now().isoformat()}: User connected: Alice_VR",
        f"{datetime.now().isoformat()}: World loaded: Crystal Caverns",
        f"{datetime.now().isoformat()}: Network sync established",
        f"{datetime.now().isoformat()}: Asset cache updated",
        f"{datetime.now().isoformat()}: User activity detected"
    ]

  def get_cpu_usage(self) -> float:
    """Generate realistic CPU usage between 20-80%"""
    base = 35.0
    variation = random.uniform(-15.0, 25.0)
    return max(5.0, min(95.0, base + variation))

  def get_memory_info(self) -> Dict[str, Any]:
    """Generate realistic memory usage"""
    total_gb = 16.0
    used_percent = random.uniform(30.0, 75.0)
    used_gb = (total_gb * used_percent) / 100.0

    return {
        "percent": round(used_percent, 1),
        "used": f"{used_gb:.1f}GB",
        "total": f"{total_gb:.1f}GB"
    }

  def get_container_status(self) -> Dict[str, Any]:
    """Generate container status"""
    return {
        "status": "running",
        "name": "resonite-headless",
        "id": "abc123def456",
        "image": "registry.resonite.io/resonite-headless:latest"
    }

  def get_worlds_data(self) -> List[Dict[str, Any]]:
    """Generate realistic worlds data"""
    num_worlds = random.randint(1, 4)
    worlds = []

    for _ in range(num_worlds):
      world_name = random.choice(self.world_names)
      users_count = random.randint(1, 8)
      max_users = random.randint(max(users_count, 5), 20)
      present_users = random.randint(1, users_count)

      # Generate session ID
      session_id = f"S-{random.randint(100000, 999999)}"

      # Calculate uptime
      uptime_minutes = random.randint(5, 240)
      uptime = f"{uptime_minutes // 60}h {uptime_minutes % 60}m" if uptime_minutes >= 60 else f"{uptime_minutes}m"

      world = {
          "name": world_name,
          "sessionId": session_id,
          "users": users_count,
          "present": present_users,
          "maxUsers": max_users,
          "uptime": uptime,
          "accessLevel": random.choice(["Private", "Friends", "FriendsOfFriends", "RegisteredUsers", "Anyone"]),
          "mobileFriendly": random.choice([True, False]),
          "description": f"A beautiful {world_name.lower()} world for exploration and creativity",
          "tags": random.sample(["Creative", "Social", "Educational", "Gaming", "Art", "Music"], 2),
          "user_count": {
              "connected_to_instance": users_count,
              "present": present_users,
              "max_users": max_users
          },
          "access_level": random.choice(["Private", "Friends", "FriendsOfFriends", "RegisteredUsers", "Anyone"]),
          "mobile_friendly": random.choice([True, False])
      }
      worlds.append(world)

    return worlds

  def get_users_data(self) -> List[Dict[str, Any]]:
    """Generate users data for a world"""
    num_users = random.randint(2, 6)
    users = []

    for _ in range(num_users):
      username = random.choice(self.user_names)
      user = {
          "username": username,
          "id": f"U-{random.randint(100000, 999999)}",
          "role": random.choice(["Guest", "Builder", "Moderator", "Admin"]),
          "sessionTime": f"{random.randint(5, 120)}m",
          "isPresent": random.choice([True, False]),
          "platform": random.choice(["Desktop", "VR", "Mobile"])
      }
      users.append(user)

    return users

  def get_server_status(self) -> Dict[str, Any]:
    """Generate server status"""
    uptime = datetime.now() - self.start_time
    uptime_str = str(uptime).split('.')[0]  # Remove microseconds

    return {
        "status": "running",
        "uptime": uptime_str,
        "version": "2024.3.28",
        "worlds_active": len(self.get_worlds_data()),
        "total_users": sum(world["users"] for world in self.get_worlds_data()),
        "server_time": datetime.now().isoformat()
    }

  def get_random_log_line(self) -> str:
    """Generate a random log line"""
    log_types = [
        f"[{datetime.now().strftime('%H:%M:%S')}] User joined: {random.choice(self.user_names)}",
        f"[{datetime.now().strftime('%H:%M:%S')}] User left: {random.choice(self.user_names)}",
        f"[{datetime.now().strftime('%H:%M:%S')}] World save completed",
        f"[{datetime.now().strftime('%H:%M:%S')}] Network sync update",
        f"[{datetime.now().strftime('%H:%M:%S')}] Asset cache refreshed",
        f"[{datetime.now().strftime('%H:%M:%S')}] Physics step: 60 FPS",
        f"[{datetime.now().strftime('%H:%M:%S')}] Memory usage: {self.get_memory_info()['percent']}%",
        f"[{datetime.now().strftime('%H:%M:%S')}] CPU usage: {self.get_cpu_usage():.1f}%"
    ]
    return random.choice(log_types)

  def get_headless_config(self) -> Dict[str, Any]:
    """Generate realistic headless config"""
    return {
        "startWorlds": [
            {
                "sessionName": "Test World 1",
                "description": "A test world for API testing",
                "maxUsers": 16,
                "accessLevel": "RegisteredUsers",
                "mobileFriendly": True,
                "tags": ["test", "api", "development"],
                "parentSessionIds": [],
                "awayKickMinutes": 60,
                "hideFromListing": False,
                "autoRecover": True
            }
        ],
        "dataFolder": "/app/data",
        "cacheFolder": "/app/cache",
        "logFolder": "/app/logs",
        "enableGCOptimization": True,
        "backgroundWorkers": 4,
        "autoSaveInterval": 300,
        "maxConcurrentAssetTransfers": 8,
        "useBinaryTransport": True,
        "maxUploadSpeed": 10000000
    }


# Initialize dummy data generator
dummy_data = DummyDataGenerator()


# =============================================================================
# CONNECTION MANAGERS FOR WEBSOCKETS
# =============================================================================

class ConnectionManager:
  """Manage WebSocket connections"""

  def __init__(self):
    self.active_connections: List[WebSocket] = []

  async def connect(self, websocket: WebSocket):
    await websocket.accept()
    self.active_connections.append(websocket)

  def disconnect(self, websocket: WebSocket):
    if websocket in self.active_connections:
      self.active_connections.remove(websocket)

  async def broadcast(self, message: dict):
    for connection in self.active_connections.copy():
      try:
        await connection.send_json(message)
      except Exception as e:
        logger.error("Error broadcasting to connection: %s", e)
        self.disconnect(connection)


# Create connection managers
logs_manager = ConnectionManager()
status_manager = ConnectionManager()
worlds_manager = ConnectionManager()
commands_manager = ConnectionManager()
cpu_manager = ConnectionManager()
memory_manager = ConnectionManager()
container_status_manager = ConnectionManager()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def safe_send_json(websocket: WebSocket, data: dict) -> bool:
  """Safely send JSON data over websocket"""
  try:
    if "timestamp" not in data:
      data["timestamp"] = datetime.now().isoformat()
    await websocket.send_json(data)
    return True
  except Exception as e:
    logger.debug("Error sending data: %s", e)
    return False


def add_timestamp(data: dict) -> dict:
  """Add timestamp to response data"""
  data["timestamp"] = datetime.now().isoformat()
  return data


# =============================================================================
# REST API ENDPOINTS
# =============================================================================

@app.get("/")
async def get_root():
  """Serve the main web interface HTML page"""
  try:
    with open("../../templates/api-index.html", encoding='utf-8') as f:
      return HTMLResponse(content=f.read())
  except FileNotFoundError:
    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head><title>Resonite Headless Manager API Test Server</title></head>
<body>
    <h1>Resonite Headless Manager API Test Server</h1>
    <p>This is a test server running with dummy data.</p>
    <p>Available endpoints:</p>
    <ul>
        <li><a href="/config">GET /config</a> - Get headless config</li>
        <li>POST /config - Update headless config</li>
        <li>POST /api/start-container - Start container</li>
        <li>POST /api/stop-container - Stop container</li>
        <li>POST /api/restart-container - Restart container</li>
        <li>GET /api/config/status - Get config status</li>
        <li>GET /api/config/settings - Get config settings</li>
        <li>POST /api/config/generate - Generate config</li>
    </ul>
    <p>WebSocket endpoints:</p>
    <ul>
        <li>ws://localhost:8000/ws/logs - Container logs</li>
        <li>ws://localhost:8000/ws/command - Commands</li>
        <li>ws://localhost:8000/ws/worlds - Worlds monitoring</li>
        <li>ws://localhost:8000/ws/cpu - CPU monitoring</li>
        <li>ws://localhost:8000/ws/memory - Memory monitoring</li>
        <li>ws://localhost:8000/ws/container_status - Container status</li>
        <li>ws://localhost:8000/ws/status - Server status</li>
        <li>ws://localhost:8000/ws/heartbeat - Heartbeat</li>
    </ul>
</body>
</html>
        """)


@app.get("/favicon.ico")
async def get_favicon():
  """Serve the favicon.ico file"""
  try:
    with open("../../templates/favicon.ico", encoding='utf-8') as f:
      return HTMLResponse(content=f.read())
  except FileNotFoundError:
    return HTMLResponse(content="")


@app.get("/config")
async def get_config():
  """Get the current headless config"""
  try:
    config = dummy_data.get_headless_config()
    return JSONResponse(content=config)
  except Exception as e:
    logger.error("Error in get_config endpoint: %s", e)
    raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/config")
async def update_config(_config_data: Dict[Any, Any]):
  """Update the headless config"""
  try:
    # In real system, this would save the config
    # Here we just validate it's proper JSON
    logger.info("Config update received (dummy mode - not actually saving)")
    return JSONResponse(content={"message": "Config updated successfully (test mode)"})
  except Exception as e:
    raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/world-properties")
async def update_world_properties(data: dict):
  """Update world properties"""
  try:
    session_id = data.get('sessionId')
    if not session_id:
      raise HTTPException(status_code=400, detail="Session ID is required")

    logger.info("World properties update for session %s (dummy mode)", session_id)
    return JSONResponse(content={"message": "Properties updated successfully (test mode)"})
  except Exception as e:
    raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/restart-container")
async def restart_container():
  """Restart the container"""
  try:
    logger.info("Container restart requested (dummy mode)")    # Simulate some processing time
    await asyncio.sleep(0.5)
    return JSONResponse(content={"message": "Container restart initiated (test mode)"})
  except Exception as e:
    logger.error("Error restarting container: %s", e)
    raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/start-container")
async def start_container():
  """Start the container"""
  try:
    logger.info("Container start requested (dummy mode)")
    await asyncio.sleep(0.3)
    return JSONResponse(content={"message": "Container start initiated (test mode)"})
  except Exception as e:
    logger.error("Error starting container: %s", e)
    raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/stop-container")
async def stop_container():
  """Stop the container"""
  try:
    logger.info("Container stop requested (dummy mode)")
    await asyncio.sleep(0.3)
    return JSONResponse(content={"message": "Container stop initiated (test mode)"})
  except Exception as e:
    logger.error("Error stopping container: %s", e)
    raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/config/status")
async def get_config_status():
  """Get whether the app is using builtin or config file settings"""
  try:
    result = {
        "using_config_file": True  # Dummy mode always reports using config file
    }
    return JSONResponse(content=result)
  except Exception as e:
    logger.error("Error in get_config_status endpoint: %s", e)
    raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/config/settings")
async def get_config_settings():
  """Get current configuration settings"""
  try:
    result = {
        "using_config_file": True,
        "config_file_path": "config.json",
        "settings": {
            "cache": {
                "worlds_interval": 10,
                "status_interval": 10,
                "sessionurl_interval": 30,
                "sessionid_interval": 30,
                "users_interval": 5,
                "listbans_interval": 60
            }
        }
    }
    return JSONResponse(content=result)
  except Exception as e:
    logger.error("Error in get_config_settings endpoint: %s", e)
    raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/config/generate")
async def generate_config():
  """Generate config file"""
  try:
    result = {
        "status": "created",
        "message": "Generated new config file at config.json (test mode)"
    }
    return JSONResponse(content=result)
  except Exception as e:
    logger.error("Error generating config file: %s", e)
    raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# WEBSOCKET ENDPOINTS
# =============================================================================

@app.websocket("/ws/logs")
async def logs_endpoint(websocket: WebSocket):
  """Handle container logs WebSocket connections"""
  await logs_manager.connect(websocket)
  logger.info("Logs WebSocket connected")

  try:
    # Send recent logs
    for log_line in dummy_data.container_logs:
      await safe_send_json(websocket, {
          "type": "container_output",
          "output": log_line,
          "timestamp": datetime.now().isoformat()
      })

    # Keep connection alive and send periodic log updates
    while True:
      await asyncio.sleep(random.uniform(2.0, 8.0))  # Random interval between logs
      log_line = dummy_data.get_random_log_line()
      await logs_manager.broadcast({
          "type": "container_output",
          "output": log_line,
          "timestamp": datetime.now().isoformat()
      })

  except WebSocketDisconnect:
    logger.info("Logs WebSocket disconnected normally")
  except Exception as e:
    logger.error("Logs WebSocket error: %s", e)
  finally:
    logs_manager.disconnect(websocket)


@app.websocket("/ws/status")
async def status_endpoint(websocket: WebSocket):
  """Handle status monitoring WebSocket connections"""
  await status_manager.connect(websocket)
  logger.info("Status WebSocket connected")

  try:
    while True:
      data = await websocket.receive_text()
      message = json.loads(data)

      if message.get("type") == "get_status":
        status = add_timestamp({
            "type": "status_update",
            "status": dummy_data.get_server_status()
        })
        await safe_send_json(websocket, status)

  except WebSocketDisconnect:
    logger.info("Status WebSocket disconnected normally")
  except Exception as e:
    logger.error("Status WebSocket error: %s", e)
  finally:
    status_manager.disconnect(websocket)


@app.websocket("/ws/worlds")
async def worlds_endpoint(websocket: WebSocket):
  """Handle worlds list WebSocket connections"""
  await worlds_manager.connect(websocket)
  logger.info("Worlds WebSocket connected")

  try:
    while True:
      data = await websocket.receive_text()
      message = json.loads(data)

      if message.get("type") == "get_worlds":
        worlds_data = dummy_data.get_worlds_data()
        response = add_timestamp({
            "type": "worlds_update",
            "worlds_data": worlds_data,
            "output": worlds_data  # Legacy compatibility
        })
        await safe_send_json(websocket, response)

  except WebSocketDisconnect:
    logger.info("Worlds WebSocket disconnected normally")
  except Exception as e:
    logger.error("Worlds WebSocket error: %s", e)
  finally:
    worlds_manager.disconnect(websocket)


@app.websocket("/ws/command")
async def command_endpoint(websocket: WebSocket):
  """Handle command WebSocket connections"""
  await commands_manager.connect(websocket)
  logger.info("Command WebSocket connected")

  try:
    while True:
      data = await websocket.receive_text()
      message = json.loads(data)

      if message.get("type") == "command":
        command = message.get("command", "")
        logger.info("Received command: %s", command)

        # Handle different commands
        if command == "friendRequests":
          response = add_timestamp({
              "type": "command_response",
              "command": "friendRequests",
              "output": dummy_data.friend_requests
          })
        elif command == "users":
          response = add_timestamp({
              "type": "command_response",
              "command": "users",
              "output": dummy_data.get_users_data()
          })
        elif command == "worlds":
          response = add_timestamp({
              "type": "command_response",
              "command": "worlds",
              "output": dummy_data.get_worlds_data()
          })
        elif command == "listbans":
          response = add_timestamp({
              "type": "bans_update",
              "bans": dummy_data.banned_users
          })
        elif command == "status":
          response = add_timestamp({
              "type": "command_response",
              "command": "status",
              "output": dummy_data.get_server_status()
          })
        elif command.startswith("acceptFriendRequest"):
          response = add_timestamp({
              "type": "command_response",
              "command": "acceptFriendRequest",
              "output": "Friend request accepted (test mode)"
          })
        elif command.startswith("kick") or command.startswith("ban"):
          response = add_timestamp({
              "type": "command_response",
              "command": command.split()[0],
              "output": f"Command executed: {command} (test mode)"
          })
        else:
          response = add_timestamp({
              "type": "command_response",
              "command": command,
              "output": f"Command '{command}' executed (test mode)"
          })

        await safe_send_json(websocket, response)

  except WebSocketDisconnect:
    logger.info("Command WebSocket disconnected normally")
  except Exception as e:
    logger.error("Command WebSocket error: %s", e)
  finally:
    commands_manager.disconnect(websocket)


@app.websocket("/ws/heartbeat")
async def heartbeat_endpoint(websocket: WebSocket):
  """Handle heartbeat connections"""
  await websocket.accept()
  logger.info("Heartbeat WebSocket connected")

  try:
    while True:
      await asyncio.sleep(30)  # Send heartbeat every 30 seconds
      await websocket.send_json({
          "type": "heartbeat",
          "timestamp": datetime.now().isoformat()
      })
  except WebSocketDisconnect:
    logger.info("Heartbeat WebSocket disconnected normally")
  except Exception as e:
    logger.error("Heartbeat WebSocket error: %s", e)


@app.websocket("/ws/cpu")
async def cpu_endpoint(websocket: WebSocket):
  """Handle CPU monitoring WebSocket connections"""
  await cpu_manager.connect(websocket)
  logger.info("CPU WebSocket connected")

  try:
    while True:
      cpu_usage = dummy_data.get_cpu_usage()
      await safe_send_json(websocket, {
          "type": "cpu_update",
          "cpu_usage": cpu_usage
      })
      await asyncio.sleep(1)  # Update every second

  except WebSocketDisconnect:
    logger.info("CPU WebSocket disconnected normally")
  except Exception as e:
    logger.error("CPU WebSocket error: %s", e)
  finally:
    cpu_manager.disconnect(websocket)


@app.websocket("/ws/memory")
async def memory_endpoint(websocket: WebSocket):
  """Handle memory monitoring WebSocket connections"""
  await memory_manager.connect(websocket)
  logger.info("Memory WebSocket connected")

  try:
    while True:
      memory_info = dummy_data.get_memory_info()
      await safe_send_json(websocket, {
          "type": "memory_update",
          "memory_percent": memory_info["percent"],
          "memory_used": memory_info["used"],
          "memory_total": memory_info["total"]
      })
      await asyncio.sleep(1)  # Update every second

  except WebSocketDisconnect:
    logger.info("Memory WebSocket disconnected normally")
  except Exception as e:
    logger.error("Memory WebSocket error: %s", e)
  finally:
    memory_manager.disconnect(websocket)


@app.websocket("/ws/container_status")
async def container_status_endpoint(websocket: WebSocket):
  """Handle container status WebSocket connections"""
  await container_status_manager.connect(websocket)
  logger.info("Container Status WebSocket connected")

  try:
    while True:
      data = await websocket.receive_text()
      message = json.loads(data)

      if message.get("type") == "get_container_status":
        status = add_timestamp({
            "type": "container_status_update",
            "status": dummy_data.get_container_status()
        })
        await safe_send_json(websocket, status)

  except WebSocketDisconnect:
    logger.info("Container Status WebSocket disconnected normally")
  except Exception as e:
    logger.error("Container Status WebSocket error: %s", e)
  finally:
    container_status_manager.disconnect(websocket)


# =============================================================================
# STARTUP AND MAIN
# =============================================================================

@app.on_event("startup")
async def startup_event():
  """Initialize test server"""
  logger.info("Starting Resonite Headless Manager API Test Server")
  logger.info("Server running with dummy data for testing")
  logger.info("Available at: http://localhost:8000")


@app.on_event("shutdown")
async def shutdown_event():
  """Clean up resources when server shuts down"""
  logger.info("Test server shutdown complete")


if __name__ == "__main__":
  print("\n" + "=" * 70)
  print("🧪 Resonite Headless Manager API Test Server")
  print("=" * 70)
  print("Starting test server with dummy data...")
  print("Server will be available at: http://localhost:8000")
  print("API documentation: http://localhost:8000")
  print("Press Ctrl+C to stop")
  print("=" * 70 + "\n")

  uvicorn.run(
      app,
      host="0.0.0.0",
      port=8000,
      log_level="info",
      access_log=True
  )
