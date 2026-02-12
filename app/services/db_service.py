"""
Database service layer.
Provides CRUD functions for all database tables.
"""
import logging
import time
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.connection import async_session
from app.db.models import (
    Commit, Reminder, Expense, Habit, JournalEntry,
    StatusUpdate, LLMLog, Memory
)

logger = logging.getLogger(__name__)


class DBService:
    """Async database service for all CRUD operations."""

    # ─── Commits ─────────────────────────────────────────────

    async def log_commit(
        self,
        sha: str,
        repo: str,
        branch: str,
        author: str,
        message: str,
        title: str,
        summary: dict,
        diff_snippet: str = None,
    ) -> Commit:
        async with async_session() as session:
            commit = Commit(
                sha=sha,
                repo=repo,
                branch=branch,
                author=author,
                message=message,
                title=title,
                summary=summary,
                diff_snippet=diff_snippet[:5000] if diff_snippet else None,
            )
            session.add(commit)
            await session.commit()
            await session.refresh(commit)
            logger.info(f"Logged commit {sha[:7]} to database")
            return commit

    async def get_commits(self, repo: str = None, limit: int = 50) -> List[Commit]:
        async with async_session() as session:
            query = select(Commit).order_by(Commit.created_at.desc()).limit(limit)
            if repo:
                query = query.where(Commit.repo == repo)
            result = await session.execute(query)
            return result.scalars().all()

    # ─── Reminders ───────────────────────────────────────────

    async def log_reminder(
        self, content: str, remind_at, chat_id: str = None
    ) -> Reminder:
        async with async_session() as session:
            reminder = Reminder(
                content=content,
                remind_at=remind_at,
                chat_id=chat_id,
            )
            session.add(reminder)
            await session.commit()
            await session.refresh(reminder)
            logger.info(f"Logged reminder: {content[:30]}...")
            return reminder

    async def mark_reminder_fired(self, reminder_id: int):
        async with async_session() as session:
            await session.execute(
                update(Reminder)
                .where(Reminder.id == reminder_id)
                .values(is_fired=True)
            )
            await session.commit()

    async def get_pending_reminders(self) -> List[Reminder]:
        async with async_session() as session:
            result = await session.execute(
                select(Reminder)
                .where(Reminder.is_fired == False)
                .order_by(Reminder.remind_at)
            )
            return result.scalars().all()

    # ─── Expenses ────────────────────────────────────────────

    async def log_expense(
        self, amount: float, currency: str, category: str, description: str
    ) -> Expense:
        async with async_session() as session:
            expense = Expense(
                amount=amount,
                currency=currency,
                category=category,
                description=description,
            )
            session.add(expense)
            await session.commit()
            await session.refresh(expense)
            logger.info(f"Logged expense: {currency} {amount} ({category})")
            return expense

    async def get_expenses(self, limit: int = 50) -> List[Expense]:
        async with async_session() as session:
            result = await session.execute(
                select(Expense).order_by(Expense.created_at.desc()).limit(limit)
            )
            return result.scalars().all()

    # ─── Habits ──────────────────────────────────────────────

    async def log_habit(self, habit_name: str) -> Habit:
        async with async_session() as session:
            habit = Habit(habit_name=habit_name)
            session.add(habit)
            await session.commit()
            await session.refresh(habit)
            logger.info(f"Logged habit: {habit_name}")
            return habit

    async def get_habits(self, limit: int = 50) -> List[Habit]:
        async with async_session() as session:
            result = await session.execute(
                select(Habit).order_by(Habit.logged_at.desc()).limit(limit)
            )
            return result.scalars().all()

    # ─── Journal Entries ─────────────────────────────────────

    async def log_journal(self, content: str, sentiment: str = "neutral") -> JournalEntry:
        async with async_session() as session:
            entry = JournalEntry(content=content, sentiment=sentiment)
            session.add(entry)
            await session.commit()
            await session.refresh(entry)
            logger.info(f"Logged journal entry (sentiment: {sentiment})")
            return entry

    async def get_journal_entries(self, limit: int = 50) -> List[JournalEntry]:
        async with async_session() as session:
            result = await session.execute(
                select(JournalEntry)
                .order_by(JournalEntry.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()

    # ─── Status Updates ──────────────────────────────────────

    async def log_status_update(
        self, content: str, source: str = "telegram"
    ) -> StatusUpdate:
        async with async_session() as session:
            status = StatusUpdate(content=content, source=source)
            session.add(status)
            await session.commit()
            await session.refresh(status)
            logger.info(f"Logged status update from {source}")
            return status

    # ─── LLM I/O Logging ────────────────────────────────────

    async def log_llm_call(
        self,
        function_name: str,
        model: str,
        input_messages: list,
        input_schema: dict = None,
        output_raw: str = None,
        output_parsed: dict = None,
        duration_ms: int = None,
        error: str = None,
    ) -> LLMLog:
        async with async_session() as session:
            log = LLMLog(
                function_name=function_name,
                model=model,
                input_messages=input_messages,
                input_schema=input_schema,
                output_raw=output_raw,
                output_parsed=output_parsed,
                duration_ms=duration_ms,
                error=error,
            )
            session.add(log)
            await session.commit()
            await session.refresh(log)
            logger.debug(f"Logged LLM call: {function_name}")
            return log

    async def get_llm_logs(
        self, function_name: str = None, limit: int = 50
    ) -> List[LLMLog]:
        async with async_session() as session:
            query = select(LLMLog).order_by(LLMLog.created_at.desc()).limit(limit)
            if function_name:
                query = query.where(LLMLog.function_name == function_name)
            result = await session.execute(query)
            return result.scalars().all()

    # ─── Vector Memory Store ─────────────────────────────────

    async def store_memory(
        self,
        content: str,
        embedding: list,
        memory_type: str = "general",
        metadata: dict = None,
    ) -> Memory:
        async with async_session() as session:
            memory = Memory(
                content=content,
                embedding=embedding,
                memory_type=memory_type,
                metadata_=metadata or {},
            )
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
            logger.info(f"Stored memory (type: {memory_type})")
            return memory

    async def search_memories(
        self,
        query_embedding: list,
        memory_type: str = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search memories by cosine similarity.
        Returns list of dicts with 'content', 'memory_type', 'metadata', 'distance'.
        """
        async with async_session() as session:
            # Use pgvector cosine distance operator <=>
            query = (
                select(
                    Memory.id,
                    Memory.content,
                    Memory.memory_type,
                    Memory.metadata_,
                    Memory.created_at,
                    Memory.embedding.cosine_distance(query_embedding).label("distance"),
                )
                .order_by("distance")
                .limit(limit)
            )
            if memory_type:
                query = query.where(Memory.memory_type == memory_type)

            result = await session.execute(query)
            rows = result.all()

            return [
                {
                    "id": row.id,
                    "content": row.content,
                    "memory_type": row.memory_type,
                    "metadata": row.metadata_,
                    "distance": float(row.distance),
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]


# Singleton instance
db_service = DBService()
