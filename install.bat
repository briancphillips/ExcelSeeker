@echo off
echo 🚀 Starting ExcelSeeker Installation...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.6 or higher.
    exit /b 1
)

REM Check Python version
for /f "tokens=2 delims=." %%I in ('python -c "import sys; print(sys.version.split()[0])"') do set PYTHON_VERSION=%%I
if %PYTHON_VERSION% LSS 6 (
    echo ❌ Python version must be 3.6 or higher.
    exit /b 1
)

echo ✅ Python 3.%PYTHON_VERSION% detected

REM Create virtual environment if it doesn't exist
if not exist venv (
    echo 📦 Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        exit /b 1
    )
)

REM Activate virtual environment
echo 🔄 Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    exit /b 1
)

REM Upgrade pip
echo 🔄 Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo 📦 Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    exit /b 1
)

echo ✅ Installation completed successfully!
echo.
echo To start ExcelSeeker:
echo 1. Run: venv\Scripts\activate.bat
echo 2. Run: python app.py
echo 3. Open: http://localhost:5001 in your browser
echo.
echo Happy searching! 🎉

pause 