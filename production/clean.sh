#!/bin/bash

# Exit on error
set -e

# Confirm cleanup
read -p "WARNING: This will remove all installed packages. Are you sure you want to continue? [y/N] " -n 1 -r
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "
Cleanup aborted."
    exit 1
fi

echo "
Starting cleanup process..."

# Clean frontend
cd frontend
if [ -d "node_modules" ]; then
    echo "Removing node_modules directory..."
    rm -rf node_modules
    echo "node_modules removed successfully."
else
    echo "node_modules directory not found, skipping..."
fi

# Clean backend
cd ../backend
if [ -d "venv" ]; then
    echo "Removing Python virtual environment..."
    rm -rf venv
    echo "Virtual environment removed successfully."
else
    echo "Virtual environment not found, skipping..."
fi

echo "Cleanup completed successfully!"