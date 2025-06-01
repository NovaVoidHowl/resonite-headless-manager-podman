let wsLogs;
let wsStatus;
let wsWorlds;
let wsCommand;
let wsCpu;
let wsMemory;
let wsContainerStatus;
let wsHeartbeat;

const output = document.getElementById('output');
const commandInput = document.getElementById('command-input');
const statusDiv = document.getElementById('status');

// Application state
let selectedWorldIndex = null;
let currentConfig = null;
let configChanged = false;
let currentWorldsData = []; // Store current worlds data for form population

// Intervals and timers
let friendRequestsInterval = 5 * 60 * 1000; // Default 5 minutes
let friendRequestsTimer = null;
let deniedFriendRequests = new Set(JSON.parse(localStorage.getItem('deniedFriendRequests') || '[]'));

let bannedUsersInterval = 5 * 60 * 1000; // Default 5 minutes
let bannedUsersTimer = null;

const AVAILABLE_ROLES = [
  'Spectator',
  'Guest',
  'Builder',
  'Moderator',
  'Admin'
];

let refreshInterval = 30 * 1000; // Default 30 seconds
let refreshTimer = null;

let statusInterval = 5 * 1000; // Default 5 seconds
let statusTimer = null;

function showLoadingOverlay(message = 'Processing request...') {
  const overlay = document.querySelector('.loading-overlay');
  const loadingText = overlay.querySelector('.loading-text');
  loadingText.textContent = message;
  overlay.classList.remove('hidden');
}

function hideLoadingOverlay() {
  const overlay = document.querySelector('.loading-overlay');
  overlay.classList.add('hidden');
}

function showError(message) {
  const toast = document.querySelector('.error-toast');
  const toastMessage = toast.querySelector('.error-toast-message');
  toastMessage.textContent = message;
  toast.classList.add('show');
  
  // Auto-hide after 5 seconds
  setTimeout(() => {
    toast.classList.remove('show');
  }, 5000);
}

function connect() {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsHost = window.location.hostname;

  // Connect to heartbeat endpoint to keep other connections alive
  wsHeartbeat = new WebSocket(`${wsProtocol}//${wsHost}:8000/ws/heartbeat`);
  wsHeartbeat.onopen = () => console.log('Heartbeat connection established');
  wsHeartbeat.onclose = () => setTimeout(() => connect(), 1000);
  wsHeartbeat.onerror = (error) => console.error('Heartbeat error:', error);

  // Connect to logs endpoint (container output)
  wsLogs = new WebSocket(`${wsProtocol}//${wsHost}:8000/ws/logs`);
  wsLogs.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'container_output') {
      appendOutput(data.output, '', data.timestamp);
    } else if (data.type === 'error') {
      showError(data.message);
    }
  };
  wsLogs.onclose = () => setTimeout(() => connect(), 1000);

  // Connect to worlds endpoint
  wsWorlds = new WebSocket(`${wsProtocol}//${wsHost}:8000/ws/worlds`);
  wsWorlds.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'worlds_update') {
      // Handle both old format (output) and new format (worlds_data)
      const worldsData = data.worlds_data || data.output;
      updateWorlds(worldsData, data.timestamp, data.cached);
    } else if (data.type === 'error') {
      showError(data.message);
    }
  };
  wsWorlds.onclose = () => setTimeout(() => connect(), 1000);

  // Connect to command endpoint
  wsCommand = new WebSocket(`${wsProtocol}//${wsHost}:8000/ws/command`);
  wsCommand.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'command_response') {
      handleCommandResponse(data);
    } else if (data.type === 'bans_update') {
      updateBannedUsers(data.bans, data.timestamp, data.cached);
    } else if (data.type === 'error') {
      showError(data.message);
    }
  };
  wsCommand.onclose = () => setTimeout(() => connect(), 1000);

  // Connect to CPU endpoint
  wsCpu = new WebSocket(`${wsProtocol}//${wsHost}:8000/ws/cpu`);
  wsCpu.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'cpu_update') {
      updateCpuUsage(data.cpu_usage);
    } else if (data.type === 'error') {
      showError(data.message);
    }
  };
  wsCpu.onclose = () => setTimeout(() => connect(), 1000);

  // Connect to memory endpoint
  wsMemory = new WebSocket(`${wsProtocol}//${wsHost}:8000/ws/memory`);
  wsMemory.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'memory_update') {
      updateMemoryUsage(data.memory_percent, data.memory_used, data.memory_total);
    } else if (data.type === 'error') {
      showError(data.message);
    }
  };
  wsMemory.onclose = () => setTimeout(() => connect(), 1000);

  // Connect to container status endpoint
  wsContainerStatus = new WebSocket(`${wsProtocol}//${wsHost}:8000/ws/container_status`);
  wsContainerStatus.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'container_status_update') {
      updateContainerStatus(data.status);
    } else if (data.type === 'error') {
      showError(data.message);
    }
  };
  wsContainerStatus.onclose = () => setTimeout(() => connect(), 1000);
  wsContainerStatus.onopen = requestContainerStatus;

  // Connect to status endpoint (separate from container status)
  wsStatus = new WebSocket(`${wsProtocol}//${wsHost}:8000/ws/status`);
  wsStatus.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'status_update') {
      updateServerStatus(data);
    } else if (data.type === 'error') {
      showError(data.message);
    }
  };
  wsStatus.onclose = () => setTimeout(() => connect(), 1000);

  // Clear existing intervals
  if (refreshTimer) clearInterval(refreshTimer);
  if (statusTimer) clearInterval(statusTimer);
  if (friendRequestsTimer) clearInterval(friendRequestsTimer);
  if (bannedUsersTimer) clearInterval(bannedUsersTimer);

  // Set up periodic container status checks
  statusTimer = setInterval(requestContainerStatus, statusInterval);

  // Set up periodic worlds updates
  refreshTimer = setInterval(() => {
    if (wsWorlds && wsWorlds.readyState === WebSocket.OPEN) {
      wsWorlds.send(JSON.stringify({ type: 'get_worlds' }));
    }
  }, refreshInterval);

  // Set up periodic friend requests updates
  friendRequestsTimer = setInterval(() => {
    if (wsCommand && wsCommand.readyState === WebSocket.OPEN) {
      wsCommand.send(JSON.stringify({
        type: 'command',
        command: 'friendRequests'
      }));
    }
  }, friendRequestsInterval);

  // Set up periodic banned users updates
  bannedUsersTimer = setInterval(() => {
    if (wsCommand && wsCommand.readyState === WebSocket.OPEN) {
      wsCommand.send(JSON.stringify({
        type: 'command',
        command: 'listbans'
      }));
    }
  }, bannedUsersInterval);

  // Initial requests
  setTimeout(() => {
    if (wsWorlds && wsWorlds.readyState === WebSocket.OPEN) {
      wsWorlds.send(JSON.stringify({ type: 'get_worlds' }));
    }
    if (wsStatus && wsStatus.readyState === WebSocket.OPEN) {
      wsStatus.send(JSON.stringify({ type: 'get_status' }));
    }
  }, 1000);
}

