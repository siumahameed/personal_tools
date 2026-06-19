@echo off
cd /d "%~dp0"
echo Installing dependencies...
pip install -r requirements.txt
if %errorlevel% equ 0 (
    echo.
    echo Setup complete! Run start.bat to launch the platform.
) else (
    echo.
    echo Installation failed. Make sure Python and pip are installed.
)
pause
