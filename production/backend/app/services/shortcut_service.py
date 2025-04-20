import json
from re import match
import time
import threading
import pygetwindow
import pyautogui
from typing import Dict, Optional
from app.utils.logger import logger
from app.enums.game_positions import GamePositions
from app.enums.shortcut_positions import GameMode, SingleModeVehiclePositions, SingleModeEnemyVehiclePositions,TwoModeLeftVehiclePositions,TwoModeRightVehiclePositions,SailModeVehiclePositions,SkyTwoModeLeftVehiclePositions,SkyTwoModeRightVehiclePositions
from app.services.window_control_services import WindowControlService
from pynput import keyboard

class ShortcutService:
    def __init__(self):
        self.listener_thread = None
        self.shortcut_config = {}
        self.load_config()
        self.window_configs = {}  # Stores mode per PID
        self.shouldBlockCardPress = False

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
        general_shortcuts = self.shortcut_config.get('generalShortcut', {})
        vehicle_shortcuts = self.shortcut_config.get('vehicleShortcut', {})
        battle_shortcuts = self.shortcut_config.get('battleShortcut', {})
        auction_shortcuts = self.shortcut_config.get('auctionShortcut', {})
        quick_sell_delay = general_shortcuts.get('quickSellDelay', 0) / 1000
        quick_refresh = general_shortcuts.get('quickRefresh', False)
        quick_sell = general_shortcuts.get('quickSell', False)
        enhanced_btn_press = general_shortcuts.get('enhancedBtnPress', False)
        auto_quick_match = battle_shortcuts.get('autoQuickMatch', False)
        mode = self.window_configs.get(pid, {}).get('mode', GameMode.SINGLE_PLAYER)
        # Dictionary to store the last time each key was pressed for debouncing
        last_key_press_time = {}
        # Debounce delay in milliseconds (adjust as needed)
        debounce_delay = 200


        def handle_quick_sell():
            if quick_sell:
                self.shouldBlockCardPress = True if enhanced_btn_press else False
                def delayed_click():
                    time.sleep(quick_sell_delay)
                    sell_card = GamePositions.SELL_CARD.value
                    WindowControlService.click_at(pid, sell_card[0], sell_card[1])
                    self.shouldBlockCardPress = False
                threading.Thread(target=delayed_click, daemon=True).start()
        
            
        def on_press(key):
            try:
                key_str = key.char
            except AttributeError:
                key_str = str(key)
                key_str = key_str.replace('Key.', '')
            # handle aunction mode first
            if mode == GameMode.AUCTION.value:
               for shortcut_key, shortcut_value in auction_shortcuts.items():
                    if (shortcut_value and key_str == shortcut_value):
                        if shortcut_key =='auctionCard0':
                            pos = GamePositions.AUNCTION_CARD_0.value
                        elif shortcut_key =='auctionCard1':
                            pos = GamePositions.AUNCTION_CARD_1.value
                        elif shortcut_key =='auctionCard2':
                            pos = GamePositions.AUNCTION_CARD_2.value
                        elif shortcut_key =='auctionCard3':
                            pos = GamePositions.AUNCTION_CARD_3.value
                        WindowControlService.click_at(pid, pos[0], pos[1])
                        time.sleep(0.1)
                        confirm_pos = GamePositions.AUCTION_CONFIRM.value
                        WindowControlService.click_at(pid, confirm_pos[0], confirm_pos[1])
                        return
            
            # Implement debouncing to prevent rapid repeated keypresses
            if enhanced_btn_press:
                now = time.time() * 1000
                last_time = last_key_press_time.get(key_str, 0)
                if now - last_time < debounce_delay:
                    return
                last_key_press_time[key_str] = now

            # monitor general shortcut key press
            for shortcut_key, shortcut_value in general_shortcuts.items():
                if (shortcut_value and key_str == shortcut_value):
                    isCard = False
                    if shortcut_key == 'firstCard':
                        pos = GamePositions.CARD_0.value
                        isCard = True
                    elif shortcut_key == 'secondCard':
                        pos = GamePositions.CARD_1.value
                        isCard = True
                    elif shortcut_key == 'thirdCard':
                        pos = GamePositions.CARD_2.value
                        isCard = True
                    elif shortcut_key == 'upgradeVehicle':
                        pos = GamePositions.UPGRADE_VEHICLE.value
                    elif shortcut_key == 'refresh':
                        pos = GamePositions.REFRESH_CARD.value
                    elif shortcut_key == 'sellCard':
                        pos = GamePositions.SELL_CARD.value

                    if self.shouldBlockCardPress and isCard:
                        return
                    WindowControlService.click_at(pid, pos[0], pos[1])
                    if quick_refresh and isCard:
                        time.sleep(0.1)
                        refresh_card = GamePositions.REFRESH_CARD.value
                        WindowControlService.click_at(pid, refresh_card[0], refresh_card[1]) # Implement quick sell logic
                    return
                       


            if mode == GameMode.SINGLE_PLAYER.value:
                direction_map = {
                    'left': SingleModeVehiclePositions,
                    'right': SingleModeEnemyVehiclePositions
                }
                ## check battle shortcut key press
                for shortcut_key, shortcut_value in self.shortcut_config.get('battleShortcut', {}).items():
                    if shortcut_value and key_str == shortcut_value:
                        if shortcut_key == 'surrender':
                            pos = GamePositions.SURRENDER.value
                        elif shortcut_key =='confirm':
                            pos = GamePositions.BATTLE_END_CONFIRM.value
                        elif shortcut_key =='battle':
                            pos = GamePositions.BATTLE.value
                        elif shortcut_key =='viewOpponentHalo':
                            pos = GamePositions.ENEMY_STATUS.value
                        elif shortcut_key == 'closeCard':
                            pos = GamePositions.CLOST_CARD.value
                        WindowControlService.click_at(pid, pos[0], pos[1])
                        if shortcut_key == 'surrender':
                            time.sleep(0.5)
                            surrender_confirm = GamePositions.SURRENDER_CONFIRM.value
                            WindowControlService.click_at(pid, surrender_confirm[0], surrender_confirm[1])
                        if shortcut_key == 'battle' and auto_quick_match:
                            time.sleep(0.2)
                            quick_match = GamePositions.QUICK_MATCH.value
                            WindowControlService.click_at(pid, quick_match[0], quick_match[1])
                        return

                ## check vehicle shortcut key press
                for direction, position_enum in direction_map.items():
                    for shortcut_index, shortcut_value in vehicle_shortcuts.get(direction, {}).items():
                        if shortcut_value and key_str == shortcut_value:

                            position = position_enum[f"VEHICLE_{shortcut_index}"].value
                            WindowControlService.click_at(pid, position[0], position[1])
                            handle_quick_sell()
                            return
            elif mode == GameMode.SINGLE_PLAYER_SAILING.value:
                for shortcut_index, shortcut_value in vehicle_shortcuts.get('left', {}).items():
                    if shortcut_value and key_str == shortcut_value:
                        position = SailModeVehiclePositions[f"VEHICLE_{shortcut_index}"].value
                        WindowControlService.click_at(pid, position[0], position[1])
                        handle_quick_sell()
                        return
            elif mode == GameMode.TWO_PLAYER.value:
                ## check vehicle shortcut key press
                direction_map = {
                    'left': TwoModeLeftVehiclePositions,
                    'right': TwoModeRightVehiclePositions
                }
                for direction, position_enum in direction_map.items():
                    for shortcut_index, shortcut_value in vehicle_shortcuts.get(direction, {}).items():
                        if shortcut_value and key_str == shortcut_value:
                            position = position_enum[f"VEHICLE_{shortcut_index}"].value
                            WindowControlService.click_at(pid, position[0], position[1])
                            handle_quick_sell()
                            return
            elif mode == GameMode.TWO_PLAYER_SKY.value:
                direction_map = {
                    'left': SkyTwoModeLeftVehiclePositions,
                    'right': SkyTwoModeRightVehiclePositions
                }
                for direction, position_enum in direction_map.items():
                    for shortcut_index, shortcut_value in vehicle_shortcuts.get(direction, {}).items():
                        if shortcut_value and key_str == shortcut_value:
                            position = position_enum[f"VEHICLE_{shortcut_index}"].value
                            WindowControlService.click_at(pid, position[0], position[1])
                            handle_quick_sell()
                            return
                
        
        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        
        while self.window_configs[pid]['active']:
            time.sleep(0.1)  # Prevent high CPU usage
            
        listener.stop()
    
    def reload_listeners(self):
        """Reload listeners for all active windows."""
        logger.info("Reloading listeners for all active windows")
        self.load_config()
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
    
    def set_config(self, pid: int, config: dict):
        """Update the shortcut mode for the specified window."""
        if pid not in self.window_configs:
            self.window_configs[pid] = {}
            self.window_configs[pid]['mode'] = GameMode.SINGLE_PLAYER.value
            self.window_configs[pid]['active'] = False
            self.window_configs[pid]['side'] = 'left'
        
        mode = config.get('mode')
        side = config.get('side')
        if mode != None:
            self.window_configs[pid]['mode'] = mode
        if side!= None:
            self.window_configs[pid]['side'] = side
        if self.window_configs[pid].get('active'):
            self.reload_listeners()