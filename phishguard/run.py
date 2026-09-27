"""
PhishGuard Unified Process Runner
Runs both FastAPI Backend and Vite Frontend concurrently with unified logging and graceful shutdown.
Usage:
    python run.py
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

# Find python interpreter in venv
venv_python_win = BACKEND_DIR / "venv_win" / "Scripts" / "python.exe"
venv_python_win_root = ROOT_DIR / "venv_win" / "Scripts" / "python.exe"
venv_python_unix = BACKEND_DIR / "venv" / "bin" / "python"

if venv_python_win.exists():
    PYTHON_EXE = str(venv_python_win)
elif venv_python_win_root.exists():
    PYTHON_EXE = str(venv_python_win_root)
elif venv_python_unix.exists():
    PYTHON_EXE = str(venv_python_unix)
else:
    PYTHON_EXE = sys.executable

# Find npm
NPM_CMD = "npm.cmd" if sys.platform == "win32" else "npm"

def main():
    print("=" * 60)
    print("       🛡️  STARTING PHISHGUARD UNIFIED ENVIRONMENT 🛡️       ")
    print("=" * 60)
    print(f"[*] Python Interpreter : {PYTHON_EXE}")
    print(f"[*] Backend Directory  : {BACKEND_DIR}")
    print(f"[*] Frontend Directory : {FRONTEND_DIR}")
    print("=" * 60)

    processes = []

    try:
        # 1. Start Backend Server (FastAPI / Uvicorn)
        print("\n[+] Launching FastAPI Backend on http://127.0.0.1:8000 ...")
        backend_cmd = [
            PYTHON_EXE,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--reload",
        ]
        backend_proc = subprocess.Popen(
            backend_cmd,
            cwd=str(BACKEND_DIR),
        )
        processes.append(("Backend", backend_proc))

        # Brief delay so backend starts cleanly
        time.sleep(1.5)

        # 2. Start Frontend Dev Server (Vite)
        print("\n[+] Launching Vite Frontend on http://localhost:5173 ...")
        frontend_cmd = [NPM_CMD, "run", "dev"]
        frontend_proc = subprocess.Popen(
            frontend_cmd,
            cwd=str(FRONTEND_DIR),
            shell=(sys.platform == "win32"),
        )
        processes.append(("Frontend", frontend_proc))

        print("\n" + "=" * 60)
        print("  🚀 ALL SERVICES RUNNING:")
        print("  - Frontend UI    : http://localhost:5173")
        print("  - Backend API    : http://127.0.0.1:8000")
        print("  - Swagger Docs   : http://127.0.0.1:8000/docs")
        print("  - Extension Dir  : d:\\Works\\phishguard\\phishguard\\extension")
        print("=" * 60)
        print("Press Ctrl+C to stop all services simultaneously.\n")

        # Monitor processes
        while True:
            for name, proc in processes:
                ret = proc.poll()
                if ret is not None:
                    print(f"[-] {name} stopped with exit code {ret}.")
                    return
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[!] Stopping all services...")
    finally:
        for name, proc in processes:
            if proc.poll() is None:
                print(f"[x] Terminating {name}...")
                try:
                    if sys.platform == "win32":
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
                    else:
                        proc.terminate()
                except Exception:
                    pass
        print("[✓] All PhishGuard services stopped cleanly.")

if __name__ == "__main__":
    main()
