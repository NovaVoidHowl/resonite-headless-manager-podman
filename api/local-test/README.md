# API Test Server

This directory contains a standalone test server for the Resonite Headless Manager API that allows testing the REST and
WebSocket APIs in isolation with dummy/stub data.

## Purpose

The test server provides:

- **Isolated API Testing**: Test the API layer without needing actual Podman containers or Resonite servers
- **Frontend Development**: Develop and test frontend applications against realistic dummy data
- **API Documentation**: Live demonstration of all available endpoints
- **Integration Testing**: Validate API contract compliance

## Features

- ✅ **Complete API Coverage**: Implements all REST and WebSocket endpoints from the production system
- ✅ **Realistic Data**: Generates believable dummy data that mimics real Resonite server responses
- ✅ **Real-time Updates**: WebSocket endpoints provide live data streams with simulated changes
- ✅ **Same Port Structure**: Runs on port 8000 just like the production system
- ✅ **CORS Enabled**: Ready for cross-origin frontend development
- ✅ **Logging**: Comprehensive logging for debugging and monitoring

## Quick Start

### Prerequisites

```bash
# Install required dependencies
pip install fastapi uvicorn python-multipart
```

### Run the Test Server

```bash
# From the api/ directory
cd api
python test_server.py
```

The server will start on `http://localhost:8000` and display:

```
🧪 Resonite Headless Manager API Test Server
======================================================================
Starting test server with dummy data...
Server will be available at: http://localhost:8000
API documentation: http://localhost:8000
Press Ctrl+C to stop
======================================================================
```

## Available Endpoints

### REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Main web interface |
| `GET` | `/config` | Get headless server configuration |
| `POST` | `/config` | Update headless server configuration |
| `POST` | `/api/world-properties` | Update world properties |
| `POST` | `/api/restart-container` | Restart the container |
| `POST` | `/api/start-container` | Start the container |
| `POST` | `/api/stop-container` | Stop the container |
| `GET` | `/api/config/status` | Get config file usage status |
| `GET` | `/api/config/settings` | Get current configuration settings |
| `POST` | `/api/config/generate` | Generate new config file |

### WebSocket Endpoints

| Endpoint | Description |
|----------|-------------|
| `ws://localhost:8000/ws/logs` | Container logs streaming |
| `ws://localhost:8000/ws/command` | Command execution |
| `ws://localhost:8000/ws/worlds` | Worlds monitoring |
| `ws://localhost:8000/ws/cpu` | CPU usage monitoring |
| `ws://localhost:8000/ws/memory` | Memory usage monitoring |
| `ws://localhost:8000/ws/container_status` | Container status updates |
| `ws://localhost:8000/ws/status` | Server status monitoring |
| `ws://localhost:8000/ws/heartbeat` | Connection heartbeat |

## Dummy Data Generated

The test server generates realistic dummy data including:

### Worlds Data

- **World Names**: Crystal Caverns, Neon Nexus, Forest Haven, Sky Palace, etc.
- **User Counts**: Randomized realistic user counts and presence
- **Session IDs**: Properly formatted session identifiers
- **Properties**: Access levels, mobile-friendly flags, descriptions, tags
- **Uptime**: Simulated world uptime tracking

### User Data

- **Usernames**: Alice_VR, Bob_Builder, Charlie_Explorer, etc.
- **Roles**: Guest, Builder, Moderator, Admin
- **Session Time**: Realistic session duration tracking
- **Platform Info**: Desktop, VR, Mobile platform indicators

### System Metrics

- **CPU Usage**: Fluctuating between 20-80% with realistic patterns
- **Memory Usage**: Dynamic memory consumption with proper formatting
- **Container Status**: Running container with proper metadata
- **Logs**: Realistic server log messages with timestamps

### Server Management

- **Friend Requests**: Sample pending friend requests
- **Ban List**: Example banned users with reasons
- **Configuration**: Realistic headless server configuration

## Testing Examples

### Test REST Endpoints

```bash
# Get server configuration
curl http://localhost:8000/config

# Get config status
curl http://localhost:8000/api/config/status

# Start container (dummy)
curl -X POST http://localhost:8000/api/start-container
```

### Test WebSocket Endpoints

```javascript
// Connect to worlds endpoint
const ws = new WebSocket('ws://localhost:8000/ws/worlds');

ws.onopen = () => {
    // Request worlds data
    ws.send(JSON.stringify({ type: 'get_worlds' }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Worlds data:', data);
};
```

### Test Command Execution

```javascript
// Connect to command endpoint
const cmdWs = new WebSocket('ws://localhost:8000/ws/command');

cmdWs.onopen = () => {
    // Send a command
    cmdWs.send(JSON.stringify({ 
        type: 'command', 
        command: 'friendRequests' 
    }));
};
```

## Integration with Frontend

The test server is designed to be a drop-in replacement for the production API server. Simply:

1. Start the test server: `python test_server.py`
2. Point your frontend to `http://localhost:8000`
3. All API calls will work with dummy data

This allows frontend development without requiring:

- Podman/Docker setup
- Resonite headless server
- Container orchestration
- Production configuration

## Customizing Dummy Data

The `DummyDataGenerator` class can be easily modified to:

- Add more realistic user names or world names
- Adjust data generation patterns
- Include specific test scenarios
- Modify response timing and frequencies

Example customization:

```python
# In test_server.py, modify the DummyDataGenerator class
def __init__(self):
    self.user_names = [
        "YourTestUser1", "YourTestUser2", "CustomUser"
    ]
    self.world_names = [
        "Your Test World", "Custom Environment"
    ]
```

## Development Workflow

1. **Start Test Server**: Run `python test_server.py`
2. **Develop Frontend**: Build your application against `localhost:8000`
3. **Test API Integration**: Verify all endpoint interactions work
4. **Switch to Production**: Change endpoint to production server when ready

## Troubleshooting

### Common Issues

**Import Errors**:
```bash
pip install fastapi uvicorn python-multipart
```

**Port Already in Use**:

- Kill other processes using port 8000
- Or modify the port in the `uvicorn.run()` call

**WebSocket Connection Issues**:

- Ensure your client connects to `ws://localhost:8000/ws/...`
- Check browser developer tools for connection errors

**Static Files Not Found**:

- The server will work without static files
- Warning message is displayed but doesn't affect API functionality

## Production vs Test Server

| Feature | Test Server | Production Server |
|---------|-------------|-------------------|
| Data Source | Generated dummy data | Real Podman containers |
| Container Control | Simulated responses | Actual container operations |
| Performance | Instant responses | Real operation timing |
| State Persistence | No persistence | Real state management |
| Resource Usage | Minimal | Production resource usage |

The test server is perfect for development and testing, while the production server handles real Resonite headless server management.
