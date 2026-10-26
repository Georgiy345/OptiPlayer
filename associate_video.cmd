@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0associate_video.ps1" %*
echo.
pause
endlocal
