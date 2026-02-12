"""
Daily Summary Task.

Runs at midnight IST to:
1. Aggregate all activities from the current day
2. Generate LLM summary
3. Create a daily_summary memory with embedding
"""
import logging
import datetime
from sqlalchemy import select, func
from app.db.connection import async_session
from app.db.models import Commit, Expense, JournalEntry, Habit, StatusUpdate
from app.services.memory import memory_service
from app.services.llm import generate_daily_summary_text

logger = logging.getLogger(__name__)


async def generate_daily_summary():
    """
    Generate and store daily summary memory at midnight.
    Aggregates all activities from the current day.
    """
    # Calculate date range for today (IST)
    ist_offset = datetime.timedelta(hours=5, minutes=30)
    ist_tz = datetime.timezone(ist_offset)
    now = datetime.datetime.now(ist_tz)
    
    # Get start and end of today in IST
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    logger.info(f"Generating daily summary for {start_of_day.date()}")
    
    # Fetch all data from today
    async with async_session() as session:
        # Commits
        commits_result = await session.execute(
            select(Commit).where(
                Commit.created_at >= start_of_day,
                Commit.created_at <= end_of_day
            )
        )
        commits = commits_result.scalars().all()
        
        # Expenses
        expenses_result = await session.execute(
            select(Expense).where(
                Expense.created_at >= start_of_day,
                Expense.created_at <= end_of_day
            )
        )
        expenses = expenses_result.scalars().all()
        
        # Journal entries
        journals_result = await session.execute(
            select(JournalEntry).where(
                JournalEntry.created_at >= start_of_day,
                JournalEntry.created_at <= end_of_day
            )
        )
        journals = journals_result.scalars().all()
        
        # Habits
        habits_result = await session.execute(
            select(Habit).where(
                Habit.logged_at >= start_of_day,
                Habit.logged_at <= end_of_day
            )
        )
        habits = habits_result.scalars().all()
        
        # Status updates
        status_result = await session.execute(
            select(StatusUpdate).where(
                StatusUpdate.created_at >= start_of_day,
                StatusUpdate.created_at <= end_of_day
            )
        )
        status_updates = status_result.scalars().all()
    
    # Calculate statistics
    total_expenses = sum(e.amount for e in expenses)
    currency = expenses[0].currency if expenses else "INR"
    
    # Get sentiment distribution for journals
    sentiment_counts = {}
    for j in journals:
        sentiment = j.sentiment or "neutral"
        sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
    
    overall_sentiment = max(sentiment_counts, key=sentiment_counts.get) if sentiment_counts else "neutral"
    
    # Get unique repos from commits
    repos = list(set(c.repo for c in commits))
    
    stats = {
        "num_commits": len(commits),
        "num_expenses": len(expenses),
        "total_expenses": total_expenses,
        "currency": currency,
        "num_journals": len(journals),
        "num_habits": len(habits),
        "num_status": len(status_updates),
        "repos": repos,
        "overall_sentiment": overall_sentiment
    }
    
    # Build summary text for LLM
    activities_text = []
    
    if commits:
        activities_text.append(f"**Code Activity:**")
        for commit in commits[:10]:  # Limit to 10 most recent
            activities_text.append(f"- {commit.title} ({commit.repo})")
    
    if expenses:
        activities_text.append(f"\n**Expenses:**")
        for expense in expenses:
            activities_text.append(f"- {expense.currency} {expense.amount} - {expense.category}: {expense.description}")
    
    if journals:
        activities_text.append(f"\n**Journal Entries:**")
        for journal in journals:
            activities_text.append(f"- ({journal.sentiment}) {journal.content[:100]}...")
    
    if habits:
        activities_text.append(f"\n**Habits Completed:**")
        habit_names = list(set(h.habit_name for h in habits))
        for habit in habit_names:
            activities_text.append(f"- {habit}")
    
    activities_summary = "\n".join(activities_text)
    
    # Generate LLM summary if we have activities
    if activities_summary:
        try:
            llm_summary = await generate_daily_summary_text(activities_summary)
        except Exception as e:
            logger.error(f"Failed to generate LLM summary: {e}")
            llm_summary = "Daily activities logged. LLM summary generation failed."
    else:
        llm_summary = "No activities recorded for today."
        logger.info("No activities to summarize for today")
        # Don't create memory if there's nothing to record
        return
    
    # Create daily summary memory
    try:
        await memory_service.create_daily_summary_memory(
            date=start_of_day.date(),
            summary_text=llm_summary,
            stats=stats
        )
        logger.info(f"Successfully created daily summary memory for {start_of_day.date()}")
    except Exception as e:
        logger.error(f"Failed to create daily summary memory: {e}")
