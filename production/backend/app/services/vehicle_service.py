from typing import Dict, Any, Optional, List
from app.utils.logger import logger
from app.services.event_services import EventService

class VehicleService:
    def __init__(self, pid) -> None:
        self.vehicle_info = {
            "side": None,  # 'left' or 'right'
            "equipment": None,  # equipment name
            "level": None,  # current game level
            "seat": None,  # opened seats for cards (1-6)
            "info": self._generate_vehicle_info()
        }
        self.event_service = EventService()
        self.pid = pid

    def _generate_vehicle_info(self) -> Dict[int, Dict[str, Any]]:
        """Generate empty vehicle info structure."""
        info = {}
        for i in range(7):  # 0-6 positions
            info[i] = {
                "card": None,
                "level": None
            }
        return info

    def get_vehicle_info(self) -> Dict[str, Any]:
        """Get the current vehicle information."""
        return self.vehicle_info

    def set_vehicle_info(self, vehicle_info: Dict[str, Any]) -> None:
        """Set the vehicle information."""
        self.vehicle_info = vehicle_info
        self.broadcast_vehicle_update()

    def update_vehicle_side(self, side: str) -> None:
        """Update the vehicle side."""
        self.vehicle_info["side"] = side
        self.broadcast_vehicle_update()

    def update_vehicle_equipment(self, equipment: str) -> None:
        """Update the vehicle equipment."""
        self.vehicle_info["equipment"] = equipment
        self.broadcast_vehicle_update()

    def update_vehicle_level(self, level: int) -> None:
        """Update the vehicle level."""
        self.vehicle_info["level"] = level
        self.broadcast_vehicle_update()

    def update_vehicle_seat(self, seat: int) -> None:
        """Update the vehicle seat count."""
        self.vehicle_info["seat"] = seat
        self.broadcast_vehicle_update()

    def deploy_card(self, position: int, card: str, level: int) -> None:
        """Deploy a card to a specific position in the vehicle."""
        if position < 0 or position > 6:
            logger.error(f"Invalid position: {position}. Must be between 0 and 6.")
            return
            
        self.vehicle_info["info"][position] = {
            "card": card,
            "level": level
        }
        self.broadcast_vehicle_update()

    def remove_card(self, position: int) -> None:
        """Remove a card from a specific position in the vehicle."""
        if position < 0 or position > 6:
            logger.error(f"Invalid position: {position}. Must be between 0 and 6.")
            return
            
        self.vehicle_info["info"][position] = {
            "card": None,
            "level": None
        }
        self.broadcast_vehicle_update()

    def clear_vehicle(self) -> None:
        """Clear all cards from the vehicle."""
        self.vehicle_info["info"] = self._generate_vehicle_info()
        self.broadcast_vehicle_update()
    
    def broadcast_vehicle_update(self) -> None:
        """Broadcast the vehicle update to all connected clients."""
        self.event_service.broadcast_vehicle(self.vehicle_info, [self.pid])