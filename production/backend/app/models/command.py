from typing import Dict, List, Optional
from dataclasses import dataclass
from app.enums.command_types import (
    CommandType, CardOperation, TimingPattern,
    FormationType, CardLevel, SpecialEventType
)

@dataclass
class TimingCommand:
    pattern: str  # INTERVAL, FIXED, DELAY
    interval: Optional[int] = None  # For INTERVAL pattern
    count: Optional[int] = None  # For INTERVAL pattern
    target: Optional[str] = None  # For INTERVAL pattern
    second: Optional[int] = None  # For FIXED pattern
    delay: Optional[int] = None  # For DELAY pattern

@dataclass
class CardCommand:
    operation: str  # DEPLOY, WITHDRAW, SWITCH, etc.
    card: str
    level: Optional[str] = None  # MAX, SPECIFIC, NOT_MAX

@dataclass
class FormationCommand:
    formation_type: str  # SAME_ROW, ORDERED

@dataclass
class SpecialEventCommand:
    event_type: str
    commands: List[Dict]  # List of follow-up commands

@dataclass
class CommandChain:
    index: int
    commands: List[Dict]  # List of commands in sequence

@dataclass
class ScriptData:
    formation: List[str]  # Initial formation
    enhanced_cards: List[str]  # Enhanced/powered up cards
    main_vehicle: Optional[str]  # Main vehicle
    sub_vehicle: Optional[str]  # Sub vehicle
    command_chain: List[CommandChain]  # Ordered list of commands
    special_events: List[SpecialEventCommand]  # Special event handlers