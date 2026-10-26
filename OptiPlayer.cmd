@echo off
setlocal
cd /d "%~dp0"
start "OptiPlayer" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0app.py" %*
endlocal
