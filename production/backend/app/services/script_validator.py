"""
Script Validator Service - Validate scripts for correctness and compatibility.

This module provides comprehensive validation including:
- Syntax validation (already done in parser)
- Semantic validation (card usage, event validity)
- Compatibility checks (deck configuration matches actions)
- Best practice warnings
"""

from typing import List, Tuple, Set, Dict, Optional
import logging

from app.models.script_models import (
    Script, LevelCommand, EventCommand, Action, ActionType,
    DeployAction, RemoveAction, PrepareAction, RepeatAction,
    SameRowAction, DiscardPlayAction, VerifyDeployAction, RawAction,
)
from app.enums.script_commands import (
    ALL_KNOWN_EVENTS, COMMON_CARDS, GameMode, get_game_mode_from_event,
)


logger = logging.getLogger(__name__)


class ValidationResult:
    """Container for validation results."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    @property
    def is_valid(self) -> bool:
        """Script is valid if there are no errors."""
        return len(self.errors) == 0

    def add_error(self, message: str) -> None:
        """Add an error (blocks execution)."""
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Add a warning (does not block execution)."""
        self.warnings.append(message)

    def add_info(self, message: str) -> None:
        """Add an informational message."""
        self.info.append(message)

    def merge(self, other: 'ValidationResult') -> None:
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.info.extend(other.info)

    def to_dict(self) -> Dict:
        """Convert to dictionary for API response."""
        return {
            "valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info
        }