// Command response handler
function handleCommandResponse(data) {
  if (data.command === 'friendRequests') {
    updateFriendRequests(data.output, data.timestamp, data.cached);
  } else if (data.command === 'users') {
    updateConnectedUsers(data.output, data.timestamp, data.cached);
  } else if (data.command === 'worlds') {
    updateWorlds(data.output, data.timestamp, data.cached);
  } else {
    console.log('Command response:', data.command, data.output, data.timestamp);
  }
}

// Server status update handler
function updateServerStatus(data) {
  // Update last updated timestamp
  const lastUpdated = document.querySelector('.last-updated');
  if (lastUpdated && data.timestamp) {
    const time = new Date(data.timestamp);
    lastUpdated.textContent = `Last updated: ${time.toLocaleTimeString()}`;
  }
  
  // Handle status-specific updates
  if (data.status) {
    console.log('Server status update:', data.status);
  }
}

function updateCpuUsage(cpuUsage) {
  const cpuUsageElement = document.getElementById('cpu-usage');
  if (cpuUsageElement) {
    cpuUsageElement.textContent = `${cpuUsage.toFixed(1)}%`;
  }
}

function updateMemoryUsage(memoryPercent, memoryUsed, memoryTotal) {
  const memoryUsageElement = document.getElementById('memory-usage');
  if (memoryUsageElement) {
    memoryUsageElement.textContent = `${memoryPercent.toFixed(1)}% (${memoryUsed}/${memoryTotal})`;
  }
}

function updateContainerStatus(status) {
  const statusDiv = document.getElementById('status');
  const statusText = statusDiv.querySelector('.status-text');

  // Remove all existing status classes
  statusDiv.classList.remove('status-connecting', 'status-running', 'status-stopped');

  if (status.error) {
    statusDiv.classList.add('status-stopped');
    statusText.textContent = `Error - ${status.error}`;
    updateContainerControls('stopped');
    return;
  }

  switch (status.status.toLowerCase()) {
    case 'running':
      statusDiv.classList.add('status-running');
      updateContainerControls('running');
      break;
    case 'stopped':
    case 'exited':
      statusDiv.classList.add('status-stopped');
      updateContainerControls('stopped');
      break;
    default:
      statusDiv.classList.add('status-connecting');
  }

  statusText.textContent = `${status.status} (${status.name})`;
}

function requestContainerStatus() {
  if (wsContainerStatus && wsContainerStatus.readyState === WebSocket.OPEN) {
    wsContainerStatus.send(JSON.stringify({ type: 'get_container_status' }));
  }
}

function sendCommand() {
  const command = commandInput.value.trim();
  if (command && wsCommand && wsCommand.readyState === WebSocket.OPEN) {
    wsCommand.send(JSON.stringify({
      type: 'command',
      command: command
    }));
    appendOutput(`${command}`, 'command-line');
    commandInput.value = '';
  }
}

