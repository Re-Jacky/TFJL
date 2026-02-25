"""
Script Simulator Service - Dry-run script execution without a game window.

This module simulates script execution by walking through all level/event 
commands and logging what actions would be performed, without actually
interacting with any window or game.
"""

from typing import List, Dict, Any, Optional
from app.models.script_models import (
    Script, LevelCommand, EventCommand, Action, ActionType,
    DeployAction, RemoveAction, PrepareAction, SwitchEquipmentAction,
    WaitUntilAction, RepeatAction, DelayAction, StopBallAction,
    CloseVerifyAction, SameRowAction, CancelSameRowAction,
    ForceOrderAction, VerifyDeployAction, DiscardPlayAction, RawAction,
)
from app.services.script_parser import ScriptParserService
from app.utils.logger import logger


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
