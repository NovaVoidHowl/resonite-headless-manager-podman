let ws;
const output = document.getElementById('output');
const commandInput = document.getElementById('command-input');
const statusDiv = document.getElementById('status');

let friendRequestsInterval = 5 * 60 * 1000; // Default 5 minutes
let friendRequestsTimer = null;
let deniedFriendRequests = new Set(JSON.parse(localStorage.getItem('deniedFriendRequests') || '[]'));

let bannedUsersInterval = 5 * 60 * 1000; // Default 5 minutes
let bannedUsersTimer = null;

// Add this constant at the top of the file with other constants
const AVAILABLE_ROLES = [
  'Spectator',
  'Guest',
  'Builder',
  'Moderator',
  'Admin'
];

/**
 * Show the loading overlay during async operations
 */
function showLoadingOverlay() {
  document.querySelector('.loading-overlay').classList.remove('hidden');
}

/**
 * Hide the loading overlay when operations complete
 */
function hideLoadingOverlay() {
  document.querySelector('.loading-overlay').classList.add('hidden');
}

/**
 * Displays an error message to the user in a toast notification
 * @param {string} message - The error message to display
 * @param {number} duration - How long to show the message in milliseconds (default: 5000ms)
 */
function displayErrorMessage(message, duration = 5000) {
  const errorToast = document.querySelector('.error-toast');
  const errorMessage = document.querySelector('.error-toast-message');

  errorMessage.textContent = message;
  errorToast.classList.add('show');

  // Auto-hide after duration
  if (duration > 0) {
    setTimeout(() => {
      hideErrorMessage();
    }, duration);
  }
}

/**
 * Hides the error message toast
 */
function hideErrorMessage() {
  const errorToast = document.querySelector('.error-toast');
  errorToast.classList.remove('show');
}

/**
 * Shows a success message toast notification
 * @param {string} message - The success message to display
 * @param {number} duration - How long to show the message in milliseconds (default: 3000ms)
 */
function showSuccessMessage(message, duration = 3000) {
  const successToast = document.querySelector('.copy-success-message');

  successToast.textContent = message;
  successToast.classList.add('show');

  // Auto-hide after duration
  setTimeout(() => {
    successToast.classList.remove('show');
  }, duration);
}

document.addEventListener('DOMContentLoaded', function() {
  hideLoadingOverlay();

  // Set up error toast close button
  const closeButton = document.querySelector('.error-toast-close');
  if (closeButton) {
    closeButton.addEventListener('click', hideErrorMessage);
  }
});

