@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\build_installer.ps1"
if errorlevel 1 pause