class ScriptValidatorService:
    """Service for validating parsed scripts."""

    @staticmethod
    def validate(script: Script) -> ValidationResult:
        """
        Perform full validation on a parsed script.

        Args:
            script: Parsed Script object

        Returns:
            ValidationResult with errors, warnings, and info
        """
        result = ValidationResult()

        # 1. Validate deck configuration
        ScriptValidatorService._validate_deck(script, result)

        # 2. Validate level commands
        ScriptValidatorService._validate_level_commands(script, result)

        # 3. Validate event commands
        ScriptValidatorService._validate_event_commands(script, result)

        # 4. Validate card usage consistency
        ScriptValidatorService._validate_card_usage(script, result)

        # 5. Check for raw/unparsed actions
        ScriptValidatorService._check_raw_actions(script, result)

        # 6. Check for best practices
        ScriptValidatorService._check_best_practices(script, result)

        return result

    @staticmethod
    def _validate_deck(script: Script, result: ValidationResult) -> None:
        """Validate deck configuration."""
        if not script.setup.deck:
            result.add_warning("Script has no deck configuration (上阵). "
                             "Actions may fail if cards are not available.")
            return

        # Check deck size (typically 10 cards max)
        if len(script.setup.deck) > 10:
            result.add_warning(f"Deck has {len(script.setup.deck)} cards. "
                             "Maximum is typically 10.")

        # Check for duplicate cards in deck
        deck_set = set()
        for card in script.setup.deck:
            if card in deck_set:
                result.add_warning(f"Duplicate card in deck: '{card}'")
            deck_set.add(card)

        # Check enhanced cards are in deck
        for card in script.setup.enhanced:
            if card not in deck_set:
                result.add_warning(f"Enhanced card '{card}' is not in deck")

    @staticmethod
    def _validate_level_commands(script: Script, result: ValidationResult) -> None:
        """Validate level-based commands."""
        if not script.commands.level_commands:
            result.add_info("Script has no level commands")
            return

        levels = [cmd.level for cmd in script.commands.level_commands]

        # Check for duplicate levels
        seen_levels: Set[int] = set()
        for level in levels:
            if level in seen_levels:
                result.add_error(f"Duplicate level command for level {level}")
            seen_levels.add(level)

        # Check level sequence (should start from 1 typically)
        min_level = min(levels)
        if min_level != 1:
            result.add_info(f"Level commands start from level {min_level}, not 1")

        # Check for gaps in critical early levels (1-10)
        early_levels = set(l for l in levels if l <= 10)
        if 1 not in early_levels:
            result.add_info("No command for level 1 (game start)")

        # Validate actions within each level command
        for level_cmd in script.commands.level_commands:
            ScriptValidatorService._validate_level_actions(level_cmd, result)

    @staticmethod
    def _validate_level_actions(
        level_cmd: LevelCommand,
        result: ValidationResult
    ) -> None:
        """Validate actions within a level command."""
        if not level_cmd.actions:
            result.add_warning(f"Level {level_cmd.level}: No actions defined")
            return

        # Check for conflicting actions
        deploy_cards: Set[str] = set()
        remove_cards: Set[str] = set()

        for action in level_cmd.actions:
            if isinstance(action, DeployAction):
                if action.card in deploy_cards:
                    result.add_warning(
                        f"Level {level_cmd.level}: Card '{action.card}' "
                        "deployed multiple times in same command"
                    )
                deploy_cards.add(action.card)

            elif isinstance(action, RemoveAction):
                remove_cards.add(action.card)

        # Check if deploying and removing same card
        overlap = deploy_cards & remove_cards
        if overlap:
            # This might be intentional (redeploy pattern)
            result.add_info(
                f"Level {level_cmd.level}: Cards {overlap} are both "
                "deployed and removed (redeploy pattern?)"
            )

    @staticmethod
    def _validate_event_commands(script: Script, result: ValidationResult) -> None:
        """Validate event-based commands."""
        if not script.commands.event_commands:
            result.add_info("Script has no event commands")
            return

        # Determine game mode from events
        game_modes: Set[GameMode] = set()
        for event_cmd in script.commands.event_commands:
            mode = get_game_mode_from_event(event_cmd.event)
            game_modes.add(mode)

        if len(game_modes) > 2:  # Collab mode is always included
            result.add_warning(
                f"Script contains events from multiple game modes: {game_modes}. "
                "This may be intentional if script is multi-purpose."
            )

        # Check each event
        seen_events: Set[str] = set()
        for event_cmd in script.commands.event_commands:
            # Check for duplicates
            if event_cmd.event in seen_events:
                result.add_warning(f"Duplicate event command: '{event_cmd.event}'")
            seen_events.add(event_cmd.event)

            # Check if event is known
            if event_cmd.event not in ALL_KNOWN_EVENTS:
                # Allow custom events but warn
                result.add_info(
                    f"Event '{event_cmd.event}' is not in known events list. "
                    "Make sure the event image template exists."
                )

            # Validate card filter if present
            if event_cmd.card_filter:
                valid_cards = {'A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'}
                for card in event_cmd.card_filter:
                    if card not in valid_cards:
                        result.add_warning(
                            f"Event '{event_cmd.event}': Invalid card filter value '{card}'"
                        )

    @staticmethod
    def _validate_card_usage(script: Script, result: ValidationResult) -> None:
        """Validate that cards used in actions are available."""
        deck_set = set(script.setup.deck)
        if not deck_set:
            return  # Already warned about missing deck

        # Collect all cards used in actions
        used_cards: Set[str] = set()

        def collect_cards(actions: List[Action]) -> None:
            for action in actions:
                if isinstance(action, (DeployAction, RemoveAction, PrepareAction)):
                    used_cards.add(action.card)
                elif isinstance(action, RepeatAction):
                    used_cards.add(action.card)
                elif isinstance(action, DiscardPlayAction):
                    used_cards.add(action.card)
                elif isinstance(action, SameRowAction):
                    used_cards.update(action.cards)

        for level_cmd in script.commands.level_commands:
            collect_cards(level_cmd.actions)

        for event_cmd in script.commands.event_commands:
            collect_cards(event_cmd.actions)

        # Check which used cards are not in deck
        missing_cards = used_cards - deck_set
        for card in missing_cards:
            if card in COMMON_CARDS:
                result.add_warning(
                    f"Card '{card}' is used in actions but not in deck (上阵)"
                )
            else:
                result.add_info(
                    f"Card '{card}' is used in actions but not in deck. "
                    "This may be a custom card name."
                )

    @staticmethod
    def _check_raw_actions(script: Script, result: ValidationResult) -> None:
        """Check for unparsed/raw actions that couldn't be recognized."""
        raw_count = 0

        for level_cmd in script.commands.level_commands:
            for action in level_cmd.actions:
                if isinstance(action, RawAction):
                    raw_count += 1
                    result.add_warning(
                        f"Level {level_cmd.level}: Unparsed action '{action.content}'"
                    )

        for event_cmd in script.commands.event_commands:
            for action in event_cmd.actions:
                if isinstance(action, RawAction):
                    raw_count += 1
                    result.add_warning(
                        f"Event '{event_cmd.event}': Unparsed action '{action.content}'"
                    )

        if raw_count > 0:
            result.add_info(
                f"Script contains {raw_count} unparsed actions. "
                "These will be skipped during execution."
            )

    @staticmethod
    def _check_best_practices(script: Script, result: ValidationResult) -> None:
        """Check for best practice violations."""

        # Check for very long action sequences (potential performance issue)
        for level_cmd in script.commands.level_commands:
            if len(level_cmd.actions) > 20:
                result.add_info(
                    f"Level {level_cmd.level}: Has {len(level_cmd.actions)} actions. "
                    "Consider breaking into multiple levels if possible."
                )

        # Check for verify_deploy usage
        has_verify_deploy = False
        for level_cmd in script.commands.level_commands:
            for action in level_cmd.actions:
                if isinstance(action, VerifyDeployAction):
                    has_verify_deploy = True
                    break

        if has_verify_deploy:
            result.add_info(
                "Script uses 验卡补星 (verify deploy). "
                "This requires OCR to be enabled and may slow execution."
            )

        # Check for repeat actions with very high counts
        for level_cmd in script.commands.level_commands:
            for action in level_cmd.actions:
                if isinstance(action, RepeatAction) and action.count > 50:
                    result.add_info(
                        f"Level {level_cmd.level}: Repeat action with {action.count} "
                        "iterations. This may take a while to complete."
                    )

    @staticmethod
    def quick_validate(content: str) -> ValidationResult:
        """
        Quick validation of raw script content without full parsing.

        Useful for editor real-time feedback.
        """
        result = ValidationResult()
        lines = content.split('\n')

        # Check for basic structure
        has_deck = False
        has_commands = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('上阵'):
                has_deck = True
            elif line[0].isdigit():
                has_commands = True

        if not has_deck:
            result.add_warning("Missing deck configuration (上阵)")

        if not has_commands:
            result.add_warning("No level commands found")

        return result