// Update the connectToWebSocket function to show loading overlay
function connectToWebSocket(successCallback) {
  showLoadingOverlay(); // Show loading overlay while connecting
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${window.location.host}/ws`;

  if (ws) {
    ws.close();
  }

  ws = new WebSocket(wsUrl);

  ws.onopen = function(e) {
    hideLoadingOverlay(); // Hide loading overlay on successful connection
    updateStatus('Connected to server', 'running');
    console.log('WebSocket connection established');
    if (successCallback) {
      successCallback();
    }
  };

  ws.onmessage = function(event) {
    handleMessage(event.data);
  };

  ws.onclose = function(event) {
    hideLoadingOverlay(); // Hide loading overlay if connection closed
    console.log('WebSocket connection closed');
    updateStatus('Disconnected from server', 'stopped');

    // Try to reconnect after a delay
    setTimeout(() => {
      updateStatus('Reconnecting...', 'connecting');
      connectToWebSocket();
    }, 5000);
  };

  ws.onerror = function(error) {
    hideLoadingOverlay(); // Hide loading overlay on error
    displayErrorMessage('WebSocket error: ' + error.message); // Show error message
    console.error('WebSocket error:', error);
    updateStatus('Connection error', 'stopped');
  };
}

// Update the sendCommand function to handle errors
function sendCommand(command) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    displayErrorMessage('Not connected to server'); // Show error message
    return;
  }

  try {
    ws.send(command);
  } catch (error) {
    displayErrorMessage('Failed to send command: ' + error.message); // Show error message
    console.error('Error sending command:', error);
  }
}

// Update the sendWorldCommand function to show loading overlay
function sendWorldCommand(worldId, command, additionalData = {}) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    displayErrorMessage('Not connected to server'); // Show error message
    return;
  }

  const data = {
    world_id: worldId,
    command: command,
    ...additionalData
  };

  try {
    showLoadingOverlay(); // Show loading overlay during command execution
    ws.send(JSON.stringify(data));
  } catch (error) {
    hideLoadingOverlay(); // Hide loading overlay on error
    displayErrorMessage('Failed to send command: ' + error.message); // Show error message
    console.error('Error sending world command:', error);
  }
}

// Update the handleMessage function to handle different message types and formats
function handleMessage(data) {
  try {
    // Check for empty or undefined data
    if (!data) {
      console.log('Received empty WebSocket message');
      return;
    }

    // Handle binary data or Blob objects
    if (data instanceof Blob) {
      // Convert blob to text and then parse
      data.text().then(text => {
        try {
          // Check if the text is empty or whitespace
          if (!text || !text.trim()) {
            console.log('Received empty Blob message');
            return;
          }

          const message = JSON.parse(text);
          processJsonMessage(message);
        } catch (parseError) {
          console.error('Error parsing Blob message:', parseError);
          console.log('Raw message content:', text);
          displayErrorMessage('Failed to parse server message');
          hideLoadingOverlay(); // Ensure loading overlay is hidden on error
        }
      }).catch(error => {
        console.error('Error reading Blob data:', error);
        displayErrorMessage('Failed to process server message');
        hideLoadingOverlay(); // Ensure loading overlay is hidden on error
      });
      return;
    }

    // For string data, check if it's empty
    if (typeof data === 'string' && !data.trim()) {
      console.log('Received empty string message');
      return;
    }

    // Handle string data - try to parse as JSON
    const message = JSON.parse(data);
    processJsonMessage(message);
  } catch (error) {
    console.error('Error parsing message:', error);
    console.log('Raw message content:', typeof data === 'string' ? data : '[non-string data]');
    displayErrorMessage('Failed to parse server message');
    hideLoadingOverlay(); // Ensure loading overlay is hidden on error
  }
}

// Update the processJsonMessage function to handle all structured data types
function processJsonMessage(message) {
  // Make sure message is an object
  if (!message || typeof message !== 'object') {
    console.error('Invalid message format:', message);
    hideLoadingOverlay();
    return;
  }

  // Handle different message types
  if (message.type === 'status' || message.type === 'status_update') {
    // Status message
    updateStatus(message.data || message.status);
    hideLoadingOverlay();

  } else if (message.type === 'worlds' || message.type === 'worlds_update') {
    // Worlds list message
    hideLoadingOverlay(); // Hide loading overlay when worlds data is received
    updateWorlds(message.data || message.worlds);

  } else if (message.type === 'world_details') {
    // World details message
    hideLoadingOverlay(); // Hide loading overlay when world details are received
    handleWorldDetailsUpdate(message.data);

  } else if (message.type === 'command_response') {
    // Command response message
    hideLoadingOverlay(); // Hide loading overlay when command response is received

    // Handle success or failure
    if (message.status === 'success') {
      // Show success message if needed for certain commands
      if (message.data && message.data.message) {
        showSuccessMessage(message.data.message);
      }
    } else {
      displayErrorMessage(message.data?.error || 'Command failed'); // Show error message
    }

  } else if (message.type === 'container_output') {
    // Container output message with structured data
    if (message.info_type === 'users' && Array.isArray(message.user_list)) {
      // Handle structured user data
      displayUsersList(message.user_list);
    } else if (message.info_type === 'worlds' && Array.isArray(message.worlds_list)) {
      // Handle structured worlds data
      displayWorldsList(message.worlds_list);
    } else if (message.info_type === 'status' && message.status_data) {
      // Handle structured status data
      displayWorldStatus(message.status_data);
    } else if (message.output) {
      // Regular output (unstructured)
      appendOutput(message.output);
    }

  } else if (message.type === 'error') {
    // Error message
    hideLoadingOverlay(); // Hide loading overlay on error
    displayErrorMessage(message.data?.error || message.message || 'Unknown error'); // Show error message
  } else if (message.type === 'bans_update') {
    // Bans update message
    updateBansList(message.bans || []);
  } else if (message.content !== undefined) {
    // Handle config content response
    const configEditor = document.getElementById('config-editor');
    if (configEditor) {
      configEditor.value = message.content || '';
      hideLoadingOverlay();
    }
  }
}

/**
 * Append output to the console output element
 * @param {string} text - Text to append
 */
function appendOutput(text) {
  if (!output) return;

  // Check if we need to add a newline before appending
  if (output.innerHTML && !output.innerHTML.endsWith('\n') && !output.innerHTML.endsWith('<br>')) {
    output.innerHTML += '\n';
  }

  // Replace newlines with <br> for HTML display
  const formattedText = text.replace(/\n/g, '<br>');

  // Append the formatted text to the output element
  output.innerHTML += formattedText;

  // Auto-scroll to bottom
  output.scrollTop = output.scrollHeight;
}

/**
 * Display structured user data in a formatted way
 * @param {Array} users - Array of user objects with structured data
 */
function displayUsersList(users) {
  if (!Array.isArray(users) || users.length === 0) {
    appendOutput("No users found.");
    return;
  }

  // Create a formatted table for the console output
  let formattedOutput = "USERS LIST:\n";
  formattedOutput += "-".repeat(80) + "\n";
  formattedOutput += "Username".padEnd(20) + " | ";
  formattedOutput += "User ID".padEnd(20) + " | ";
  formattedOutput += "Role".padEnd(10) + " | ";
  formattedOutput += "Present".padEnd(8) + " | ";
  formattedOutput += "Ping".padEnd(8) + " | ";
  formattedOutput += "FPS".padEnd(8) + " | ";
  formattedOutput += "Silenced\n";
  formattedOutput += "-".repeat(80) + "\n";

  users.forEach(user => {
    formattedOutput += (user.name || "Unknown").padEnd(20).substring(0, 19) + " | ";
    formattedOutput += (user.user_id || "N/A").padEnd(20).substring(0, 19) + " | ";
    formattedOutput += (user.role || "Unknown").padEnd(10).substring(0, 9) + " | ";
    formattedOutput += (user.present ? "Yes" : "No").padEnd(8) + " | ";
    formattedOutput += (user.ping || "0 ms").padEnd(8) + " | ";
    formattedOutput += (user.fps ? user.fps.toString() : "0").padEnd(8) + " | ";
    formattedOutput += (user.silenced ? "Yes" : "No") + "\n";
  });

  formattedOutput += "-".repeat(80) + "\n";
  formattedOutput += `Total users: ${users.length}\n`;

  appendOutput(formattedOutput);
}

/**
 * Display structured worlds data in a formatted way
 * @param {Array} worlds - Array of world objects with structured data
 */
function displayWorldsList(worlds) {
  if (!Array.isArray(worlds) || worlds.length === 0) {
    appendOutput("No worlds found.");
    return;
  }

  // Create a formatted table for the console output
  let formattedOutput = "WORLDS LIST:\n";
  formattedOutput += "-".repeat(80) + "\n";
  formattedOutput += "Index".padEnd(6) + " | ";
  formattedOutput += "World Name".padEnd(25) + " | ";
  formattedOutput += "Users".padEnd(7) + " | ";
  formattedOutput += "Present".padEnd(8) + " | ";
  formattedOutput += "Max".padEnd(5) + " | ";
  formattedOutput += "Access Level".padEnd(15) + "\n";
  formattedOutput += "-".repeat(80) + "\n";

  worlds.forEach(world => {
    formattedOutput += (world.index !== undefined ? world.index.toString() : "?").padEnd(6) + " | ";
    formattedOutput += (world.name || "Unknown").padEnd(25).substring(0, 24) + " | ";
    formattedOutput += (world.users !== undefined ? world.users.toString() : "0").padEnd(7) + " | ";
    formattedOutput += (world.present !== undefined ? world.present.toString() : "0").padEnd(8) + " | ";
    formattedOutput += (world.maxUsers !== undefined ? world.maxUsers.toString() : "0").padEnd(5) + " | ";
    formattedOutput += (world.accessLevel || "Unknown").padEnd(15).substring(0, 14) + "\n";
  });

  formattedOutput += "-".repeat(80) + "\n";
  formattedOutput += `Total worlds: ${worlds.length}\n`;

  appendOutput(formattedOutput);
}

/**
 * Display structured world status data in a formatted way
 * @param {Object} status - World status object with structured data
 */
function displayWorldStatus(status) {
  if (!status || typeof status !== 'object') {
    appendOutput("No status data available.");
    return;
  }

  // Create a formatted output for the console
  let formattedOutput = "WORLD STATUS:\n";
  formattedOutput += "-".repeat(80) + "\n";

  // Basic info section
  formattedOutput += "Name:            " + (status.name || "Unknown") + "\n";
  formattedOutput += "Session ID:      " + (status.sessionId || "Unknown") + "\n";
  formattedOutput += "Users:           " + (status.users !== undefined ? status.users : "0") + "\n";
  formattedOutput += "Present Users:   " + (status.present !== undefined ? status.present : "0") + "\n";
  formattedOutput += "Max Users:       " + (status.maxUsers !== undefined ? status.maxUsers : "0") + "\n";
  formattedOutput += "Uptime:          " + (status.uptime || "Unknown") + "\n";
  formattedOutput += "Access Level:    " + (status.accessLevel || "Unknown") + "\n";
  formattedOutput += "Hidden:          " + (status.hidden === true ? "Yes" : "No") + "\n";
  formattedOutput += "Mobile Friendly: " + (status.mobileFriendly === true ? "Yes" : "No") + "\n";

  // Description
  if (status.description) {
    formattedOutput += "Description:     " + status.description + "\n";
  }

  // Tags
  if (status.tags) {
    formattedOutput += "Tags:            " + status.tags + "\n";
  }

  // Users list
  if (status.usersList && Array.isArray(status.usersList) && status.usersList.length > 0) {
    formattedOutput += "\nUsers in world: " + status.usersList.join(", ") + "\n";
  }

  appendOutput(formattedOutput);
}

// Add function to copy world information to clipboard
function copyWorldInfo(worldId) {
  const worldCard = document.querySelector(`[data-world-id="${worldId}"]`);
  if (!worldCard) return;

  const worldName = worldCard.querySelector('.world-name').textContent;
  const worldAddress = `resonite://neos/${worldId}`;

  try {
    navigator.clipboard.writeText(worldAddress);
    showSuccessMessage(`Copied link to ${worldName}`);
  } catch (error) {
    displayErrorMessage('Failed to copy to clipboard');
    console.error('Clipboard error:', error);
  }
}

