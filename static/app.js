let wsLogs;
let wsStatus;
let wsWorlds;
let wsCommand;
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
      appendOutput(data.output);
    }
  };
  wsLogs.onclose = () => setTimeout(() => connect(), 1000);

  // Connect to status endpoint
  wsStatus = new WebSocket(`${wsProtocol}//${wsHost}:8000/ws/status`);
  wsStatus.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'status_update') {
      updateStatus(data.status);
    } else if (data.type === 'error') {
      showError(data.message);
    }
  };
  wsStatus.onclose = () => setTimeout(() => connect(), 1000);

  // Connect to worlds endpoint
  wsWorlds = new WebSocket(`${wsProtocol}//${wsHost}:8000/ws/worlds`);
  wsWorlds.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'worlds_update') {
      updateWorlds(data.output);
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
        updateFriendRequests(data.output);
      }
      console.log('command_response', data.output);
    } else if (data.type === 'bans_update') {
      updateBannedUsers(data.bans);
    } else if (data.type === 'error') {
      showError(data.message);
    }
  };
  wsCommand.onclose = () => setTimeout(() => connect(), 1000);

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

function appendOutput(text, className = '') {
  const div = document.createElement('div');
  div.textContent = text;
  if (className) {
    div.className = className;
  }
  output.appendChild(div);
  output.scrollTop = output.scrollHeight;
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

function updateStatus(status) {
  const statusDiv = document.getElementById('status');
  const statusText = statusDiv.querySelector('.status-text');
  const lastUpdated = statusDiv.querySelector('.last-updated');
  const cpuUsage = document.getElementById('cpu-usage');
  const memoryUsage = document.getElementById('memory-usage');

  // Update last-updated timestamp
  const now = new Date();
  const timeString = now.toLocaleTimeString();
  lastUpdated.textContent = `Last updated: ${timeString}`;

  // Remove all existing status classes
  statusDiv.classList.remove('status-connecting', 'status-running', 'status-stopped');

  if (status.error) {
    statusDiv.classList.add('status-stopped');
    statusText.textContent = `Error - ${status.error}`;
    updateContainerControls('stopped');
    return;
  }

  // Update system stats
  if (status.cpu_usage !== undefined) {
    cpuUsage.textContent = `${status.cpu_usage.toFixed(1)}%`;
  }

  if (status.memory_percent !== undefined) {
    memoryUsage.textContent = `${status.memory_percent.toFixed(1)}% (${status.memory_used}/${status.memory_total})`;
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

function updateWorlds(worlds) {
  const worldsList = document.getElementById('worlds-list');

  // Clear existing worlds
  worldsList.innerHTML = '';

  // If worlds is undefined/null, show loading placeholder
  if (!worlds) {
    const loadingPlaceholder = document.createElement('div');
    loadingPlaceholder.className = 'world-card loading';
    loadingPlaceholder.innerHTML = `
      <div class="loading-content">
        <span class="loading-text">Retrieving Instance Data</span>
      </div>
    `;
    worldsList.appendChild(loadingPlaceholder);
    return;
  }

  if (worlds.length === 0) {
    const noWorldsDiv = document.createElement('div');
    noWorldsDiv.className = 'no-worlds';
    noWorldsDiv.textContent = 'No active worlds found';
    worldsList.appendChild(noWorldsDiv);
    return;
  }

  worlds.forEach((world, index) => {
    const worldDiv = document.createElement('div');
    worldDiv.className = 'world-card';
    worldDiv.dataset.sessionId = world.sessionId;
    worldDiv.dataset.name = world.name;
    worldDiv.dataset.hidden = world.hidden;
    worldDiv.dataset.description = world.description;
    worldDiv.dataset.accessLevel = world.accessLevel;
    worldDiv.dataset.maxUsers = world.maxUsers;
    worldDiv.dataset.index = index; // Add the index to the dataset
    worldDiv.dataset.usersList = JSON.stringify(world.users_list || []); // Add users list to dataset

    // Add click handler
    worldDiv.addEventListener('click', () => selectWorld(world.sessionId));

    // Create tags HTML if tags exist
    const tagsHtml = world.tags ?
      `<div class="world-tags">
            ${world.tags.split(',').map(tag => `<span class="tag">${tag.trim()}</span>`).join('')}
           </div>` : '';

    // Create users list HTML if users exist
    const usersHtml = world.users_list && world.users_list.length > 0 ?
      `<div class="user-list">
            <span class="label">Connected Users:</span>
            <div class="users">
              ${world.users_list.map(user => `
                <div class="user-card">
                  <div class="user-header">
                    <div class="user-info">
                      <span class="user-name">${user.username}</span>
                      <div class="copy-buttons">
                        <button onclick="event.stopPropagation(); copyText('${user.username}', 'username')" class="copy-user-btn" title="Copy Username">
                          Copy Name
                        </button>
                        <button onclick="event.stopPropagation(); copyText('${user.userId}', 'userId')" class="copy-user-btn" title="Copy User ID">
                          Copy ID
                        </button>
                      </div>
                    </div>
                    <select class="role-select" onchange="handleRoleChange(event, '${user.username}', ${index})">
                      ${AVAILABLE_ROLES.map(role => `
                        <option value="${role}" ${user.role === role ? 'selected' : ''}>
                          ${role}
                        </option>
                      `).join('')}
                    </select>
                  </div>
                  <div class="user-stats">
                    <span class="user-stat" title="Present Status">
                      <i class="status-dot ${user.present ? 'present' : 'away'}"></i>
                      ${user.present ? 'Present' : 'Away'}
                    </span>
                    <span class="user-stat" title="Ping">
                      ${user.ping !== undefined ? `${user.ping}ms` : 'N/A'}
                    </span>
                    <span class="user-stat" title="FPS">
                      ${user.fps !== undefined ? `${user.fps.toFixed(1)} FPS` : 'N/A'}
                    </span>
                    ${user.silenced ? '<span class="user-stat silenced" title="User is silenced">🔇</span>' : ''}
                  </div>
                  <div class="user-actions">
                    <button onclick="event.stopPropagation(); handleUserAction('kick', '${user.username}', ${index})" class="user-action-btn" title="Kick User">
                      Kick
                    </button>
                    <button onclick="event.stopPropagation(); handleUserAction('respawn', '${user.username}', ${index})" class="user-action-btn" title="Respawn User">
                      Respawn
                    </button>
                    <button onclick="event.stopPropagation(); handleUserAction('${user.silenced ? 'unsilence' : 'silence'}', '${user.username}', ${index})" class="user-action-btn ${user.silenced ? 'unsilence' : 'silence'}" title="${user.silenced ? 'Unsilence User' : 'Silence User'}">
                      ${user.silenced ? 'Unsilence' : 'Silence'}
                    </button>
                    <button onclick="event.stopPropagation(); handleUserAction('ban', '${user.username}', ${index})" class="user-action-btn ban" title="Ban User">
                      Ban
                    </button>
                  </div>
                </div>
              `).join('')}
            </div>
           </div>` : '';

    worldDiv.innerHTML = `
          <span class="world-name">${world.name}</span>
          <div class="session-id-container">
            <div class="session-id">Session: ${world.sessionId}</div>
            <button
              class="copy-button"
              onclick="event.stopPropagation(); copyToClipboard('${world.sessionId}')"
              data-session-id="${world.sessionId}">
              Copy
            </button>
          </div>
          <div class="world-details">
            <div class="world-stat">
              <span class="label">Users:</span>
              <span>${world.users}/${world.maxUsers}</span>
            </div>
            <div class="world-stat">
              <span class="label">Present:</span>
              <span>${world.present}</span>
            </div>
            <div class="world-stat">
              <span class="label">Access:</span>
              <span>${world.accessLevel}</span>
            </div>
            <div class="world-stat">
              <span class="label">Uptime:</span>
              <span>${world.uptime}</span>
            </div>
            <div class="world-stat">
              <span class="label">Hidden:</span>
              <span>${world.hidden ? 'Yes' : 'No'}</span>
            </div>
            <div class="world-stat">
              <span class="label">Mobile:</span>
              <span>${world.mobileFriendly ? 'Yes' : 'No'}</span>
            </div>
            ${world.description ?
        `<div class="world-description">${world.description}</div>` : ''}
            ${tagsHtml}
            ${usersHtml}
          </div>
        `;

    worldsList.appendChild(worldDiv);
  });
}

// Handle Enter key in input
commandInput.addEventListener('keypress', function (e) {
  if (e.key === 'Enter') {
    sendCommand();
  }
});

// Initial connection
connect();

function toggleConsole() {
  const consoleSection = document.querySelector('.console-section');
  const toggleButton = document.querySelector('.toggle-console:nth-of-type(1)');
  const isExpanded = consoleSection.style.display === 'block';

  // Close config panel if open
  const configSection = document.querySelector('.config-section');
  const configButton = document.querySelector('.toggle-console:nth-of-type(2)');
  configSection.style.display = 'none';
  configButton.classList.remove('expanded');

  consoleSection.style.display = isExpanded ? 'none' : 'block';
  toggleButton.classList.toggle('expanded', !isExpanded);

  if (!isExpanded) {
    const input = document.getElementById('command-input');
    input.focus();
  }
}

function toggleConfig() {
  const configSection = document.querySelector('.config-section');
  const toggleButton = document.querySelector('.toggle-console:nth-of-type(2)');
  const isExpanded = configSection.style.display === 'block';

  // Close console panel if open
  const consoleSection = document.querySelector('.console-section');
  const consoleButton = document.querySelector('.toggle-console:nth-of-type(1)');
  consoleSection.style.display = 'none';
  consoleButton.classList.remove('expanded');

  configSection.style.display = isExpanded ? 'none' : 'block';
  toggleButton.classList.toggle('expanded', !isExpanded);

  if (!isExpanded && !currentConfig) {
    loadConfig();
  }
}

function copyToClipboard(sessionId) {
  const button = document.querySelector(`button[data-session-id="${sessionId}"]`);
  if (!button) return;

  // Check if the Clipboard API is supported
  if (!navigator.clipboard) {
    // Fallback for browsers that don't support the Clipboard API
    const textArea = document.createElement('textarea');
    textArea.value = sessionId;
    textArea.style.position = 'fixed';  // Avoid scrolling to bottom
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
      document.execCommand('copy');
      const originalText = button.textContent;
      button.textContent = 'Copied!';
      button.classList.add('copied');

      setTimeout(() => {
        button.textContent = originalText;
        button.classList.remove('copied');
      }, 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }

    document.body.removeChild(textArea);
    return;
  }

  // Use Clipboard API if available
  navigator.clipboard.writeText(sessionId)
    .then(() => {
      const originalText = button.textContent;
      button.textContent = 'Copied!';
      button.classList.add('copied');

      setTimeout(() => {
        button.textContent = originalText;
        button.classList.remove('copied');
      }, 2000);
    })
    .catch(err => {
      console.error('Failed to copy text:', err);
    });
}

let currentConfig = null;

async function loadConfig() {
  console.log('loadConfig')
  try {
    const response = await fetch(`http://${window.location.hostname}:8000/config`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const result = await response.json();
    const editor = document.getElementById('config-editor');

    // Set the raw content in the editor
    editor.value = result.content;

    // Try to parse it as JSON
    try {
      const parsedConfig = JSON.parse(result.content);
      currentConfig = parsedConfig;
      hideError();
    } catch (jsonError) {
      showError(`Invalid JSON: ${jsonError.message}`);
    }

    updateLineNumbers();
    updateLineHighlight();
  } catch (error) {
    showError(`Failed to load config: ${error.message}`);
  }
}

async function saveConfig() {
  const editor = document.getElementById('config-editor');
  try {
    // Validate JSON
    const config = JSON.parse(editor.value);

    // Send to server using window.location.hostname
    const response = await fetch(`http://${window.location.hostname}:8000/config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to save config');
    }

    currentConfig = config;
    hideError();
    showSuccess();
  } catch (error) {
    showError(`Invalid JSON: ${error.message}`);
  }
}

function formatConfig() {
  const editor = document.getElementById('config-editor');
  try {
    const config = JSON.parse(editor.value);
    editor.value = JSON.stringify(config, null, 2);
    updateLineNumbers();
    hideError();
  } catch (error) {
    showError(`Invalid JSON: ${error.message}`);
  }
}

function showError(message) {
  const errorDiv = document.querySelector('.error-message');
  errorDiv.textContent = message;
  errorDiv.style.display = 'block';
  errorDiv.style.backgroundColor = '#ff6b6b22';
  errorDiv.style.color = '#ff6b6b';
}

function showSuccess() {
  const errorDiv = document.querySelector('.error-message');
  errorDiv.textContent = 'Config saved successfully!';
  errorDiv.style.display = 'block';
  errorDiv.style.backgroundColor = '#4CAF5022';
  errorDiv.style.color = '#4CAF50';
  setTimeout(() => {
    errorDiv.style.display = 'none';
  }, 3000);
}

function hideError() {
  const errorDiv = document.querySelector('.error-message');
  errorDiv.style.display = 'none';
}

let refreshInterval = 30 * 1000; // Default 30 seconds
let refreshTimer = null;

function updateRefreshInterval() {
  console.log('updateRefreshInterval');
  const input = document.getElementById('refresh-interval');
  const newInterval = Math.max(5, Math.min(60, parseInt(input.value))) * 1000;

  if (refreshInterval !== newInterval) {
    refreshInterval = newInterval;

    // Clear existing timer
    if (refreshTimer) {
      clearInterval(refreshTimer);
    }

    // Set up new timer
    refreshTimer = setInterval(() => {
      if (wsWorlds && wsWorlds.readyState === WebSocket.OPEN) {
        wsWorlds.send(JSON.stringify({ type: 'get_worlds' }));
      }
    }, refreshInterval);
  }
}

// Add event listener for the refresh interval input
document.getElementById('refresh-interval').addEventListener('change', updateRefreshInterval);
document.getElementById('refresh-interval').addEventListener('input', updateRefreshInterval);

function updateLineNumbers() {
  const editor = document.getElementById('config-editor');
  const lineNumbers = document.getElementById('line-numbers');
  const lines = editor.value.split('\n');

  // Create div elements for each line number
  const numbersHtml = lines
    .map((_, i) => `<div>${(i + 1).toString().padStart(3)}</div>`)
    .join('');

  lineNumbers.innerHTML = numbersHtml;

  // Sync scroll position
  lineNumbers.scrollTop = editor.scrollTop;
}

// Update the scroll event listener
document.getElementById('config-editor').addEventListener('scroll', function () {
  const lineNumbers = document.getElementById('line-numbers');
  lineNumbers.scrollTop = this.scrollTop;

  const highlight = document.getElementById('config-editor-highlight');
  if (highlight) {
    highlight.style.transform = `translateY(-${this.scrollTop}px)`;
  }
});

// Add event listeners for the config editor
document.getElementById('config-editor').addEventListener('input', () => {
  updateLineNumbers();
  updateLineHighlight();
});

document.getElementById('config-editor').addEventListener('keyup', updateLineHighlight);
document.getElementById('config-editor').addEventListener('click', updateLineHighlight);
document.getElementById('config-editor').addEventListener('scroll', function () {
  document.getElementById('line-numbers').scrollTop = this.scrollTop;
  const highlight = document.getElementById('config-editor-highlight');
  if (highlight) {
    highlight.style.transform = `translateY(-${this.scrollTop}px)`;
  }
});

function updateLineHighlight() {
  const editor = document.getElementById('config-editor');
  const lineNumbers = document.getElementById('line-numbers');
  const lineHeight = 21; // Fixed line height to match CSS

  // Get cursor position
  const cursorPosition = editor.selectionStart;
  const lines = editor.value.substr(0, cursorPosition).split('\n');
  const currentLineNumber = lines.length;

  // Update line numbers highlight
  const lineNumberElements = editor.value.split('\n')
    .map((_, i) => `<div class="${i + 1 === currentLineNumber ? 'current-line' : ''}">${(i + 1).toString().padStart(3)}</div>`)
    .join('');
  lineNumbers.innerHTML = lineNumberElements;

  // Update editor line highlight
  let highlight = document.getElementById('config-editor-highlight');
  if (!highlight) {
    highlight = document.createElement('div');
    highlight.id = 'config-editor-highlight';
    editor.parentElement.insertBefore(highlight, editor);
  }

  highlight.style.top = `${(currentLineNumber - 1) * lineHeight + 10}px`; // Add padding offset
}

// Add function to handle world selection
function selectWorld(sessionId) {
  const worldsList = document.getElementById('worlds-list');
  const previousSelected = worldsList.querySelector('.world-card.selected');
  if (previousSelected) {
    previousSelected.classList.remove('selected');
  }

  const selectedWorld = worldsList.querySelector(`[data-session-id="${sessionId}"]`);
  if (selectedWorld) {
    selectedWorld.classList.add('selected');
    updateWorldPropertiesEditor(sessionId);
    updateConnectedUsers(selectedWorld);
  }
}

// Add this new function to update Connected Users panel
function updateConnectedUsers(worldCard, forceRefresh = false) {
  const connectedUsersPanel = document.getElementById('connected-users');
  const worldName = worldCard.querySelector('.world-name').textContent;
  const sessionId = worldCard.dataset.sessionId;
  
  // Update panel header
  document.getElementById('connected-users-world-name').textContent = worldName;
  
  // Update users list
  const connectedUsersList = document.getElementById('connected-users-list');
  const world = findWorldBySessionId(sessionId);
  
  if (world && world.users_list && world.users_list.length > 0) {
    connectedUsersList.innerHTML = `
      <div class="users">
        ${world.users_list.map(user => `
          <div class="user-card">
            <div class="user-header">
              <div class="user-info">
                <span class="user-name">${user.username}</span>
                <div class="copy-buttons">
                  <button onclick="event.stopPropagation(); copyText('${user.username}', 'username')" class="copy-user-btn" title="Copy Username">
                    Copy Name
                  </button>
                  <button onclick="event.stopPropagation(); copyText('${user.userId}', 'userId')" class="copy-user-btn" title="Copy User ID">
                    Copy ID
                  </button>
                </div>
              </div>
              <select class="role-select" onchange="handleRoleChange(event, '${user.username}', ${worldCard.dataset.index})">
                ${AVAILABLE_ROLES.map(role => `
                  <option value="${role}" ${user.role === role ? 'selected' : ''}>
                    ${role}
                  </option>
                `).join('')}
              </select>
            </div>
            <div class="user-stats">
              <span class="user-stat" title="Present Status">
                <i class="status-dot ${user.present ? 'present' : 'away'}"></i>
                ${user.present ? 'Present' : 'Away'}
              </span>
              <span class="user-stat" title="Ping">
                ${user.ping !== undefined ? `${user.ping}ms` : 'N/A'}
              </span>
              <span class="user-stat" title="FPS">
                ${user.fps !== undefined ? `${user.fps.toFixed(1)} FPS` : 'N/A'}
              </span>
              ${user.silenced ? '<span class="user-stat silenced" title="User is silenced">🔇</span>' : ''}
            </div>
            <div class="user-actions">
              <button onclick="event.stopPropagation(); handleUserAction('kick', '${user.username}', ${worldCard.dataset.index})" class="user-action-btn" title="Kick User">
                Kick
              </button>
              <button onclick="event.stopPropagation(); handleUserAction('respawn', '${user.username}', ${worldCard.dataset.index})" class="user-action-btn" title="Respawn User">
                Respawn
              </button>
              <button onclick="event.stopPropagation(); handleUserAction('${user.silenced ? 'unsilence' : 'silence'}', '${user.username}', ${worldCard.dataset.index})" class="user-action-btn ${user.silenced ? 'unsilence' : 'silence'}" title="${user.silenced ? 'Unsilence User' : 'Silence User'}">
                ${user.silenced ? 'Unsilence' : 'Silence'}
              </button>
              <button onclick="event.stopPropagation(); handleUserAction('ban', '${user.username}', ${worldCard.dataset.index})" class="user-action-btn ban" title="Ban User">
                Ban
              </button>
            </div>
          </div>
        `).join('')}
      </div>`;
  } else {
    connectedUsersList.innerHTML = '<div class="no-users">No users connected</div>';
  }
  
  connectedUsersPanel.style.display = 'block';
}

// Add function to refresh users list
function refreshUsersList() {
  if (wsWorlds && wsWorlds.readyState === WebSocket.OPEN) {
    wsWorlds.send(JSON.stringify({ type: 'get_worlds' }));
  }
}

// Helper function to find world data by session ID
function findWorldBySessionId(sessionId) {
  const worldCard = document.querySelector(`.world-card[data-session-id="${sessionId}"]`);
  if (!worldCard) return null;

  // Find the matching world data from the card's dataset
  const index = parseInt(worldCard.dataset.index);
  const allWorlds = document.getElementById('worlds-list').querySelectorAll('.world-card');
  const worldsArray = Array.from(allWorlds).map(card => ({
    sessionId: card.dataset.sessionId,
    name: card.dataset.name,
    hidden: card.dataset.hidden === 'true',
    description: card.dataset.description || '',
    accessLevel: card.dataset.accessLevel,
    maxUsers: parseInt(card.dataset.maxUsers),
    users_list: JSON.parse(card.dataset.usersList || '[]')
  }));

  return worldsArray.find(world => world.sessionId === sessionId);
}

// Add this function to handle world selection
function updateWorldPropertiesEditor(sessionId) {
  const worldCard = document.querySelector(`.world-card[data-session-id="${sessionId}"]`);
  if (!worldCard) return;

  const propertiesEditor = document.getElementById('world-properties');
  propertiesEditor.style.display = 'block';

  // Update world name in the header
  document.getElementById('selected-world-name').textContent = worldCard.querySelector('.world-name').textContent;

  // Update form values and store original values
  const form = {
    name: document.getElementById('world-name'),
    hidden: document.getElementById('world-hidden'),
    description: document.getElementById('world-description'),
    accessLevel: document.getElementById('world-access-level'),
    maxUsers: document.getElementById('world-max-users')
  };

  form.name.value = worldCard.dataset.name;
  form.hidden.checked = worldCard.dataset.hidden === 'true';
  form.description.value = worldCard.dataset.description || '';
  form.accessLevel.value = worldCard.dataset.accessLevel;
  form.maxUsers.value = worldCard.dataset.maxUsers;

  // Store original values for comparison
  propertiesEditor.dataset.originalName = worldCard.dataset.name;
  propertiesEditor.dataset.originalHidden = worldCard.dataset.hidden;
  propertiesEditor.dataset.originalDescription = worldCard.dataset.description || '';
  propertiesEditor.dataset.originalAccessLevel = worldCard.dataset.accessLevel;
  propertiesEditor.dataset.originalMaxUsers = worldCard.dataset.maxUsers;

  // Store session ID and world index for the save function
  propertiesEditor.dataset.sessionId = sessionId;
  propertiesEditor.dataset.worldIndex = worldCard.dataset.index;
}

// Helper function to find world data by session ID
function findWorldBySessionId(sessionId) {
  const worldCard = document.querySelector(`.world-card[data-session-id="${sessionId}"]`);
  if (!worldCard) return null;

  // Extract world data from the card's dataset
  return {
    name: worldCard.dataset.name,
    hidden: worldCard.dataset.hidden === 'true',
    description: worldCard.dataset.description || '',
    accessLevel: worldCard.dataset.accessLevel,
    maxUsers: parseInt(worldCard.dataset.maxUsers)
  };
}

// Update the save function to check for changes and send appropriate commands
async function saveWorldProperties() {
  const propertiesEditor = document.getElementById('world-properties');
  const sessionId = propertiesEditor.dataset.sessionId;
  const worldIndex = propertiesEditor.dataset.worldIndex;

  // Get current values
  const currentValues = {
    name: document.getElementById('world-name').value,
    hidden: document.getElementById('world-hidden').checked,
    description: document.getElementById('world-description').value,
    accessLevel: document.getElementById('world-access-level').value,
    maxUsers: parseInt(document.getElementById('world-max-users').value)
  };

  // Get original values
  const originalValues = {
    name: propertiesEditor.dataset.originalName,
    hidden: propertiesEditor.dataset.originalHidden === 'true',
    description: propertiesEditor.dataset.originalDescription,
    accessLevel: propertiesEditor.dataset.originalAccessLevel,
    maxUsers: parseInt(propertiesEditor.dataset.originalMaxUsers)
  };

  // First focus the world
  wsCommand.send(JSON.stringify({
    type: 'command',
    command: `focus ${worldIndex}`
  }));

  // Wait for focus command to complete
  await new Promise(resolve => setTimeout(resolve, 500));

  // Array to store commands that need to be executed
  const commands = [];

  // Check each field for changes and add necessary commands
  if (currentValues.name !== originalValues.name) {
    commands.push(`name ${currentValues.name}`);
  }

  if (currentValues.hidden !== originalValues.hidden) {
    commands.push(`hideFromListing ${currentValues.hidden}`);
  }

  if (currentValues.description !== originalValues.description) {
    commands.push(`description ${currentValues.description}`);
  }

  if (currentValues.accessLevel !== originalValues.accessLevel) {
    commands.push(`accessLevel ${currentValues.accessLevel}`);
  }

  if (currentValues.maxUsers !== originalValues.maxUsers) {
    commands.push(`maxUsers ${currentValues.maxUsers}`);
  }

  // Execute each command sequentially
  for (const command of commands) {
    wsCommand.send(JSON.stringify({
      type: 'command',
      command: command
    }));
    // Wait between commands
    await new Promise(resolve => setTimeout(resolve, 200));
  }

  // If any changes were made, save the config and reload
  if (commands.length > 0) {
    // Save the world configuration
    wsCommand.send(JSON.stringify({
      type: 'command',
      command: 'saveConfig'
    }));

    // Wait for save to complete
    await new Promise(resolve => setTimeout(resolve, 500));

    // Reload the config editor
    loadConfig();

    // Refresh the worlds list
    wsWorlds.send(JSON.stringify({ type: 'get_worlds' }));
  }

  // Close the properties editor
  propertiesEditor.style.display = 'none';

  // Clear the selected state from the world card
  const worldsList = document.getElementById('worlds-list');
  const selectedWorld = worldsList.querySelector('.world-card.selected');
  if (selectedWorld) {
    selectedWorld.classList.remove('selected');
  }
}

// Add this function to handle friend requests updates
function updateFriendRequests(requests) {
  const requestsList = document.getElementById('friend-requests-list');
  const header = document.querySelector('.friend-requests-card .sidebar-header');

  // Convert requests to array if it's a string
  const requestsArray = Array.isArray(requests) ? requests : [requests];
  
  // Filter out empty strings and previously denied requests
  const filteredRequests = requestsArray.filter(username => 
    username && username.trim() && !deniedFriendRequests.has(username.trim())
  );

  // Update the header with request count
  const existingCount = header.querySelector('.request-count');
  if (existingCount) {
    existingCount.remove();
  }

  if (filteredRequests && filteredRequests.length > 0) {
    const count = document.createElement('span');
    count.className = 'request-count';
    count.textContent = filteredRequests.length;
    header.appendChild(count);
  }

  if (!filteredRequests || filteredRequests.length === 0) {
    requestsList.innerHTML = '<div class="no-requests">No pending friend requests</div>';
    return;
  }

  requestsList.innerHTML = filteredRequests
    .map(username => `
      <div class="friend-request">
        <div class="username">${username.trim()}</div>
        <div class="request-actions">
          <button onclick="handleFriendRequest('accept', '${username.trim()}')" class="accept-button">Accept</button>
          <button onclick="handleFriendRequest('deny', '${username.trim()}')" class="deny-button">Deny</button>
        </div>
      </div>
    `)
    .join('');
}

// Add function to handle friend request actions
async function handleFriendRequest(action, username) {
  // Update the command format for accepting friend requests
  const command = action === 'accept' ? `acceptFriendRequest ${username}` : `denyFriend ${username}`;

  wsCommand.send(JSON.stringify({
    type: 'command',
    command: command
  }));

  // If denying, add to denied list and save to localStorage
  if (action === 'deny') {
    deniedFriendRequests.add(username);
    localStorage.setItem('deniedFriendRequests', JSON.stringify([...deniedFriendRequests]));
  }

  // Refresh friend requests after action
  setTimeout(() => {
    if (wsCommand.readyState === WebSocket.OPEN) {
      wsCommand.send(JSON.stringify({
        type: 'command',
        command: 'friendRequests'
      }));
    }
  }, 1000); // Wait 1 second before refreshing to allow the command to process
}

// Add function to update friend requests interval
function updateFriendRequestsInterval() {
  const input = document.getElementById('friend-requests-interval');
  const newInterval = Math.max(1, parseInt(input.value)) * 60 * 1000; // Convert minutes to milliseconds

  if (friendRequestsInterval !== newInterval) {
    friendRequestsInterval = newInterval;

    // Clear existing timer
    if (friendRequestsTimer) {
      clearInterval(friendRequestsTimer);
    }

    // Set up new timer
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

// Add event listener for the friend requests interval input
document.getElementById('friend-requests-interval').addEventListener('change', updateFriendRequestsInterval);
document.getElementById('friend-requests-interval').addEventListener('input', updateFriendRequestsInterval);

// Add this function after the selectWorld function

async function sendWorldCommand(command) {
  const propertiesEditor = document.getElementById('world-properties');
  const sessionId = propertiesEditor.dataset.sessionId;

  if (!sessionId) {
    console.error('No world selected');
    return;
  }

  // Map commands to their actual console commands
  const commandMap = {
    'restart': `restart ${sessionId}`,
    'save': `save ${sessionId}`,
    'close': `close ${sessionId}`
  };

  const actualCommand = commandMap[command];

  if (!actualCommand) {
    console.error('Invalid command');
    return;
  }

  // Send the command through the websocket
  wsCommand.send(JSON.stringify({
    type: 'command',
    command: actualCommand
  }));

  // After a short delay, refresh the worlds list
  setTimeout(() => {
    wsWorlds.send(JSON.stringify({ type: 'get_worlds' }));
  }, 1000);
}

async function restartContainer() {
  if (confirm('Are you sure you want to restart the Docker container? This will close all worlds.')) {
    try {
      const response = await fetch('/api/restart-container', {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error('Failed to restart container');
      }

      // The WebSocket will automatically reconnect after container restart
    } catch (error) {
      console.error('Error restarting container:', error);
    }
  }
}

// Add this function after the existing functions
function toggleCard(cardId) {
  const content = document.getElementById(cardId);
  const header = content.previousElementSibling;

  content.classList.toggle('collapsed');
  header.classList.toggle('collapsed');

  // Store the state in localStorage
  localStorage.setItem(`${cardId}-collapsed`, content.classList.contains('collapsed'));
}

// Add this function to initialize the collapse states
function initializeCardStates() {
  const cards = ['app-settings', 'friend-requests'];

  cards.forEach(cardId => {
    const content = document.getElementById(cardId);
    const header = content.previousElementSibling;
    const isCollapsed = localStorage.getItem(`${cardId}-collapsed`) === 'true';

    if (isCollapsed) {
      content.classList.add('collapsed');
      header.classList.add('collapsed');
    }
  });
}

// Add this new function to clear denied requests (can be called from console if needed)
function clearDeniedFriendRequests() {
  if (confirm('Are you sure you want to clear all denied friend requests? They will start showing up in the list again.')) {
    deniedFriendRequests.clear();
    localStorage.removeItem('deniedFriendRequests');
    // Refresh the requests list
    wsCommand.send(JSON.stringify({
      type: 'command',
      command: 'friendRequests'
    }));
  }
}

// Replace the updateBannedUsers function with this simpler version
function updateBannedUsers(bans) {
  const bansList = document.getElementById('banned-users-list');

  if (!bans || bans.length === 0) {
    bansList.innerHTML = '<div class="no-bans">No banned users</div>';
    return;
  }

  bansList.innerHTML = bans
    .map(ban => `
            <div class="banned-user">
                <div class="ban-info">
                    <span class="banned-username">${ban.username}</span>
                    <span class="ban-reason">${ban.userId}</span>
                </div>
                <button onclick="unbanUser('${ban.username}')" class="unban-button">
                    Unban
                </button>
            </div>
        `)
    .join('');
}

// Add this function to handle unbanning users
function unbanUser(username) {
  if (confirm(`Are you sure you want to unban ${username}?`)) {
    wsCommand.send(JSON.stringify({
      type: 'command',
      command: `unbanByName ${username}`
    }));

    // Refresh the bans list after a short delay
    setTimeout(() => {
      wsCommand.send(JSON.stringify({
        type: 'command',
        command: 'listbans'
      }));
    }, 1000);
  }
}

// Add this function to handle banning users
function banUser() {
  const usernameInput = document.getElementById('ban-username');
  const username = usernameInput.value.trim();

  if (!username) {
    alert('Please enter a username');
    return;
  }

  if (confirm(`Are you sure you want to ban ${username}?`)) {
    wsCommand.send(JSON.stringify({
      type: 'command',
      command: `banByName ${username}`
    }));

    // Clear the input
    usernameInput.value = '';

    // Refresh the bans list after a short delay
    setTimeout(() => {
      wsCommand.send(JSON.stringify({
        type: 'command',
        command: 'listbans'
      }));
    }, 1000);
  }
}

// Add event listener for Enter key in ban input
document.addEventListener('DOMContentLoaded', () => {
  const banInput = document.getElementById('ban-username');
  banInput.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
      banUser();
    }
  });
});

// Add this function after the existing functions
async function handleUserAction(action, username, worldIndex) {
  if (!wsCommand || wsCommand.readyState !== WebSocket.OPEN) return;

  // First focus the correct world
  if (action !== 'ban') { // Ban doesn't require focusing
    wsCommand.send(JSON.stringify({
      type: 'command',
      command: `focus ${worldIndex}`
    }));

    // Wait a moment for the focus command to complete
    setTimeout(() => {
      const command = getActionCommand(action, username);
      if (command) {
        wsCommand.send(JSON.stringify({
          type: 'command',
          command: command
        }));

        // Refresh the worlds list after a short delay
        setTimeout(() => {
          if (wsWorlds && wsWorlds.readyState === WebSocket.OPEN) {
            wsWorlds.send(JSON.stringify({ type: 'get_worlds' }));
          }
        }, 1000);
      }
    }, 500);
  } else {
    // Handle ban action directly
    wsCommand.send(JSON.stringify({
      type: 'command',
      command: `banByName ${username}`
    }));
  }
}

// Helper function for handleUserAction
function getActionCommand(action, username) {
  switch (action) {
    case 'kick': return `kick ${username}`;
    case 'respawn': return `respawn ${username}`;
    case 'silence': return `silence ${username}`;
    case 'unsilence': return `unsilence ${username}`;
    default: return null;
  }
}

// Add this new function after handleUserAction
async function handleRoleChange(event, username, worldIndex) {
  const newRole = event.target.value;

  if (wsCommand && wsCommand.readyState === WebSocket.OPEN) {
    // First focus the world
    wsCommand.send(JSON.stringify({
      type: 'command',
      command: `focus ${worldIndex}`
    }));

    // Wait a moment for the focus command to complete
    setTimeout(() => {
      wsCommand.send(JSON.stringify({
        type: 'command',
        command: `role ${username} ${newRole}`
      }));

      // Refresh the worlds list after a short delay
      setTimeout(() => {
        if (wsWorlds && wsWorlds.readyState === WebSocket.OPEN) {
          wsWorlds.send(JSON.stringify({ type: 'get_worlds' }));
        }
      }, 1000);
    }, 500);
  }
}

// Add this function after the saveWorldProperties function
function cancelWorldProperties() {
  const propertiesEditor = document.getElementById('world-properties');
  const connectedUsersPanel = document.getElementById('connected-users');
  propertiesEditor.style.display = 'none';
  connectedUsersPanel.style.display = 'none';

  // Clear the selected state from the world card
  const worldsList = document.getElementById('worlds-list');
  const selectedWorld = worldsList.querySelector('.world-card.selected');
  if (selectedWorld) {
    selectedWorld.classList.remove('selected');
  }
}

// Add this new function after copyToClipboard function
function copyText(text, type) {
  // Check if the Clipboard API is supported
  if (!navigator.clipboard) {
    // Fallback for browsers that don't support the Clipboard API
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';  // Avoid scrolling to bottom
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
      document.execCommand('copy');
      showCopySuccess(type);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }

    document.body.removeChild(textArea);
    return;
  }

  // Use Clipboard API if available
  navigator.clipboard.writeText(text)
    .then(() => {
      showCopySuccess(type);
    })
    .catch(err => {
      console.error('Failed to copy text:', err);
    });
}

// Add this helper function for showing the success message
function showCopySuccess(type) {
  const message = document.createElement('div');
  message.className = 'copy-success-message';
  message.textContent = `${type === 'username' ? 'Username' : 'User ID'} copied!`;
  document.body.appendChild(message);

  // Trigger animation
  setTimeout(() => message.classList.add('show'), 10);

  // Remove after animation
  setTimeout(() => {
    message.classList.remove('show');
    setTimeout(() => document.body.removeChild(message), 300);
  }, 2000);
}
