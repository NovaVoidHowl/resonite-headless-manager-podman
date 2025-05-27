# WebSocket API Documentation

The application exposes a WebSocket API that can be used to interact with the Resonite headless server programmatically.
This enables you to create custom clients or automation tools.

## Connection

The application provides multiple WebSocket endpoints:

- `ws://your-server-ip:8000/ws/command` - For sending commands to the server
- `ws://your-server-ip:8000/ws/worlds` - For worlds monitoring
- `ws://your-server-ip:8000/ws/status` - For status monitoring
- `ws://your-server-ip:8000/ws/logs` - For container logs monitoring
- `ws://your-server-ip:8000/ws/heartbeat` - Heartbeat connection to keep other WebSockets alive

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

### 2. Status Request

Get container status and system metrics:

```json
{
  "type": "get_status"
}
```

Returns CPU usage, memory usage, and container status information.

### 3. Worlds Request

Get information about all running worlds:

```json
{
  "type": "get_worlds"
}
```

### 4. Logs Request

Get container logs:

```json
{
  "type": "get_logs"
}
```

## Response Formats

The server sends different types of responses based on the request:

### 1. Command Response

```json
{
  "type": "command_response",
  "command": "original_command",
  "output": "command_output"
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
  ]
}
```

### 3. Status Update

Response to status request:

```json
{
  "type": "status_update",
  "status": {
    "status": "running",
    "cpu_usage": "5.2",
    "memory_percent": "45.3",
    "memory_used": "4.2GB",
    "memory_total": "16.0GB",
    "name": "container_name",
    "id": "container_id",
    "image": "container_image"
  }
}
```

### 4. Worlds Update

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
          "userId": "U-xxx",
          "present": true,
          "ping": 50,
          "fps": 72.5,
          "silenced": false
        }
      ]
    }
  ]
}
```

### 5. Logs Update

Response to logs request:

```json
{
  "type": "logs_update",
  "output": "container logs content"
}
```

### 6. Container Output

Real-time container output messages:

```json
{
  "type": "container_output",
  "output": "output_text",
  "timestamp": "2025-05-27T12:34:56.789"
}
```

### 7. Error Response

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

- `GET /config` - Get the current headless server configuration
- `POST /config` - Update the headless server configuration

## Additional Features

- Real-time monitoring of container status, resource usage, and logs
- Automatic reconnection handling
- Connection state management
- CORS support for web interface integration
- Heartbeat mechanism to keep connections alive
