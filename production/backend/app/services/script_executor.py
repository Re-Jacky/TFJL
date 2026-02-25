"""
Script Executor Service - Execute parsed scripts with level monitoring.

This module handles:
- Level monitoring via OCR (game level detection)
- Action execution based on current level
- Vehicle state tracking (cards deployed on vehicle)
- Event detection and response
- Start/pause/stop controls
- Execution state management
"""

import asyncio
import threading
import time
from typing import Optional, Dict, Any, Callable, List, TYPE_CHECKING
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

if TYPE_CHECKING:
    from app.services.event_services import EventService


class VehicleState:
    """
    Track deployed cards on a vehicle.
    
    Vehicle position mechanics:
    - Initial positions: only 0 and 6 are available
    - Position 6 is special: ONLY for cards 射线, 宝库, 潜艇, 火炮, 咬人娃娃
    - These special cards can ONLY go to position 6
    - Positions 1-5 must be unlocked via upgrade_vehicle action
    - Unlock order: 1 -> 2 -> 3 -> 4 -> 5 (one at a time)
    
    Deployment order: bottom-to-top, right-to-left.
    Both normal and force order modes fill positions in order 0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6.
    
    The difference:
    - Normal mode: Find first EMPTY position in order 0->1->..->5 (skip 6 unless special card)
    - Force order mode: Deploy to NEXT position in strict sequence (skip 6 unless special card)
    
    When removing a card, the position becomes empty.
    Next deploy fills the lowest-numbered empty position (excluding 6 for non-special cards).
    """
    
    # Deployment order for normal cards: positions 0-5 (NOT 6)
    DEPLOY_ORDER = [0, 1, 2, 3, 4, 5]
    NUM_POSITIONS = 7  # Total positions including special pos 6
    
    # Special cards that can ONLY be deployed to position 6
    SPECIAL_POS6_CARDS = {'射线', '宝库', '潜艇', '火炮', '咬人娃娃'}
    
    # Initial unlocked positions (0 and 6)
    INITIAL_POSITIONS = {0, 6}
    
    # Upgrade order: which position to unlock next
    UPGRADE_ORDER = [1, 2, 3, 4, 5]
    
    def __init__(self):
        # Map position (0-6) to card info: {'card': str, 'level': int} or None
        self._cells: Dict[int, Optional[Dict[str, Any]]] = {
            i: None for i in range(self.NUM_POSITIONS)
        }
        self._card_positions: Dict[str, int] = {}  # card name -> position (for fast lookup on remove)
        self._current_level: int = 0
        self._equipment: Optional[str] = None
        self._side: str = 'left'  # default side
        self._force_order: bool = False  # When True, deploy in strict sequence 0->1->2...
        self._force_order_index: int = 0  # Next position index in forced order
        
        # Unlocked positions - initially only 0 and 6
        self._unlocked_positions: set = set(self.INITIAL_POSITIONS)
    
    def reset(self) -> None:
        """Reset vehicle state (e.g., when script starts or level resets)."""
        self._cells = {i: None for i in range(self.NUM_POSITIONS)}
        self._card_positions.clear()
        self._current_level = 0
        self._equipment = None
        self._force_order = False
        self._force_order_index = 0
        self._unlocked_positions = set(self.INITIAL_POSITIONS)
    
    def set_level(self, level: int) -> None:
        """Update current game level."""
        self._current_level = level
    
    def set_equipment(self, equipment: str) -> None:
        """Update current equipment."""
        self._equipment = equipment
    
    def set_force_order(self, enabled: bool) -> None:
        """Enable or disable force order mode."""
        self._force_order = enabled
        if enabled:
            self._force_order_index = 0
            logger.info("[VehicleState] Force order mode ENABLED")
        else:
            logger.info("[VehicleState] Force order mode DISABLED")
    
    def is_force_order(self) -> bool:
        """Check if force order mode is active."""
        return self._force_order
    
    def is_special_card(self, card: str) -> bool:
        """Check if card is a special pos-6-only card."""
        return card in self.SPECIAL_POS6_CARDS
    
    def get_unlocked_positions(self) -> set:
        """Get set of currently unlocked positions."""
        return set(self._unlocked_positions)
    
    def is_position_unlocked(self, pos: int) -> bool:
        """Check if a position is unlocked."""
        return pos in self._unlocked_positions
    
    def get_next_unlock_position(self) -> Optional[int]:
        """Get the next position that can be unlocked, or None if all unlocked."""
        for pos in self.UPGRADE_ORDER:
            if pos not in self._unlocked_positions:
                return pos
        return None
    
    def unlock_position(self, pos: int) -> bool:
        """
        Unlock a position on the vehicle.
        
        Returns True if position was successfully unlocked.
        """
        if pos in self._unlocked_positions:
            logger.debug(f"[VehicleState] Position {pos} already unlocked")
            return False
        
        # Can only unlock in order
        next_unlock = self.get_next_unlock_position()
        if next_unlock != pos:
            logger.warning(f"[VehicleState] Cannot unlock position {pos}, next unlock must be {next_unlock}")
            return False
        
        self._unlocked_positions.add(pos)
        logger.info(f"[VehicleState] Unlocked position {pos}")
        return True
    
    def get_available_deploy_position(self, card: str) -> Optional[int]:
        """
        Get the next available position for deploying a card.
        
        For special cards: returns 6 if empty, None otherwise.
        For normal cards: returns first empty unlocked position in DEPLOY_ORDER (0,1,2,3,4,5).
        """
        if self.is_special_card(card):
            # Special cards can only go to position 6
            if self._cells[6] is None:
                return 6
            return None  # Position 6 is occupied
        
        # Normal cards: find first empty unlocked position
        for pos in self.DEPLOY_ORDER:
            if pos in self._unlocked_positions and self._cells[pos] is None:
                return pos
        return None  # No available position
    
    def needs_upgrade_for_deploy(self, card: str) -> bool:
        """
        Check if vehicle needs to be upgraded to have a position for this card.
        
        Returns True if all unlocked positions are occupied and more positions can be unlocked.
        """
        if self.is_special_card(card):
            # Special cards go to pos 6 which is always unlocked
            return False
        
        # Check if any unlocked position is empty
        for pos in self.DEPLOY_ORDER:
            if pos in self._unlocked_positions and self._cells[pos] is None:
                return False  # Have empty position
        
        # All unlocked positions are full - check if we can unlock more
        return self.get_next_unlock_position() is not None

    def deploy(self, card: str, level: int) -> Optional[int]:
        """
        Deploy a card to the vehicle.
        
        Behavior:
        1. Special cards (射线, 宝库, 潜艇, 火炮, 咬人娃娃) -> position 6 ONLY
        2. If card is already on vehicle: replace in place (update level, keep position)
        3. In force order mode: deploy to next position in sequence 0->1->2->3->4->5 (skip 6)
        4. In normal mode: deploy to first empty unlocked position
        
        Returns the position where card was deployed, or None if no position available.
        """
        is_special = self.is_special_card(card)
        
        # Special cards go to position 6 only
        if is_special:
            if self._cells[6] is not None:
                old_card = self._cells[6]['card']
                if old_card in self._card_positions:
                    del self._card_positions[old_card]
            
            self._cells[6] = {'card': card, 'level': level}
            self._card_positions[card] = 6
            logger.info(f"[VehicleState] Deployed special card '{card}' (level {level}) to position 6")
            return 6
        
        # Check if card is already on the vehicle - replace in place
        if card in self._card_positions:
            pos = self._card_positions[card]
            self._cells[pos] = {'card': card, 'level': level}
            logger.info(f"[VehicleState] Replaced '{card}' (level {level}) in place at position {pos}")
            return pos
        
        if self._force_order:
            # Force order: deploy to next position in strict sequence 0->1->2..->5 (skip 6)
            while self._force_order_index < len(self.DEPLOY_ORDER):
                pos = self.DEPLOY_ORDER[self._force_order_index]
                self._force_order_index += 1
                
                # Skip if position is not unlocked yet
                if pos not in self._unlocked_positions:
                    continue
                
                # Place card even if position is occupied (overwrite)
                old_card = self._cells[pos]
                if old_card and old_card['card'] in self._card_positions:
                    del self._card_positions[old_card['card']]
                self._cells[pos] = {'card': card, 'level': level}
                self._card_positions[card] = pos
                logger.info(f"[VehicleState] Force deployed '{card}' (level {level}) to position {pos}")
                return pos
            logger.warning(f"[VehicleState] Force order exhausted, cannot deploy '{card}'")
            return None
        else:
            # Normal mode: find first empty unlocked position
            for pos in self.DEPLOY_ORDER:
                if pos in self._unlocked_positions and self._cells[pos] is None:
                    self._cells[pos] = {'card': card, 'level': level}
                    self._card_positions[card] = pos
                    logger.info(f"[VehicleState] Deployed '{card}' (level {level}) to position {pos}")
                    return pos
            logger.warning(f"[VehicleState] No available position, cannot deploy '{card}'")
            return None
    
    def remove(self, card: str) -> Optional[int]:
        """
        Remove a card from the vehicle.
        
        Returns the position that was cleared, or None if card not found.
        """
        if card not in self._card_positions:
            logger.warning(f"[VehicleState] Card '{card}' not found on vehicle")
            return None
        
        pos = self._card_positions.pop(card)
        self._cells[pos] = None
        logger.info(f"[VehicleState] Removed '{card}' from position {pos}")
        return pos
    
    def to_broadcast_dict(self) -> Dict[str, Any]:
        """
        Convert to dict format expected by frontend SSE handler.
        
        Format: {
            'side': 'left' | 'right',
            'equipment': str | None,
            'level': int,
            'unlocked_positions': [0, 6, ...],
            'info': {0: {'card': str, 'level': int}, 1: {...}, ...}
        }
        """
        info = {}
        for pos, cell in self._cells.items():
            if cell is None:
                info[pos] = {'card': None, 'level': None}
            else:
                info[pos] = {'card': cell['card'], 'level': cell['level']}
        
        return {
            'side': self._side,
            'equipment': self._equipment,
            'level': self._current_level,
            'unlocked_positions': sorted(list(self._unlocked_positions)),
            'info': info
        }

