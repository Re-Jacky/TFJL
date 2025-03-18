from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CollabRequest(BaseModel):
    user_id: str
    action: str
    data: Optional[dict] = None

class IceFortressRequest(BaseModel):
    fortress_id: str
    player_id: str
    action: str
    position: Optional[dict] = None

class DarkMoonRequest(BaseModel):
    moon_phase: str
    player_id: str
    action: str

class TimingEventRequest(BaseModel):
    event_id: str
    player_id: str
    timestamp: datetime
    action: str

class BattleRequest(BaseModel):
    battle_id: str
    player_id: str
    action: str
    target_id: Optional[str] = None
    skills: Optional[List[str]] = None

class BaseResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None