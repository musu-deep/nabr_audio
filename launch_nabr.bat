@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ==============================================
echo            NABR AUDIO AGENT LAUNCHER
echo ==============================================

echo [1/5] Checking Python 3.11...
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Please install Python 3.11 first.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [2/5] Creating virtual environment...
  py -3.11 -m venv .venv
  if errorlevel 1 (
    echo Failed to create .venv using Python 3.11. Make sure Python 3.11 is installed.
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"

echo [3/5] Upgrading pip...
python -m pip install --upgrade pip

echo [4/5] Installing requirements...
pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install Python requirements.
  pause
  exit /b 1
)

echo [5/5] Opening browser and starting local server...
start "" http://127.0.0.1:8008
python -m uvicorn app.main:app --host 127.0.0.1 --port 8008

pause
