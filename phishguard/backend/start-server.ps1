<#
start-server.ps1

PowerShell helper to create/activate a venv (if needed), install minimal dev deps,
and start the FastAPI uvicorn server for local development.

Usage examples:
  # Start with defaults (host 127.0.0.1, port 8000)
  .\start-server.ps1

  # Start with reload enabled (auto-reload on code changes)
  .\start-server.ps1 -Reload

  # Install full requirements before starting (may be slow)
  .\start-server.ps1 -FullInstall

  # Specify a different port
  .\start-server.ps1 -Port 9000

Notes:
- Requires Python 3.8+ available on PATH or in the system.
- By default this installs a small set of packages needed for running tests
  and local development (uvicorn, fastapi, requests, tldextract, python-whois,
  selenium, webdriver-manager).
- If your policy blocks running scripts, run:
    powershell -ExecutionPolicy Bypass -File .\start-server.ps1
#>

param(
    [int]$Port = 8000,
    [string]$ServerHost = '127.0.0.1',
    [switch]$Reload,
    [switch]$FullInstall
)

function Write-Info($msg){ Write-Host "[start-server] $msg" -ForegroundColor Cyan }
function Write-ErrorExit($msg){ Write-Host "[start-server] ERROR: $msg" -ForegroundColor Red; exit 1 }

# Ensure we're in the backend directory
Push-Location -Path (Split-Path -Path $MyInvocation.MyCommand.Definition -Parent)

# Find or create a venv
$activateCandidates = @('.\venv\Scripts\Activate.ps1', '.\.venv\Scripts\Activate.ps1')
$activateScript = $null
foreach ($c in $activateCandidates) {
    if (Test-Path $c) { $activateScript = $c; break }
}

if (-not $activateScript) {
    # No venv found — try to create one
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        $pythonCommand = Get-Command py -ErrorAction SilentlyContinue
    }
    if (-not $pythonCommand) {
        Write-ErrorExit "Python is not available. Install Python 3.8+ and re-run."
    }

    Write-Info "No virtualenv found. Creating venv at .\venv..."
    & $pythonCommand.Source -m venv .\venv
    if ($LASTEXITCODE -ne 0) { Write-ErrorExit "Failed to create virtualenv" }
    $activateScript = '.\venv\Scripts\Activate.ps1'
}

Write-Info "Activating virtualenv: $activateScript"
. $activateScript

# Upgrade pip
Write-Info "Upgrading pip..."
python -m pip install --upgrade pip | Out-Null

if ($FullInstall) {
    if (Test-Path '.\requirements.txt') {
        Write-Info "Installing full requirements from requirements.txt (this may take long)..."
        pip install -r .\requirements.txt
    } else {
        Write-ErrorExit "requirements.txt not found in backend folder."
    }
} else {
    Write-Info "Installing minimal dev/test deps (uvicorn, fastapi, motor, certifi, python-multipart, requests, tldextract, python-whois, selenium, webdriver-manager)..."
    pip install uvicorn fastapi motor certifi python-multipart requests tldextract python-whois selenium webdriver-manager
}

# Start uvicorn
# Build reload flag in a way compatible with older PowerShell versions
if ($Reload.IsPresent) { $reloadFlag = "--reload" } else { $reloadFlag = "" }
Write-Info "Starting uvicorn on http://$ServerHost`:$Port (Reload = $($Reload.IsPresent))"
Write-Info "Press Ctrl+C to stop."

# Run in the foreground so logs stream to the console
if ($reloadFlag -ne "") {
    python -m uvicorn main:app --host $ServerHost --port $Port $reloadFlag
} else {
    python -m uvicorn main:app --host $ServerHost --port $Port
}

# Return to previous directory
Pop-Location
