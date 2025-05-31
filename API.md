# WebSocket API Documentation

The application exposes a WebSocket API that can be used to interact with the Resonite headless server programmatically.
This enables you to create custom clients or automation tools.

## Connection

The application provides multiple WebSocket endpoints:

- `ws://your-server-ip:8000/ws/command` - For sending commands to the server
- `ws://your-server-ip:8000/ws/worlds` - For worlds monitoring
- `ws://your-server-ip:8000/ws/logs` - For container logs streaming
- `ws://your-server-ip:8000/ws/cpu` - For CPU usage monitoring
- `ws://your-server-ip:8000/ws/memory` - For memory usage monitoring
- `ws://your-server-ip:8000/ws/container_status` - For container status monitoring
- `ws://your-server-ip:8000/ws/heartbeat` - Heartbeat connection to keep other WebSockets alive
- `ws://your-server-ip:8000/ws/status` - For status monitoring and updates

## Message Format

All messages use JSON format with a `type` field indicating the operation:

```json
{
  "type": "command_type",
  "command": "command_string"  // For command type messages
}
```

## Available Commands

The WebSocket API supports the following message types:

### 1. Command Messages

Send a command to the headless server:

```json
{
  "type": "command",
  "command": "command_string"
}
```

Special commands:

- `listbans` - Returns a structured list of banned users
- `friendRequests` - Returns a list of pending friend requests
- `worlds` - Returns information about all running worlds
- `status` - Returns current server status
- `users` - Returns list of users
- `sessionUrl` - Returns session URL
- `sessionID` - Returns session ID

### 2. Container Status Request

Get container status:

```json
{
  "type": "get_container_status"
}
```

Returns container status information.

### 3. Worlds Request

Get information about all running worlds:

```json
{
  "type": "get_worlds"
}
```

### 4. Status Request

Get server status:

```json
{
  "type": "get_status"
}
```

## Resource Monitoring

### 1. CPU Usage

The CPU endpoint automatically streams CPU usage updates every second. No request message needed.

### 2. Memory Usage

The memory endpoint automatically streams memory usage updates every second. No request message needed.

### 3. Container Logs

The logs endpoint automatically streams log updates in real-time. Upon connection, it sends recent logs
and then streams new logs as they occur.

## Response Formats

The server sends different types of responses based on the request:

### 1. Command Response

```json
{
  "type": "command_response",
  "command": "original_command",
  "output": "command_output",
  "timestamp": "2025-05-31T12:34:56.789Z"
}
```

### 2. Bans Update

Response to `listbans` command:

```json
{
  "type": "bans_update",
  "bans": [
    {
      "username": "banned_user",
      "userId": "U-xxx"
    }
  ],
  "timestamp": "2025-05-31T12:34:56.789Z"
}
```

### 3. CPU Update

Automatic updates from the CPU endpoint:

```json
{
  "type": "cpu_update",
  "cpu_usage": 5.2
}
```

### 4. Memory Update

Automatic updates from the memory endpoint:

```json
{
  "type": "memory_update",
  "memory_percent": 45.3,
  "memory_used": "4.2GB",
  "memory_total": "16.0GB"
}
```

### 5. Container Status Update

Response to container status request:

```json
{
  "type": "container_status_update",
  "status": {
    "status": "running",
    "name": "container_name",
    "id": "container_id",
    "image": "container_image"
  }
}
```

### 6. Worlds Update

Response to worlds request:

```json
{
  "type": "worlds_update",
  "output": [
    {
      "name": "World Name",
      "sessionId": "S-xxx",
      "users": 2,
      "present": 2,
      "maxUsers": 10,
      "uptime": "2 hours 30 minutes",
      "accessLevel": "Anyone",
      "hidden": false,
      "mobileFriendly": true,
      "description": "World description",
      "tags": "tag1,tag2",
      "users_list": [
        {
          "username": "User1",
          "id": "U-xxx",
          "role": "User",
          "present": true,
          "ping": 50,
          "fps": 72.5,
          "silenced": false
        }
      ]
    }
  ],
  "timestamp": "2025-05-31T12:34:56.789Z",
  "cached": true // Optional, present when response is from cache
}
```

### 7. Container Output

Real-time container log messages:

```json
{
  "type": "container_output",
  "output": "output_text",
  "timestamp": "2025-05-31T12:34:56.789Z"
}
```

### 8. Error Response

When an error occurs:

```json
{
  "type": "error",
  "message": "Error description"
}
```

## HTTP Endpoints

The application also provides REST endpoints:

### 1. Configuration Management

#### Configuration File Management

- `GET /api/config/status` - Check if using config file or built-in settings

```json
{
  "using_config_file": true
}
```

- `GET /api/config/settings` - Get current configuration settings

```json
{
  "using_config_file": true,
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
```

- `POST /api/config/generate` - Generate config.json file if not exists

```json
{
  "status": "created",
  "message": "Generated new config file at config.json"
}
```

or if config exists:

```json
{
  "status": "unchanged",
  "message": "Config file already exists and is being used"
}
```

#### Headless Server Configuration

- `GET /config` - Get the current headless server configuration
- `POST /config` - Update the headless server configuration

### 2. Container Control

- `POST /api/start-container` - Start the container
- `POST /api/stop-container` - Stop the container
- `POST /api/restart-container` - Restart the container

### 3. World Management

- `POST /api/world-properties` - Update world properties (requires session ID)

## Additional Features

- Real-time streaming of CPU usage, memory usage, and container logs
- Separate endpoints for different monitoring concerns
- Automatic reconnection handling
- Connection state management
- CORS support for web interface integration
- Heartbeat mechanism to keep connections alive
- Request-based container status updates to reduce API load
- Command caching with configurable intervals
- Cache invalidation hooks (e.g., ban/unban commands invalidate ban list cache)
