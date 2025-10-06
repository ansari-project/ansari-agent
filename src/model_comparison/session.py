"""Session management with TTL and LRU eviction."""

import asyncio
import time
import uuid
from collections import OrderedDict
from typing import Dict, List, Optional
from .models import ChatMessage
from .config import config


class Session:
    """Session holding conversation history for all models."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = time.time()
        self.last_accessed = time.time()
        # Separate history per model
        self.histories: Dict[str, List[ChatMessage]] = {
            model_id: [] for model_id in config.MODELS.keys()
        }

    def update_access_time(self) -> None:
        """Update last access timestamp."""
        self.last_accessed = time.time()

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return (time.time() - self.last_accessed) > config.SESSION_TTL_SECONDS

    def add_message(self, model_id: str, message: ChatMessage) -> None:
        """Add message to model's history with truncation."""
        if model_id not in self.histories:
            return

        self.histories[model_id].append(message)
        self._truncate_history(model_id)

    def _truncate_history(self, model_id: str) -> None:
        """Truncate history to max turns or tokens."""
        history = self.histories[model_id]

        # Truncate by turns
        if len(history) > config.MAX_HISTORY_TURNS * 2:  # *2 for user+assistant pairs
            self.histories[model_id] = history[-(config.MAX_HISTORY_TURNS * 2):]
            history = self.histories[model_id]

        # Truncate by tokens (rough estimate: 4 chars = 1 token)
        total_chars = sum(len(msg.content) for msg in history)
        estimated_tokens = total_chars // 4

        if estimated_tokens > config.MAX_HISTORY_TOKENS:
            # Remove oldest messages until under limit
            while history and estimated_tokens > config.MAX_HISTORY_TOKENS:
                removed = history.pop(0)
                estimated_tokens -= len(removed.content) // 4

    def get_history(self, model_id: str) -> List[ChatMessage]:
        """Get conversation history for a model."""
        return self.histories.get(model_id, []).copy()


class SessionManager:
    """Manages sessions with LRU eviction and TTL."""

    def __init__(self):
        self._sessions: OrderedDict[str, Session] = OrderedDict()
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start_cleanup_task(self) -> None:
        """Start background task to clean up expired sessions."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_cleanup_task(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_loop(self) -> None:
        """Periodically clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break

    async def _cleanup_expired(self) -> None:
        """Remove expired sessions."""
        async with self._lock:
            expired = [
                sid for sid, session in self._sessions.items()
                if session.is_expired()
            ]
            for sid in expired:
                del self._sessions[sid]

    async def create_session(self) -> str:
        """Create a new session and return its ID."""
        session_id = str(uuid.uuid4())
        session = Session(session_id)

        async with self._lock:
            # LRU eviction if at max
            if len(self._sessions) >= config.MAX_SESSIONS:
                # Remove oldest (first item in OrderedDict)
                self._sessions.popitem(last=False)

            self._sessions[session_id] = session
            self._sessions.move_to_end(session_id)

        return session_id

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID, updating access time."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                if session.is_expired():
                    # Clean up on access
                    del self._sessions[session_id]
                    return None
                session.update_access_time()
                self._sessions.move_to_end(session_id)
            return session

    async def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def get_session_count(self) -> int:
        """Get current number of active sessions."""
        async with self._lock:
            return len(self._sessions)


# Global session manager
session_manager = SessionManager()
