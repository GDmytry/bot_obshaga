@echo off
title SmartDorm Launcher

echo ===================================================
echo     Starting Smart-Dorm 502
echo ===================================================

cd /d "%~dp0"

echo [1/2] Starting Ngrok (port 8000)...
start "Ngrok-SmartDorm" cmd /k "ngrok http --domain=omen-correct-alright.ngrok-free.dev 8000"

timeout /t 2 >nul

echo [2/2] Starting Telegram Bot...
start "SmartDorm-Bot" cmd /k "venv\Scripts\python.exe main.py"

echo.
echo DONE! Processes started in new windows.
echo If any window shows an error, check if ngrok is installed and venv is working.
pause
