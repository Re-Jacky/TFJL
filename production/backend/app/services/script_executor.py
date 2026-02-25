"""
Script Executor Service - Execute parsed scripts with level monitoring.

This module handles:
- Level monitoring via OCR (game level detection)
- Action execution based on current level
- Event detection and response
- Start/pause/stop controls
- Execution state management
"""

import asyncio
import threading
import time
from typing import Optional, Dict, Any, Callable, List
import logging
from datetime import datetime

from app.models.script_models import (
    Script, LevelCommand, EventCommand, Action, ActionType,
    ExecutionState, ScriptExecutionStatus,
    DeployAction, RemoveAction, PrepareAction, SwitchEquipmentAction,
    WaitUntilAction, RepeatAction, DelayAction, StopBallAction,
    CloseVerifyAction, SameRowAction, CancelSameRowAction,
    ForceOrderAction, VerifyDeployAction, DiscardPlayAction, RawAction,
)
from app.services.window_control_services import WindowControlService
from app.utils.logger import logger


class LevelMonitor:
    """
    Monitor game level using OCR.
    
    Runs in a separate thread, periodically capturing the level display
    and updating the current level.
    """
    
    # Level display region (x, y, width, height) - adjust based on game UI
    LEVEL_REGION = (510, 85, 60, 30)  # Approximate level display position
    
    # Level clock/timer region for detecting seconds
    CLOCK_REGION = (560, 85, 50, 25)  # Approximate clock position
    
    def __init__(self, window_pid: int, poll_interval: float = 0.5):
        self.window_pid = window_pid
        self.poll_interval = poll_interval
        self._current_level = 0
        self._current_second = 0.0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._level_callbacks: List[Callable[[int], None]] = []
    
    @property
    def current_level(self) -> int:
        with self._lock:
            return self._current_level
    
    @property
    def current_second(self) -> float:
        with self._lock:
            return self._current_second
    
    def add_level_callback(self, callback: Callable[[int], None]) -> None:
        """Add a callback to be called when level changes."""
        self._level_callbacks.append(callback)
    
    def start(self) -> None:
        """Start the level monitoring thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"[LevelMonitor] Started for window {self.window_pid}")
    
    def stop(self) -> None:
        """Stop the level monitoring thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("[LevelMonitor] Stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                new_level = self._detect_level()
                new_second = self._detect_clock_second()
                
                with self._lock:
                    old_level = self._current_level
                    self._current_level = new_level
                    self._current_second = new_second
                
                # Notify callbacks if level changed
                if new_level != old_level and new_level > 0:
                    logger.info(f"[LevelMonitor] Level changed: {old_level} -> {new_level}")
                    for callback in self._level_callbacks:
                        try:
                            callback(new_level)
                        except Exception as e:
                            logger.error(f"[LevelMonitor] Callback error: {e}")
                
            except Exception as e:
                logger.error(f"[LevelMonitor] Detection error: {e}")
            
            time.sleep(self.poll_interval)
    
    def _detect_level(self) -> int:
        """Detect current game level using OCR."""
        try:
            import pytesseract
            import cv2
            
            # Capture level region
            hwnd = WindowControlService.find_window(self.window_pid)
            screenshot_gray = WindowControlService.capture_region(hwnd, self.LEVEL_REGION)
            
            # Preprocess for OCR
            _, thresholded = cv2.threshold(screenshot_gray, 150, 255, cv2.THRESH_BINARY)
            
            # OCR config for digits
            config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
            text = pytesseract.image_to_string(thresholded, config=config).strip()
            
            if text.isdigit():
                return int(text)
            return self._current_level  # Keep previous if detection failed
            
        except Exception as e:
            logger.debug(f"[LevelMonitor] Level detection failed: {e}")
            return self._current_level
    
    def _detect_clock_second(self) -> float:
        """Detect current clock second using OCR."""
        try:
            import pytesseract
            import cv2
            
            # Capture clock region
            hwnd = WindowControlService.find_window(self.window_pid)
            screenshot_gray = WindowControlService.capture_region(hwnd, self.CLOCK_REGION)
            
            # Preprocess for OCR
            _, thresholded = cv2.threshold(screenshot_gray, 150, 255, cv2.THRESH_BINARY)
            
            # OCR config for digits and decimal point
            config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.'
            text = pytesseract.image_to_string(thresholded, config=config).strip()
            
            try:
                return float(text)
            except ValueError:
                return self._current_second
            
        except Exception as e:
            logger.debug(f"[LevelMonitor] Clock detection failed: {e}")
            return self._current_second


class ScriptExecutorService:
    """
    Service for executing parsed scripts.
    
    Manages execution state, level monitoring, and action execution.
    """
    
    # Singleton instance storage per window
    _instances: Dict[int, 'ScriptExecutorService'] = {}
    
    @classmethod
    def get_instance(cls, window_pid: int) -> 'ScriptExecutorService':
        """Get or create executor instance for a window."""
        if window_pid not in cls._instances:
            cls._instances[window_pid] = cls(window_pid)
        return cls._instances[window_pid]
    
    @classmethod
    def remove_instance(cls, window_pid: int) -> None:
        """Remove executor instance for a window."""
        if window_pid in cls._instances:
            instance = cls._instances.pop(window_pid)
            instance.stop()
    
    def __init__(self, window_pid: int):
        self.window_pid = window_pid
        self.script: Optional[Script] = None
        self.status = ScriptExecutionStatus()
        self.level_monitor = LevelMonitor(window_pid)
        
        self._execution_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused by default
        self._stop_event = threading.Event()
        
        # Register level change callback
        self.level_monitor.add_level_callback(self._on_level_change)
        
        # Track executed levels to avoid duplicate execution
        self._executed_levels: set = set()
        
        # Pending actions queue (for actions waiting on clock time)
        self._pending_actions: List[Dict[str, Any]] = []
    
    def load_script(self, script: Script) -> None:
        """Load a script for execution."""
        with self._lock:
            self.script = script
            self._executed_levels.clear()
            self._pending_actions.clear()
            logger.info(f"[Executor] Loaded script: {script.metadata.name}")
    
    def start(self) -> bool:
        """Start script execution."""
        with self._lock:
            if not self.script:
                logger.error("[Executor] No script loaded")
                return False
            
            if self.status.state == ExecutionState.RUNNING:
                logger.warning("[Executor] Already running")
                return False
            
            self.status.state = ExecutionState.RUNNING
            self.status.start_time = time.time()
            self.status.error_message = None
            self._stop_event.clear()
            self._pause_event.set()
        
        # Start level monitor
        self.level_monitor.start()
        
        # Start execution thread
        self._execution_thread = threading.Thread(
            target=self._execution_loop,
            daemon=True
        )
        self._execution_thread.start()
        
        logger.info("[Executor] Started")
        return True
    
    def pause(self) -> bool:
        """Pause script execution."""
        with self._lock:
            if self.status.state != ExecutionState.RUNNING:
                return False
            
            self.status.state = ExecutionState.PAUSED
            self._pause_event.clear()
        
        logger.info("[Executor] Paused")
        return True
    
    def resume(self) -> bool:
        """Resume script execution."""
        with self._lock:
            if self.status.state != ExecutionState.PAUSED:
                return False
            
            self.status.state = ExecutionState.RUNNING
            self._pause_event.set()
        
        logger.info("[Executor] Resumed")
        return True
    
    def stop(self) -> bool:
        """Stop script execution."""
        with self._lock:
            self.status.state = ExecutionState.STOPPED
            self._stop_event.set()
            self._pause_event.set()  # Unblock if paused
        
        # Stop level monitor
        self.level_monitor.stop()
        
        # Wait for execution thread
        if self._execution_thread:
            self._execution_thread.join(timeout=2.0)
            self._execution_thread = None
        
        logger.info("[Executor] Stopped")
        return True
    
    def get_status(self) -> ScriptExecutionStatus:
        """Get current execution status."""
        with self._lock:
            self.status.current_level = self.level_monitor.current_level
            self.status.current_second = self.level_monitor.current_second
            return self.status.model_copy()
    
    def _on_level_change(self, new_level: int) -> None:
        """Callback when game level changes."""
        with self._lock:
            # Clear pending actions from previous level
            self._pending_actions.clear()
            
            # Check if we have commands for this level
            if self.script and new_level not in self._executed_levels:
                level_cmd = self.script.get_level_command(new_level)
                if level_cmd:
                    logger.info(f"[Executor] Scheduling level {new_level} commands")
                    self._schedule_level_actions(level_cmd)
                    self._executed_levels.add(new_level)
    
    def _schedule_level_actions(self, level_cmd: LevelCommand) -> None:
        """Schedule actions from a level command."""
        for action in level_cmd.actions:
            # Actions with wait_until need special handling
            if isinstance(action, WaitUntilAction):
                self._pending_actions.append({
                    'type': 'wait_until',
                    'second': action.second,
                    'subsequent_actions': []
                })
            elif self._pending_actions and self._pending_actions[-1]['type'] == 'wait_until':
                # This action follows a wait_until
                self._pending_actions[-1]['subsequent_actions'].append(action)
            else:
                # Execute immediately
                self._pending_actions.append({
                    'type': 'immediate',
                    'action': action
                })
    
    def _execution_loop(self) -> None:
        """Main execution loop."""
        logger.info("[Executor] Execution loop started")
        
        while not self._stop_event.is_set():
            # Wait if paused
            self._pause_event.wait()
            
            if self._stop_event.is_set():
                break
            
            try:
                self._process_pending_actions()
            except Exception as e:
                logger.error(f"[Executor] Execution error: {e}")
                with self._lock:
                    self.status.state = ExecutionState.ERROR
                    self.status.error_message = str(e)
                break
            
            time.sleep(0.1)  # Small delay to prevent busy loop
        
        logger.info("[Executor] Execution loop ended")
    
    def _process_pending_actions(self) -> None:
        """Process pending actions based on current clock time."""
        current_second = self.level_monitor.current_second
        
        with self._lock:
            to_remove = []
            
            for i, pending in enumerate(self._pending_actions):
                if pending['type'] == 'immediate':
                    # Execute immediately
                    self._execute_action(pending['action'])
                    self.status.actions_executed += 1
                    to_remove.append(i)
                    
                elif pending['type'] == 'wait_until':
                    # Check if time has come
                    if current_second >= pending['second']:
                        # Execute all subsequent actions
                        for action in pending['subsequent_actions']:
                            self._execute_action(action)
                            self.status.actions_executed += 1
                        to_remove.append(i)
            
            # Remove processed actions (reverse order to preserve indices)
            for i in reversed(to_remove):
                self._pending_actions.pop(i)
    
    def _execute_action(self, action: Action) -> None:
        """Execute a single action."""
        logger.debug(f"[Executor] Executing: {action.type.value}")
        
        if isinstance(action, DeployAction):
            self._execute_deploy(action)
        elif isinstance(action, RemoveAction):
            self._execute_remove(action)
        elif isinstance(action, PrepareAction):
            self._execute_prepare(action)
        elif isinstance(action, SwitchEquipmentAction):
            self._execute_switch_equipment(action)
        elif isinstance(action, WaitUntilAction):
            # Handled in scheduling, not here
            pass
        elif isinstance(action, RepeatAction):
            self._execute_repeat(action)
        elif isinstance(action, DelayAction):
            self._execute_delay(action)
        elif isinstance(action, StopBallAction):
            self._execute_stop_ball()
        elif isinstance(action, CloseVerifyAction):
            self._execute_close_verify()
        elif isinstance(action, SameRowAction):
            self._execute_same_row(action)
        elif isinstance(action, CancelSameRowAction):
            self._execute_cancel_same_row()
        elif isinstance(action, ForceOrderAction):
            self._execute_force_order()
        elif isinstance(action, VerifyDeployAction):
            self._execute_verify_deploy(action)
        elif isinstance(action, DiscardPlayAction):
            self._execute_discard_play(action)
        elif isinstance(action, RawAction):
            logger.warning(f"[Executor] Skipping raw action: {action.content}")
        else:
            logger.warning(f"[Executor] Unknown action type: {type(action)}")
    
    # ========================================================================
    # Action Implementations - TODO: Connect to actual game control
    # ========================================================================
    
    def _execute_deploy(self, action: DeployAction) -> None:
        """Deploy a card."""
        logger.info(f"[Executor] Deploy: {action.card} (level: {action.level})")
        # TODO: Implement actual card deployment
        # This should:
        # 1. Find the card in hand or scroll to find it
        # 2. Click to deploy with specified level requirement
        pass
    
    def _execute_remove(self, action: RemoveAction) -> None:
        """Remove a card from battlefield."""
        logger.info(f"[Executor] Remove: {action.card}")
        # TODO: Implement card removal
        pass
    
    def _execute_prepare(self, action: PrepareAction) -> None:
        """Prepare a card in hand."""
        logger.info(f"[Executor] Prepare: {action.card}")
        # TODO: Implement card preparation
        pass
    
    def _execute_switch_equipment(self, action: SwitchEquipmentAction) -> None:
        """Switch equipment."""
        logger.info(f"[Executor] Switch equipment: {action.equipment}")
        # TODO: Implement equipment switching
        pass
    
    def _execute_repeat(self, action: RepeatAction) -> None:
        """Execute repeated card deployment."""
        logger.info(f"[Executor] Repeat: {action.card} every {action.interval}s x{action.count}")
        
        # Execute in a separate thread to not block
        def repeat_loop():
            for i in range(action.count):
                if self._stop_event.is_set() or not self._pause_event.is_set():
                    break
                
                logger.debug(f"[Executor] Repeat iteration {i+1}/{action.count}: {action.card}")
                # TODO: Actual card deployment
                time.sleep(action.interval)
        
        thread = threading.Thread(target=repeat_loop, daemon=True)
        thread.start()
    
    def _execute_delay(self, action: DelayAction) -> None:
        """Execute delay."""
        logger.info(f"[Executor] Delay: {action.milliseconds}ms")
        time.sleep(action.milliseconds / 1000.0)
    
    def _execute_stop_ball(self) -> None:
        """Execute stop ball."""
        logger.info("[Executor] Stop ball")
        # TODO: Implement stop ball action
        pass
    
    def _execute_close_verify(self) -> None:
        """Close verification panel."""
        logger.info("[Executor] Close verify")
        # TODO: Implement close verify
        pass
    
    def _execute_same_row(self, action: SameRowAction) -> None:
        """Deploy cards in same row."""
        logger.info(f"[Executor] Same row: {action.cards}")
        # TODO: Implement same row deployment
        pass
    
    def _execute_cancel_same_row(self) -> None:
        """Cancel same row mode."""
        logger.info("[Executor] Cancel same row")
        # TODO: Implement cancel same row
        pass
    
    def _execute_force_order(self) -> None:
        """Enable force order mode."""
        logger.info("[Executor] Force order")
        # TODO: Implement force order mode
        pass
    
    def _execute_verify_deploy(self, action: VerifyDeployAction) -> None:
        """Execute verify and deploy."""
        logger.info(f"[Executor] Verify deploy (max_only: {action.max_only}, count: {action.count})")
        # TODO: Implement verify deploy
        pass
    
    def _execute_discard_play(self, action: DiscardPlayAction) -> None:
        """Discard and play a card."""
        logger.info(f"[Executor] Discard play: {action.card}")
        # TODO: Implement discard play
        pass
