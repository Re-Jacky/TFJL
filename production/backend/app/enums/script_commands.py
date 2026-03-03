"""
Script Commands - Enum definitions for script command parsing.

This module defines:
- Command patterns for regex matching
- Known event triggers for different game modes
- Equipment names
- Card names (common ones)
"""

from enum import Enum
from typing import Dict, List, Set
import json
from pathlib import Path


class CommandPattern(Enum):
    """
    Regex patterns for parsing script commands.
    Patterns use named groups for extraction.
    """
    # Card Operations
    DEPLOY = r'^上(?P<card>.+?)(?P<level>满|不满|\d+级)?$'
    REMOVE = r'^下(?P<card>.+)$'
    PREPARE = r'^预备手牌(?P<card>.+)$'
    
    # Equipment
    SWITCH_EQUIPMENT = r'^换(?P<equipment>.+)$'
    
    # Timing
    WAIT_UNTIL = r'^时钟秒(?P<second>[\d.]+)$'
    REPEAT = r'^每(?P<interval>[\d.]+)秒共(?P<count>\d+)次(?P<card>.+)$'
    DELAY = r'^延时(?P<ms>\d+)毫秒$'
    
    # Formation
    SAME_ROW = r'^(?P<card1>.+?)(?P<card2>.+?)同排$'
    CANCEL_SAME_ROW = r'^同排取消$'
    FORCE_ORDER = r'^强制顺序上卡$'
    
    # Control
    STOP_BALL = r'^停球$'
    CLOSE_VERIFY = r'^关闭验光$'
    
    # Special
    VERIFY_DEPLOY = r'^验卡补星(?:仅满级)?(?P<count>\d+次)?$'
    DISCARD_PLAY = r'^弃牌出牌(?P<card>.+)$'
    
    # Sequence marker
    AFTER = r'^过后$'


class HeaderPattern(Enum):
    """Regex patterns for parsing script header lines."""
    DECK = r'^上阵[：:](.+)$'
    SKINS = r'^皮肤[：:](.*)$'
    ENHANCED = r'^魔化[：:](.+)$'
    MAIN_VEHICLE = r'^主战车[：:](.+)$'
    SUB_VEHICLE = r'^副战车[：:](.+)$'


class Equipment(Enum):
    """Known equipment names."""
    DRAGON_HEART = "龙心"
    PIPE = "烟斗"
    ASSAULT = "强袭"
    # Add more as needed


class GameMode(Enum):
    """Game modes that support different event sets."""
    ICE_CASTLE = "寒冰"      # 寒冰堡
    DARK_MOON = "暗月"       # 暗月岛
    VORTEX = "旋涡"          # 旋涡
    COLLAB = "合作"          # 合作


# ============================================================================
# EVENT TRIGGERS - Known events for image recognition
# ============================================================================

# Ice Castle (寒冰) Events
ICE_CASTLE_EVENTS: Set[str] = {
    # 雷神 (Thor) events
    "寒冰雷神无球",
    "寒冰雷神红球",
    "寒冰雷神蓝球",
    "寒冰雷神6球完",
    
    # 邪暗精灵 events
    "寒冰邪暗精灵",
    "寒冰邪暗精灵结束",
    
    # 泰坦 (Titan) events - Phase 1
    "寒冰泰坦阶段一准备",
    "寒冰泰坦阶段一大黑洞",
    "寒冰泰坦阶段一大白洞",
    
    # 泰坦 Phase 3
    "寒冰泰坦阶段三准备",
    "寒冰泰坦阶段三黑洞",
    "寒冰泰坦阶段三大黑洞",
    "寒冰泰坦阶段三大白洞",
    
    # 泰坦 Phase 5
    "寒冰泰坦阶段五准备",
    "寒冰泰坦阶段五黑洞",
    "寒冰泰坦阶段五大黑洞",
    "寒冰泰坦阶段五大白洞",
    
    # 泰坦 Phase 6
    "寒冰泰坦阶段六准备",
    "寒冰泰坦阶段六坍塌",
}