class DeckState:
    """
    Track card deck and hand state for deployment simulation.
    
    Game mechanics:
    - Deck contains all cards from script setup (上阵)
    - Hand shows 3 different cards at a time from available pool
    - Each card can be deployed multiple times until reaching max level
    - Max level: 4 normally, 5 if card is in enhanced (魔化) list
    - Refresh replaces all 3 hand cards with new random cards from available pool
    - Available pool = cards that haven't reached max level yet
    """
    
    HAND_SIZE = 3
    DEFAULT_MAX_LEVEL = 4
    ENHANCED_MAX_LEVEL = 5
    
    def __init__(self, deck: List[str], enhanced: Optional[List[str]] = None):
        """
        Initialize deck state.
        
        Args:
            deck: List of card names in the deck (from script setup)
            enhanced: List of enhanced card names (魔化) that have max level 5
        """
        self._deck = list(deck)  # All cards in deck
        self._enhanced = set(enhanced or [])  # Cards with max level 5
        
        # Track deployment count for each card (0 = not deployed yet)
        self._card_deploy_count: Dict[str, int] = {card: 0 for card in deck}
        
        # Current hand (3 cards)
        self._hand: List[str] = []
        
        # Refresh count for statistics
        self._refresh_count = 0
        
        # Initial hand draw
        self._refresh_hand()
    
    def _get_max_level(self, card: str) -> int:
        """Get max level for a card (5 if enhanced, 4 otherwise)."""
        return self.ENHANCED_MAX_LEVEL if card in self._enhanced else self.DEFAULT_MAX_LEVEL
    
    def _get_available_cards(self) -> List[str]:
        """Get cards that haven't reached max level yet."""
        available = []
        for card in self._deck:
            max_level = self._get_max_level(card)
            if self._card_deploy_count.get(card, 0) < max_level:
                available.append(card)
        return available
    
    def _refresh_hand(self) -> List[str]:
        """
        Refresh hand with new cards from available pool.
        Returns the new hand cards.
        """
        import random
        
        available = self._get_available_cards()
        
        if not available:
            self._hand = []
            return []
        
        # Pick up to HAND_SIZE different cards
        if len(available) <= self.HAND_SIZE:
            self._hand = list(available)
        else:
            self._hand = random.sample(available, self.HAND_SIZE)
        
        return list(self._hand)
    
    def refresh(self) -> List[str]:
        """
        Player clicks refresh button - get new hand cards.
        Returns the new hand cards.
        """
        self._refresh_count += 1
        return self._refresh_hand()
    
    def is_card_in_hand(self, card: str) -> bool:
        """Check if a card is currently in hand."""
        return card in self._hand
    
    def get_hand(self) -> List[str]:
        """Get current hand cards."""
        return list(self._hand)
    
    def deploy_card(self, card: str) -> bool:
        """
        Deploy a card from hand.
        
        Game mechanics:
        - Card must be in current hand
        - Card must not be at max level
        - On deploy: increment card's deploy count
        - On deploy: ALL cards in hand are removed (not just the deployed one)
        - Player must refresh to get new cards after deploying
        
        Returns True if card was successfully deployed (was in hand and not maxed).
        Side effect: increments card's deploy count, clears entire hand.
        """
        if card not in self._hand:
            return False
        
        max_level = self._get_max_level(card)
        current_count = self._card_deploy_count.get(card, 0)
        
        if current_count >= max_level:
            return False
        
        # Increment deploy count
        self._card_deploy_count[card] = current_count + 1
        
        # IMPORTANT: Deploying ANY card clears the ENTIRE hand
        # Player must refresh to get new cards
        self._hand.clear()
        
        return True
    
    def find_card_with_refresh(self, card: str, max_refreshes: int = 100) -> int:
        """
        Search for a card by refreshing until found.
        
        Args:
            card: Card name to find
            max_refreshes: Maximum refresh attempts before giving up
        
        Returns:
            Number of refreshes needed (0 if already in hand, -1 if not found after max attempts)
        """
        # Check if card is available at all
        if card not in self._deck:
            return -1
        
        max_level = self._get_max_level(card)
        if self._card_deploy_count.get(card, 0) >= max_level:
            return -1  # Card already maxed out
        
        # Check if already in hand
        if self.is_card_in_hand(card):
            return 0
        
        # Refresh until found
        for i in range(max_refreshes):
            self.refresh()
            if self.is_card_in_hand(card):
                return i + 1
        
        return -1  # Not found after max attempts
    
    def find_priority_card_in_hand(self, priority_list: List[str]) -> Optional[str]:
        """
        Find the highest-priority card that is currently in hand.
        
        Used for forced order deployment: when multiple cards from the pending list
        are in hand, deploy them in priority order.
        
        Args:
            priority_list: List of card names in priority order (first = highest priority)
        
        Returns:
            The card name with highest priority that is in hand, or None if none found.
        """
        for card in priority_list:
            if self.is_card_in_hand(card):
                return card
        return None
    
    def find_card_with_refresh_broadcast(
        self,
        card: str,
        max_refreshes: int = 100
    ) -> tuple:
        """
        Search for a card by refreshing, returning each refresh result for broadcasting.
        
        This is a generator version that yields after each refresh so the caller
        can broadcast the hand state.
        
        Args:
            card: Card name to find
            max_refreshes: Maximum refresh attempts before giving up
        
        Returns:
            Tuple of (found: bool, refresh_count: int, final_hand: List[str])
        """
        # Check if card is available at all
        if card not in self._deck:
            return (False, 0, self.get_hand())
        
        max_level = self._get_max_level(card)
        if self._card_deploy_count.get(card, 0) >= max_level:
            return (False, 0, self.get_hand())  # Card already maxed out
        
        # Check if already in hand
        if self.is_card_in_hand(card):
            return (True, 0, self.get_hand())
        
        # Refresh until found
        for i in range(max_refreshes):
            self.refresh()
            if self.is_card_in_hand(card):
                return (True, i + 1, self.get_hand())
        
        return (False, max_refreshes, self.get_hand())  # Not found after max attempts
    def get_card_level(self, card: str) -> int:
        """Get current deployment count (level) of a card."""
        return self._card_deploy_count.get(card, 0)
    
    def get_refresh_count(self) -> int:
        """Get total refresh count for statistics."""
        return self._refresh_count
    
    def reset(self) -> None:
        """Reset deck state to initial."""
        self._card_deploy_count = {card: 0 for card in self._deck}
        self._refresh_count = 0
        self._refresh_hand()

    def reset_card_level(self, card: str) -> None:
        """Reset a single card's deploy count to 0 (used when card is removed from vehicle)."""
        if card in self._card_deploy_count:
            self._card_deploy_count[card] = 0
    
    def to_broadcast_dict(self) -> Dict[str, Any]:
        """Convert to dict for SSE broadcasting."""
        return {
            'hand': list(self._hand),
            'refresh_count': self._refresh_count,
            'card_levels': dict(self._card_deploy_count),
            'available_count': len(self._get_available_cards())
        }

