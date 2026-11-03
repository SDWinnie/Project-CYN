@echo off
title PROJECT CYN (2D GIF DESKTOP OVERLAY)
echo ======================================================================
echo  [PROJECT CYN] 2D Transparent Animated GIF Desktop Overlay
echo  Master: Admin Oliver
echo  Visual Rig: 2D Sprite & GIF Controller (Frameless Transparent Window)
echo ======================================================================

cd /d "%~dp0\.."

echo Launching CYN 2D Overlay App...
python desktop_overlay_2d\cyn_overlay_app.py %*

pause
