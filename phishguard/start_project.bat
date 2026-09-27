@echo off
title PhishGuard Full Stack Launcher
cd /d "%~dp0"

echo ===================================================
echo     Starting PhishGuard Full Stack Environment
echo ===================================================

if exist "backend\venv_win\Scripts\python.exe" (
    "backend\venv_win\Scripts\python.exe" run.py
) else if exist "venv_win\Scripts\python.exe" (
    "venv_win\Scripts\python.exe" run.py
) else (
    python run.py
)

pause
