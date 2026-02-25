"""
Event Detection Service - Detect game events via image recognition.

This service monitors the game window for specific visual patterns (boss events,
special triggers) and notifies the executor when events are detected.
"""

import threading
import time
from typing import Optional, Dict, Set, Callable, List, Tuple
from pathlib import Path
import cv2
import numpy as np

from app.services.window_control_services import WindowControlService
from app.services.image_services import ImageService
from app.services.utility_services import UtilityService
from app.enums.script_commands import ALL_KNOWN_EVENTS, get_game_mode_from_event, GameMode
from app.utils.logger import logger


class EventDetector:
    """
    Monitors game window for event triggers using template matching.
    
    Events are detected by matching pre-defined image templates against
    specific regions of the game window.
    """
    
    EVENT_CHECK_REGION = (300, 200, 400, 200)
    CONFIDENCE_THRESHOLD = 0.85
    
    def __init__(self, window_pid: int, poll_interval: float = 1.0):
        self.window_pid = window_pid
        self.poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        self._event_callbacks: List[Callable[[str], None]] = []
        self._active_events: Set[str] = set()
        self._last_detected_event: Optional[str] = None
        self._event_cooldown: Dict[str, float] = {}
        
        self._event_templates: Dict[str, np.ndarray] = {}
        self._image_service = ImageService.get_instance()
    
    def add_event_callback(self, callback: Callable[[str], None]) -> None:
        self._event_callbacks.append(callback)
    
    def set_active_events(self, events: Set[str]) -> None:
        with self._lock:
            self._active_events = events
            self._load_event_templates(events)
    
    def _load_event_templates(self, events: Set[str]) -> None:
        self._event_templates.clear()
        event_images_path = UtilityService.get_public_path() / "images" / "events"
        
        for event in events:
            template_path = event_images_path / f"{event}.jpg"
            if template_path.exists():
                try:
                    template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
                    if template is not None:
                        self._event_templates[event] = template
                        logger.debug(f"[EventDetector] Loaded template for: {event}")
                except Exception as e:
                    logger.warning(f"[EventDetector] Failed to load template {event}: {e}")
            else:
                logger.debug(f"[EventDetector] No template found for event: {event}")
    
    def start(self) -> None:
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._thread.start()
        logger.info(f"[EventDetector] Started for window {self.window_pid}")
    
    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("[EventDetector] Stopped")
    
    def _detection_loop(self) -> None:
        while self._running:
            try:
                detected_event = self._check_for_events()
                
                if detected_event and detected_event != self._last_detected_event:
                    if self._should_trigger_event(detected_event):
                        logger.info(f"[EventDetector] Detected event: {detected_event}")
                        self._last_detected_event = detected_event
                        self._event_cooldown[detected_event] = time.time()
                        
                        for callback in self._event_callbacks:
                            try:
                                callback(detected_event)
                            except Exception as e:
                                logger.error(f"[EventDetector] Callback error: {e}")
                
            except Exception as e:
                logger.error(f"[EventDetector] Detection error: {e}")
            
            time.sleep(self.poll_interval)
    
    def _should_trigger_event(self, event: str) -> bool:
        cooldown_period = 2.0
        last_trigger = self._event_cooldown.get(event, 0)
        return (time.time() - last_trigger) > cooldown_period
    
    def _check_for_events(self) -> Optional[str]:
        if not self._event_templates:
            return None
        
        try:
            hwnd = WindowControlService.find_window(self.window_pid)
            screenshot_gray = WindowControlService.capture_region(hwnd, self.EVENT_CHECK_REGION)
            
            best_match: Optional[Tuple[str, float]] = None
            
            for event_name, template in self._event_templates.items():
                if template.shape[0] > screenshot_gray.shape[0] or template.shape[1] > screenshot_gray.shape[1]:
                    continue
                
                result = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                
                if max_val >= self.CONFIDENCE_THRESHOLD:
                    if best_match is None or max_val > best_match[1]:
                        best_match = (event_name, max_val)
            
            if best_match:
                logger.debug(f"[EventDetector] Best match: {best_match[0]} ({best_match[1]:.2f})")
                return best_match[0]
            
            return None
            
        except Exception as e:
            logger.debug(f"[EventDetector] Check failed: {e}")
            return None
    
    def clear_last_event(self) -> None:
        with self._lock:
            self._last_detected_event = None


class EventDetectionService:
    """
    Service layer for managing event detection across windows.
    """
    
    _detectors: Dict[int, EventDetector] = {}
    
    @classmethod
    def get_detector(cls, window_pid: int) -> EventDetector:
        if window_pid not in cls._detectors:
            cls._detectors[window_pid] = EventDetector(window_pid)
        return cls._detectors[window_pid]
    
    @classmethod
    def remove_detector(cls, window_pid: int) -> None:
        if window_pid in cls._detectors:
            detector = cls._detectors.pop(window_pid)
            detector.stop()
    
    @classmethod
    def get_available_events(cls) -> Set[str]:
        return ALL_KNOWN_EVENTS.copy()
    
    @classmethod
    def get_events_by_mode(cls, mode_name: str) -> Set[str]:
        try:
            mode = GameMode(mode_name)
            return {e for e in ALL_KNOWN_EVENTS if get_game_mode_from_event(e) == mode}
        except ValueError:
            return set()
