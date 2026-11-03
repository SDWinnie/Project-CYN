@echo off
title Install Project CYN Windows Background Service
echo ======================================================================
echo  Installing Project CYN as a Windows Autostart Resident Service...
echo ======================================================================

set SCRIPT_PATH=%~dp0..\backend\cyn_tray_service.py

echo Registering in Windows CurrentUser Run Registry...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ProjectCYNService" /t REG_SZ /d "\"%~dp0..\backend\cyn_tray_service.py\"" /f

echo.
echo [SUCCESS] Project CYN has been registered as an automatic Windows service!
echo It will now run quietly in the background on every user login.
echo.
echo Starting service now...
start "" pythonw "%SCRIPT_PATH%"
pause
