# PowerShell script to clean up the Python virtual environment and remove unnecessary files.

# Save the original working directory
$originalDir = Get-Location

# Function to restore original directory and exit
function Restore-DirectoryAndExit {
    param([int]$ExitCode = 0)
    Set-Location $originalDir
    exit $ExitCode
}

# Set up Ctrl+C handler to restore directory
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    Set-Location $using:originalDir
}

# Change to the project root directory (parent of _local-dev)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

Write-Host "Working in project root: $projectRoot" -ForegroundColor Cyan

# Function to check if virtual environment is active
function Test-VirtualEnvironmentActive {
    # Check if VIRTUAL_ENV environment variable is set and points to our Res-Manager
    if ($env:VIRTUAL_ENV) {
        $currentVenv = Split-Path -Leaf $env:VIRTUAL_ENV
        if ($currentVenv -eq "Res-Manager") {
            return $true
        }
    }
    
    # Also check if python.exe is running from our virtual environment
    try {
        $pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
        if ($pythonPath -and $pythonPath.Contains("Res-Manager")) {
            return $true
        }
    } catch {
        # Ignore errors
    }
    
    return $false
}

# Check for active virtual environment
if (Test-VirtualEnvironmentActive) {
    Write-Host "" -ForegroundColor Red
    Write-Host "⚠️  WARNING: The Python virtual environment appears to be active!" -ForegroundColor Red
    Write-Host "" -ForegroundColor Red
    Write-Host "Please deactivate the virtual environment before running this script:" -ForegroundColor Yellow
    Write-Host "  1. In your terminal, run: deactivate" -ForegroundColor White
    Write-Host "  2. In VS Code, change the Python interpreter:" -ForegroundColor White
    Write-Host "     - Press Ctrl+Shift+P" -ForegroundColor White
    Write-Host "     - Type 'Python: Select Interpreter'" -ForegroundColor White
    Write-Host "     - Choose a system Python or different environment" -ForegroundColor White
    Write-Host "" -ForegroundColor White
    Write-Host "Press 'C' to continue anyway (may fail) or 'Q' to quit and exit..." -ForegroundColor Yellow
    
    do {
        $key = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        $keyChar = $key.Character.ToString().ToUpper()
        
        if ($keyChar -eq "Q") {
            Write-Host ""
            Write-Host "Exiting cleanup script..." -ForegroundColor Yellow
            Restore-DirectoryAndExit 0
        } elseif ($keyChar -eq "C") {
            Write-Host ""
            Write-Host "Continuing with cleanup (this may fail)..." -ForegroundColor Yellow
            break
        }
        # If neither C nor Q was pressed, keep waiting for valid input
    } while ($true)
}

# Remove the Python virtual environment directory
if (Test-Path "Res-Manager") {
    Write-Host "Removing Python virtual environment..." -ForegroundColor Yellow
    try {
        Remove-Item -Recurse -Force "Res-Manager" -ErrorAction Stop
        Write-Host "Python virtual environment removed." -ForegroundColor Green
    } catch {
        Write-Host "Failed to remove virtual environment: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "This usually means the environment is still active. Please:" -ForegroundColor Yellow
        Write-Host "  1. Deactivate the virtual environment (run 'deactivate')" -ForegroundColor White
        Write-Host "  2. Close VS Code or change the Python interpreter" -ForegroundColor White
        Write-Host "  3. Run this script again" -ForegroundColor White
        Write-Host ""
        Write-Host "Continuing with cache cleanup..." -ForegroundColor Yellow
    }
} else {
    Write-Host "No Python virtual environment found." -ForegroundColor Blue
}

# Remove the python cache directories
Write-Host "Removing Python cache directories..." -ForegroundColor Yellow
$cacheCount = 0
Get-ChildItem -Path . -Recurse -Directory -Name "__pycache__" | ForEach-Object {
    $cachePath = Join-Path $PWD $_
    if (Test-Path $cachePath) {
        Remove-Item -Recurse -Force $cachePath
        Write-Host "Removed: $cachePath" -ForegroundColor Gray
        $cacheCount++
    }
}

if ($cacheCount -eq 0) {
    Write-Host "No Python cache directories found." -ForegroundColor Blue
} else {
    Write-Host "Removed $cacheCount Python cache directories." -ForegroundColor Green
}

Write-Host "Cleanup completed." -ForegroundColor Green

# Restore the original working directory
Set-Location $originalDir
Write-Host "Restored working directory to: $(Get-Location)" -ForegroundColor Cyan
