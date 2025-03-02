@echo off
color 0A
python --version 2>&1 | findstr /R /C:"Python 3\.[1-9][0-9]" >nul
IF %ERRORLEVEL% NEQ 0 (
    echo Python 3.10 or later is required. Please install Python 3.10 or newer.
    pause
    exit /B 1
)
IF NOT EXIST "venv" (
    echo Virtual environment not found. Creating one...
    python -m venv venv
    IF %ERRORLEVEL% NEQ 0 (
        echo Failed to create virtual environment.
        pause
        exit /B 1
    )
)
call .\venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
pause