class LevelMonitor:
    """
    Monitor game level using OCR.
    
    Runs in a separate thread, periodically capturing the level display
    and updating the current level. Uses a local timer to track seconds
    since level start (the game has no visible clock - '时钟秒XX' means
    XX seconds after level began).
    """
    
    # Level display region (x, y, width, height) - adjust based on game UI
    LEVEL_REGION = (510, 85, 60, 30)  # Approximate level display position
    
    def __init__(self, window_pid: int, poll_interval: float = 0.5):
        self.window_pid = window_pid
        self.poll_interval = poll_interval
        self._current_level = 0
        self._level_start_time: Optional[float] = None  # When current level started
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
        """Get seconds elapsed since current level started."""
        with self._lock:
            if self._level_start_time is None:
                return 0.0
            return time.time() - self._level_start_time
    
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
                
                with self._lock:
                    old_level = self._current_level
                    
                    # Check if level changed
                    if new_level != old_level and new_level > 0:
                        self._current_level = new_level
                        self._level_start_time = time.time()  # Reset timer on level change
                        logger.info(f"[LevelMonitor] Level changed: {old_level} -> {new_level}, timer reset")
                        
                        # Notify callbacks (outside lock would be better but keep simple)
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

class ScriptExecutorService:
    """
    Service for executing parsed scripts.
    
    Manages execution state, level monitoring, vehicle state, and action execution.
    Broadcasts vehicle state changes via SSE to update frontend UI.
    """
    
    # Singleton instance storage per window
    _instances: Dict[int, 'ScriptExecutorService'] = {}
    _event_service: Optional['EventService'] = None  # Shared event service
    
    @classmethod
    def set_event_service(cls, event_service: 'EventService') -> None:
        """Set the shared event service for broadcasting."""
        cls._event_service = event_service
    
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
        self.vehicle_state = VehicleState()  # Track deployed cards
        
        self._execution_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused by default
        self._stop_event = threading.Event()
        
        # Async loop for broadcasting (runs in background thread)
        self._async_loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Register level change callback
        self.level_monitor.add_level_callback(self._on_level_change)
        
        # Track executed levels to avoid duplicate execution
        self._executed_levels: set = set()
        
        # Pending actions queue (for actions waiting on clock time)
        self._pending_actions: List[Dict[str, Any]] = []
    
    def _broadcast_vehicle_state(self) -> None:
        """Broadcast current vehicle state to frontend via SSE."""
        if self._event_service is None:
            logger.warning("[Executor] No event service configured, cannot broadcast")
            return
        
        vehicle_data = self.vehicle_state.to_broadcast_dict()
        session_id = str(self.window_pid)
        
        # Run async broadcast in a thread-safe way
        try:
            # Create new event loop for this thread if needed
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run broadcast coroutine
            loop.run_until_complete(
                self._event_service.broadcast_vehicle(vehicle_data, [session_id])
            )
            logger.debug(f"[Executor] Broadcasted vehicle state: {vehicle_data}")
        except Exception as e:
            logger.error(f"[Executor] Failed to broadcast vehicle state: {e}")
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
            
            # Update vehicle state with new level
            self.vehicle_state.set_level(new_level)
            
            # Check if we have commands for this level
            if self.script and new_level not in self._executed_levels:
                level_cmd = self.script.get_level_command(new_level)
                if level_cmd:
                    logger.info(f"[Executor] Scheduling level {new_level} commands")
                    self._schedule_level_actions(level_cmd)
                    self._executed_levels.add(new_level)
            
            # Broadcast level change to frontend
            self._broadcast_vehicle_state()
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
        """Deploy a card and update vehicle state."""
        logger.info(f"[Executor] Deploy: {action.card} (level: {action.level})")
        
        # Update vehicle state
        position = self.vehicle_state.deploy(action.card, action.level or 1)
        if position is not None:
            # Broadcast updated vehicle state to frontend
            self._broadcast_vehicle_state()
        
        # TODO: Implement actual card deployment (game control)
        # This should:
        # 1. Find the card in hand or scroll to find it
        # 2. Click to deploy with specified level requirement
    
    def _execute_remove(self, action: RemoveAction) -> None:
        """Remove a card from battlefield and update vehicle state."""
        logger.info(f"[Executor] Remove: {action.card}")
        
        # Update vehicle state
        position = self.vehicle_state.remove(action.card)
        if position is not None:
            # Broadcast updated vehicle state to frontend
            self._broadcast_vehicle_state()
        
        # TODO: Implement actual card removal (game control)
    def _execute_prepare(self, action: PrepareAction) -> None:
        """Prepare a card in hand."""
        logger.info(f"[Executor] Prepare: {action.card}")
        # TODO: Implement card preparation
        pass
    
    def _execute_switch_equipment(self, action: SwitchEquipmentAction) -> None:
        """Switch equipment and update vehicle state."""
        logger.info(f"[Executor] Switch equipment: {action.equipment}")
        
        # Update vehicle state
        self.vehicle_state.set_equipment(action.equipment)
        # Broadcast updated vehicle state to frontend
        self._broadcast_vehicle_state()
        
        # TODO: Implement actual equipment switching (game control)

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
