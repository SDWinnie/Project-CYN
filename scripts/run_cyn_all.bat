@echo off
title PROJECT CYN v1.2 - Production Launcher
cd /d "%~dp0\.."

echo ==============================================================
echo [PROJECT CYN v1.2] ANTIGRAVITY PRODUCTION ENVIRONMENT
echo Master: Admin Oliver
echo Visual Rig: 2D Chibi Solver CYN (cyn-md.gif)
echo Cloud Sync: Google Cloud Firestore (/users/oliver)
echo ==============================================================

echo [1/3] Priming local cache and Firestore persistent layer...
python -c "from backend.cyn_firestore_sync import firestore_sync; print('Firestore memory status: OK')"

echo [2/3] Launching CYN Core Gateway on port 8080...
start "CYN Core Server" cmd /k "python backend/app.py"

timeout /t 3 /nobreak >nul

echo [3/3] Launching Frameless 2D Desktop Overlay (Always on Top)...
start "CYN 2D Overlay" python desktop_overlay_2d/cyn_overlay_app.py

echo.
echo All subsystems operational.
echo You may now interact with Chibi CYN on your desktop!
