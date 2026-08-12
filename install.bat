@echo off
setlocal

echo.
echo  ==========================================
echo   wault - a keyboard first wallpaper switcher
echo  ==========================================
echo.

:: Check Python is installed
py --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Please install Python 3.11+ from https://python.org
    pause
    exit /b 1
)

:: Create virtual environment
echo  [1/3] Creating virtual environment...
py -m venv .venv
if errorlevel 1 (
    echo  [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

:: Install dependencies
echo  [2/3] Installing dependencies...
.venv\Scripts\pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

:: Launch once so it registers itself to startup
echo  [3/3] Launching wault and registering startup shortcut...
start "" .venv\Scripts\pythonw.exe main.py

echo.
echo  Done! wault is now running in your system tray.
echo  Press Alt+W anywhere to open the wallpaper picker.
echo  It will auto-start the next time you boot your PC.
echo.
pause