function appendOutput(text, className = '', timestamp = null) {
  const div = document.createElement('div');
  div.textContent = text;
  if (className) {
    div.className = className;
  }
  
  // Add timestamp if provided
  if (timestamp) {
    const time = new Date(timestamp);
    const timeString = time.toLocaleString();
    div.setAttribute('data-timestamp', timeString);
    div.className += ' log-line';
  }
  
  output.appendChild(div);
  
  // Keep only the last 1000 lines to prevent memory issues
  while (output.childNodes.length > 1000) {
    output.removeChild(output.firstChild);
  }
  
  output.scrollTop = output.scrollHeight;
}

function updateWorlds(worlds, timestamp, cached = false) {
  const worldsList = document.getElementById('worlds-list');
  worldsList.innerHTML = '';
  
  // Handle different response formats and ensure worlds is an array
  let worldsArray = [];
  if (Array.isArray(worlds)) {
    worldsArray = worlds;
  } else if (worlds && typeof worlds === 'object' && Array.isArray(worlds.worlds)) {
    worldsArray = worlds.worlds;
  } else if (worlds && typeof worlds === 'string') {
    try {
      const parsed = JSON.parse(worlds);
      worldsArray = Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      console.warn('Failed to parse worlds data:', worlds, error);
      worldsArray = [];
    }
  }
  
  // Store current worlds data globally for form population
  currentWorldsData = worldsArray;
  
  if (!worldsArray || worldsArray.length === 0) {
    worldsList.innerHTML = '<div class="no-worlds">No worlds running</div>';
    return;
  }
  
  worldsArray.forEach((world, index) => {
    const worldDiv = document.createElement('div');
    worldDiv.className = 'world-item';
    worldDiv.setAttribute('data-timestamp', new Date(timestamp).toLocaleString());
    worldDiv.setAttribute('data-world-index', index);
    
    if (cached) {
      worldDiv.classList.add('cached-data');
    }
    
    // Create world header - handle both old and new data structure
    const worldHeader = document.createElement('div');
    worldHeader.className = 'world-header';
    
    // Handle both old format and new structured format
    const users = world.user_count ? world.user_count.connected_to_instance : world.users;
    const present = world.user_count ? world.user_count.present : world.present;
    const maxUsers = world.user_count ? world.user_count.max_users : world.maxUsers;
    
    worldHeader.innerHTML = `
      <div class="world-title">
        <h3>${world.name || 'Unnamed World'}</h3>
        <span class="session-id" title="Session ID: ${world.sessionId}">${world.sessionId}</span>
      </div>
      <div class="world-stats">
        <span class="users-count">${users}/${maxUsers} users</span>
        <span class="uptime">${world.uptime || 'Unknown'}</span>
      </div>
    `;
    
    // Create world details - handle both old and new data structure
    const worldDetails = document.createElement('div');
    worldDetails.className = 'world-details';
    
    // Handle both old format and new structured format
    const accessLevel = world.access_level || world.accessLevel;
    const mobileFriendly = world.mobile_friendly !== undefined ? world.mobile_friendly : world.mobileFriendly;
    
    worldDetails.innerHTML = `
      <div class="world-info">
        <div class="info-row">
          <span class="label">Access Level:</span>
          <span class="value">${accessLevel}</span>
        </div>
        <div class="info-row">
          <span class="label">Hidden:</span>
          <span class="value">${world.hidden ? 'Yes' : 'No'}</span>
        </div>
        <div class="info-row">
          <span class="label">Mobile Friendly:</span>
          <span class="value">${mobileFriendly ? 'Yes' : 'No'}</span>
        </div>
        ${world.description ? `<div class="info-row"><span class="label">Description:</span><span class="value">${world.description}</span></div>` : ''}
        ${world.tags ? `<div class="info-row"><span class="label">Tags:</span><span class="value">${world.tags}</span></div>` : ''}
      </div>
      <div class="world-actions">
        <button onclick="selectWorld(${index})" class="select-world-btn">Select World</button>
        <button onclick="toggleWorldUsers(${index})" class="show-users-btn" id="show-users-btn-${index}">Show Users (${present})</button>
      </div>
      <div class="world-users-section" id="world-users-${index}" style="display: none;">
        <div class="users-header">
          <span class="users-title">Connected Users</span>
          <button onclick="refreshWorldUsersList(${index})" class="refresh-users-btn" title="Refresh users list">
            ↻
          </button>
        </div>
        <div class="users-list" id="users-list-${index}">
          <div class="loading-users">Loading users...</div>
        </div>
      </div>
    `;
    
    worldDiv.appendChild(worldHeader);
    worldDiv.appendChild(worldDetails);
    worldsList.appendChild(worldDiv);
  });
  
  // Update last updated timestamp
  const lastUpdated = document.querySelector('.last-updated');
  if (lastUpdated && timestamp) {
    const time = new Date(timestamp);
    lastUpdated.textContent = `Last updated: ${time.toLocaleTimeString()}${cached ? ' (cached)' : ''}`;
  }
}

