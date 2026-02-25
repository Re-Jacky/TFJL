"""
Script Models - Pydantic models for the script automation system.

This module defines the data structures for:
- Script metadata and setup configuration
- Individual action commands (deploy, remove, timing, etc.)
- Level-based and event-based command groups
- Script execution state
"""

from typing import List, Optional, Union, Literal, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# ENUMS - Command Types and Levels
# ============================================================================

class ActionType(str, Enum):
    """All supported action types in the script DSL."""
    # Card Operations
    DEPLOY = "deploy"                    # 上{card}{level?}
    REMOVE = "remove"                    # 下{card}
    PREPARE = "prepare"                  # 预备手牌{card}
    
    # Equipment
    SWITCH_EQUIPMENT = "switch_equipment"  # 换{equip}
    
    # Timing
    WAIT_UNTIL = "wait_until"            # 时钟秒{n}
    REPEAT = "repeat"                    # 每{n}秒共{m}次{card}
    DELAY = "delay"                      # 延时{n}毫秒
    
    # Control
    STOP_BALL = "stop_ball"              # 停球
    CLOSE_VERIFY = "close_verify"        # 关闭验光
    
    # Formation
    SAME_ROW = "same_row"                # {card1}{card2}同排
    CANCEL_SAME_ROW = "cancel_same_row"  # 同排取消
    FORCE_ORDER = "force_order"          # 强制顺序上卡
    
    # Special
    VERIFY_DEPLOY = "verify_deploy"      # 验卡补星
    DISCARD_PLAY = "discard_play"        # 弃牌出牌{card}
    
    # Sequence
    AFTER = "after"                      # 过后 (marks next action as dependent)
    
    # Raw/Unknown
    RAW = "raw"                          # Unparsed command


class CardLevel(str, Enum):
    """Card level specifications."""
    MAX = "满"           # Maximum level
    NOT_MAX = "不满"     # Not maximum level
    LEVEL_1 = "1级"
    LEVEL_2 = "2级"
    LEVEL_3 = "3级"
    LEVEL_4 = "4级"
    LEVEL_5 = "5级"
    LEVEL_6 = "6级"
    LEVEL_7 = "7级"
    LEVEL_8 = "8级"
    LEVEL_9 = "9级"
    NONE = None          # No level specified


