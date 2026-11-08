@echo off
rem One-click launcher: backend(8000) + admin-web(5173) + pos(5174)
rem Keep this file ASCII-only; the real logic lives in scripts\dev-env.ps1
set "NO_PROXY=127.0.0.1,localhost"
set "no_proxy=127.0.0.1,localhost"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev-env.ps1" -Action start
set RC=%ERRORLEVEL%
echo.
if not "%RC%"=="0" (echo [ERROR] Start failed. Please read the messages above.) else (echo Start finished. The three service windows are running.)
echo Press any key to close this launcher window (services keep running).
pause >nul
