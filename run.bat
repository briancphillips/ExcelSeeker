@echo off
echo Starting ExcelSeeker...

REM Start the folder selection service
start "Folder Service" cmd /c "cd folder_service && npm start"

REM Wait a moment for the folder service to initialize
timeout /t 2 /nobreak > nul

REM Activate virtual environment and start Flask app
call venv\Scripts\activate.bat
python app.py
pause 