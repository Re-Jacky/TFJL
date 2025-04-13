import json
import time
import threading
import pygetwindow
import pyautogui
from typing import Dict, Optional
from app.utils.logger import logger
from app.enums.shortcut_positions import GameMode, SingleModeVehiclePositions, SingleModeEnemyVehiclePositions
from app.services.window_control_services import WindowControlService
from pynput import keyboard

class ShortcutService:
    def __init__(self):
        self.active = False
        self.listener_thread = None
        self.shortcut_config = {}
        self.load_config()
        self.window_configs = {}  # Stores mode and quick_sell per PID

    def load_config(self):
        """Load the shortcut configuration from file."""
        try:
            from app.services.utility_services import UtilityService
            config = UtilityService.get_shortcut()
            if config.get("status") == "success":
                self.shortcut_config = config.get("shortcut", {})
        except Exception as e:
            logger.error(f"Error loading shortcut config: {str(e)}")

    

    def start_listening(self, pid: int):
        """Start listening for keyboard shortcuts for the specified window."""
        if self.active:
            self.stop_listening(pid)
            
        self.active = True
        self.listener_thread = threading.Thread(
            target=self._listen_for_shortcuts,
            daemon=True
        )
        self.listener_thread.start()
        logger.info(f"Started shortcut listener for window {pid}")

    def stop_listening(self, pid: int):
        """Stop listening for keyboard shortcuts."""
        self.active = False
        if self.listener_thread:
            self.listener_thread.join(timeout=1)
        logger.info("Stopped shortcut listener")



    def set_mode(self, pid: int, mode: GameMode):
        """Update the shortcut mode for the specified window."""
        if pid not in self.window_configs:
            self.window_configs[pid] = {}
        self.window_configs[pid]['mode'] = mode
        logger.info(f"Shortcut mode updated for window {pid}: {mode}")
        if mode == GameMode.NONE:
            self.stop_listening(pid)
        else:
            self.start_listening(pid)
    
    def set_quick_sell(self, pid: int, quick_sell: bool):
        """Update quick sell setting for the specified window."""
        if pid not in self.window_configs:
            self.window_configs[pid] = {}
        self.window_configs[pid]['quick_sell'] = quick_sell
        logger.info(f"Quick sell updated for window {pid}: {quick_sell}")
        
    def _listen_for_shortcuts(self):
        """Monitor keyboard inputs and trigger actions based on configuration."""
        
        
        def on_press(key):
            try:
                key_str = key.char
            except AttributeError:
                key_str = str(key)
                
            # for shortcut_key in self.shortcut_config.get('generalShortcut', {}).values():
            #     if shortcut_key and key_str == shortcut_key:
            #         logger.info(f"Detected general shortcut key press: {key_str}")
                    
            mode = next((w['mode'] for w in self.window_configs.values() if 'mode' in w), GameMode.NONE)
            if mode != GameMode.NONE:
                # monitor general shortcut key press
                for shortcut_key in self.shortcut_config.get('generalShortcut', {}).values():
                    if shortcut_key and key_str == shortcut_key:
                        logger.info(f"Detected general shortcut key press: {key_str}")
                        # Check if quick_sell is enabled for the current mode
                       


            if mode == GameMode.SINGLE_PLAYER:
                vehicle_shortcuts = self.shortcut_config.get('vehicleShortcut', {})
                for side in ['left', 'right']:
                    for shortcut_key in vehicle_shortcuts.get(side, {}).values():
                        if shortcut_key and key_str == shortcut_key:
                            logger.info(f"Detected vehicle shortcut key press: {key_str}")
                            if mode == GameMode.SINGLE_PLAYER:
                                vehicle_num = int(key_str.split('_')[-1])
                                position = SingleModeVehiclePositions[f"VEHICLE_{vehicle_num}"].value
                                WindowControlService.click_at(next(iter(self.window_configs.keys())), position[0], position[1])
        
        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        
        while self.active:
            time.sleep(0.1)  # Prevent high CPU usage
            
        listener.stop()