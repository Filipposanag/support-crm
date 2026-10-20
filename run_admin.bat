@echo off
REM ==== Support CRM - launch as Administrator ====
REM Check if already running elevated
net session >nul 2>&1
if %errorlevel% NEQ 0 (
    echo Requesting administrator privileges ^(UAC^)...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
REM ==== Running as Administrator from here ====
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"
python main.py
pause
