#!/usr/bin/env pwsh
Write-Host "Scanning for secrets in codebase..."
# Simple regex to find common API keys (mocking trufflehog for this example)
$regex = "AIza[0-9A-Za-z-_]{35}"
Get-ChildItem -Path . -Recurse -File -Exclude node_modules,venv,venv_win | Select-String -Pattern $regex
Write-Host "Scan completed."

