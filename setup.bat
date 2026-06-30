@echo off
REM Double-click to run setup.ps1 via PowerShell (bypass execution policy)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
pause
