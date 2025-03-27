import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from datetime import datetime
from threading import Lock

class Logger:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.logger = self._setup_logger()

    def _get_logs_dir(self):
        if getattr(sys, 'frozen', False):
            # Running in PyInstaller bundle inside Electron app
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))
        else:
            # Running in development
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        logs_dir = os.path.join(base_path, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        return logs_dir

    def _setup_logger(self):
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
        logs_dir = self._get_logs_dir()
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

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)

# Create a global logger instance
logger = Logger()