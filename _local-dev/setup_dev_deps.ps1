# Development Environment Setup Script for Resonite Headless Manager
# This script creates a Python virtual environment and installs dependencies
# It can be run multiple times safely and leaves the shell in an active environment state

param(
    [switch]$Force,  # Force recreation of virtual environment
    [switch]$Help    # Show help
)

# Show help if requested
if ($Help) {
    Write-Host "Development Environment Setup Script" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\setup_dev_deps.ps1 [-Force] [-Help]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Parameters:"
    Write-Host "  -Force    Force recreation of the virtual environment" -ForegroundColor Cyan
    Write-Host "  -Help     Show this help message" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "This script will:"
    Write-Host "  1. Create a Python virtual environment in 'Res-Manager' folder"
    Write-Host "  2. Install packages from requirements.txt"
    Write-Host "  3. Install development packages from requirements-dev.txt"
    Write-Host "  4. Activate the environment in your current shell"
    exit 0
}

# Get the repository root (parent directory of _local-dev)
$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $RepoRoot "Res-Manager"
$RequirementsPath = Join-Path $RepoRoot "requirements.txt"
$DevRequirementsPath = Join-Path $RepoRoot "requirements-dev.txt"

Write-Host "=== Resonite Headless Manager - Development Environment Setup ===" -ForegroundColor Green
Write-Host "Repository root: $RepoRoot" -ForegroundColor Gray
Write-Host "Virtual environment path: $VenvPath" -ForegroundColor Gray
Write-Host ""

# Check if Python is available
try {
    $PythonVersion = python --version 2>&1
    Write-Host "Found Python: $PythonVersion" -ForegroundColor Green
} catch {
    Write-Error "Python is not available in PATH. Please install Python and ensure it's in your PATH."
    exit 1
}

# Check if virtual environment exists
$VenvExists = Test-Path $VenvPath
$PyvenvCfg = Join-Path $VenvPath "pyvenv.cfg"

if ($VenvExists -and (-not $Force)) {
    Write-Host "Virtual environment already exists at: $VenvPath" -ForegroundColor Yellow
    
    # Check if it's a valid virtual environment
    if (Test-Path $PyvenvCfg) {
        Write-Host "Virtual environment appears to be valid." -ForegroundColor Green
    } else {
        Write-Warning "Virtual environment may be corrupted. Consider using -Force to recreate."
    }
} elseif ($Force -and $VenvExists) {
    Write-Host "Removing existing virtual environment (Force mode)..." -ForegroundColor Yellow
    Remove-Item -Path $VenvPath -Recurse -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    $VenvExists = $false
}

# Create virtual environment if it doesn't exist
if (-not $VenvExists) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    try {
        python -m venv $VenvPath
        Write-Host "Virtual environment created successfully." -ForegroundColor Green
    } catch {
        Write-Error "Failed to create virtual environment: $_"
        exit 1
    }
}

# Determine activation script path
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
if (-not (Test-Path $ActivateScript)) {
    Write-Error "Activation script not found at: $ActivateScript"
    exit 1
}

# Activate the virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
try {
    & $ActivateScript
    Write-Host "Virtual environment activated." -ForegroundColor Green
} catch {
    Write-Error "Failed to activate virtual environment: $_"
    exit 1
}

# Upgrade pip first
Write-Host "Upgrading pip..." -ForegroundColor Yellow
try {
    python -m pip install --upgrade pip
    Write-Host "pip upgraded successfully." -ForegroundColor Green
} catch {
    Write-Warning "Failed to upgrade pip, continuing anyway..."
}

# Install main requirements
if (Test-Path $RequirementsPath) {
    Write-Host "Installing requirements from requirements.txt..." -ForegroundColor Yellow
    try {
        pip install -r $RequirementsPath
        Write-Host "Main requirements installed successfully." -ForegroundColor Green
    } catch {
        Write-Error "Failed to install main requirements: $_"
        exit 1
    }
} else {
    Write-Warning "requirements.txt not found at: $RequirementsPath"
}

# Install development requirements
if (Test-Path $DevRequirementsPath) {
    Write-Host "Installing development requirements from requirements-dev.txt..." -ForegroundColor Yellow
    try {
        pip install -r $DevRequirementsPath
        Write-Host "Development requirements installed successfully." -ForegroundColor Green
    } catch {
        Write-Error "Failed to install development requirements: $_"
        exit 1
    }
} else {
    Write-Warning "requirements-dev.txt not found at: $DevRequirementsPath"
}

# Show installed packages
Write-Host ""
Write-Host "=== Installed Packages ===" -ForegroundColor Green
pip list

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host "Virtual environment is now active in your current shell." -ForegroundColor Yellow
Write-Host "You can deactivate it by running: deactivate" -ForegroundColor Gray
Write-Host ""
Write-Host "To manually activate this environment in the future, run:" -ForegroundColor Gray
Write-Host "  $ActivateScript" -ForegroundColor Cyan
Write-Host ""
Write-Host "Development environment is ready!" -ForegroundColor Green