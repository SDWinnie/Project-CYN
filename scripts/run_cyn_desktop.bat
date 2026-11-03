@echo off
title PROJECT CYN (v7.0 FULL-SPECTRUM EDITION)
echo ======================================================================
echo  [PROJECT CYN] Absolute Solver Worker Drone Runtime
echo  Master: Admin Oliver
echo  Backend: Gemini Multimodal Live API & WebGL Three.js Runtime
echo ======================================================================

cd /d "%~dp0\..\backend"
echo Starting CYN Local Core Gateway on http://localhost:8080 ...

start "" http://localhost:8080
python app.py

pause
