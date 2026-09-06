#!/usr/bin/env pwsh
Write-Host "Auditing Python dependencies..."
pip install pip-audit
pip-audit -r backend/requirements.txt

Write-Host "Auditing Node dependencies..."
cd frontend
npm audit
cd ..
Write-Host "Audit completed."