function updateFriendRequests(requests, timestamp, cached = false) {
  const requestsList = document.getElementById('friend-requests-list');
  requestsList.innerHTML = '';
  
  // Handle different response formats and ensure requests is an array
  let requestsArray = [];
  if (Array.isArray(requests)) {
    requestsArray = requests;
  } else if (requests && typeof requests === 'object' && Array.isArray(requests.requests)) {
    requestsArray = requests.requests;
  } else if (requests && typeof requests === 'string') {
    try {
      const parsed = JSON.parse(requests);
      requestsArray = Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      console.warn('Failed to parse friend requests data:', requests, error);
      requestsArray = [];
    }
  }
  
  if (!requestsArray || requestsArray.length === 0) {
    requestsList.innerHTML = '<div class="no-requests">No pending friend requests</div>';
    return;
  }
  
  // Filter out denied requests
  const filteredRequests = requestsArray.filter(request => 
    !deniedFriendRequests.has(request.id || request.username)
  );
  
  if (filteredRequests.length === 0) {
    requestsList.innerHTML = '<div class="no-requests">No pending friend requests</div>';
    return;
  }
  
  filteredRequests.forEach(request => {
    const requestDiv = document.createElement('div');
    requestDiv.className = 'friend-request';
    requestDiv.setAttribute('data-timestamp', new Date(timestamp).toLocaleString());
    
    if (cached) {
      requestDiv.classList.add('cached-data');
    }
    
    requestDiv.innerHTML = `
      <div class="request-info">
        <div class="request-username">${request.username}</div>
        <div class="request-id">${request.id || 'Unknown ID'}</div>
      </div>
      <div class="request-actions">
        <button onclick="acceptFriendRequest('${request.id || request.username}')" class="accept-btn">Accept</button>
        <button onclick="denyFriendRequest('${request.id || request.username}')" class="deny-btn">Deny</button>
      </div>
    `;
    
    requestsList.appendChild(requestDiv);
  });
}

function updateBannedUsers(bans, timestamp, cached = false) {
  const bansList = document.getElementById('banned-users-list');
  bansList.innerHTML = '';
  
  // Handle different response formats and ensure bans is an array
  let bansArray = [];
  if (Array.isArray(bans)) {
    bansArray = bans;
  } else if (bans && typeof bans === 'object' && Array.isArray(bans.bans)) {
    bansArray = bans.bans;
  } else if (bans && typeof bans === 'string') {
    try {
      const parsed = JSON.parse(bans);
      bansArray = Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      console.warn('Failed to parse banned users data:', bans, error);
      bansArray = [];
    }
  }
  
  if (!bansArray || bansArray.length === 0) {
    bansList.innerHTML = '<div class="no-bans">No banned users</div>';
    return;
  }
  
  bansArray.forEach(ban => {
    const banDiv = document.createElement('div');
    banDiv.className = 'ban-item';
    banDiv.setAttribute('data-timestamp', new Date(timestamp).toLocaleString());
    
    if (cached) {
      banDiv.classList.add('cached-data');
    }
    
    banDiv.innerHTML = `
      <div class="ban-info">
        <div class="ban-username">${ban.username}</div>
        <div class="ban-id">${ban.userId || 'Unknown ID'}</div>
      </div>
      <div class="ban-actions">
        <button onclick="unbanUser('${ban.username}')" class="unban-btn">Unban</button>
      </div>
    `;
    
    bansList.appendChild(banDiv);
  });
}

