@echo off
title Build Project CYN Desktop Service Executable
echo ======================================================================
echo  Building Standalone Windows Executable via PyInstaller...
echo ======================================================================

cd /d "%~dp0\.."

pyinstaller --noconfirm --onedir --windowed ^
    --name "CYN_Desktop_Service" ^
    --add-data "web_avatar;web_avatar" ^
    --add-data "backend;backend" ^
    --hidden-import "pystray" ^
    --hidden-import "aiohttp" ^
    --hidden-import "google.genai" ^
    --hidden-import "openwakeword" ^
    --hidden-import "sounddevice" ^
    --hidden-import "PIL" ^
    "backend/cyn_tray_service.py"

echo.
echo ======================================================================
echo  Build complete! Check dist/CYN_Desktop_Service/CYN_Desktop_Service.exe
echo ======================================================================
pause
