@echo off
echo Starting cleanup process...

REM Clean frontend
cd frontend
if exist node_modules (
    echo Removing node_modules directory...
    rmdir /s /q node_modules
    echo node_modules removed successfully.
) else (
    echo node_modules directory not found, skipping...
)

REM Clean backend
cd ..\backend
if exist venv (
    echo Removing Python virtual environment...
    rmdir /s /q venv
    echo Virtual environment removed successfully.
) else (
    echo Virtual environment not found, skipping...
)

echo Cleanup completed successfully!
pause