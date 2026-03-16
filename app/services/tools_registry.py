import logging
import inspect
import datetime
from typing import Dict, Callable, Any, Optional

logger = logging.getLogger(__name__)

class ToolsRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, dict] = {}

    def register(self, name: str, func: Callable, schema: Optional[dict] = None):
        """Register a tool with its function and optional schema."""
        self._tools[name] = func
        if schema:
            self._schemas[name] = schema
        logger.info(f"Registered tool: {name}")

    async def execute(self, name: str, args: dict = None) -> Any:
        """Execute a registered tool by name with arguments."""
        if name not in self._tools:
            logger.error(f"Tool not found: {name}")
            return f"Error: Tool '{name}' not found."

        func = self._tools[name]
        args = args or {}
        
        try:
            # Check if function is async
            if inspect.iscoroutinefunction(func):
                return await func(**args)
            return func(**args)
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            return f"Error executing tool {name}: {str(e)}"

    def get_tool_names(self) -> list:
        return list(self._tools.keys())

    def get_system_prompt_part(self) -> str:
        """Generate a system prompt section describing available tools."""
        lines = ["\nAvailable Tools (use 'tool_call' in JSON response to invoke):"]
        for name, func in self._tools.items():
            doc = inspect.getdoc(func) or "No description."
            # Get first line of docstring
            summary = doc.split("\n")[0]
            # Get signature
            sig = inspect.signature(func)
            lines.append(f"- {name}{sig}: {summary}")
        return "\n".join(lines)

# Create a singleton instance
tools_registry = ToolsRegistry()

# ─── Standard Tools Implementation ______________________________

from app.services.summaries import get_expenses_summary, get_reminders_summary, get_habits_summary
from app.services.google_calendar import google_calendar_client

async def tool_view_expenses(limit: int = 10, period: str = "recent") -> str:
    """
    View recent expenses.
    Args:
        limit: Number of expenses to show.
        period: 'recent', 'today', 'week' (currently only 'recent' fully supported via summary).
    """
    # For now, we just map to the existing summary function which defaults to 10
    # In future we can add period filtering to `get_expenses_summary`
    return await get_expenses_summary(limit=limit)

async def tool_view_reminders() -> str:
    """View pending reminders."""
    return await get_reminders_summary()

async def tool_view_habits() -> str:
    """View recent habits."""
    return await get_habits_summary()

def tool_create_event(summary: str, start_time: str, description: str = "", duration_minutes: int = 30) -> str:
    """
    Create a new calendar event.
    Args:
        summary: Title of the event.
        start_time: Start time in ISO format (e.g., '2023-10-27T10:00:00').
        description: Description of the event.
        duration_minutes: Duration in minutes.
    """
    try:
        dt = datetime.datetime.fromisoformat(start_time)
    except ValueError:
        return f"Error: Invalid start_time format '{start_time}'. Use ISO format (YYYY-MM-DDTHH:MM:SS)."

    event = google_calendar_client.create_event(
        summary=summary,
        description=description,
        start_time=dt,
        duration_minutes=duration_minutes
    )
    
    if event:
        return f"Event created: {event.get('htmlLink')}"
    return "Failed to create event."

def tool_view_calendar(max_results: int = 10) -> str:
    """View upcoming calendar events."""
    events = google_calendar_client.list_upcoming_events(max_results=max_results)
    if not events:
        return "No upcoming events found."
    
    result = "📅 *Upcoming Events:*\n"
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        # Simple formatting, can be improved
        result += f"- {event['summary']} at {start}\n"
    return result

# Register standard tools
tools_registry.register("view_expenses", tool_view_expenses)
tools_registry.register("view_reminders", tool_view_reminders)
tools_registry.register("view_habits", tool_view_habits)
tools_registry.register("view_calendar", tool_view_calendar)
tools_registry.register("create_event", tool_create_event)
