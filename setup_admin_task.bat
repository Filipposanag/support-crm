@echo off
REM ===== Support CRM: one-time setup of elevated scheduled task =====
REM Needs admin ONCE to register the task. After that no UAC is needed.
net session >nul 2>&1
if %errorlevel% NEQ 0 (
    echo Requesting administrator privileges ^(one-time UAC^)...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
set "APPDIR=%~dp0"
if "%APPDIR:~-1%"=="\" set "APPDIR=%APPDIR:~0,-1%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$a=New-ScheduledTaskAction -Execute '%APPDIR%\.venv\Scripts\pythonw.exe' -Argument 'main.py' -WorkingDirectory '%APPDIR%'; $p=New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest; $s=New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero); Register-ScheduledTask -TaskName 'SupportCRM' -Action $a -Principal $p -Settings $s -Force"
echo.
echo Done! From now on double-click "Support CRM.bat" to open as admin without UAC.
pause
