from enum import Enum

class CommandType(Enum):
    # Basic command types
    CARD_OPERATION = "card_op"
    TIMING = "timing"
    SPECIAL_EVENT = "special"
    FORMATION = "formation"
    EQUIPMENT = "equipment"

class CardOperation(Enum):
    DEPLOY = "上"  # Deploy card
    WITHDRAW = "下"  # Withdraw card
    SWITCH = "换"  # Switch equipment
    PREPARE = "预备手牌"  # Prepare card
    FORCE_DEPLOY = "强制补星"  # Force deploy
    CHECK_DEPLOY = "验卡补星"  # Check and deploy
    DISCARD_DEPLOY = "弃牌出牌"  # Discard and deploy

class TimingPattern(Enum):
    INTERVAL = "每"  # Interval timing (e.g., every X seconds)
    FIXED = "时钟秒"  # Fixed timing (e.g., at second X)
    DELAY = "延时"  # Delay timing
    AFTER = "过后"  # After previous action

class FormationType(Enum):
    SAME_ROW = "同排"  # Same row deployment
    ORDERED = "强制顺序上卡"  # Forced order deployment

class CardLevel(Enum):
    MAX = "满"  # Maximum level
    SPECIFIC = "级"  # Specific level
    NOT_MAX = "不满"  # Not maximum level

class SpecialEventType(Enum):
    STOP_BALL = "停球"  # Stop ball
    CLOSE_VERIFY = "关闭验光"  # Close verification
    VERIFY_CARD = "验卡"  # Verify card