# Development Server Setup

This directory contains scripts to easily run both the API test server and web UI server simultaneously for local
development and testing.

## Quick Start

### Windows

Double-click `run_dev_servers.bat` or run from command prompt:

```cmd
run_dev_servers.bat
```

### Linux/macOS

```bash
./run_dev_servers.sh
```

### Python (Cross-platform)

```bash
python run_dev_servers.py
```

## What it does

The development server launcher:

1. **Starts API Test Server** on port 8000

   - Uses stub data source (no real containers needed)
   - Provides all REST and WebSocket endpoints
   - API documentation available at <http://localhost:8000/docs>

2. **Starts Web UI Server** on port 8080

   - Serves the web interface
   - Connects to the API server for live testing

3. **Shows separate colored logs** for each server

   - API server logs in cyan
   - Web UI server logs in green
   - Timestamps and clear server identification

## Access Points

Once both servers are running:

- **Web Interface**: <http://localhost:8080>
- **API Server**: <http://localhost:8000>
- **API Documentation**: <http://localhost:8000/docs>
- **OpenAPI JSON**: <http://localhost:8000/openapi.json>

## Features

- ✅ **No real containers needed** - uses stub data for testing
- ✅ **Automatic startup** of both servers
- ✅ **Graceful shutdown** with Ctrl+C
- ✅ **Colored logs** for easy identification
- ✅ **Cross-platform** compatibility
- ✅ **Error handling** and status monitoring

## Stopping the Servers

Press `Ctrl+C` in the terminal to gracefully stop both servers.

## Development Workflow

1. Start the development servers
2. Open <http://localhost:8080> in your browser
3. Make changes to the web UI or API code
4. Restart the servers to see changes
5. Use <http://localhost:8000/docs> to test API endpoints directly

## Troubleshooting

### Port Already in Use

If you get port errors, make sure no other applications are using:

- Port 8000 (API server)
- Port 8080 (Web UI server)

### Python Not Found

Make sure Python is installed and available in your PATH.

### File Not Found Errors

Run the script from the root directory of the resonite-headless-manager repository.

## File Structure

```text
resonite-headless-manager/
├── run_dev_servers.py      # Main Python script
├── run_dev_servers.bat     # Windows batch file
├── run_dev_servers.sh      # Linux/macOS shell script
├── webserver.py            # Web UI server
└── api/local-test/
    └── test_server_new.py   # API test server
```
