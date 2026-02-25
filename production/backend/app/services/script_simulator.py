"""
Script Simulator Service - Dry-run script execution without a game window.

This module provides two simulation modes:
1. Static simulation: Walk through commands and produce action log (no side effects)
2. Live dry-run: Step through with VehicleState tracking and SSE broadcasts (for UI testing)
"""

import asyncio
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from app.models.script_models import (
    Script, LevelCommand, EventCommand, Action, ActionType,
    DeployAction, RemoveAction, PrepareAction, SwitchEquipmentAction,
    WaitUntilAction, RepeatAction, DelayAction, StopBallAction,
    CloseVerifyAction, SameRowAction, CancelSameRowAction,
    ForceOrderAction, VerifyDeployAction, DiscardPlayAction, RawAction,
)
from app.services.script_parser import ScriptParserService
from app.services.script_executor import VehicleState, DeckState
from app.utils.logger import logger

if TYPE_CHECKING:
    from app.services.event_services import EventService


class SimulatedAction:
    """Represents a simulated action with timing and details."""
    
    def __init__(
        self,
        level: int,
        second: Optional[float],
        action_type: str,
        description: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.level = level
        self.second = second
        self.action_type = action_type
        self.description = description
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "second": self.second,
            "action_type": self.action_type,
            "description": self.description,
            "details": self.details
        }


