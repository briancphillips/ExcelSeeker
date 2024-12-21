@echo off
echo 🚀 Starting ExcelSeeker...

REM Check if virtual environment exists
if not exist venv (
    echo ❌ Virtual environment not found. Please run install.bat first.
    pause
    exit /b 1
)

REM Activate virtual environment
echo 🔄 Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)

REM Start the application
echo ✨ Launching ExcelSeeker...
python app.py 