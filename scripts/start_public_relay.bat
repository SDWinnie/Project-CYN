@echo off
title PROJECT CYN (v7.0) - Global Public Relay Server
echo ======================================================================
echo  [PROJECT CYN] Starting Public Cloudflare Relay + WebSocket Gateway...
echo  Allows Android phone and external browsers to connect from anywhere!
echo ======================================================================

cd /d "%~dp0\..\backend"
echo Launching CYN Core Gateway and Global Intermediary Tunnel...

start "" http://localhost:8080
python app.py

pause