// Container control functions
async function startContainer() {
  try {
    showLoadingOverlay('Starting container...');
    const response = await fetch(`http://${window.location.hostname}:8000/api/start-container`, {
      method: 'POST'
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to start container');
    }
    
    hideLoadingOverlay();
    updateContainerControls('running');
  } catch (error) {
    hideLoadingOverlay();
    showError(error.message);
  }
}

async function stopContainer() {
  try {
    showLoadingOverlay('Stopping container...');
    const response = await fetch(`http://${window.location.hostname}:8000/api/stop-container`, {
      method: 'POST'
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to stop container');
    }
    
    hideLoadingOverlay();
    updateContainerControls('stopped');
  } catch (error) {
    hideLoadingOverlay();
    showError(error.message);
  }
}

async function restartContainer() {
  try {
    showLoadingOverlay('Restarting container...');
    const response = await fetch(`http://${window.location.hostname}:8000/api/restart-container`, {
      method: 'POST'
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to restart container');
    }
    
    hideLoadingOverlay();
    updateContainerControls('running');
  } catch (error) {
    hideLoadingOverlay();
    showError(error.message);
  }
}

function updateContainerControls(status) {
  const startBtn = document.getElementById('startContainer');
  const stopBtn = document.getElementById('stopContainer');
  const restartBtn = document.getElementById('restartContainer');
  
  if (status === 'running') {
    startBtn.classList.add('hidden');
    stopBtn.classList.remove('hidden');
    restartBtn.classList.remove('hidden');
    startBtn.disabled = true;
    stopBtn.disabled = false;
    restartBtn.disabled = false;
  } else if (status === 'stopped') {
    startBtn.classList.remove('hidden');
    stopBtn.classList.add('hidden');
    restartBtn.classList.add('hidden');
    startBtn.disabled = false;
    stopBtn.disabled = true;
    restartBtn.disabled = true;
  } else {
    // For unknown status, hide all buttons
    startBtn.classList.add('hidden');
    stopBtn.classList.add('hidden');
    restartBtn.classList.add('hidden');
    startBtn.disabled = true;
    stopBtn.disabled = true;
    restartBtn.disabled = true;
  }
}

// UI Control Functions

function toggleConsole() {
  const consoleSection = document.querySelector('.console-section');
  const toggleBtn = document.querySelector('.toggle-console');
  const icon = toggleBtn.querySelector('.icon');
  
  consoleSection.classList.toggle('visible');
  
  if (consoleSection.classList.contains('visible')) {
    icon.textContent = '▲';
  } else {
    icon.textContent = '▼';
  }
}

function toggleConfig() {
  const configSection = document.querySelector('.config-section');
  const toggleBtn = document.querySelector('.toggle-console:last-child');
  const icon = toggleBtn.querySelector('.icon');
  
  configSection.classList.toggle('visible');
  
  if (configSection.classList.contains('visible')) {
    icon.textContent = '▲';
    loadConfig();
  } else {
    icon.textContent = '▼';
  }
}

function toggleCard(cardId) {
  const cardContent = document.getElementById(cardId);
  const header = cardContent.previousElementSibling;
  const icon = header.querySelector('.collapse-icon');
  
  cardContent.classList.toggle('collapsed');
  header.classList.toggle('collapsed');
  
  if (cardContent.classList.contains('collapsed')) {
    icon.textContent = '▶';
  } else {
    icon.textContent = '▼';
  }
}

// World Management Functions

function selectWorld(worldIndex) {
  selectedWorldIndex = worldIndex;
  
  // Get world data from the current worlds list
  const worldsList = document.getElementById('worlds-list');
  const worldItems = worldsList.querySelectorAll('.world-item');
  
  if (worldIndex >= 0 && worldIndex < worldItems.length) {
    // Clear previous selection
    worldItems.forEach(item => item.classList.remove('selected'));
    
    // Mark new selection
    worldItems[worldIndex].classList.add('selected');
    
    // Show world properties panel
    showWorldProperties(worldIndex);
  }
}

function showWorldProperties(worldIndex) {
  const worldPropertiesPanel = document.getElementById('world-properties');
  const selectedWorldName = document.getElementById('selected-world-name');
  
  if (worldIndex >= 0 && worldIndex < currentWorldsData.length) {
    const world = currentWorldsData[worldIndex];
    
    // Update the selected world name
    selectedWorldName.textContent = world.name || 'Unnamed World';
    worldPropertiesPanel.style.display = 'block';
    
    // Populate all form fields with actual world data
    document.getElementById('world-name').value = world.name || '';
    document.getElementById('world-hidden').checked = world.hidden || false;
    document.getElementById('world-description').value = world.description || '';
    
    // Handle access level (both old and new data structure)
    const accessLevel = world.access_level || world.accessLevel || 'Anyone';
    document.getElementById('world-access-level').value = accessLevel;
    
    // Handle max users (both old and new data structure)
    const maxUsers = world.user_count ? world.user_count.max_users : (world.maxUsers || 10);
    document.getElementById('world-max-users').value = maxUsers;
  }
}

function toggleWorldUsers(worldIndex) {
  const usersSection = document.getElementById(`world-users-${worldIndex}`);
  const showUsersBtn = document.getElementById(`show-users-btn-${worldIndex}`);
  
  if (usersSection.style.display === 'none') {
    // Show users section
    usersSection.style.display = 'block';
    showUsersBtn.textContent = showUsersBtn.textContent.replace('Show', 'Hide');
    
    // Set the selected world index for API calls
    selectedWorldIndex = worldIndex;
    
    // Load users data
    refreshWorldUsersList(worldIndex);
  } else {
    // Hide users section
    usersSection.style.display = 'none';
    showUsersBtn.textContent = showUsersBtn.textContent.replace('Hide', 'Show');
  }
}

function refreshWorldUsersList(worldIndex) {
  const usersList = document.getElementById(`users-list-${worldIndex}`);
  if (usersList) {
    usersList.innerHTML = '<div class="loading-users">Loading users...</div>';
  }
  
  // Set the selected world index for API calls
  selectedWorldIndex = worldIndex;
  
  if (wsCommand && wsCommand.readyState === WebSocket.OPEN) {
    wsCommand.send(JSON.stringify({
      type: 'command',
      command: 'users'
    }));
  }
}

function updateConnectedUsers(users, timestamp, cached = false) {
  // Target the specific world's users list instead of sidebar
  if (selectedWorldIndex === null) return;
  
  const usersList = document.getElementById(`users-list-${selectedWorldIndex}`);
  if (!usersList) return;
  
  usersList.innerHTML = '';
  
  // Handle different response formats and ensure users is an array
  let usersArray = [];
  if (Array.isArray(users)) {
    usersArray = users;
  } else if (users && typeof users === 'object' && Array.isArray(users.users)) {
    usersArray = users.users;
  } else if (users && typeof users === 'string') {
    try {
      const parsed = JSON.parse(users);
      usersArray = Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      console.warn('Failed to parse users data:', users, error);
      usersArray = [];
    }
  }
  
  if (!usersArray || usersArray.length === 0) {
    usersList.innerHTML = '<div class="no-users">No users connected</div>';
    return;
  }
  
  usersArray.forEach(user => {
    const userDiv = document.createElement('div');
    userDiv.className = 'user-item';
    userDiv.setAttribute('data-timestamp', new Date(timestamp).toLocaleString());
    
    if (cached) {
      userDiv.classList.add('cached-data');
    }
    
    userDiv.innerHTML = `
      <div class="user-info">
        <div class="user-name">${user.username}</div>
        <div class="user-details">
          <span class="user-id">${user.id}</span>
          <span class="user-role">${user.role}</span>
          <span class="user-status ${user.present ? 'present' : 'away'}">${user.present ? 'Present' : 'Away'}</span>
          ${user.ping ? `<span class="user-ping">${user.ping}ms</span>` : ''}
          ${user.fps ? `<span class="user-fps">${user.fps.toFixed(1)} FPS</span>` : ''}
          ${user.silenced ? '<span class="user-silenced">Silenced</span>' : ''}
        </div>
      </div>
      <div class="user-actions">
        <select onchange="changeUserRole('${user.username}', this.value)" class="role-select">
          ${AVAILABLE_ROLES.map(role => 
            `<option value="${role}" ${role === user.role ? 'selected' : ''}>${role}</option>`
          ).join('')}
        </select>
        <button onclick="kickUser('${user.username}')" class="kick-btn">Kick</button>
        <button onclick="banUser('${user.username}')" class="ban-btn">Ban</button>
      </div>
    `;
    
    usersList.appendChild(userDiv);
  });
}

function sendWorldCommand(command) {
  if (selectedWorldIndex === null) {
    showError('No world selected');
    return;
  }
  
  if (selectedWorldIndex >= currentWorldsData.length) {
    showError('Invalid world selection');
    return;
  }
  
  // Get the session ID from stored world data
  const world = currentWorldsData[selectedWorldIndex];
  const sessionId = world.sessionId;
  
  if (!sessionId) {
    showError('No session ID found for selected world');
    return;
  }
  
  if (wsCommand && wsCommand.readyState === WebSocket.OPEN) {
    wsCommand.send(JSON.stringify({
      type: 'command',
      command: `${command} ${sessionId}`
    }));
    
    showLoadingOverlay(`Executing ${command} command...`);
    setTimeout(hideLoadingOverlay, 2000);
  }
}

function saveWorldProperties() {
  if (selectedWorldIndex === null) {
    showError('No world selected');
    return;
  }
  
  if (selectedWorldIndex >= currentWorldsData.length) {
    showError('Invalid world selection');
    return;
  }
  
  const world = currentWorldsData[selectedWorldIndex];
  const sessionId = world.sessionId;
  
  if (!sessionId) {
    showError('No session ID found for selected world');
    return;
  }
  
  // Get form values
  const newName = document.getElementById('world-name').value.trim();
  const newHidden = document.getElementById('world-hidden').checked;
  const newDescription = document.getElementById('world-description').value.trim();
  const newAccessLevel = document.getElementById('world-access-level').value;
  const newMaxUsers = parseInt(document.getElementById('world-max-users').value);
  
  // Validate inputs
  if (!newName) {
    showError('World name cannot be empty');
    return;
  }
  
  if (isNaN(newMaxUsers) || newMaxUsers < 1 || newMaxUsers > 100) {
    showError('Max users must be between 1 and 100');
    return;
  }
  
  if (!wsCommand || wsCommand.readyState !== WebSocket.OPEN) {
    showError('Command WebSocket is not connected');
    return;
  }
  
  showLoadingOverlay('Applying changes to world...');
  
  // Track commands sent and completed
  let commandsToSend = [];
  let commandsCompleted = 0;
  
  // Compare current values with form values to determine what needs to be changed
  const currentName = world.name || '';
  const currentHidden = world.hidden || false;
  const currentDescription = world.description || '';
  const currentAccessLevel = world.access_level || world.accessLevel || 'Anyone';
  const currentMaxUsers = world.user_count ? world.user_count.max_users : (world.maxUsers || 10);
  
  // Build list of commands to send
  if (newName !== currentName) {
    commandsToSend.push(`name "${newName}"`);
  }
  
  if (newHidden !== currentHidden) {
    commandsToSend.push(`hidefromlisting ${newHidden}`);
  }
  
  if (newDescription !== currentDescription) {
    commandsToSend.push(`description "${newDescription}"`);
  }
  
  if (newAccessLevel !== currentAccessLevel) {
    commandsToSend.push(`accesslevel ${newAccessLevel}`);
  }
  
  if (newMaxUsers !== currentMaxUsers) {
    commandsToSend.push(`maxusers ${newMaxUsers}`);
  }
  
  if (commandsToSend.length === 0) {
    hideLoadingOverlay();
    showError('No changes detected');
    return;
  }
  
  // Function to send next command
  const sendNextCommand = () => {
    if (commandsCompleted >= commandsToSend.length) {
      // All commands completed, refresh worlds list
      hideLoadingOverlay();
      if (wsWorlds && wsWorlds.readyState === WebSocket.OPEN) {
        wsWorlds.send(JSON.stringify({ type: 'get_worlds' }));
      }
      // Keep the properties panel open to show updated values
      setTimeout(() => {
        if (selectedWorldIndex !== null) {
          showWorldProperties(selectedWorldIndex);
        }
      }, 1000);
      return;
    }
    
    const command = commandsToSend[commandsCompleted];
    wsCommand.send(JSON.stringify({
      type: 'command',
      command: command
    }));
    
    commandsCompleted++;
    
    // Send next command after a short delay
    setTimeout(sendNextCommand, 500);
  };
  
  // Start sending commands
  sendNextCommand();
}

function cancelWorldProperties() {
  const worldPropertiesPanel = document.getElementById('world-properties');
  worldPropertiesPanel.style.display = 'none';
  selectedWorldIndex = null;
  
  // Clear selection from worlds list
  const worldItems = document.querySelectorAll('.world-item');
  worldItems.forEach(item => item.classList.remove('selected'));
}

// User Management Functions

function changeUserRole(username, newRole) {
  if (wsCommand && wsCommand.readyState === WebSocket.OPEN) {
    wsCommand.send(JSON.stringify({
      type: 'command',
      command: `role "${username}" ${newRole}`
    }));
    
    showLoadingOverlay(`Changing ${username}'s role to ${newRole}...`);
    setTimeout(hideLoadingOverlay, 2000);
  }
}

function kickUser(username) {
  if (confirm(`Are you sure you want to kick ${username}?`)) {
    if (wsCommand && wsCommand.readyState === WebSocket.OPEN) {
      wsCommand.send(JSON.stringify({
        type: 'command',
        command: `kick "${username}"`
      }));
      
      showLoadingOverlay(`Kicking ${username}...`);
      setTimeout(() => {
        hideLoadingOverlay();
        refreshUsersList();
      }, 2000);
    }
  }
}

function banUser(username) {
  if (!username) {
    username = document.getElementById('ban-username').value.trim();
  }
  
  if (!username) {
    showError('Please enter a username to ban');
    return;
  }
  
  if (confirm(`Are you sure you want to ban ${username}?`)) {
    if (wsCommand && wsCommand.readyState === WebSocket.OPEN) {
      wsCommand.send(JSON.stringify({
        type: 'command',
        command: `ban "${username}"`
      }));
      
      showLoadingOverlay(`Banning ${username}...`);
      
      // Clear input field
      const banInput = document.getElementById('ban-username');
      if (banInput) {
        banInput.value = '';
      }
      
      setTimeout(() => {
        hideLoadingOverlay();
        // Refresh both users and bans list
        refreshUsersList();
        wsCommand.send(JSON.stringify({
          type: 'command',
          command: 'listbans'
        }));
      }, 2000);
    }
  }
}

function unbanUser(username) {
  if (confirm(`Are you sure you want to unban ${username}?`)) {
    if (wsCommand && wsCommand.readyState === WebSocket.OPEN) {
      wsCommand.send(JSON.stringify({
        type: 'command',
        command: `unban "${username}"`
      }));
      
      showLoadingOverlay(`Unbanning ${username}...`);
      setTimeout(() => {
        hideLoadingOverlay();
        // Refresh bans list
        wsCommand.send(JSON.stringify({
          type: 'command',
          command: 'listbans'
        }));
      }, 2000);
    }
  }
}

// Friend Request Management

function acceptFriendRequest(requestId) {
  if (wsCommand && wsCommand.readyState === WebSocket.OPEN) {
    wsCommand.send(JSON.stringify({
      type: 'command',
      command: `acceptFriendRequest "${requestId}"`
    }));
    
    showLoadingOverlay('Accepting friend request...');
    setTimeout(() => {
      hideLoadingOverlay();
      // Refresh friend requests
      wsCommand.send(JSON.stringify({
        type: 'command',
        command: 'friendRequests'
      }));
    }, 2000);
  }
}

function denyFriendRequest(requestId) {
  // Add to denied list
  deniedFriendRequests.add(requestId);
  localStorage.setItem('deniedFriendRequests', JSON.stringify([...deniedFriendRequests]));
  
  // Remove from UI
  const requestDiv = document.querySelector(`[data-request-id="${requestId}"]`);
  if (requestDiv) {
    requestDiv.remove();
  }
  
  // Check if we need to show "no requests" message
  const requestsList = document.getElementById('friend-requests-list');
  if (requestsList.children.length === 0) {
    requestsList.innerHTML = '<div class="no-requests">No pending friend requests</div>';
  }
}

function clearDeniedFriendRequests() {
  deniedFriendRequests.clear();
  localStorage.removeItem('deniedFriendRequests');
  
  // Refresh friend requests
  if (wsCommand && wsCommand.readyState === WebSocket.OPEN) {
    wsCommand.send(JSON.stringify({
      type: 'command',
      command: 'friendRequests'
    }));
  }
}

// Config Management Functions

async function loadConfig() {
  try {
    const response = await fetch('/config');
    const config = await response.text();
    
    const configEditor = document.getElementById('config-editor');
    configEditor.value = config;
    currentConfig = config;
    configChanged = false;
    
    updateLineNumbers();
    
    // Add change listener
    configEditor.addEventListener('input', () => {
      configChanged = true;
      updateLineNumbers();
    });
    
  } catch (error) {
    showError('Failed to load configuration: ' + error.message);
  }
}

async function saveConfig() {
  const configEditor = document.getElementById('config-editor');
  const newConfig = configEditor.value;
  
  // Validate JSON
  try {
    JSON.parse(newConfig);
  } catch (error) {
    showError('Invalid JSON: ' + error.message);
    return;
  }
  
  try {
    showLoadingOverlay('Saving configuration...');
    
    const response = await fetch('/config', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: newConfig
    });
    
    if (!response.ok) {
      throw new Error('Failed to save configuration');
    }
    
    currentConfig = newConfig;
    configChanged = false;
    hideLoadingOverlay();
    
    // Show success message
    const errorMessage = document.querySelector('.config-section .error-message');
    errorMessage.textContent = 'Configuration saved successfully!';
    errorMessage.style.color = '#4CAF50';
    setTimeout(() => {
      errorMessage.textContent = '';
    }, 3000);
    
  } catch (error) {
    hideLoadingOverlay();
    showError('Failed to save configuration: ' + error.message);
  }
}

function formatConfig() {
  const configEditor = document.getElementById('config-editor');
  const config = configEditor.value;
  
  try {
    const parsed = JSON.parse(config);
    const formatted = JSON.stringify(parsed, null, 2);
    configEditor.value = formatted;
    configChanged = true;
    updateLineNumbers();
  } catch (error) {
    showError('Invalid JSON: ' + error.message);
  }
}

function updateLineNumbers() {
  const configEditor = document.getElementById('config-editor');
  const lineNumbers = document.getElementById('line-numbers');
  
  const lines = configEditor.value.split('\n');
  const numberLines = lines.map((_, index) => `<div>${index + 1}</div>`).join('');
  lineNumbers.innerHTML = numberLines;
  
  // Sync scroll
  lineNumbers.scrollTop = configEditor.scrollTop;
}

// Settings Management

function updateRefreshInterval() {
  const interval = parseInt(document.getElementById('refresh-interval').value) * 1000;
  if (interval >= 10000) { // Minimum 10 seconds
    refreshInterval = interval;
    
    // Clear and restart the timer
    if (refreshTimer) {
      clearInterval(refreshTimer);
    }
    
    refreshTimer = setInterval(() => {
      if (wsWorlds && wsWorlds.readyState === WebSocket.OPEN) {
        wsWorlds.send(JSON.stringify({ type: 'get_worlds' }));
      }
    }, refreshInterval);
  }
}

function updateFriendRequestsInterval() {
  const interval = parseInt(document.getElementById('friend-requests-interval').value) * 60 * 1000;
  if (interval >= 60000) { // Minimum 1 minute
    friendRequestsInterval = interval;
    
    // Clear and restart the timer
    if (friendRequestsTimer) {
      clearInterval(friendRequestsTimer);
    }
    
    friendRequestsTimer = setInterval(() => {
      if (wsCommand && wsCommand.readyState === WebSocket.OPEN) {
        wsCommand.send(JSON.stringify({
          type: 'command',
          command: 'friendRequests'
        }));
      }
    }, friendRequestsInterval);
  }
}

// Initialize event listeners
document.addEventListener('DOMContentLoaded', function() {
  // Add event listeners for settings
  const refreshIntervalInput = document.getElementById('refresh-interval');
  if (refreshIntervalInput) {
    refreshIntervalInput.addEventListener('change', updateRefreshInterval);
  }
  
  const friendRequestsIntervalInput = document.getElementById('friend-requests-interval');
  if (friendRequestsIntervalInput) {
    friendRequestsIntervalInput.addEventListener('change', updateFriendRequestsInterval);
  }
  
  // Add error toast close button functionality
  const errorToastClose = document.querySelector('.error-toast-close');
  if (errorToastClose) {
    errorToastClose.addEventListener('click', () => {
      document.querySelector('.error-toast').classList.remove('show');
    });
  }
  
  // Config editor scroll sync
  const configEditor = document.getElementById('config-editor');
  if (configEditor) {
    configEditor.addEventListener('scroll', () => {
      const lineNumbers = document.getElementById('line-numbers');
      if (lineNumbers) {
        lineNumbers.scrollTop = configEditor.scrollTop;
      }
    });
  }

  // Add Enter key support for command input
  const commandInput = document.getElementById('command-input');
  if (commandInput) {
    commandInput.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        sendCommand();
      }
    });
  }
  
  // Initialize connection
  connect();
});
