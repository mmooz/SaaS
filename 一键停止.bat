@echo off
rem One-click stopper: close the three console windows started by the launcher
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev-env.ps1" -Action stop
echo.
pause
