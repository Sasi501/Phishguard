# PhishGuard PowerShell Launcher
Set-Location -Path $PSScriptRoot

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "    Starting PhishGuard Full Stack Environment     " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

$pythonExe = "$PSScriptRoot\backend\venv_win\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "$PSScriptRoot\venv_win\Scripts\python.exe"
}
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

& $pythonExe "$PSScriptRoot\run.py"
