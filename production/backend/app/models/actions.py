from typing import Optional
from app.enums.action_enum import CardActionEnum, LevelActionEnum

class CardAction:
    def __init__(self, action_type: CardActionEnum, card: str, level: Optional[LevelActionEnum] = None):
        self.type = action_type
        self.card = card
        self.level = level

    def __str__(self) -> str:
        action_str = self.type.value + self.card
        if self.level:
            action_str += self.level.value
        return action_str