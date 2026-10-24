@echo off
cd /d "%~dp0"
if "%~1"=="" (python update.py) else (python update.py "%~1")
echo.
pause
