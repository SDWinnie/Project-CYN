@echo off
title Build Project CYN Android Companion APK
echo ======================================================================
echo  Compiling Project CYN Android Companion App (Foreground Service)...
echo ======================================================================

cd /d "%~dp0\..\android_companion"
call .\gradlew.bat assembleDebug

echo.
echo ======================================================================
echo  APK Build Finished!
echo  Output: android_companion\app\build\outputs\apk\debug\app-debug.apk
echo ======================================================================
pause