# Dark Moon (暗月) Events
DARK_MOON_EVENTS: Set[str] = {
    # Common triggers
    "装甲狼蛛",
    "暗月财阀",
    
    # 雷神 events
    "暗月雷神1号球同色",
    "暗月雷神1号球不同色",
    "暗月雷神2号球同色",
    "暗月雷神2号球不同色",
    
    # 小丑 (Clown) events
    "暗月小丑出无敌",
    "暗月小丑回满血",
    
    # 猫咪 events
    "暗月猫咪留牌",
    "暗月猫咪吃牌",
    
    # 地精 events
    "暗月地精留牌",
    "暗月地精吃牌",
    "暗月地精不吃",
    "暗月地精顺子",
    
    # 财阀 events
    "暗月财阀留牌",
    "暗月财阀吃牌",
    "暗月财阀完成",
    
    # 天使 events
    "暗月天使技能准备",
    "暗月天使技能开始",
    "暗月天使技能结束",
    
    # 火灵 events
    "暗月火灵技能准备",
    "暗月火灵技能开始",
    
    # 水灵 events (by day)
    "暗月水灵初一",
    "暗月水灵初二",
    "暗月水灵初三",
    "暗月水灵初四",
    "暗月水灵初五",
    "暗月水灵初六",
    "暗月水灵初七",
    "暗月水灵初八",
    "暗月水灵初九",
    
    # 风灵 events
    "暗月风灵初次下卡",
    "暗月风灵每两次攻击上卡",
    "暗月风灵每两次攻击下卡",
    "暗月风灵左车龙卷风初现",
    "暗月风灵左车龙卷风在右",
    "暗月风灵左车龙卷风在左",
    "暗月风灵右车龙卷风初现",
    "暗月风灵右车龙卷风在右",
    "暗月风灵右车龙卷风在左",
    
    # 土灵 events
    "暗月土灵打符",
    "暗月土灵留符",
    "暗月土灵二阶段",
    "暗月土灵三符",
    "暗月土灵三符转二阶段",
    
    # 噬魂 events
    "暗月噬魂预知符文",
    "暗月噬魂准备",
    "暗月噬魂左车控紫风",
    "暗月噬魂左车控黄风",
    "暗月噬魂二阶段开始",
    "暗月噬魂二阶段火灵准备",
    "暗月噬魂二阶段月圆准备",
    "暗月噬魂二阶段符文准备",
    "暗月噬魂火灵喷火开始",
    "暗月噬魂火灵喷火结束",
    "暗月噬魂天使喷火开始",
    "暗月噬魂天使喷火结束",
    "暗月噬魂初三",
    "暗月噬魂初五",
    "暗月噬魂初六",
    "暗月噬魂初七",
    "暗月噬魂初八",
    "暗月噬魂初九",
    "暗月噬魂初十",
    "暗月噬魂十一",
    "暗月噬魂十二",
    "暗月噬魂十三",
    "暗月噬魂十四",
    "暗月噬魂紫刃",
    "暗月噬魂打符",
    "暗月噬魂留符",
    "暗月噬魂留符最多个数",
    
    # 大圣 events
    "暗月大圣蓄力",
    
    # 哪吒 events
    "暗月哪吒第2球灵",
    "暗月哪吒第9球魔",
    
    # 魔化猫咪 events
    "暗月魔化猫咪准备",
    "暗月魔化猫咪不吃",
    "暗月魔化猫咪顺子",
    "暗月魔化猫咪攻击",
    "暗月魔化猫咪留牌1",
    "暗月魔化猫咪留牌2",
    "暗月魔化猫咪留牌3",
    "暗月魔化猫咪留牌4",
    "暗月魔化猫咪留牌5",
    "暗月魔化猫咪留牌6",
    "暗月魔化猫咪留牌7",
    "暗月魔化猫咪留牌王",
    
    # 魔化财阀 events
    "暗月魔化财阀准备",
    "暗月魔化财阀拿牌",
    "暗月魔化财阀过牌",
    "暗月魔化财阀初始牌点1",
    "暗月魔化财阀初始牌点K",
}

# All known events combined
ALL_KNOWN_EVENTS: Set[str] = ICE_CASTLE_EVENTS | DARK_MOON_EVENTS


def get_game_mode_from_event(event: str) -> GameMode:
    """Determine game mode from event name."""
    if event.startswith("寒冰"):
        return GameMode.ICE_CASTLE
    elif event.startswith("暗月"):
        return GameMode.DARK_MOON
    elif event.startswith("旋涡"):
        return GameMode.VORTEX
    return GameMode.COLLAB


def is_known_event(event: str) -> bool:
    """Check if an event is in the known events list."""
    return event in ALL_KNOWN_EVENTS


def get_events_for_mode(mode: GameMode) -> Set[str]:
    """Get all known events for a specific game mode."""
    if mode == GameMode.ICE_CASTLE:
        return ICE_CASTLE_EVENTS
    elif mode == GameMode.DARK_MOON:
        return DARK_MOON_EVENTS
    return set()


# ============================================================================
# CARD NAMES - Common cards referenced in scripts
# ============================================================================

def _load_card_names() -> Set[str]:
    """
    Load card names from public/card_names.json.
    Raises FileNotFoundError if file not found or JSONDecodeError if invalid.
    """
    # Try to find public folder (works from backend/ or production/)
    public_path = Path(__file__).parent.parent.parent.parent / 'public' / 'card_names.json'
    if not public_path.exists():
        # Try alternative path
        public_path = Path(__file__).parent.parent.parent / 'public' / 'card_names.json'
    
    # Load JSON - will raise FileNotFoundError if missing
    with open(public_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # Read flat array structure
        return set(data['cards'])


# Load card names dynamically from JSON file
COMMON_CARDS: Set[str] = _load_card_names()


# ============================================================================
# LEVEL PATTERNS - For parsing card levels
# ============================================================================

LEVEL_PATTERNS: Dict[str, str] = {
    "满": "max",
    "不满": "not_max",
    "1级": "1",
    "2级": "2",
    "3级": "3",
    "4级": "4",
    "5级": "5",
    "6级": "6",
    "7级": "7",
    "8级": "8",
    "9级": "9",
}


def parse_level(level_str: str) -> str:
    """Parse level string to standardized format."""
    if not level_str:
        return ""
    return LEVEL_PATTERNS.get(level_str, level_str)
