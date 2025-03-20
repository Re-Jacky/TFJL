@echo off
setlocal EnableDelayedExpansion

REM Function to log messages with timestamp
:log_message
set message=%~1
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set datetime=!datetime:~0,4!-!datetime:~4,2!-!datetime:~6,2! !datetime:~8,2!:!datetime:~10,2!:!datetime:~12,2!
echo [!datetime!] %message%
goto :eof

REM Function to clean build artifacts
:clean_artifacts
set dir=%~1
cd %dir%
for %%A in (build dist dist_electron) do (
    if exist %%A (
        call :log_message "Removing %dir% %%A directory..."
        rmdir /s /q %%A
    )
)
cd ..
goto :eof

REM Function to detect Python command
:detect_python
where python3 >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
    call :log_message "Using python3..."
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=python
        call :log_message "Using python..."
    ) else (
        call :log_message "Error: Neither 'python3' nor 'python' command found"
        exit /b 1
    )
)
goto :eof

call :log_message "Starting build process..."

REM Initialize Python
call :detect_python

REM Clean up build artifacts
call :log_message "Cleaning up previous build artifacts..."
call :clean_artifacts frontend
call :clean_artifacts backend

REM Build backend
cd backend

REM Check if virtual environment exists
if not exist venv (
    call :log_message "Setting up Python virtual environment..."
    %PYTHON_CMD% -m venv venv
) else (
    call :log_message "Python virtual environment already exists, skipping setup..."
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if requirements are installed
pip freeze > temp_requirements.txt
findstr /I /M "requirements.txt" temp_requirements.txt > nul
if %errorlevel% neq 0 (
    call :log_message "Installing Python dependencies..."
    pip install -r requirements.txt
) else (
    call :log_message "Python dependencies already installed, skipping installation..."
)
del temp_requirements.txt
call :log_message "Building backend executable..."
%PYTHON_CMD% build_server.py

REM Deactivate virtual environment
deactivate

REM Build frontend
cd ..\frontend
if not exist node_modules (
    call :log_message "Installing npm dependencies..."
    npm install
) else (
    call :log_message "npm dependencies already installed, skipping installation..."
)
call :log_message "Building frontend and packaging with Electron..."
npm run electron:build

call :log_message "Build completed successfully!"
pause