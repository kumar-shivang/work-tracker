"""
Pending Actions Store.

Temporarily stores unconfirmed actions (expenses, reminders, etc.)
so that inline keyboard buttons can confirm/cancel/edit them.
"""
import time
import uuid
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PendingActions:
    """Stores actions awaiting user confirmation via inline buttons."""

    def __init__(self, default_ttl: int = 300):
        self._store: dict[str, dict] = {}
        self.default_ttl = default_ttl

    def store(self, action_data: dict, ttl_seconds: int = None) -> str:
        """
        Store an action and return its unique ID.
        
        Args:
            action_data: Dict with keys like 'type', 'content', 'amount', etc.
            ttl_seconds: Time-to-live in seconds (default 300 = 5 minutes).
            
        Returns:
            Unique action ID string.
        """
        action_id = str(uuid.uuid4())[:8]
        ttl = ttl_seconds or self.default_ttl
        self._store[action_id] = {
            "data": action_data,
            "expires_at": time.time() + ttl,
        }
        self._cleanup()
        return action_id

    def get(self, action_id: str) -> Optional[dict]:
        """Get action data by ID, returns None if expired or not found."""
        self._cleanup()
        entry = self._store.get(action_id)
        if entry and entry["expires_at"] > time.time():
            return entry["data"]
        return None

    def remove(self, action_id: str) -> Optional[dict]:
        """Remove and return action data by ID."""
        entry = self._store.pop(action_id, None)
        if entry:
            return entry["data"]
        return None

    def _cleanup(self):
        """Remove expired entries."""
        now = time.time()
        expired = [k for k, v in self._store.items() if v["expires_at"] <= now]
        for k in expired:
            del self._store[k]


# Singleton instance
pending_actions = PendingActions()
