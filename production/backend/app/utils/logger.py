import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from datetime import datetime

# Determine if we're running from PyInstaller bundle
def get_logs_dir():
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle inside Electron app
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))
    else:
        # Running in development
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    logs_dir = os.path.join(base_path, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir

# Get logs directory
logs_dir = get_logs_dir()

# Configure logging
def setup_logger():
    # Create logger
    logger = logging.getLogger('tfjl')
    logger.setLevel(logging.INFO)

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # Create file handler
    log_file = os.path.join(logs_dir, f'tfjl_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Create and configure the logger
logger = setup_logger()