class ScriptSimulatorService:
    """
    Service for simulating script execution without a real game window.
    
    Walks through all script commands and produces a log of what actions
    would be executed at each level/time.
    """
    
    @staticmethod
    def simulate_script(
        content: str,
        name: str = "test.txt",
        script_type: str = "collab"
    ) -> Dict[str, Any]:
        """
        Simulate script execution and return action log.
        
        Args:
            content: Raw script content
            name: Script filename
            script_type: 'collab' or 'activity'
            
        Returns:
            Dict with success status, action_log, errors, warnings, and summary
        """
        # First parse the script
        script, errors, warnings = ScriptParserService.parse_script(
            content=content,
            name=name,
            script_type=script_type
        )
        
        if script is None:
            return {
                "success": False,
                "action_log": [],
                "errors": errors,
                "warnings": warnings,
                "summary": None
            }
        
        # Simulate execution
        action_log: List[Dict[str, Any]] = []
        total_actions = 0
        
        # Process level commands
        for level_cmd in script.commands.level_commands:
            level_actions = ScriptSimulatorService._simulate_level_command(level_cmd)
            action_log.extend(level_actions)
            total_actions += len(level_actions)
        
        # Process event commands
        for event_cmd in script.commands.event_commands:
            event_actions = ScriptSimulatorService._simulate_event_command(event_cmd)
            action_log.extend(event_actions)
            total_actions += len(event_actions)
        
        # Build summary
        summary = ScriptSimulatorService._build_summary(script, action_log)
        
        return {
            "success": True,
            "action_log": action_log,
            "errors": errors,
            "warnings": warnings,
            "summary": summary
        }
    
    @staticmethod
    def _simulate_level_command(level_cmd: LevelCommand) -> List[Dict[str, Any]]:
        """Simulate actions for a level command."""
        actions = []
        current_second: Optional[float] = None
        
        for action in level_cmd.actions:
            simulated = ScriptSimulatorService._simulate_action(
                action,
                level=level_cmd.level,
                current_second=current_second
            )
            
            # Update current_second if this is a wait_until action
            if isinstance(action, WaitUntilAction):
                current_second = action.second
            
            if simulated:
                actions.append(simulated.to_dict())
        
        return actions
    
    @staticmethod
    def _simulate_event_command(event_cmd: EventCommand) -> List[Dict[str, Any]]:
        """Simulate actions for an event command."""
        actions = []
        
        # Add event trigger entry
        event_entry = SimulatedAction(
            level=0,  # Events are level-independent
            second=None,
            action_type="EVENT_TRIGGER",
            description=f"When event '{event_cmd.event}' detected",
            details={
                "event": event_cmd.event,
                "card_filter": event_cmd.card_filter,
                "point_total": event_cmd.point_total
            }
        )
        actions.append(event_entry.to_dict())
        
        for action in event_cmd.actions:
            simulated = ScriptSimulatorService._simulate_action(
                action,
                level=0,
                current_second=None,
                event_context=event_cmd.event
            )
            if simulated:
                actions.append(simulated.to_dict())
        
        return actions
    
    @staticmethod
    def _simulate_action(
        action: Action,
        level: int,
        current_second: Optional[float],
        event_context: Optional[str] = None
    ) -> Optional[SimulatedAction]:
        """Convert a single action to a simulated action."""
        
        if isinstance(action, DeployAction):
            level_str = f" (level: {action.level})" if action.level else ""
            return SimulatedAction(
                level=level,
                second=current_second,
                action_type="DEPLOY",
                description=f"Deploy card: {action.card}{level_str}",
                details={"card": action.card, "card_level": action.level}
            )
        
        elif isinstance(action, RemoveAction):
            return SimulatedAction(
                level=level,
                second=current_second,
                action_type="REMOVE",
                description=f"Remove card: {action.card}",
                details={"card": action.card}
            )
        
        elif isinstance(action, PrepareAction):
            return SimulatedAction(
                level=level,
                second=current_second,
                action_type="PREPARE",
                description=f"Prepare card in hand: {action.card}",
                details={"card": action.card}
            )
        
        elif isinstance(action, SwitchEquipmentAction):
            return SimulatedAction(
                level=level,
                second=current_second,
                action_type="SWITCH_EQUIPMENT",
                description=f"Switch equipment to: {action.equipment}",
                details={"equipment": action.equipment}
            )
        
        elif isinstance(action, WaitUntilAction):
            return SimulatedAction(
                level=level,
                second=action.second,
                action_type="WAIT_UNTIL",
                description=f"Wait until clock second: {action.second}",
                details={"target_second": action.second}
            )
        
        elif isinstance(action, RepeatAction):
            return SimulatedAction(
                level=level,
                second=current_second,
                action_type="REPEAT",
                description=f"Repeat {action.card} every {action.interval}s, {action.count} times",
                details={
                    "card": action.card,
                    "interval": action.interval,
                    "count": action.count
                }
            )
        
        elif isinstance(action, DelayAction):
            return SimulatedAction(
                level=level,
                second=current_second,
                action_type="DELAY",
                description=f"Delay for {action.milliseconds}ms",
                details={"milliseconds": action.milliseconds}
            )
        
        elif isinstance(action, StopBallAction):
            return SimulatedAction(
                level=level,
                second=current_second,
                action_type="STOP_BALL",
                description="Stop ball"
            )
        
        elif isinstance(action, CloseVerifyAction):
            return SimulatedAction(
                level=level,
                second=current_second,
                action_type="CLOSE_VERIFY",
                description="Close verification panel"
            )
        
        elif isinstance(action, SameRowAction):
            cards_str = ", ".join(action.cards)
            return SimulatedAction(
                level=level,
                second=current_second,
                action_type="SAME_ROW",
                description=f"Deploy same row: {cards_str}",
                details={"cards": action.cards}
            )
        
        elif isinstance(action, CancelSameRowAction):
            return SimulatedAction(
                level=level,
                second=current_second,
                action_type="CANCEL_SAME_ROW",
                description="Cancel same row mode"
            )
        
        elif isinstance(action, ForceOrderAction):
            return SimulatedAction(
                level=level,
                second=current_second,
                action_type="FORCE_ORDER",
                description="Enable force order mode"
            )
        
        elif isinstance(action, VerifyDeployAction):
            desc = "Verify deploy"
            if action.max_only:
                desc += " (max level only)"
            if action.count:
                desc += f" x{action.count}"
            return SimulatedAction(
                level=level,
                second=current_second,
                action_type="VERIFY_DEPLOY",
                description=desc,
                details={"max_only": action.max_only, "count": action.count}
            )
        
        elif isinstance(action, DiscardPlayAction):
            return SimulatedAction(
                level=level,
                second=current_second,
                action_type="DISCARD_PLAY",
                description=f"Discard and play: {action.card}",
                details={"card": action.card}
            )
        
        elif isinstance(action, RawAction):
            return SimulatedAction(
                level=level,
                second=current_second,
                action_type="RAW",
                description=f"Unknown command: {action.content}",
                details={"content": action.content}
            )
        
        return None
    
    @staticmethod
    def _build_summary(script: Script, action_log: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build execution summary statistics."""
        levels_covered = set()
        action_types: Dict[str, int] = {}
        cards_used = set()
        
        for action in action_log:
            if action["level"] > 0:
                levels_covered.add(action["level"])
            
            atype = action["action_type"]
            action_types[atype] = action_types.get(atype, 0) + 1
            
            details = action.get("details", {})
            if "card" in details and details["card"]:
                cards_used.add(details["card"])
            if "cards" in details:
                cards_used.update(details["cards"])
        
        return {
            "script_name": script.metadata.name,
            "script_type": script.metadata.script_type,
            "total_actions": len(action_log),
            "levels_covered": sorted(list(levels_covered)),
            "level_count": len(levels_covered),
            "event_count": len(script.commands.event_commands),
            "action_type_counts": action_types,
            "cards_used": sorted(list(cards_used)),
            "deck": script.setup.deck
        }


class DryRunSimulator:
    """
    Live dry-run simulator with VehicleState, DeckState tracking and SSE broadcasts.
    
    This simulates realistic gameplay:
    - Simulates level progression from 1 to max_level (from script)
    - Vehicle position mechanics: initial positions 0 and 6, auto-upgrade to unlock more
    - Special card handling: 射线, 宝库, 潜艇, 火炮, 咬人娃娃 can only go to pos 6
    - Step-by-step card level progression (level 1 -> 2 -> 3 -> 4)
    - Priority-based deployment for forced order mode
    - Broadcasts all state changes via SSE for real-time UI updates
    """
    
    _event_service: Optional['EventService'] = None
    
    # Delay constants (in seconds)
    LEVEL_UP_DELAY = 0.2  # Delay between card level increments
    REFRESH_DELAY = 0.15  # Delay after each refresh
    UPGRADE_DELAY = 0.25  # Delay after vehicle upgrade
    
    # Time costs for simulation (in seconds)
    REFRESH_TIME_COST = 0.3  # Time cost per refresh in simulation
    DEPLOY_TIME_COST = 0.2   # Time cost per deploy in simulation
    LEVEL_DURATION = 1.0     # Each game level lasts 1 second
    @classmethod
    def set_event_service(cls, event_service: 'EventService') -> None:
        """Set the shared event service for broadcasting."""
        cls._event_service = event_service
    
    @classmethod
    async def run_dry_run(
        cls,
        content: str,
        name: str = "test.txt",
        script_type: str = "collab",
        session_id: str = "dry-run",
        action_delay_ms: int = 300,
        level_delay_ms: int = 500
    ) -> Dict[str, Any]:
        """
        Execute a live dry-run simulation with realistic level progression.
        
        Simulates the game level-by-level from 1 to max_level:
        - At each level, checks if script has commands
        - For deploy actions, searches hand and refreshes to find card
        - Auto-upgrades vehicle when positions are needed
        - Shows step-by-step card level progression
        - Tracks vehicle state, deck state, and broadcasts via SSE
        
        Args:
            content: Raw script content
            name: Script filename
            script_type: 'collab' or 'activity'
            session_id: SSE session ID for broadcasting
            action_delay_ms: Delay between actions (for visual effect)
            level_delay_ms: Delay between levels
        
        Returns:
            Dict with success status, action_log, vehicle_history, deck_stats, and summary
        """
        # Parse the script
        script, errors, warnings = ScriptParserService.parse_script(
            content=content,
            name=name,
            script_type=script_type
        )
        
        if script is None:
            return {
                "success": False,
                "action_log": [],
                "vehicle_history": [],
                "deck_stats": None,
                "errors": errors,
                "warnings": warnings,
                "summary": None
            }
        
        # Initialize vehicle state
        vehicle_state = VehicleState()
        action_log: List[Dict[str, Any]] = []
        vehicle_history: List[Dict[str, Any]] = []
        
        # Initialize deck state from script setup
        deck = script.setup.deck or []
        enhanced = script.setup.enhanced or []
        deck_state = DeckState(deck=deck, enhanced=enhanced) if deck else None
        
        # Build level -> commands lookup map
        level_commands_map: Dict[int, LevelCommand] = {}
        for level_cmd in script.commands.level_commands:
            level_commands_map[level_cmd.level] = level_cmd
        
        # Determine max level from script (highest level with commands)
        if level_commands_map:
            max_level = max(level_commands_map.keys())
        else:
            max_level = 1  # Default to at least 1 level
        
        # Track pending cards for forced order deployment
        pending_force_order_actions: List[DeployAction] = []
        
        # Broadcast initial state
        await cls._broadcast_log(f"开始模拟: 共 {max_level} 关", session_id)
        await cls._broadcast_log(f"🚗 载具初始位置: 0, 6 (位置6为特殊卡专用)", session_id)
        if deck_state:
            await cls._broadcast_deck(deck_state, session_id)
            await cls._broadcast_log(f"卡组: {', '.join(deck)}", session_id)
            await cls._broadcast_log(f"初始手牌: {', '.join(deck_state.get_hand())}", session_id)
        
        # Simulate level-by-level progression
        for level in range(1, max_level + 1):
            # Reset force order mode at the start of each level
            if vehicle_state.is_force_order():
                vehicle_state.set_force_order(False)
                pending_force_order_actions.clear()
            
            # Update vehicle state level
            vehicle_state.set_level(level)
            
            # Broadcast level change
            await cls._broadcast_vehicle(vehicle_state, session_id)
            await cls._broadcast_log(f"=== 第 {level} 关 ===", session_id)
            vehicle_history.append({
                "event": "level_change",
                "level": level,
                "state": vehicle_state.to_broadcast_dict()
            })
            
            # Check if this level has commands
            level_cmd = level_commands_map.get(level)
            
            if level_cmd:
                # Track current clock second for wait_until
                current_second: Optional[float] = None
                
                # Collect deploy actions for batch processing
                pending_deploy_actions: List[DeployAction] = []
                
                # Process actions at this level
                for action in level_cmd.actions:
                    # Handle wait_until (just update current_second, no actual wait)
                    if isinstance(action, WaitUntilAction):
                        current_second = action.second
                        action_log.append({
                            "level": level,
                            "second": current_second,
                            "action_type": "WAIT_UNTIL",
                            "description": f"Wait until clock second: {action.second}"
                        })
                        await cls._broadcast_log(f"[第{level}关 {current_second}秒] 等待时钟", session_id)
                        continue
                    
                    # Handle ForceOrderAction - enable force order mode
                    if isinstance(action, ForceOrderAction):
                        vehicle_state.set_force_order(True)
                        await cls._broadcast_log(f"[第{level}关] 📌 启用强制顺序模式", session_id)
                        await cls._broadcast_vehicle(vehicle_state, session_id)
                        action_log.append({
                            "level": level,
                            "second": current_second,
                            "action_type": "FORCE_ORDER",
                            "description": "启用强制顺序模式"
                        })
                        continue
                    
                    # Collect deploy actions for batch processing (both force and non-force mode)
                    if isinstance(action, DeployAction):
                        pending_deploy_actions.append(action)
                        continue
                    
                    # Execute non-deploy actions immediately
                    action_entry = await cls._execute_action(
                        action, vehicle_state, deck_state, level, current_second, session_id,
                        action_delay_ms
                    )
                    
                    if action_entry:
                        action_log.append(action_entry)
                        vehicle_history.append({
                            "event": "action",
                            "level": level,
                            "action": action_entry,
                            "state": vehicle_state.to_broadcast_dict(),
                            "deck_state": deck_state.to_broadcast_dict() if deck_state else None
                        })
                    
                    # Delay between actions
                    await asyncio.sleep(action_delay_ms / 1000.0)

                # Process pending deploy actions at end of level
                if pending_deploy_actions and deck_state:
                    if vehicle_state.is_force_order():
                        # Force order mode: use strict position order + priority leveling
                        await cls._broadcast_log(
                            f"🎯 强制顺序部署: {', '.join(a.card for a in pending_deploy_actions)}",
                            session_id
                        )
                        deploy_entries = await cls._execute_force_order_deploys(
                            pending_deploy_actions,
                            vehicle_state,
                            deck_state,
                            level,
                            current_second,
                            session_id,
                            action_delay_ms
                        )
                    else:
                        # Non-force mode: use priority-based deployment (no position order)
                        await cls._broadcast_log(
                            f"🎯 优先级部署: {', '.join(a.card for a in pending_deploy_actions)}",
                            session_id
                        )
                        deploy_entries = await cls._execute_priority_deploys(
                            pending_deploy_actions,
                            vehicle_state,
                            deck_state,
                            level,
                            current_second,
                            session_id,
                            action_delay_ms
                        )
                    
                    for entry in deploy_entries:
                        action_log.append(entry)
                        vehicle_history.append({
                            "event": "action",
                            "level": level,
                            "action": entry,
                            "state": vehicle_state.to_broadcast_dict(),
                            "deck_state": deck_state.to_broadcast_dict()
                        })
            
            # Delay between levels
            await asyncio.sleep(level_delay_ms / 1000.0)
        
        # Build summary with deck statistics
        summary = ScriptSimulatorService._build_summary(script, action_log)
        
        # Add deck statistics to summary
        deck_stats = None
        if deck_state:
            deck_stats = {
                "total_refreshes": deck_state.get_refresh_count(),
                "card_levels": {card: deck_state.get_card_level(card) for card in deck},
                "final_hand": deck_state.get_hand()
            }
            summary["deck_stats"] = deck_stats
        
        await cls._broadcast_log(f"模拟完成! 总刷新次数: {deck_state.get_refresh_count() if deck_state else 0}", session_id)
        
        return {
            "success": True,
            "action_log": action_log,
            "vehicle_history": vehicle_history,
            "deck_stats": deck_stats,
            "errors": errors,
            "warnings": warnings,
            "summary": summary
        }
    
    @classmethod
    async def _broadcast_vehicle(cls, vehicle_state: VehicleState, session_id: str) -> None:
        """Broadcast vehicle state via SSE."""
        if cls._event_service is None:
            logger.warning("[DryRunSimulator] No event service configured")
            return
        
        vehicle_data = vehicle_state.to_broadcast_dict()
        try:
            await cls._event_service.broadcast_vehicle(vehicle_data, [session_id])
            logger.debug(f"[DryRunSimulator] Broadcasted vehicle: {vehicle_data}")
        except Exception as e:
            logger.error(f"[DryRunSimulator] Broadcast failed: {e}")
    
    @classmethod
    async def _broadcast_deck(cls, deck_state: DeckState, session_id: str) -> None:
        """Broadcast deck state via SSE."""
        if cls._event_service is None:
            return
        
        deck_data = deck_state.to_broadcast_dict()
        try:
            # Use broadcast_log with deck info for now (can add dedicated deck broadcast later)
            hand_str = ', '.join(deck_state.get_hand())
            await cls._event_service.broadcast_log(
                "debug",
                f"[手牌] {hand_str} | 刷新次数: {deck_state.get_refresh_count()}",
                [session_id]
            )
            logger.debug(f"[DryRunSimulator] Broadcasted deck: {deck_data}")
        except Exception as e:
            logger.error(f"[DryRunSimulator] Deck broadcast failed: {e}")
    
    @classmethod
    async def _broadcast_log(cls, message: str, session_id: str, level: str = "info") -> None:
        """Broadcast log message via SSE."""
        if cls._event_service is None:
            return
        try:
            await cls._event_service.broadcast_log(level, message, [session_id])
        except Exception as e:
            logger.error(f"[DryRunSimulator] Log broadcast failed: {e}")
    
    @classmethod
    async def _upgrade_vehicle_if_needed(
        cls,
        vehicle_state: VehicleState,
        card: str,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Upgrade vehicle to unlock positions if needed for deploying a card.
        
        Returns list of upgrade action entries for the action log.
        """
        upgrade_entries = []
        
        # Special cards don't need normal position upgrades (they go to pos 6)
        if vehicle_state.is_special_card(card):
            return upgrade_entries
        
        # Keep upgrading until we have an available position
        while vehicle_state.needs_upgrade_for_deploy(card):
            next_pos = vehicle_state.get_next_unlock_position()
            if next_pos is None:
                break  # All positions unlocked
            
            # Unlock the position
            vehicle_state.unlock_position(next_pos)
            
            # Broadcast upgrade
            await cls._broadcast_log(
                f"🔓 载具升级: 解锁位置 {next_pos}",
                session_id
            )
            await cls._broadcast_vehicle(vehicle_state, session_id)
            
            upgrade_entries.append({
                "level": vehicle_state._current_level,
                "second": None,
                "action_type": "VEHICLE_UPGRADE",
                "description": f"载具升级: 解锁位置 {next_pos}",
                "details": {
                    "unlocked_position": next_pos,
                    "all_unlocked": sorted(list(vehicle_state.get_unlocked_positions()))
                }
            })
            
            # Small delay for visual effect
            await asyncio.sleep(cls.UPGRADE_DELAY)
        
        return upgrade_entries
    
    @classmethod
    async def _deploy_with_level_progression(
        cls,
        card: str,
        target_level: int,
        current_level_in_deck: int,
        vehicle_state: VehicleState,
        session_id: str
    ) -> None:
        """
        Deploy a card with step-by-step level progression.
        
        The card goes from current_level_in_deck to target_level, broadcasting each step.
        """
        # Deploy at current level first
        position = vehicle_state.deploy(card, current_level_in_deck)
        
        if position is None:
            await cls._broadcast_log(
                f"⚠️ 无法部署 {card}: 没有可用位置",
                session_id,
                "warning"
            )
            return position
        
        # Broadcast initial deployment
        await cls._broadcast_vehicle(vehicle_state, session_id)
        
        # If target level is higher, show level progression
        # Note: In real game, target_level from deck_state is the level AFTER this deploy
        # So we just show the current level (which is the latest deploy count)
        # The step-by-step is shown in the log
        
        return position
    
    @classmethod
    async def _execute_force_order_deploys(
        cls,
        pending_actions: List[DeployAction],
        vehicle_state: VehicleState,
        deck_state: DeckState,
        level: int,
        current_second: Optional[float],
        session_id: str,
        action_delay_ms: int
    ) -> List[Dict[str, Any]]:
        """
        Execute force order deployment in TWO PHASES:
        
        Phase 1 - Initial Deployment (STRICT ORDER for vehicle positions):
        - Cards must be deployed in EXACT order to get correct vehicle positions
        - 水灵 -> pos 0, 咕咕 -> pos 1, 圣骑 -> pos 2, etc.
        - Must wait/refresh for each specific card in sequence
        
        Phase 2 - Level Up (PRIORITY-BASED to minimize refresh cost):
        - Once all cards have initial positions, level them up to targets
        - Deploy ANY available card from hand that needs more levels
        - Use priority order when multiple cards are in hand
        """
        deploy_entries = []
        max_refreshes_total = 500  # Safety limit
        total_refresh_count = 0
        
        # Time tracking for simulation level
        simulation_time = 0.0  # Simulated time elapsed in seconds
        start_level = level  # Level when force order started
        
        def get_simulation_level() -> int:
            """Calculate current simulation level based on elapsed time."""
            return start_level + int(simulation_time / cls.LEVEL_DURATION)

        # Build card -> target level map, preserving priority order
        card_targets: Dict[str, int] = {}
        card_order: List[str] = []  # Strict order for initial deployment
        
        for action in pending_actions:
            card = action.card
            target = cls._parse_target_level(action.level, card, deck_state)
            max_level = deck_state._get_max_level(card)
            card_targets[card] = min(target, max_level)
            if card not in card_order:
                card_order.append(card)
        
        # Log initial targets
        targets_str = ', '.join(f"{c}->Lv.{card_targets[c]}" for c in card_order)
        await cls._broadcast_log(f"🎯 目标: {targets_str}", session_id)
        
        # ============================================================
        # PHASE 1: Initial deployment in STRICT ORDER (for positions)
        # With opportunistic level-ups during refreshes
        # ============================================================
        await cls._broadcast_log(f"📦 阶段1: 按顺序部署卡片到载具位置", session_id)
        
        # Helper to deploy a card and log it
        async def deploy_and_log(card_name: str, is_initial: bool) -> Optional[Dict[str, Any]]:
            """Deploy a card, update states, log, and return entry if target reached."""
            nonlocal simulation_time
            is_special = vehicle_state.is_special_card(card_name)
            sim_level = get_simulation_level()
            
            # Upgrade vehicle if needed (for initial deploy)
            if is_initial:
                upgrade_entries = await cls._upgrade_vehicle_if_needed(
                    vehicle_state, card_name, session_id
                )
                deploy_entries.extend(upgrade_entries)
            
            if deck_state.deploy_card(card_name):
                # Add deploy time cost
                simulation_time += cls.DEPLOY_TIME_COST
                sim_level = get_simulation_level()
                
                new_level = deck_state.get_card_level(card_name)
                position = vehicle_state.deploy(card_name, new_level)
                
                await cls._broadcast_vehicle(vehicle_state, session_id)
                await cls._broadcast_deck(deck_state, session_id)
                
                pos_info = f" -> 位置 {position}" if position is not None else ""
                special_info = " [特殊卡]" if is_special else ""
                action_type = "部署到" if is_initial else "升级到"
                
                await cls._broadcast_log(
                    f"[关{sim_level}] 🃏 {card_name} {action_type} Lv.{new_level}{special_info}{pos_info}",
                    session_id
                )
                
                if new_level >= card_targets[card_name]:
                    deploy_entries.append({
                        "level": sim_level, "second": current_second,
                        "action_type": "DEPLOY",
                        "description": f"部署完成: {card_name} Lv.{new_level}{special_info}{pos_info}",
                        "details": {
                            "card": card_name, "card_level": new_level,
                            "target_level": card_targets[card_name], "position": position,
                            "is_special": is_special, "force_order": True,
                            "simulation_level": sim_level
                        }
                    })
                    await cls._broadcast_log(f"[关{sim_level}] ✅ {card_name} 已达到目标 Lv.{new_level}", session_id)
                    return True  # Target reached
                
                await asyncio.sleep(cls.LEVEL_UP_DELAY)
                return False  # Deployed but not at target yet
            return None  # Deploy failed
        
        # Helper to find and deploy any already-deployed card that needs levels
        async def try_opportunistic_levelup() -> bool:
            """Deploy any already-deployed card in hand that needs more levels. Returns True if deployed."""
            for c in card_order:
                current_lvl = deck_state.get_card_level(c)
                # Card must be already deployed (level > 0) and need more levels
                if current_lvl > 0 and current_lvl < card_targets[c] and deck_state.is_card_in_hand(c):
                    await deploy_and_log(c, is_initial=False)
                    return True
            return False
        
        cards_needing_initial_deploy = [c for c in card_order if deck_state.get_card_level(c) == 0]
        
        for card in cards_needing_initial_deploy:
            # Wait for this specific card (strict order for positions)
            while not deck_state.is_card_in_hand(card):
                if total_refresh_count >= max_refreshes_total:
                    await cls._broadcast_log(
                        f"⚠️ 刷新上限, 无法找到 {card}",
                        session_id, "warning"
                    )
                    deploy_entries.append({
                        "level": level, "second": current_second,
                        "action_type": "DEPLOY",
                        "description": f"⚠️ 跳过: {card} (未找到)",
                        "details": {"card": card, "not_available": True, "force_order": True}
                    })
                    break
                
                # Add refresh time cost
                simulation_time += cls.REFRESH_TIME_COST
                sim_level = get_simulation_level()
                
                new_hand = deck_state.refresh()
                total_refresh_count += 1
                await cls._broadcast_log(
                    f"[关{sim_level}] 🔄 刷新第{total_refresh_count}次 (找{card}): [{', '.join(new_hand)}]",
                    session_id
                )
                await cls._broadcast_deck(deck_state, session_id)
                await asyncio.sleep(cls.REFRESH_DELAY)
                
                # Opportunistic level-up: deploy any already-deployed card that needs levels
                # Keep deploying until hand is empty or no more opportunistic deploys
                while await try_opportunistic_levelup():
                    # After deploying, hand is cleared, need to refresh again
                    if not deck_state.is_card_in_hand(card):
                        # Target card not in hand, refresh will happen in outer loop
                        break
            
            if not deck_state.is_card_in_hand(card):
                continue  # Card not found after max refreshes, skip to next
            
            # Deploy the card (initial deploy for position)
            await deploy_and_log(card, is_initial=True)
        
        # ============================================================
        # PHASE 2: Level up using PRIORITY (to minimize refresh cost)
        # ============================================================
        def get_cards_needing_levels() -> List[str]:
            """Get cards that need more levels, in priority order."""
            return [
                card for card in card_order
                if deck_state.get_card_level(card) < card_targets[card]
            ]
        
        def find_deployable_card(pending: List[str]) -> Optional[str]:
            """Find highest priority card from pending that is in hand."""
            for card in pending:
                if deck_state.is_card_in_hand(card):
                    return card
            return None
        
        pending = get_cards_needing_levels()
        if pending:
            await cls._broadcast_log(
                f"📦 阶段2: 升级卡片到目标等级 ({len(pending)}张待升级)",
                session_id
            )
        
        while True:
            pending = get_cards_needing_levels()
            if not pending:
                break  # All cards reached target levels
            
            if total_refresh_count >= max_refreshes_total:
                await cls._broadcast_log(
                    f"⚠️ 达到最大刷新次数 {max_refreshes_total}",
                    session_id, "warning"
                )
                for card in pending:
                    current_lvl = deck_state.get_card_level(card)
                    deploy_entries.append({
                        "level": level, "second": current_second,
                        "action_type": "DEPLOY",
                        "description": f"⚠️ 跳过: {card} Lv.{current_lvl}/{card_targets[card]}",
                        "details": {
                            "card": card, "card_level": current_lvl,
                            "target_level": card_targets[card],
                            "not_available": True, "force_order": True
                        }
                    })
                break
            
            # Find any deployable card from hand (priority-based)
            card_to_deploy = find_deployable_card(pending)
            
            if card_to_deploy is None:
                # No pending card in hand - refresh
                # Add refresh time cost
                simulation_time += cls.REFRESH_TIME_COST
                sim_level = get_simulation_level()
                
                new_hand = deck_state.refresh()
                total_refresh_count += 1
                await cls._broadcast_log(
                    f"[关{sim_level}] 🔄 刷新第{total_refresh_count}次: [{', '.join(new_hand)}]",
                    session_id
                )
                await cls._broadcast_deck(deck_state, session_id)
                await asyncio.sleep(cls.REFRESH_DELAY)
                continue
            
            # Deploy the card
            card = card_to_deploy
            target_level = card_targets[card]
            is_special = vehicle_state.is_special_card(card)
            
            if deck_state.deploy_card(card):
                # Add deploy time cost
                simulation_time += cls.DEPLOY_TIME_COST
                sim_level = get_simulation_level()
                
                new_level = deck_state.get_card_level(card)
                position = vehicle_state.deploy(card, new_level)
                
                await cls._broadcast_vehicle(vehicle_state, session_id)
                await cls._broadcast_deck(deck_state, session_id)
                
                pos_info = f" -> 位置 {position}" if position is not None else ""
                special_info = " [特殊卡]" if is_special else ""
                remaining = len(get_cards_needing_levels())
                
                await cls._broadcast_log(
                    f"[关{sim_level}] 🃏 {card} 升级到 Lv.{new_level}/{target_level}{special_info}{pos_info} (剩余{remaining}张)",
                    session_id
                )
                
                if new_level >= target_level:
                    deploy_entries.append({
                        "level": sim_level, "second": current_second,
                        "action_type": "DEPLOY",
                        "description": f"部署完成: {card} Lv.{new_level}{special_info}{pos_info}",
                        "details": {
                            "card": card, "card_level": new_level,
                            "target_level": target_level, "position": position,
                            "is_special": is_special, "force_order": True,
                            "simulation_level": sim_level
                        }
                    })
                    await cls._broadcast_log(f"[关{sim_level}] ✅ {card} 已达到目标 Lv.{new_level}", session_id)
                
                await asyncio.sleep(cls.LEVEL_UP_DELAY)
        
        # Final summary
        final_sim_level = get_simulation_level()
        await cls._broadcast_log(
            f"🎉 强制顺序部署完成, 总刷新{total_refresh_count}次, 模拟关卡{start_level}->{final_sim_level}",
            session_id
        )
        
        return deploy_entries
    
    @classmethod
    async def _execute_priority_deploys(
        cls,
        pending_actions: List[DeployAction],
        vehicle_state: VehicleState,
        deck_state: DeckState,
        level: int,
        current_second: Optional[float],
        session_id: str,
        action_delay_ms: int
    ) -> List[Dict[str, Any]]:
        """
        Execute deployment using PRIORITY-BASED logic (non-force-order mode).
        
        Unlike force order mode, there's no strict position order.
        Cards are deployed based on priority (order in script) and availability in hand.
        Deploy any available card that needs levels to minimize refresh cost.
        """
        deploy_entries = []
        max_refreshes_total = 500  # Safety limit
        total_refresh_count = 0
        
        # Time tracking for simulation level
        simulation_time = 0.0
        start_level = level
        
        def get_simulation_level() -> int:
            return start_level + int(simulation_time / cls.LEVEL_DURATION)
        
        # Build card -> target level map, preserving priority order
        card_targets: Dict[str, int] = {}
        card_order: List[str] = []  # Priority order
        
        for action in pending_actions:
            card = action.card
            target = cls._parse_target_level(action.level, card, deck_state)
            max_level = deck_state._get_max_level(card)
            card_targets[card] = min(target, max_level)
            if card not in card_order:
                card_order.append(card)
        
        # Log initial targets
        targets_str = ', '.join(f"{c}->Lv.{card_targets[c]}" for c in card_order)
        await cls._broadcast_log(f"🎯 目标: {targets_str}", session_id)
        
        def get_cards_needing_levels() -> List[str]:
            """Get cards that need more levels, in priority order."""
            return [
                card for card in card_order
                if deck_state.get_card_level(card) < card_targets[card]
            ]
        
        def find_deployable_card(pending: List[str]) -> Optional[str]:
            """Find highest priority card from pending that is in hand."""
            for card in pending:
                if deck_state.is_card_in_hand(card):
                    return card
            return None
        
        # Main deployment loop - priority-based
        while True:
            pending = get_cards_needing_levels()
            if not pending:
                break  # All cards reached target levels
            
            if total_refresh_count >= max_refreshes_total:
                sim_level = get_simulation_level()
                await cls._broadcast_log(
                    f"[关{sim_level}] ⚠️ 达到最大刷新次数 {max_refreshes_total}",
                    session_id, "warning"
                )
                for card in pending:
                    current_lvl = deck_state.get_card_level(card)
                    deploy_entries.append({
                        "level": sim_level, "second": current_second,
                        "action_type": "DEPLOY",
                        "description": f"⚠️ 跳过: {card} Lv.{current_lvl}/{card_targets[card]}",
                        "details": {
                            "card": card, "card_level": current_lvl,
                            "target_level": card_targets[card],
                            "not_available": True,
                            "simulation_level": sim_level
                        }
                    })
                break
            
            # Find any deployable card from hand (priority-based)
            card_to_deploy = find_deployable_card(pending)
            
            if card_to_deploy is None:
                # No pending card in hand - refresh
                simulation_time += cls.REFRESH_TIME_COST
                sim_level = get_simulation_level()
                
                new_hand = deck_state.refresh()
                total_refresh_count += 1
                await cls._broadcast_log(
                    f"[关{sim_level}] 🔄 刷新第{total_refresh_count}次: [{', '.join(new_hand)}]",
                    session_id
                )
                await cls._broadcast_deck(deck_state, session_id)
                await asyncio.sleep(cls.REFRESH_DELAY)
                continue
            
            # Deploy the card
            card = card_to_deploy
            target_level = card_targets[card]
            is_special = vehicle_state.is_special_card(card)
            current_card_level = deck_state.get_card_level(card)
            
            # Auto-upgrade vehicle if this is first deploy of the card
            if current_card_level == 0:
                upgrade_entries = await cls._upgrade_vehicle_if_needed(
                    vehicle_state, card, session_id
                )
                deploy_entries.extend(upgrade_entries)
            
            if deck_state.deploy_card(card):
                # Add deploy time cost
                simulation_time += cls.DEPLOY_TIME_COST
                sim_level = get_simulation_level()
                
                new_level = deck_state.get_card_level(card)
                position = vehicle_state.deploy(card, new_level)
                
                await cls._broadcast_vehicle(vehicle_state, session_id)
                await cls._broadcast_deck(deck_state, session_id)
                
                pos_info = f" -> 位置 {position}" if position is not None else ""
                special_info = " [特殊卡]" if is_special else ""
                remaining = len(get_cards_needing_levels())
                
                await cls._broadcast_log(
                    f"[关{sim_level}] 🃏 {card} 升级到 Lv.{new_level}/{target_level}{special_info}{pos_info} (剩余{remaining}张)",
                    session_id
                )
                
                if new_level >= target_level:
                    deploy_entries.append({
                        "level": sim_level, "second": current_second,
                        "action_type": "DEPLOY",
                        "description": f"部署完成: {card} Lv.{new_level}{special_info}{pos_info}",
                        "details": {
                            "card": card, "card_level": new_level,
                            "target_level": target_level, "position": position,
                            "is_special": is_special,
                            "simulation_level": sim_level
                        }
                    })
                    await cls._broadcast_log(f"[关{sim_level}] ✅ {card} 已达到目标 Lv.{new_level}", session_id)
                
                await asyncio.sleep(cls.LEVEL_UP_DELAY)
        
        # Final summary
        final_sim_level = get_simulation_level()
        await cls._broadcast_log(
            f"🎉 优先级部署完成, 总刷新{total_refresh_count}次, 模拟关卡{start_level}->{final_sim_level}",
            session_id
        )
        
        return deploy_entries

    @classmethod
    async def _execute_action(
        cls,
        action: Action,
        vehicle_state: VehicleState,
        deck_state: Optional[DeckState],
        level: int,
        current_second: Optional[float],
        session_id: str,
        action_delay_ms: int = 300
    ) -> Optional[Dict[str, Any]]:
        """Execute a single action, update vehicle/deck state, broadcast log, and return log entry."""
        result: Optional[Dict[str, Any]] = None
        
        if isinstance(action, DeployAction):
            result = await cls._execute_deploy(
                action, vehicle_state, deck_state, level, current_second, session_id
            )
        
        elif isinstance(action, RemoveAction):
            # Remove card from vehicle
            position = vehicle_state.remove(action.card)
            
            # Reset card's deploy count so it can be redeployed fresh
            if deck_state:
                deck_state.reset_card_level(action.card)
                await cls._broadcast_deck(deck_state, session_id)
            
            desc = f"移除卡牌: {action.card}" + (f" <- 位置 {position}" if position is not None else " (未找到)")
            
            # Broadcast updated state
            await cls._broadcast_vehicle(vehicle_state, session_id)

            result = {
                "level": level,
                "second": current_second,
                "action_type": "REMOVE",
                "description": desc,
                "details": {
                    "card": action.card,
                    "position": position
                }
            }
        
        elif isinstance(action, SwitchEquipmentAction):
            # Switch equipment
            vehicle_state.set_equipment(action.equipment)
            desc = f"切换装备: {action.equipment}"
            
            # Broadcast updated state
            await cls._broadcast_vehicle(vehicle_state, session_id)
            
            result = {
                "level": level,
                "second": current_second,
                "action_type": "SWITCH_EQUIPMENT",
                "description": desc,
                "details": {
                    "equipment": action.equipment
                }
            }
        
        elif isinstance(action, PrepareAction):
            desc = f"准备手牌: {action.card}"
            result = {
                "level": level,
                "second": current_second,
                "action_type": "PREPARE",
                "description": desc,
                "details": {"card": action.card}
            }
        
        elif isinstance(action, RepeatAction):
            desc = f"重复部署: {action.card} 每{action.interval}秒 x{action.count}"
            result = {
                "level": level,
                "second": current_second,
                "action_type": "REPEAT",
                "description": desc,
                "details": {
                    "card": action.card,
                    "interval": action.interval,
                    "count": action.count
                }
            }
        
        elif isinstance(action, DelayAction):
            desc = f"延迟: {action.milliseconds}ms"
            result = {
                "level": level,
                "second": current_second,
                "action_type": "DELAY",
                "description": desc,
                "details": {"milliseconds": action.milliseconds}
            }
        
        elif isinstance(action, StopBallAction):
            desc = "停止滚球"
            result = {
                "level": level,
                "second": current_second,
                "action_type": "STOP_BALL",
                "description": desc
            }
        
        elif isinstance(action, CloseVerifyAction):
            desc = "关闭验证面板"
            result = {
                "level": level,
                "second": current_second,
                "action_type": "CLOSE_VERIFY",
                "description": desc
            }
        
        elif isinstance(action, SameRowAction):
            # For same_row, deploy all cards
            positions = []
            for card in action.cards:
                # Try to find and deploy each card from deck
                if deck_state:
                    refresh_count = deck_state.find_card_with_refresh(card)
                    if refresh_count > 0:
                        await cls._broadcast_log(
                            f"搜索卡牌 {card}: 刷新 {refresh_count} 次",
                            session_id
                        )
                    if refresh_count >= 0:
                        deck_state.deploy_card(card)
                
                # Auto-upgrade vehicle if needed
                await cls._upgrade_vehicle_if_needed(vehicle_state, card, session_id)
                
                pos = vehicle_state.deploy(card, 1)  # Default level 1
                positions.append({"card": card, "position": pos})
            desc = f"同排部署: {', '.join(action.cards)}"
            
            # Broadcast updated state
            await cls._broadcast_vehicle(vehicle_state, session_id)
            if deck_state:
                await cls._broadcast_deck(deck_state, session_id)
            
            result = {
                "level": level,
                "second": current_second,
                "action_type": "SAME_ROW",
                "description": desc,
                "details": {
                    "cards": action.cards,
                    "positions": positions
                }
            }
        
        elif isinstance(action, CancelSameRowAction):
            desc = "取消同排模式"
            result = {
                "level": level,
                "second": current_second,
                "action_type": "CANCEL_SAME_ROW",
                "description": desc
            }
        
        elif isinstance(action, VerifyDeployAction):
            desc = "验卡补星"
            if action.max_only:
                desc += " (仅满级)"
            if action.count:
                desc += f" x{action.count}"
            result = {
                "level": level,
                "second": current_second,
                "action_type": "VERIFY_DEPLOY",
                "description": desc,
                "details": {"max_only": action.max_only, "count": action.count}
            }
        
        elif isinstance(action, DiscardPlayAction):
            desc = f"弃牌出牌: {action.card}"
            result = {
                "level": level,
                "second": current_second,
                "action_type": "DISCARD_PLAY",
                "description": desc,
                "details": {"card": action.card}
            }
        
        elif isinstance(action, RawAction):
            desc = f"未知命令: {action.content}"
            result = {
                "level": level,
                "second": current_second,
                "action_type": "RAW",
                "description": desc,
                "details": {"content": action.content}
            }
        
        # Broadcast log for all actions
        if result:
            log_msg = f"[第{level}关" + (f" {current_second}秒" if current_second else "") + f"] {result['description']}"
            await cls._broadcast_log(log_msg, session_id)
        
        return result
    
    @classmethod
    async def _execute_deploy(
        cls,
        action: DeployAction,
        vehicle_state: VehicleState,
        deck_state: Optional[DeckState],
        level: int,
        current_second: Optional[float],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Execute deploy action with full mechanics:
        1. Parse target level from action.level (e.g., '满' = max, '3级' = 3)
        2. Auto-upgrade vehicle if position needed
        3. Deploy card MULTIPLE times until target level reached
        4. Broadcast each level increment to UI
        """
        card = action.card
        total_refresh_count = 0
        card_not_available = False
        is_special = vehicle_state.is_special_card(card)
        deploy_log_entries = []  # Collect all deploy steps
        
        if not deck_state:
            # No deck state - just deploy once with given level
            position = vehicle_state.deploy(card, 1)
            await cls._broadcast_vehicle(vehicle_state, session_id)
            return {
                "level": level,
                "second": current_second,
                "action_type": "DEPLOY",
                "description": f"部署卡牌: {card} -> 位置 {position}",
                "details": {
                    "card": card,
                    "card_level": 1,
                    "position": position,
                    "is_special": is_special,
                    "refresh_count": 0,
                    "not_available": False
                }
            }
        
        # Parse target level from action.level
        target_level = cls._parse_target_level(action.level, card, deck_state)
        current_card_level = deck_state.get_card_level(card)
        
        await cls._broadcast_log(
            f"🎯 目标: {card} -> Lv.{target_level} (当前 Lv.{current_card_level})",
            session_id
        )
        
        # Check if card is already at or beyond target level
        if current_card_level >= target_level:
            await cls._broadcast_log(
                f"✅ {card} 已达到目标等级 Lv.{current_card_level}",
                session_id
            )
            return {
                "level": level,
                "second": current_second,
                "action_type": "DEPLOY",
                "description": f"✅ {card} 已达到目标等级 Lv.{current_card_level}",
                "details": {
                    "card": card,
                    "card_level": current_card_level,
                    "position": vehicle_state._card_positions.get(card),
                    "is_special": is_special,
                    "refresh_count": 0,
                    "not_available": False
                }
            }
        
        # Step 0: Auto-upgrade vehicle if needed (only once at start)
        upgrade_entries = await cls._upgrade_vehicle_if_needed(
            vehicle_state, card, session_id
        )
        
        # Deploy card MULTIPLE times until target level reached
        final_position = None
        while current_card_level < target_level:
            # Step 1: Find card in hand (refresh if not there)
            if not deck_state.is_card_in_hand(card):
                # Need to refresh to find the card
                found = False
                for i in range(100):  # Max 100 refreshes per search
                    new_hand = deck_state.refresh()
                    total_refresh_count += 1
                    
                    await cls._broadcast_log(
                        f"🔄 刷新第{total_refresh_count}次: [{', '.join(new_hand)}]",
                        session_id
                    )
                    await cls._broadcast_deck(deck_state, session_id)
                    await asyncio.sleep(cls.REFRESH_DELAY)
                    
                    if deck_state.is_card_in_hand(card):
                        found = True
                        break
                
                if not found:
                    # Couldn't find card after many refreshes
                    card_not_available = True
                    await cls._broadcast_log(
                        f"⚠️ 刷新100次后仍未找到: {card}",
                        session_id,
                        "warning"
                    )
                    break
            
            # Step 2: Deploy from hand
            if deck_state.deploy_card(card):
                current_card_level = deck_state.get_card_level(card)
                
                # Step 3: Update vehicle state
                final_position = vehicle_state.deploy(card, current_card_level)
                
                # Broadcast the level-up
                await cls._broadcast_vehicle(vehicle_state, session_id)
                await cls._broadcast_deck(deck_state, session_id)
                
                pos_info = f" -> 位置 {final_position}" if final_position is not None else ""
                special_info = " [特殊卡]" if is_special else ""
                
                await cls._broadcast_log(
                    f"🃏 {card} 升级到 Lv.{current_card_level}/{target_level}{special_info}{pos_info}",
                    session_id
                )
                
                # Small delay for visual effect between level-ups
                await asyncio.sleep(cls.LEVEL_UP_DELAY)
            else:
                # Card deploy failed (shouldn't happen if in hand, but safety check)
                await cls._broadcast_log(
                    f"⚠️ 部署失败: {card}",
                    session_id,
                    "warning"
                )
                break
        
        # Build final result
        if card_not_available:
            desc = f"⚠️ 跳过部署: {card} (不可用)"
        elif current_card_level >= target_level:
            special_info = " [特殊卡]" if is_special else ""
            desc = f"部署完成: {card} Lv.{current_card_level}{special_info} -> 位置 {final_position} (刷新{total_refresh_count}次)"
        else:
            desc = f"部分部署: {card} Lv.{current_card_level}/{target_level}"
        
        return {
            "level": level,
            "second": current_second,
            "action_type": "DEPLOY",
            "description": desc,
            "details": {
                "card": card,
                "card_level": current_card_level,
                "target_level": target_level,
                "position": final_position,
                "is_special": is_special,
                "refresh_count": total_refresh_count,
                "not_available": card_not_available
            }
        }
    
    @classmethod
    def _parse_target_level(
        cls,
        level_str: Optional[str],
        card: str,
        deck_state: DeckState
    ) -> int:
        """
        Parse target level from action.level string.
        
        Supported formats:
        - None or '满' -> max level (4 or 5 for enhanced)
        - '不满' -> max level - 1
        - 'N级' or 'N' -> level N
        """
        max_level = deck_state._get_max_level(card)
        
        # None (no level specified) means 'at least level 1' - deploy once
        if level_str is None:
            return 1
        
        # '满' means max level (4 normally, 5 for enhanced/魔化 cards)
        if level_str == '满':
            return max_level
        
        # '不满' means max level - 1
            return max(1, max_level - 1)
        
        # Try to parse numeric level like '3级' or '3'
        import re
        match = re.match(r'(\d+)', level_str)
        if match:
            parsed_level = int(match.group(1))
            return min(parsed_level, max_level)  # Cap at max level
        
        # Default to max level if can't parse
        return max_level
