#!/usr/bin/env python3
"""
Test server for Resonite Headless Manager API testing.

This script uses the existing API infrastructure with a stub data source,
providing a test environment with dummy/stub data for testing the REST and
WebSocket APIs in isolation from the actual Podman container management system.

Features:
- Uses the production API infrastructure (APIManager)
- Uses stub data source for realistic dummy data
- Serves both REST and WebSocket APIs on port 8000
- Provides all endpoints from the real system
- Useful for frontend development and API testing

Usage:
    python test_server.py

The server will start on http://localhost:8000 with the same API structure
as the production system.
"""

import os
import sys
import logging
import uvicorn

# Add parent directories to path to import our modules
current_dir = os.path.dirname(__file__)
api_dir = os.path.join(current_dir, '..')
root_dir = os.path.join(current_dir, '..', '..')

sys.path.insert(0, api_dir)
sys.path.insert(0, root_dir)

# Now import our modules after path setup
from api_manager import APIManager  # noqa: E402 # pylint: disable=wrong-import-position,import-error
from data_sources.factory import DataSourceFactory  # noqa: E402 # pylint: disable=wrong-import-position


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_server():
  """
  Create a test server using the existing API infrastructure with stub data source.

  Returns:
      FastAPI: Configured FastAPI application with all endpoints
  """
  logger.info("Creating test server with stub data source...")

  # Calculate the templates path relative to the project root
  project_root = os.path.join(current_dir, '..', '..')
  templates_path = os.path.join(project_root, 'templates')
  logger.info("Using templates path: %s", templates_path)

  # Create a stub data source for testing
  data_source = DataSourceFactory.create_data_source(
      source_type="stub",
      container_name="resonite-headless-test"
  )

  # Create the API manager with our stub data source and templates path
  api_manager = APIManager(data_source, templates_path=templates_path)

  # Get the configured FastAPI app
  app = api_manager.get_app()

  logger.info("Test server created with data source: %s",
              data_source.get_data_source_info()["type"])

  return app


def main():
  """Main function to start the test server."""
  print("\n" + "=" * 70)
  print("🧪 Resonite Headless Manager API Test Server")
  print("=" * 70)
  print("Using production API infrastructure with stub data source...")
  print("Server will be available at: http://localhost:8000")
  print("Press Ctrl+C to stop")
  print("=" * 70 + "\n")

  # Create the test server
  app = create_test_server()

  # Start the server
  uvicorn.run(
      app,
      host="127.0.0.1",
      port=8000,
      log_level="info",
      access_log=True
  )


if __name__ == "__main__":
  main()
