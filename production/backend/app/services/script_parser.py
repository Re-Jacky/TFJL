"""
Script Parser Service - Parse DSL scripts into structured data.

This module handles:
- Parsing script headers (deck, skins, enhanced, vehicles)
- Parsing level-based commands (e.g., "1,上火灵满,上蛇女满")
- Parsing event-based commands (e.g., "寒冰雷神红球,上火灵")
- Handling Chinese punctuation variations
- Extracting card filters and point totals from event commands
"""

import re
from typing import List, Optional, Tuple, Dict, Any
import logging

from app.models.script_models import (
    Script, ScriptMetadata, ScriptSetup, ScriptCommands,
    LevelCommand, EventCommand, Action, ActionType,
    DeployAction, RemoveAction, PrepareAction, SwitchEquipmentAction,
    WaitUntilAction, RepeatAction, DelayAction, StopBallAction,
    CloseVerifyAction, SameRowAction, CancelSameRowAction,
    ForceOrderAction, VerifyDeployAction, DiscardPlayAction, RawAction,
)
from app.enums.script_commands import (
    CommandPattern, HeaderPattern, ALL_KNOWN_EVENTS, COMMON_CARDS,
)


logger = logging.getLogger(__name__)


class ScriptParserService:
    """Service for parsing script DSL into structured data."""

    # Punctuation normalization map (Chinese to ASCII)
    PUNCTUATION_MAP = {
        '，': ',',
        '：': ':',
        '；': ';',
        '。': '.',
        '（': '(',
        '）': ')',
        '　': ' ',  # Full-width space
    }

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize Chinese punctuation to ASCII equivalents."""
        for chinese, ascii_char in ScriptParserService.PUNCTUATION_MAP.items():
            text = text.replace(chinese, ascii_char)
        return text.strip()

    @staticmethod
    def parse_script(
        content: str,
        name: str = "untitled",
        script_type: str = "collab"
    ) -> Tuple[Optional[Script], List[str], List[str]]:
        """
        Parse a script file content into a Script object.

        Args:
            content: Raw script file content
            name: Script name (usually filename)
            script_type: Type of script ('collab' or 'activity')

        Returns:
            Tuple of (Script or None, list of errors, list of warnings)
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Normalize the entire content
        content = ScriptParserService.normalize_text(content)
        lines = content.split('\n')

        # Parse header section
        setup, header_end_line = ScriptParserService._parse_header(lines, warnings)

        # Parse command sections
        level_commands: List[LevelCommand] = []
        event_commands: List[EventCommand] = []

        for line_num, line in enumerate(lines[header_end_line:], start=header_end_line + 1):
            line = line.strip()
            if not line:
                continue

            # Try to parse as level command first
            level_cmd = ScriptParserService._parse_level_command(line, line_num, warnings)
            if level_cmd:
                level_commands.append(level_cmd)
                continue

            # Try to parse as event command
            event_cmd = ScriptParserService._parse_event_command(line, line_num, warnings)
            if event_cmd:
                event_commands.append(event_cmd)
                continue

            # Unknown line format
            warnings.append(f"Line {line_num}: Unrecognized line format: '{line[:50]}...'")

        # Sort level commands by level
        level_commands.sort(key=lambda x: x.level)

        # Create script object
        metadata = ScriptMetadata(
            name=name,
            script_type=script_type,
            version="1.0",
            description=None
        )

        commands = ScriptCommands(
            level_commands=level_commands,
            event_commands=event_commands
        )

        script = Script(
            metadata=metadata,
            setup=setup,
            commands=commands
        )

        return script, errors, warnings

    @staticmethod
    def _parse_header(
        lines: List[str],
        warnings: List[str]
    ) -> Tuple[ScriptSetup, int]:
        """
        Parse the header section of a script.

        Returns:
            Tuple of (ScriptSetup, line number where header ends)
        """
        setup = ScriptSetup()
        header_end_line = 0

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Check if line matches any header pattern
            matched = False

            # Deck (上阵)
            match = re.match(HeaderPattern.DECK.value, line)
            if match:
                cards_str = match.group(1)
                setup.deck = ScriptParserService._parse_card_list(cards_str)
                header_end_line = line_num + 1
                matched = True

            # Skins (皮肤)
            if not matched:
                match = re.match(HeaderPattern.SKINS.value, line)
                if match:
                    cards_str = match.group(1)
                    setup.skins = ScriptParserService._parse_card_list(cards_str)
                    header_end_line = line_num + 1
                    matched = True

            # Enhanced (魔化)
            if not matched:
                match = re.match(HeaderPattern.ENHANCED.value, line)
                if match:
                    cards_str = match.group(1)
                    setup.enhanced = ScriptParserService._parse_card_list(cards_str)
                    header_end_line = line_num + 1
                    matched = True

            # Main Vehicle (主战车)
            if not matched:
                match = re.match(HeaderPattern.MAIN_VEHICLE.value, line)
                if match:
                    vehicle = match.group(1).strip()
                    if vehicle and vehicle != "未设置":
                        setup.main_vehicle = vehicle
                    header_end_line = line_num + 1
                    matched = True

            # Sub Vehicle (副战车)
            if not matched:
                match = re.match(HeaderPattern.SUB_VEHICLE.value, line)
                if match:
                    vehicle = match.group(1).strip()
                    if vehicle and vehicle != "未设置":
                        setup.sub_vehicle = vehicle
                    header_end_line = line_num + 1
                    matched = True

            # If no header pattern matched and we've seen headers before,
            # this is likely the start of commands
            if not matched and header_end_line > 0:
                break

        return setup, header_end_line

    @staticmethod
    def _parse_card_list(cards_str: str) -> List[str]:
        """Parse a comma-separated list of cards."""
        if not cards_str:
            return []
        cards = [c.strip() for c in cards_str.split(',') if c.strip()]
        return cards

    @staticmethod
    def _parse_level_command(
        line: str,
        line_num: int,
        warnings: List[str]
    ) -> Optional[LevelCommand]:
        """
        Parse a level-based command line.

        Format: {level},{action1},{action2},...
        Example: "1,上火灵满,上蛇女满"
        """
        parts = [p.strip() for p in line.split(',') if p.strip()]
        if not parts:
            return None

        # First part must be a number (level)
        try:
            level = int(parts[0])
        except ValueError:
            return None  # Not a level command

        if level < 1 or level > 999:
            warnings.append(f"Line {line_num}: Level {level} is out of range (1-999)")
            return None

        # Parse actions from remaining parts
        actions = ScriptParserService._parse_actions(parts[1:], line_num, warnings)

        return LevelCommand(level=level, actions=actions)

    @staticmethod
    def _parse_event_command(
        line: str,
        line_num: int,
        warnings: List[str]
    ) -> Optional[EventCommand]:
        """
        Parse an event-based command line.

        Format: {event_name},{action1},{action2},...
        Example: "寒冰雷神红球,上火灵"

        Special formats:
        - "暗月地精不吃,A,K,2,Q" - event with card filter
        - "牌点总数50点" - action with point total
        """
        parts = [p.strip() for p in line.split(',') if p.strip()]
        if not parts:
            return None

        # First part is the event name
        event_name = parts[0]

        # Check if this looks like an event (not a number, not a known action)
        if re.match(r'^\d+$', event_name):
            return None  # This is a level command

        # Parse remaining parts as actions
        action_parts = parts[1:]

        # Check for card filter (e.g., "暗月地精不吃,5,8,9,10,J,Q,K")
        card_filter = None
        point_total = None
        filtered_action_parts = []

        for part in action_parts:
            # Check for point total
            point_match = re.match(r'^牌点总数(\d+)点$', part)
            if point_match:
                point_total = int(point_match.group(1))
                continue

            # Check if this is a card value (for filter)
            if re.match(r'^[A2-9JQK]$|^10$', part):
                if card_filter is None:
                    card_filter = []
                card_filter.append(part)
                continue

            filtered_action_parts.append(part)

        actions = ScriptParserService._parse_actions(filtered_action_parts, line_num, warnings)

        return EventCommand(
            event=event_name,
            actions=actions,
            card_filter=card_filter,
            point_total=point_total
        )

    @staticmethod
    def _parse_actions(
        parts: List[str],
        line_num: int,
        warnings: List[str]
    ) -> List[Action]:
        """
        Parse a list of action strings into Action objects.

        Handles the "过后" (after) marker for chained actions.
        """
        actions: List[Action] = []
        after_previous = False

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Check for "过后" marker
            if part == "过后":
                after_previous = True
                continue

            # Try to parse the action
            action = ScriptParserService._parse_single_action(part, line_num, warnings)
            if action:
                action.after_previous = after_previous
                actions.append(action)
                after_previous = False

        return actions

    @staticmethod
    def _parse_single_action(
        action_str: str,
        line_num: int,
        warnings: List[str]
    ) -> Optional[Action]:
        """Parse a single action string into an Action object."""

        # Deploy: 上{card}{level?}
        match = re.match(CommandPattern.DEPLOY.value, action_str)
        if match:
            return DeployAction(
                card=match.group('card'),
                level=match.group('level')
            )

        # Remove: 下{card}
        match = re.match(CommandPattern.REMOVE.value, action_str)
        if match:
            return RemoveAction(card=match.group('card'))

        # Prepare: 预备手牌{card}
        match = re.match(CommandPattern.PREPARE.value, action_str)
        if match:
            return PrepareAction(card=match.group('card'))

        # Switch Equipment: 换{equipment}
        match = re.match(CommandPattern.SWITCH_EQUIPMENT.value, action_str)
        if match:
            return SwitchEquipmentAction(equipment=match.group('equipment'))

        # Wait Until: 时钟秒{n}
        match = re.match(CommandPattern.WAIT_UNTIL.value, action_str)
        if match:
            return WaitUntilAction(second=float(match.group('second')))

        # Repeat: 每{n}秒共{m}次{card}
        match = re.match(CommandPattern.REPEAT.value, action_str)
        if match:
            return RepeatAction(
                interval=float(match.group('interval')),
                count=int(match.group('count')),
                card=match.group('card')
            )

        # Delay: 延时{n}毫秒
        match = re.match(CommandPattern.DELAY.value, action_str)
        if match:
            return DelayAction(milliseconds=int(match.group('ms')))

        # Stop Ball: 停球
        match = re.match(CommandPattern.STOP_BALL.value, action_str)
        if match:
            return StopBallAction()

        # Close Verify: 关闭验光
        match = re.match(CommandPattern.CLOSE_VERIFY.value, action_str)
        if match:
            return CloseVerifyAction()

        # Same Row: {card1}{card2}同排
        match = re.match(CommandPattern.SAME_ROW.value, action_str)
        if match:
            return SameRowAction(cards=[match.group('card1'), match.group('card2')])

        # Cancel Same Row: 同排取消
        match = re.match(CommandPattern.CANCEL_SAME_ROW.value, action_str)
        if match:
            return CancelSameRowAction()

        # Force Order: 强制顺序上卡
        match = re.match(CommandPattern.FORCE_ORDER.value, action_str)
        if match:
            return ForceOrderAction()

        # Verify Deploy: 验卡补星{仅满级?}{count?}
        match = re.match(CommandPattern.VERIFY_DEPLOY.value, action_str)
        if match:
            count_str = match.group('count')
            count = None
            if count_str:
                count = int(count_str.replace('次', ''))
            max_only = '仅满级' in action_str
            return VerifyDeployAction(max_only=max_only, count=count)

        # Discard Play: 弃牌出牌{card}
        match = re.match(CommandPattern.DISCARD_PLAY.value, action_str)
        if match:
            return DiscardPlayAction(card=match.group('card'))

        # Unknown action - store as raw
        warnings.append(f"Line {line_num}: Unknown action format: '{action_str}'")
        return RawAction(content=action_str)

    @staticmethod
    def validate_script(script: Script) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a parsed script for semantic correctness.

        Returns:
            Tuple of (is_valid, list of errors, list of warnings)
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Check deck configuration
        if not script.setup.deck:
            warnings.append("Script has no deck configuration (上阵)")

        # Check for duplicate levels
        levels = [cmd.level for cmd in script.commands.level_commands]
        duplicates = [l for l in levels if levels.count(l) > 1]
        if duplicates:
            unique_dups = list(set(duplicates))
            errors.append(f"Duplicate level definitions: {unique_dups}")

        # Check that cards used in actions are in the deck
        deck_set = set(script.setup.deck)
        for level_cmd in script.commands.level_commands:
            for action in level_cmd.actions:
                card = ScriptParserService._get_action_card(action)
                if card and card not in deck_set and card in COMMON_CARDS:
                    warnings.append(
                        f"Level {level_cmd.level}: Card '{card}' used but not in deck"
                    )

        # Check that events are known
        for event_cmd in script.commands.event_commands:
            if event_cmd.event not in ALL_KNOWN_EVENTS:
                # Check if it looks like a partial match
                partial_matches = [
                    e for e in ALL_KNOWN_EVENTS
                    if event_cmd.event in e or e in event_cmd.event
                ]
                if partial_matches:
                    warnings.append(
                        f"Event '{event_cmd.event}' not in known events. "
                        f"Similar: {partial_matches[:3]}"
                    )
                else:
                    warnings.append(f"Event '{event_cmd.event}' not in known events list")

        is_valid = len(errors) == 0
        return is_valid, errors, warnings

    @staticmethod
    def _get_action_card(action: Action) -> Optional[str]:
        """Extract the card name from an action if applicable."""
        if isinstance(action, (DeployAction, RemoveAction, PrepareAction, DiscardPlayAction)):
            return action.card
        if isinstance(action, RepeatAction):
            return action.card
        return None

    @staticmethod
    def serialize_script(script: Script) -> str:
        """
        Serialize a Script object back to DSL format.

        This is useful for saving modified scripts back to file.
        """
        lines: List[str] = []

        # Header section
        if script.setup.deck:
            lines.append(f"上阵：{','.join(script.setup.deck)},")
        else:
            lines.append("上阵：")

        if script.setup.skins:
            lines.append(f"皮肤：{','.join(script.setup.skins)},")
        else:
            lines.append("皮肤：")

        if script.setup.enhanced:
            lines.append(f"魔化：{','.join(script.setup.enhanced)},")
        else:
            lines.append("魔化：")

        lines.append(f"主战车：{script.setup.main_vehicle or '未设置'}")
        lines.append(f"副战车：{script.setup.sub_vehicle or '未设置'}")
        lines.append("")  # Empty line after header

        # Level commands
        for level_cmd in script.commands.level_commands:
            actions_str = ScriptParserService._serialize_actions(level_cmd.actions)
            lines.append(f"{level_cmd.level},{actions_str}")

        lines.append("")  # Empty line between sections

        # Event commands
        for event_cmd in script.commands.event_commands:
            actions_str = ScriptParserService._serialize_actions(event_cmd.actions)

            # Add card filter if present
            if event_cmd.card_filter:
                actions_str += ',' + ','.join(event_cmd.card_filter)

            # Add point total if present
            if event_cmd.point_total:
                actions_str += f",牌点总数{event_cmd.point_total}点"

            if actions_str:
                lines.append(f"{event_cmd.event},{actions_str}")
            else:
                lines.append(f"{event_cmd.event},")

        lines.append("")  # Trailing newline

        return '\n'.join(lines)

    @staticmethod
    def _serialize_actions(actions: List[Action]) -> str:
        """Serialize a list of actions back to DSL format."""
        parts: List[str] = []

        for action in actions:
            if action.after_previous:
                parts.append("过后")

            action_str = ScriptParserService._serialize_single_action(action)
            if action_str:
                parts.append(action_str)

        return ','.join(parts)

    @staticmethod
    def _serialize_single_action(action: Action) -> str:
        """Serialize a single action to DSL format."""
        if isinstance(action, DeployAction):
            level_str = action.level or ""
            return f"上{action.card}{level_str}"

        if isinstance(action, RemoveAction):
            return f"下{action.card}"

        if isinstance(action, PrepareAction):
            return f"预备手牌{action.card}"

        if isinstance(action, SwitchEquipmentAction):
            return f"换{action.equipment}"

        if isinstance(action, WaitUntilAction):
            return f"时钟秒{action.second}"

        if isinstance(action, RepeatAction):
            return f"每{action.interval}秒共{action.count}次{action.card}"

        if isinstance(action, DelayAction):
            return f"延时{action.milliseconds}毫秒"

        if isinstance(action, StopBallAction):
            return "停球"

        if isinstance(action, CloseVerifyAction):
            return "关闭验光"

        if isinstance(action, SameRowAction):
            return f"{''.join(action.cards)}同排"

        if isinstance(action, CancelSameRowAction):
            return "同排取消"

        if isinstance(action, ForceOrderAction):
            return "强制顺序上卡"

        if isinstance(action, VerifyDeployAction):
            result = "验卡补星"
            if action.max_only:
                result += "仅满级"
            if action.count:
                result += f"{action.count}次"
            return result

        if isinstance(action, DiscardPlayAction):
            return f"弃牌出牌{action.card}"

        if isinstance(action, RawAction):
            return action.content

        return ""
