
import datetime
import logging
from typing import List, Optional
from app.services.db_service import db_service
from app.services.memory import memory_service

logger = logging.getLogger(__name__)

def ist_now() -> datetime.datetime:
    """Get current time in IST."""
    ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    return datetime.datetime.now(ist_tz)

def escape_md(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    if not text:
        return ""
    # Escape backslash first to avoid double-escaping
    text = text.replace('\\', '\\\\')
    special = r'_*[]()~`>#+-=|{}.!'
    for ch in special:
        text = text.replace(ch, f'\\{ch}')
    return text

async def get_reminders_summary() -> str:
    """Fetch and format pending reminders."""
    try:
        reminders = await db_service.get_pending_reminders()
        if not reminders:
            return "📭 *No upcoming reminders\\.*"

        lines = [f"⏰ *Upcoming Reminders*\n"]
        for r in reminders:
            time_str = r.remind_at.strftime("%b %d, %I:%M %p") if r.remind_at else "?"
            lines.append(f"  • {escape_md(time_str)}: {escape_md(r.content)}")
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error fetching reminders summary: {e}")
        return "❌ Error fetching reminders."

async def get_expenses_summary(limit: int = 10) -> str:
    """Fetch and format recent expenses."""
    try:
        expenses = await db_service.get_expenses(limit=limit)
        if not expenses:
            return "📭 *No expenses logged yet\\.*"

        lines = [f"💰 *Recent Expenses*\n"]
        total = 0.0
        currency = "INR"
        
        for exp in expenses:
            date_str = exp.created_at.strftime("%b %d") if exp.created_at else "?"
            lines.append(
                f"  • {escape_md(date_str)}: {escape_md(str(exp.currency))} "
                f"{escape_md(str(exp.amount))} — {escape_md(exp.description or exp.category or 'N/A')}"
            )
            try:
                total += float(exp.amount or 0)
            except (ValueError, TypeError):
                pass
            if exp.currency:
               currency = exp.currency

        lines.append(f"\n*Total:* {escape_md(currency)} {escape_md(f'{total:.2f}')}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error fetching expenses summary: {e}")
        return "❌ Error fetching expenses."

async def get_habits_summary(limit: int = 20) -> str:
    """Fetch and format today's habits."""
    try:
        habits = await db_service.get_habits(limit=limit)
        today = ist_now().date()
        today_habits = [h for h in habits if h.logged_at and h.logged_at.date() == today]

        if not today_habits:
            return "📭 *No habits logged today\\.*"

        lines = [f"✅ *Today's Habits* — {escape_md(today.strftime('%b %d'))}\n"]
        for h in today_habits:
            time_str = h.logged_at.strftime("%I:%M %p") if h.logged_at else ""
            lines.append(f"  • {escape_md(h.habit_name)} — {escape_md(time_str)}")
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error fetching habits summary: {e}")
        return "❌ Error fetching habits."

async def get_daily_summary() -> str:
    """Generate a summary of all today's activities."""
    now = ist_now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        memories = await memory_service.retrieve_by_date_range(
            start_date=start_of_day,
            end_date=now,
            limit=50
        )

        if not memories:
            return "📭 *No activities logged yet today\\.*"

        # Group by type
        by_type = {}
        for m in memories:
            mt = m.memory_type or "other"
            by_type.setdefault(mt, []).append(m.content)

        summary_parts = [f"📊 *Today's Summary* — {escape_md(now.strftime('%b %d, %A'))}\n"]
        
        type_emoji = {
            "commit": "💻", "expense": "💰", "habit": "✅",
            "journal": "📓", "reminder": "⏰", "status_update": "📝",
            "daily_summary": "📋"
        }
        
        for mtype, items in by_type.items():
            emoji = type_emoji.get(mtype, "📌")
            summary_parts.append(f"\n{emoji} *{escape_md(mtype.replace('_', ' ').title())}* \\({len(items)}\\)")
            for item in items[:5]:  # Cap at 5 per type for brevity
                short = item[:100] + "..." if len(item) > 100 else item
                summary_parts.append(f"  • {escape_md(short)}")
            if len(items) > 5:
                summary_parts.append(f"  _\\.\\.\\.and {len(items) - 5} more_")

        return "\n".join(summary_parts)
    except Exception as e:
        logger.error(f"Error generating daily summary: {e}")
        return "❌ Couldn't generate summary."