// Update saveWorldProperties to show success message
function saveWorldProperties() {
  const worldId = document.getElementById('world-properties').dataset.worldId;
  if (!worldId) return;

  showLoadingOverlay();

  const properties = {
    name: document.getElementById('world-name').value,
    description: document.getElementById('world-description').value,
    accessLevel: document.getElementById('world-access-level').value,
    maxUsers: parseInt(document.getElementById('world-max-users').value) || 16,
    hidden: document.getElementById('world-hidden').checked
  };

  sendWorldCommand(worldId, 'update_properties', { properties });

  // Success message will be shown when we receive confirmation from the server
}

// Update saveConfig to show success message
function saveConfig() {
  const configText = document.getElementById('config-editor').value;
  const errorDisplay = document.querySelector('.config-section .error-message');
  errorDisplay.textContent = '';

  try {
    // Validate JSON
    JSON.parse(configText);

    // Send to server
    showLoadingOverlay();
    sendCommand(JSON.stringify({
      command: 'update_config',
      config: configText
    }));

    // Success will be shown when we receive confirmation from the server
  } catch (error) {
    errorDisplay.textContent = `Error: ${error.message}`;
  }
}

// Update the fetchWorldsList function to show loading overlay
function fetchWorldsList() {
  showLoadingOverlay(); // Show loading overlay
  const worldsContainer = document.getElementById('worlds-list');
  worldsContainer.innerHTML = '<div class="worlds-loading"><span class="loader"></span> Loading worlds...</div>';

  sendCommand(JSON.stringify({ command: 'get_worlds' }));
}

