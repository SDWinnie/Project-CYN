@echo off
title Project CYN - Offline Simulator Engine
echo ======================================================================
echo  Launching Project CYN Offline Simulator & Benchmark Suite...
echo ======================================================================

cd /d "%~dp0\..\simulator"
python cyn_simulator.py

pause
