@echo off
title SmartDorm Stopper

echo ===================================================
echo     Stopping Smart-Dorm 502
echo ===================================================

echo [1/2] Stopping Ngrok...
taskkill /IM ngrok.exe /F /T >nul 2>&1
taskkill /FI "WINDOWTITLE eq Ngrok-SmartDorm*" /F /T >nul 2>&1

echo [2/2] Stopping Telegram Bot...
taskkill /FI "WINDOWTITLE eq SmartDorm-Bot*" /F /T >nul 2>&1

powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'main.py' } | Invoke-CimMethod -MethodName Terminate" >nul 2>&1

echo.
echo STOPPED! All services have been terminated.
timeout /t 3 >nul