// Initial connection
connectToWebSocket();

/**
 * Toggle the console panel visibility
 */
function toggleConsole() {
  const consoleSection = document.querySelector('.console-section');
  const toggleButton = document.querySelector('.toggle-console');
  const icon = toggleButton.querySelector('.icon');

  // Toggle visibility
  if (consoleSection.style.display === 'block') {
    consoleSection.style.display = 'none';
    toggleButton.classList.remove('expanded');
    icon.textContent = '▼';
  } else {
    consoleSection.style.display = 'block';
    toggleButton.classList.add('expanded');
    icon.textContent = '▲';

    // Auto-focus the input field when opening console
    setTimeout(() => {
      const commandInput = document.getElementById('command-input');
      if (commandInput) {
        commandInput.focus();
      }
    }, 100);
  }
}

/**
 * Toggle the config editor panel visibility
 */
function toggleConfig() {
  const configSection = document.querySelector('.config-section');
  const toggleButton = document.querySelector('button:nth-child(2)');
  
  // Toggle visibility
  if (configSection.style.display === 'block') {
    configSection.style.display = 'none';
    if (toggleButton) {
      toggleButton.classList.remove('expanded');
      
      // Find the icon safely
      const icon = toggleButton.querySelector('.icon');
      if (icon) {
        icon.textContent = '▼';
      }
    }
  } else {
    configSection.style.display = 'block';
    if (toggleButton) {
      toggleButton.classList.add('expanded');
      
      // Find the icon safely
      const icon = toggleButton.querySelector('.icon');
      if (icon) {
        icon.textContent = '▲';
      }
    }

    // Fetch config when opening the editor
    sendCommand(JSON.stringify({ command: 'get_config' }));
  }
}

