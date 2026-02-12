"""
Conversation Context Manager.

Manages per-chat conversation history and integrates with the memory system
to provide rich context for LLM-powered conversational responses.
"""
import logging
import datetime
from typing import Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class ConversationContext:
    """Manages per-chat conversation history and memory retrieval."""

    def __init__(self, max_history: int = 5):
        self._history: dict[str, list[dict]] = defaultdict(list)
        self.max_history = max_history

    def add_message(self, chat_id: str, role: str, content: str):
        """Add a message to the conversation history."""
        self._history[chat_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now().isoformat(),
        })
        # Trim to max_history (keep last N messages)
        if len(self._history[chat_id]) > self.max_history:
            self._history[chat_id] = self._history[chat_id][-self.max_history:]

    def get_history(self, chat_id: str) -> list[dict]:
        """Get conversation history for a chat."""
        return self._history.get(chat_id, [])

    def clear(self, chat_id: str):
        """Clear conversation history for a chat."""
        self._history.pop(chat_id, None)

    async def build_context(self, chat_id: str, message: str) -> list[dict]:
        """
        Build enriched LLM messages with:
        - System prompt with current time and capabilities
        - Relevant memories from semantic search
        - Recent conversation history
        - Current user message
        """
        from app.services.memory import memory_service

        ist_offset = datetime.timedelta(hours=5, minutes=30)
        ist_tz = datetime.timezone(ist_offset)
        current_time = datetime.datetime.now(ist_tz)

        # Search for relevant memories
        memory_context = ""
        try:
            memories = await memory_service.search_memories(query=message, limit=3)
            if memories:
                memory_items = []
                for m in memories:
                    mem_type = m.get("memory_type", "unknown")
                    content = m.get("content", "")
                    similarity = m.get("similarity", 0)
                    if similarity > 0.3:  # Only include reasonably relevant memories
                        memory_items.append(f"  [{mem_type}] {content}")
                if memory_items:
                    memory_context = "\n\nRelevant memories from your history:\n" + "\n".join(memory_items)
        except Exception as e:
            logger.warning(f"Failed to search memories for context: {e}")

        system_prompt = f"""You are a personal assistant bot on Telegram for Shivang. You help track work, expenses, habits, journal entries, reminders, and provide summaries.

Current time: {current_time.strftime('%Y-%m-%d %H:%M IST')}
Day: {current_time.strftime('%A')}

Your capabilities:
- Set reminders (parse natural language times)
- Log expenses (amount, currency, category)
- Track habits (exercise, reading, meditation, etc.)
- Journal entries (with sentiment)
- Status updates for work tracking
- Search past memories and activities
- Provide summaries of recent activity

Respond naturally and conversationally. Be concise but friendly. Use emojis sparingly.
When you detect an actionable intent (reminder, expense, habit, journal, status_update), include it in your response.
When the user asks questions about their past activity, use the memory context provided.{memory_context}"""

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        history = self.get_history(chat_id)
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        # Add current message
        messages.append({"role": "user", "content": message})

        return messages


# Singleton instance
conversation_context = ConversationContext()
