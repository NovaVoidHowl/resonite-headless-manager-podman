let wsLogs;
let wsStatus;
let wsWorlds;
let wsCommand;
let wsCpu;
let wsMemory;
let wsContainerStatus;
const output = document.getElementById('output');
const commandInput = document.getElementById('command-input');
const statusDiv = document.getElementById('status');

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

  // Connect to logs endpoint (container output)
  wsLogs = new WebSocket(`${wsProtocol}//${wsHost}:8000/ws/logs`);
  wsLogs.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'container_output') {
      appendOutput(data.output, '', data.timestamp);
    }
  };
  wsLogs.onclose = () => setTimeout(() => connect(), 1000);

  // Connect to worlds endpoint
  wsWorlds = new WebSocket(`${wsProtocol}//${wsHost}:8000/ws/worlds`);
  wsWorlds.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'worlds_update') {
      updateWorlds(data.output, data.timestamp);
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
      if (data.command === 'friendRequests') {
        updateFriendRequests(data.output, data.timestamp);
      }
      console.log('command_response', data.output, data.timestamp);
    } else if (data.type === 'bans_update') {
      updateBannedUsers(data.bans, data.timestamp);
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
    }
  };
  wsCpu.onclose = () => setTimeout(() => connect(), 1000);

  // Connect to memory endpoint
  wsMemory = new WebSocket(`${wsProtocol}//${wsHost}:8000/ws/memory`);
  wsMemory.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'memory_update') {
      updateMemoryUsage(data.memory_percent, data.memory_used, data.memory_total);
    }
  };
  wsMemory.onclose = () => setTimeout(() => connect(), 1000);

  // Connect to container status endpoint
  wsStatus = new WebSocket(`${wsProtocol}//${wsHost}:8000/ws/container_status`);
  wsStatus.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'container_status_update') {
      updateContainerStatus(data.status);
    } else if (data.type === 'error') {
      showError(data.message);
    }
  };
  wsStatus.onclose = () => setTimeout(() => connect(), 1000);
  wsStatus.onopen = requestContainerStatus;

  // Set up periodic container status checks
  setInterval(requestContainerStatus, 5000); // Check every 5 seconds

  // Set up periodic status updates
  setInterval(() => {
    if (wsWorlds && wsWorlds.readyState === WebSocket.OPEN) {
      wsWorlds.send(JSON.stringify({ type: 'get_worlds' }));
    }
  }, refreshInterval);

  // Set up periodic friend requests updates
  setInterval(() => {
    if (wsCommand && wsCommand.readyState === WebSocket.OPEN) {
      wsCommand.send(JSON.stringify({
        type: 'command',
        command: 'friendRequests'
      }));
    }
  }, friendRequestsInterval);

  // Set up periodic banned users updates
  setInterval(() => {
    if (wsCommand && wsCommand.readyState === WebSocket.OPEN) {
      wsCommand.send(JSON.stringify({
        type: 'command',
        command: 'listbans'
      }));
    }
  }, bannedUsersInterval);
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
  if (wsStatus && wsStatus.readyState === WebSocket.OPEN) {
    wsStatus.send(JSON.stringify({ type: 'get_container_status' }));
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

function updateWorlds(worlds, timestamp) {
  // Update worlds list with timestamp
  const worldsList = document.getElementById('worlds-list');
  worldsList.innerHTML = '';
  worlds.forEach(world => {
    const worldDiv = document.createElement('div');
    worldDiv.className = 'world-item';
    worldDiv.setAttribute('data-timestamp', new Date(timestamp).toLocaleString());
    // ... rest of world item creation
  });
}

function updateFriendRequests(requests, timestamp) {
  // Update friend requests with timestamp
  const requestsList = document.getElementById('friend-requests-list');
  requestsList.innerHTML = '';
  requests.forEach(request => {
    const requestDiv = document.createElement('div');
    requestDiv.className = 'friend-request';
    requestDiv.setAttribute('data-timestamp', new Date(timestamp).toLocaleString());
    // ... rest of friend request item creation
  });
}

function updateBannedUsers(bans, timestamp) {
  // Update banned users list with timestamp
  const bansList = document.getElementById('bans-list');
  bansList.innerHTML = '';
  bans.forEach(ban => {
    const banDiv = document.createElement('div');
    banDiv.className = 'ban-item';
    banDiv.setAttribute('data-timestamp', new Date(timestamp).toLocaleString());
    // ... rest of ban item creation
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
