#!/bin/bash

# Exit on error
set -e

# Function to log messages with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to detect Python command
detect_python() {
    if command -v python &> /dev/null; then
        PYTHON_CMD="python"
        log_message "Using python..."
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        log_message "Using python3..."
    else
        log_message "Error: Neither 'python3' nor 'python' command found"
        exit 1
    fi
}

# Function to clean build artifacts
clean_artifacts() {
    local dir=$1
    cd $dir
    for artifact in "build" "dist" "dist_electron"; do
        if [ -d "$artifact" ]; then
            log_message "Removing ${dir} ${artifact} directory..."
            rm -rf "$artifact"
        fi
    done
    cd ..
}

log_message "Starting build process..."

# Initialize Python
detect_python

# Clean up build artifacts
log_message "Cleaning up previous build artifacts..."
clean_artifacts "frontend"
clean_artifacts "backend"

# Function to setup and manage Python environment
setup_python_env() {
    if [ ! -d "venv" ]; then
        log_message "Setting up Python virtual environment..."
        $PYTHON_CMD -m venv venv
    else
        log_message "Python virtual environment already exists, skipping setup..."
    fi

    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi

    if ! pip freeze | grep -q -f requirements.txt; then
        log_message "Installing Python dependencies..."
        pip install -r requirements.txt
    else
        log_message "Python dependencies already installed, skipping installation..."
    fi
}

# Function to build backend
build_backend() {
    log_message "Building backend executable..."
    $PYTHON_CMD build_server.py
    deactivate
}

# Function to build frontend
build_frontend() {
    if [ ! -d "node_modules" ]; then
        log_message "Installing npm dependencies..."
        npm install
    else
        log_message "npm dependencies already installed, skipping installation..."
    fi
    log_message "Building frontend and packaging with Electron..."
    npm run electron:build
}

# Build backend
cd ./backend
setup_python_env
build_backend

# Build frontend
cd ../frontend
build_frontend

log_message "Build completed successfully!"