/**
 * Format the JSON in the config editor
 */
function formatConfig() {
  const editor = document.getElementById('config-editor');
  try {
    const jsonObj = JSON.parse(editor.value);
    editor.value = JSON.stringify(jsonObj, null, 2);
  } catch (error) {
    const errorDisplay = document.querySelector('.config-section .error-message');
    errorDisplay.textContent = `Error: ${error.message}`;
  }
}

/**
 * Clear the list of denied friend requests
 */
function clearDeniedFriendRequests() {
  deniedFriendRequests.clear();
  localStorage.setItem('deniedFriendRequests', JSON.stringify(Array.from(deniedFriendRequests)));
  showSuccessMessage('Denied friend requests cleared');
  fetchFriendRequests();
}

/**
 * Ban a user by username
 */
function banUser() {
  const username = document.getElementById('ban-username').value.trim();
  if (!username) {
    displayErrorMessage('Please enter a username to ban');
    return;
  }

  showLoadingOverlay();
  sendCommand(JSON.stringify({
    command: 'ban_user',
    username: username
  }));

  // Clear the input field
  document.getElementById('ban-username').value = '';
}

/**
 * Cancel editing world properties and hide the panel
 */
function cancelWorldProperties() {
  const worldPropertiesPanel = document.getElementById('world-properties');
  worldPropertiesPanel.style.display = 'none';
}

/**
 * Update the status display with the current headless server status
 * @param {string} message - Status message to display
 * @param {string} status - Status type (connecting, running, stopped)
 */
function updateStatus(message, status) {
  const statusText = statusDiv.querySelector('.status-text');
  if (statusText) {
    statusText.textContent = message;
  }

  // Remove all status classes
  statusDiv.classList.remove('status-connecting', 'status-running', 'status-stopped');

  // Add the current status class
  if (status) {
    statusDiv.classList.add(`status-${status}`);
  }

  // Update last updated time
  const lastUpdated = document.querySelector('.last-updated');
  if (lastUpdated) {
    const now = new Date();
    lastUpdated.textContent = `Last updated: ${now.toLocaleTimeString()}`;
  }
}

/**
 * Updates the worlds list with received world data
 * @param {Array} worlds - Array of world data objects
 */
function updateWorlds(worlds) {
  const worldsContainer = document.getElementById('worlds-list');

  // Clear existing content
  worldsContainer.innerHTML = '';

  if (!worlds || worlds.length === 0) {
    worldsContainer.innerHTML = '<div class="no-worlds">No active worlds</div>';
    return;
  }

  // Sort worlds by name
  worlds.sort((a, b) => a.name.localeCompare(b.name));

  // Create world cards
  worlds.forEach(world => {
    const worldCard = document.createElement('div');
    worldCard.className = 'world-card';
    worldCard.dataset.worldId = world.id;

    worldCard.innerHTML = `
      <div class="world-name">${world.name}</div>
      <div class="world-details">
        <div class="world-stat">
          <span class="label">Users:</span>
          <span>${world.users} / ${world.maxUsers}</span>
        </div>
        <div class="world-stat">
          <span class="label">Access:</span>
          <span>${world.accessLevel}</span>
        </div>
        <div class="world-stat">
          <span class="label">Hidden:</span>
          <span>${world.hidden ? 'Yes' : 'No'}</span>
        </div>
        <div class="world-stat">
          <span class="label">Uptime:</span>
          <span>${formatUptime(world.uptime)}</span>
        </div>
        <div class="world-description">${world.description || 'No description'}</div>
      </div>
    `;

    // Add click event for world selection
    worldCard.addEventListener('click', () => selectWorld(world.id));

    // Add the world card to the container
    worldsContainer.appendChild(worldCard);
  });
}

