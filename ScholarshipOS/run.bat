@echo off
title ScholarAI Web Dashboard
echo ===================================================
echo   ScholarAI Web Dashboard Launcher (FastAPI)
echo ===================================================
echo.
cd /d "%~dp0"
echo Starting FastAPI web server...
python main.py --web
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Server terminated unexpectedly or Python is not installed.
    echo Please ensure dependencies are installed via 'pip install -r requirements.txt'.
    pause
)
