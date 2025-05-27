# WebSocket API Documentation

The application exposes a WebSocket API that can be used to interact with the Resonite headless server programmatically.
This enables you to create custom clients or automation tools.

## Connection

Connect to the WebSocket endpoint at `ws://your-server-ip:8000/ws`

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
    "cpu_usage": "5.2",
    "memory_percent": "45.3",
    "memory_used": "4.2GB",
    "memory_total": "16.0GB",
    // Additional container status information
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

### 5. Error Response

When an error occurs:

```json
{
  "type": "error",
  "message": "Error description"
}
```

## Real-time Updates

The WebSocket connection also receives real-time container output messages:

```json
{
  "type": "container_output",
  "output": "output_text"
}
```