/**
 * Format uptime in seconds to a readable format
 * @param {number} seconds - Uptime in seconds
 * @returns {string} - Formatted uptime string
 */
function formatUptime(seconds) {
  if (!seconds) return 'N/A';

  const days = Math.floor(seconds / (24 * 60 * 60));
  const hours = Math.floor((seconds % (24 * 60 * 60)) / (60 * 60));
  const minutes = Math.floor((seconds % (60 * 60)) / 60);

  if (days > 0) {
    return `${days}d ${hours}h ${minutes}m`;
  } else if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else {
    return `${minutes}m`;
  }
}

/**
 * Select a world and display its properties
 * @param {string} worldId - ID of the world to select
 */
function selectWorld(worldId) {
  // Clear previous selection
  document.querySelectorAll('.world-card.selected').forEach(card => {
    card.classList.remove('selected');
  });

  // Mark the selected world
  const selectedCard = document.querySelector(`[data-world-id="${worldId}"]`);
  if (selectedCard) {
    selectedCard.classList.add('selected');
  }

  // Show loading overlay
  showLoadingOverlay();

  // Request world details
  sendCommand(JSON.stringify({
    command: 'get_world_details',
    world_id: worldId
  }));
}

/**
 * Handle world details update and populate the properties panel
 * @param {Object} worldData - World details data
 */
function handleWorldDetailsUpdate(worldData) {
  const worldPropertiesPanel = document.getElementById('world-properties');

  // Store the world ID in the panel
  worldPropertiesPanel.dataset.worldId = worldData.id;

  // Set world name in the selected section
  document.getElementById('selected-world-name').textContent = worldData.name;

  // Populate form fields
  document.getElementById('world-name').value = worldData.name;
  document.getElementById('world-description').value = worldData.description || '';
  document.getElementById('world-access-level').value = worldData.accessLevel;
  document.getElementById('world-max-users').value = worldData.maxUsers;
  document.getElementById('world-hidden').checked = worldData.hidden;

  // Show the properties panel
  worldPropertiesPanel.style.display = 'block';
}

/**
 * Fetch and display friend requests
 */
function fetchFriendRequests() {
  sendCommand(JSON.stringify({ command: 'get_friend_requests' }));
}

/**
 * Start checking for friend requests periodically
 */
function startFriendRequestsTimer() {
  if (friendRequestsTimer) {
    clearInterval(friendRequestsTimer);
  }

  // Get the interval from the settings
  const interval = parseInt(document.getElementById('friend-requests-interval').value) || 5;
  friendRequestsInterval = interval * 60 * 1000;

  // Initial fetch
  fetchFriendRequests();

  // Set up periodic checking
  friendRequestsTimer = setInterval(fetchFriendRequests, friendRequestsInterval);
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  // Set up event listeners
  if (commandInput) {
    commandInput.addEventListener('keypress', function(event) {
      if (event.key === 'Enter') {
        const command = commandInput.value;
        if (command.trim()) {
          sendCommand(command);
          commandInput.value = '';
        }
      }
    });
  }

  // Set up interval inputs
  const refreshIntervalInput = document.getElementById('refresh-interval');
  if (refreshIntervalInput) {
    refreshIntervalInput.addEventListener('change', function() {
      const interval = parseInt(refreshIntervalInput.value) || 30;
      // Store in localStorage for persistence
      localStorage.setItem('refreshInterval', interval);
    });

    // Set initial value from localStorage or default
    refreshIntervalInput.value = localStorage.getItem('refreshInterval') || 30;
  }

  const friendRequestsIntervalInput = document.getElementById('friend-requests-interval');
  if (friendRequestsIntervalInput) {
    friendRequestsIntervalInput.addEventListener('change', function() {
      const interval = parseInt(friendRequestsIntervalInput.value) || 5;
      localStorage.setItem('friendRequestsInterval', interval);
      startFriendRequestsTimer();
    });

    // Set initial value from localStorage or default
    friendRequestsIntervalInput.value = localStorage.getItem('friendRequestsInterval') || 5;
  }

  // Start timers
  startFriendRequestsTimer();

  // Initial fetch of worlds list
  fetchWorldsList();

  // Set up automatic refresh of worlds list
  setInterval(fetchWorldsList, (parseInt(localStorage.getItem('refreshInterval')) || 30) * 1000);
});