class ExecutionState(str, Enum):
    """Script execution states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


# ============================================================================
# ACTION MODELS - Individual commands
# ============================================================================

class BaseAction(BaseModel):
    """Base class for all actions."""
    type: ActionType
    after_previous: bool = False  # If True, execute after previous action completes


class DeployAction(BaseAction):
    """Deploy a card to the battlefield. 上{card}{level?}"""
    type: Literal[ActionType.DEPLOY] = ActionType.DEPLOY
    card: str
    level: Optional[str] = None  # 满, 不满, 3级, etc.


class RemoveAction(BaseAction):
    """Remove a card from the battlefield. 下{card}"""
    type: Literal[ActionType.REMOVE] = ActionType.REMOVE
    card: str


class PrepareAction(BaseAction):
    """Prepare a card in hand. 预备手牌{card}"""
    type: Literal[ActionType.PREPARE] = ActionType.PREPARE
    card: str


class SwitchEquipmentAction(BaseAction):
    """Switch equipment. 换{equip}"""
    type: Literal[ActionType.SWITCH_EQUIPMENT] = ActionType.SWITCH_EQUIPMENT
    equipment: str  # 龙心, 烟斗, 强袭, etc.


class WaitUntilAction(BaseAction):
    """Wait until a specific second in the current level. 时钟秒{n}"""
    type: Literal[ActionType.WAIT_UNTIL] = ActionType.WAIT_UNTIL
    second: float  # Supports decimals like 2.5


class RepeatAction(BaseAction):
    """Repeat an action multiple times. 每{n}秒共{m}次{card}"""
    type: Literal[ActionType.REPEAT] = ActionType.REPEAT
    interval: float  # Seconds between each action
    count: int       # Number of times to repeat
    card: str        # Card to use


class DelayAction(BaseAction):
    """Delay for specified milliseconds. 延时{n}毫秒"""
    type: Literal[ActionType.DELAY] = ActionType.DELAY
    milliseconds: int


class StopBallAction(BaseAction):
    """Stop the ball. 停球"""
    type: Literal[ActionType.STOP_BALL] = ActionType.STOP_BALL


class CloseVerifyAction(BaseAction):
    """Close verification. 关闭验光"""
    type: Literal[ActionType.CLOSE_VERIFY] = ActionType.CLOSE_VERIFY


class SameRowAction(BaseAction):
    """Deploy two cards in the same row. {card1}{card2}同排"""
    type: Literal[ActionType.SAME_ROW] = ActionType.SAME_ROW
    cards: List[str]  # Two cards to deploy in same row


class CancelSameRowAction(BaseAction):
    """Cancel same row deployment mode. 同排取消"""
    type: Literal[ActionType.CANCEL_SAME_ROW] = ActionType.CANCEL_SAME_ROW


class ForceOrderAction(BaseAction):
    """Force ordered card deployment. 强制顺序上卡"""
    type: Literal[ActionType.FORCE_ORDER] = ActionType.FORCE_ORDER


class VerifyDeployAction(BaseAction):
    """Verify and deploy cards. 验卡补星"""
    type: Literal[ActionType.VERIFY_DEPLOY] = ActionType.VERIFY_DEPLOY
    max_only: bool = False  # 验卡补星仅满级
    count: Optional[int] = None  # 验卡补星仅满级100次


class DiscardPlayAction(BaseAction):
    """Discard and play a card. 弃牌出牌{card}"""
    type: Literal[ActionType.DISCARD_PLAY] = ActionType.DISCARD_PLAY
    card: str


class RawAction(BaseAction):
    """Raw/unparsed action for unknown commands."""
    type: Literal[ActionType.RAW] = ActionType.RAW
    content: str


# Union type for all actions
Action = Union[
    DeployAction,
    RemoveAction,
    PrepareAction,
    SwitchEquipmentAction,
    WaitUntilAction,
    RepeatAction,
    DelayAction,
    StopBallAction,
    CloseVerifyAction,
    SameRowAction,
    CancelSameRowAction,
    ForceOrderAction,
    VerifyDeployAction,
    DiscardPlayAction,
    RawAction,
]


# ============================================================================
# COMMAND GROUP MODELS - Level and Event based
# ============================================================================

class LevelCommand(BaseModel):
    """Commands to execute at a specific game level."""
    level: int = Field(..., ge=1, le=999, description="Game level (1-999)")
    actions: List[Action] = Field(default_factory=list)
    
    @field_validator('level')
    @classmethod
    def validate_level(cls, v: int) -> int:
        if v < 1 or v > 999:
            raise ValueError(f"Level must be between 1 and 999, got {v}")
        return v


class EventCommand(BaseModel):
    """Commands to execute when an event is detected."""
    event: str = Field(..., description="Event trigger name (e.g., '寒冰雷神红球')")
    actions: List[Action] = Field(default_factory=list)
    card_filter: Optional[List[str]] = None  # For events like "暗月地精不吃,A,K,2,Q"
    point_total: Optional[int] = None  # For events like "牌点总数50点"


# ============================================================================
# SCRIPT STRUCTURE MODELS
# ============================================================================

class ScriptSetup(BaseModel):
    """Script header/setup configuration."""
    deck: List[str] = Field(default_factory=list, description="Cards in deck (上阵)")
    skins: List[str] = Field(default_factory=list, description="Card skins (皮肤)")
    enhanced: List[str] = Field(default_factory=list, description="Enhanced cards (魔化)")
    main_vehicle: Optional[str] = Field(None, description="Main vehicle (主战车)")
    sub_vehicle: Optional[str] = Field(None, description="Sub vehicle (副战车)")


class ScriptCommands(BaseModel):
    """Script command sections."""
    level_commands: List[LevelCommand] = Field(
        default_factory=list,
        description="Commands triggered by game level"
    )
    event_commands: List[EventCommand] = Field(
        default_factory=list,
        description="Commands triggered by game events"
    )


class ScriptMetadata(BaseModel):
    """Script metadata."""
    name: str = Field(..., description="Script filename")
    script_type: Literal['collab', 'activity'] = Field(
        'collab',
        description="Script type (collab or activity)"
    )
    version: str = Field("1.0", description="Script format version")
    description: Optional[str] = None


class Script(BaseModel):
    """Complete script structure."""
    metadata: ScriptMetadata
    setup: ScriptSetup
    commands: ScriptCommands
    
    def get_level_command(self, level: int) -> Optional[LevelCommand]:
        """Get commands for a specific level."""
        for cmd in self.commands.level_commands:
            if cmd.level == level:
                return cmd
        return None
    
    def get_event_command(self, event: str) -> Optional[EventCommand]:
        """Get commands for a specific event."""
        for cmd in self.commands.event_commands:
            if cmd.event == event:
                return cmd
        return None


# ============================================================================
# EXECUTION STATE MODELS
# ============================================================================

class ScriptExecutionStatus(BaseModel):
    """Current execution status of a script."""
    state: ExecutionState = ExecutionState.IDLE
    current_level: int = 0
    current_second: float = 0.0
    last_executed_level: Optional[int] = None
    last_event: Optional[str] = None
    error_message: Optional[str] = None
    actions_executed: int = 0
    start_time: Optional[float] = None  # Unix timestamp


class ScriptExecutionRequest(BaseModel):
    """Request to start/control script execution."""
    script_name: str
    script_type: Literal['collab', 'activity'] = 'collab'
    window_pid: int
    action: Literal['start', 'pause', 'resume', 'stop']


class ScriptExecutionResponse(BaseModel):
    """Response from execution control."""
    success: bool
    message: str
    status: Optional[ScriptExecutionStatus] = None


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================

class ParseScriptRequest(BaseModel):
    """Request to parse a script file."""
    content: str
    name: str = "untitled"
    script_type: Literal['collab', 'activity'] = 'collab'


class ParseScriptResponse(BaseModel):
    """Response from script parsing."""
    success: bool
    script: Optional[Script] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ValidateScriptRequest(BaseModel):
    """Request to validate a script."""
    content: str


class ValidateScriptResponse(BaseModel):
    """Response from script validation."""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class TestScriptRequest(BaseModel):
    """Request to test/simulate script execution."""
    content: str
    name: str = "test.txt"
    script_type: Literal['collab', 'activity'] = 'collab'
    dry_run: bool = False  # If True, use live dry-run with SSE broadcasting
    session_id: str = "dry-run"  # SSE session ID for dry-run mode
    action_delay_ms: int = 300  # Delay between actions (ms)
    level_delay_ms: int = 500  # Delay between levels (ms)

class SimulatedActionLog(BaseModel):
    """A single simulated action entry."""
    level: int
    second: Optional[float] = None
    action_type: str
    description: str
    details: Dict[str, Any] = Field(default_factory=dict)


class TestScriptSummary(BaseModel):
    """Summary statistics from test execution."""
    script_name: str
    script_type: str
    total_actions: int
    levels_covered: List[int]
    level_count: int
    event_count: int
    action_type_counts: Dict[str, int]
    cards_used: List[str]
    deck: List[str]


class TestScriptResponse(BaseModel):
    """Response from script test/simulation."""
    success: bool
    action_log: List[SimulatedActionLog] = Field(default_factory=list)
    vehicle_history: List[Dict[str, Any]] = Field(default_factory=list)  # For dry-run mode
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    summary: Optional[TestScriptSummary] = None
