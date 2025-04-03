from typing import Dict, Any, Optional
from asyncio import Queue
from app.utils.logger import logger
from datetime import datetime

class EventService:
    def __init__(self):
        self._sessions: Dict[str, Queue] = {}
        self._event_types = {
            'log': 'log',
            'vehicle': 'vehicle'
        }

    async def connect(self, session_id: str) -> Queue:
        """Get or create a client connection for session ID."""
        if session_id not in self._sessions:
            self._sessions[session_id] = Queue()
            logger.info(f"New client connection created for session {session_id}")
        else:
            logger.info(f"Client reconnected to session {session_id}")
        return self._sessions[session_id]

    async def disconnect(self, client: Queue) -> None:
        """Remove a client connection."""
        for session_id, queue in self._sessions.items():
            if queue == client:
                del self._sessions[session_id]
                logger.info(f"Client disconnected from session {session_id}")
                break

    async def disconnect_by_session_id(self, session_id: str) -> None:
        """Remove client connection for a given session ID."""
        if session_id in self._sessions:
            await self.disconnect(self._sessions[session_id])
            logger.info(f"Client disconnected from session {session_id}")

    async def broadcast(self, event_type: str, data: Any, session_ids: Optional[list[str]] = None) -> None:
        """Broadcast an event to clients in specified sessions. If no session_ids provided, broadcast to all sessions."""
        if event_type not in self._event_types:
            logger.error(f"Invalid event type: {event_type}")
            return

        event_message = {
            "type": event_type,
            "data": data
        }

        target_sessions = session_ids if session_ids else self._sessions.keys()
        for session_id in target_sessions:
            if session_id not in self._sessions:
                logger.warning(f"Session {session_id} not found")
                continue

            client = self._sessions[session_id]
            try:
                await client.put(event_message)
            except Exception as e:
                logger.error(f"Error broadcasting to client in session {session_id}: {str(e)}")
                await self.disconnect(client)
                try:
                    await client.put(None)  # Signal client to disconnect
                except Exception:
                    pass

    async def broadcast_log(self, level: str, message:str, session_ids: Optional[list[str]] = None) -> None:
        """Broadcast a log event to clients in specified sessions."""
        formatted_data = {
            "message": message,
            "level": level,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        await self.broadcast('log', formatted_data, session_ids)

    # vehicle data should be like : {'side': 'left', 'info': {1: {'card': 'GuGu', 'level': 4}, 2: {'card': 'Xiao ye', 'level': 1}}
    async def broadcast_vehicle(self, side: str, info: Dict, session_ids: Optional[list[str]] = None) -> None:
        """Broadcast a vehicle event to clients in specified sessions."""
        formatted_data = {
            "side": side,
            "info": info
        }
        await self.broadcast('vehicle', formatted_data, session_ids)

    async def format_sse(self, data: Dict) -> str:
        """Format the data as a Server-Sent Event message."""
        return f"data: {str(data)}\n\n"

    def get_event_types(self) -> Dict[str, str]:
        """Get all available event types."""
        return self._event_types.copy()
