import json
from re import match
import time
import threading
from unittest import case
import pygetwindow
import pyautogui
from typing import Dict, Optional
from app.utils.logger import logger
from app.enums.game_positions import GamePositions
from app.enums.shortcut_positions import GameMode, SingleModeVehiclePositions, SingleModeEnemyVehiclePositions
from app.services.window_control_services import WindowControlService
from pynput import keyboard

class ShortcutService:
    def __init__(self):
        self.listener_thread = None
        self.shortcut_config = {}
        self.load_config()
        self.window_configs = {}  # Stores mode per PID
        self.quick_sell_delay = 0.5  # Delay in seconds before selling

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
        if self.window_configs.get(pid, {}).get('active', False):
            self.stop_listening(pid)
        
            
        self.window_configs[pid]['active'] = True
        self.listener_thread = threading.Thread(
            target=self._listen_for_shortcuts,
            args=(pid,),
            daemon=True
        )
        self.listener_thread.start()
        logger.info(f"Started shortcut listener for window {pid}")

    def stop_listening(self, pid: int):
        """Stop listening for keyboard shortcuts."""
        self.window_configs[pid]['active'] = False
        if self.listener_thread:
            self.listener_thread.join(timeout=1)
        logger.info("Stopped shortcut listener")
        
    def _listen_for_shortcuts(self, pid: int):
        """Monitor keyboard inputs and trigger actions based on configuration.
        
        Args:
            pid: The process ID of the window to monitor.
        """
        
        def on_press(key):
            try:
                key_str = key.char
                logger.info(f"Detected key press: {key_str}")
            except AttributeError:
                key_str = str(key)
                
            # for shortcut_key in self.shortcut_config.get('generalShortcut', {}).values():
            #     if shortcut_key and key_str == shortcut_key:
            #         logger.info(f"Detected general shortcut key press: {key_str}")
                    
            mode = self.window_configs.get(pid, {}).get('mode', GameMode.NONE)
            quick_sell = self.shortcut_config.get('generalShortcut', {}).get('quickSell', False)
            if mode != GameMode.NONE.value:
                # monitor general shortcut key press
                for shortcut_key, shortcut_value in self.shortcut_config.get('generalShortcut', {}).items():
                    if (shortcut_value and key_str == shortcut_value) or (shortcut_value == 'Space' and key_str == 'Key.space'):
                        if shortcut_key == 'firstCard':
                            pos = GamePositions.CARD_0.value
                        elif shortcut_key == 'secondCard':
                            pos = GamePositions.CARD_1.value
                        elif shortcut_key == 'thirdCard':
                            pos = GamePositions.CARD_2.value
                        elif shortcut_key == 'upgradeVehicle':
                            pos = GamePositions.UPGRADE_VEHICLE.value
                        elif shortcut_key == 'refresh':
                            pos = GamePositions.REFRESH_CARD.value
                        elif shortcut_key == 'sellCard':
                            pos = '' ## TBD                        logger.info(f"Clicked at position: {pos}")
                        # WindowControlService.click_at(pid, pos[0], pos[1])
                        return
                       


            if mode == GameMode.SINGLE_PLAYER.value:
                vehicle_shortcuts = self.shortcut_config.get('vehicleShortcut', {})
                direction_map = {
                    'left': SingleModeVehiclePositions,
                    'right': SingleModeEnemyVehiclePositions
                }
                ## check battle shortcut key press
                for shortcut_key, shortcut_value in self.shortcut_config.get('battleShortcut', {}).items():
                    if shortcut_value and key_str == shortcut_value:
                        logger.info(f"Detected battle shortcut key press: {key_str}")
                        if shortcut_key == 'surrender':
                            pos = GamePositions.SURRENDER.value
                        elif shortcut_key =='confirm':
                            pos = GamePositions.BATTLE_END_CONFIRM.value
                        elif shortcut_key =='battle':
                            pos = GamePositions.BATTLE.value
                        elif shortcut_key =='quickMatch':
                            pos = GamePositions.QUICK_MATCH.value
                        elif shortcut_key =='viewOpponentHalo':
                            pos = GamePositions.ENEMY_STATUS.value
                        logger.info(f"Clicked at position: {pos}")
                        # WindowControlService.click_at(pid, pos[0], pos[1])
                        return

                ## check vehicle shortcut key press
                for direction, position_enum in direction_map.items():
                    for shortcut_index, shortcut_value in vehicle_shortcuts.get(direction, {}).items():
                        if shortcut_value and key_str == shortcut_value:
                            logger.info(f"Detected {direction} vehicle shortcut key press: {key_str} (shortcut: {shortcut_index})")
                            position = position_enum[f"VEHICLE_{shortcut_index}"].value
                            logger.info(f"Clicked at position: {position}")
                            # WindowControlService.click_at(pid, position[0], position[1])
                            if quick_sell:
                                time.sleep(self.quick_sell_delay)
                                logger.info(f"Clicked sell card")
                                # WindowControlService.click_at(pid, ) # Implement quick sell logic
                            return
            elif mode == GameMode.SINGLE_PLAYER_SAILING.value:
                # Implement logic for two-player mode
                pass
            elif mode == GameMode.TWO_PLAYER.value:
                # Implement logic for two-player mode
                pass
            elif mode == GameMode.TWO_PLAYER_SKY.value:
                # Implement logic for two-player mode
                pass
        
        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        
        while self.window_configs[pid]['active']:
            time.sleep(0.1)  # Prevent high CPU usage
            
        listener.stop()
    
    def reload_listeners(self):
        """Reload listeners for all active windows."""
        logger.info("Reloading listeners for all active windows")
        for pid in self.window_configs:
            if self.window_configs[pid].get('active', False):
                self.start_listening(pid)

    def set_active(self, pid: int, active: bool):
        """Set the active state for a window."""
        """Update the shortcut mode for the specified window."""
        if pid not in self.window_configs:
            self.window_configs[pid] = {}
            self.window_configs[pid]['mode'] = GameMode.SINGLE_PLAYER.value
            self.window_configs[pid]['active'] = active

        self.window_configs[pid]['active'] = active
        if active:
            self.start_listening(pid)
        else:
            self.stop_listening(pid)