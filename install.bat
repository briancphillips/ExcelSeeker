@echo off
echo ExcelSeeker Installer
echo ===================

REM Check if Python is installed
python --version > nul 2>&1
if errorlevel 1 (
    echo Python is not installed! Please install Python 3.6 or higher.
    echo You can download Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment and install requirements
echo Installing required packages...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install flask flask-uploads werkzeug==2.0.3 xlrd python-dotenv xlwt

REM Create necessary directories
if not exist "temp" mkdir temp
if not exist "static" mkdir static
if not exist "templates" mkdir templates

echo.
echo Installation complete!
echo.
echo To start ExcelSeeker:
echo 1. Double-click 'run.bat'
echo.
pause 