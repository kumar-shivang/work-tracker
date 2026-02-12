"""
SQLAlchemy ORM models for Work Tracker database.

Tables:
  - commits: Git commit summaries with structured JSONB data
  - reminders: Scheduled reminders from Telegram bot
  - expenses: Expense tracking
  - habits: Habit logging
  - journal_entries: Journal/reflections
  - status_updates: Status check-ins
  - llm_logs: Full LLM input/output audit trail (JSONB)
  - memories: Vector memory store for context retrieval (pgvector)
"""
import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime,
    Index, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


# ─── Structured Data Tables ─────────────────────────────────

class Commit(Base):
    __tablename__ = "commits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sha = Column(String(40), unique=True, nullable=False, index=True)
    repo = Column(String(255), nullable=False)
    branch = Column(String(255))
    author = Column(String(255))
    message = Column(Text)
    title = Column(String(255))
    summary = Column(JSONB)           # {files_modified, key_changes, purpose}
    diff_snippet = Column(Text)       # First N chars of diff for reference
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Commit(sha='{self.sha[:7]}', repo='{self.repo}')>"


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    remind_at = Column(DateTime(timezone=True), nullable=False, index=True)
    is_fired = Column(Boolean, default=False)
    chat_id = Column(String(50))      # Telegram chat ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Reminder(content='{self.content[:30]}...', at={self.remind_at})>"


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    category = Column(String(100))
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Expense({self.currency} {self.amount}, {self.category})>"


class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    habit_name = Column(String(255), nullable=False)
    logged_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Habit('{self.habit_name}')>"


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    sentiment = Column(String(20))    # positive, neutral, negative
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<JournalEntry(sentiment='{self.sentiment}')>"


class StatusUpdate(Base):
    __tablename__ = "status_updates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    source = Column(String(50), default="telegram")  # telegram, webhook, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<StatusUpdate('{self.content[:30]}...')>"


# ─── LLM I/O Logging (JSONB) ────────────────────────────────

class LLMLog(Base):
    __tablename__ = "llm_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    function_name = Column(String(100), index=True)  # e.g. summarize_diff, parse_user_intent
    model = Column(String(100))
    input_messages = Column(JSONB)     # Full messages array sent to LLM
    input_schema = Column(JSONB)       # Response format schema, if any
    output_raw = Column(Text)          # Raw string response from LLM
    output_parsed = Column(JSONB)      # Parsed JSON output, if applicable
    duration_ms = Column(Integer)      # How long the call took
    error = Column(Text)               # Error message if call failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<LLMLog(fn='{self.function_name}', model='{self.model}')>"


# ─── Vector Memory Store (pgvector) ─────────────────────────

class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))   # OpenAI embedding dimension
    metadata_ = Column("metadata", JSONB)  # Extra context (source, tags, etc.)
    memory_type = Column(String(50), index=True)  # conversation, commit, journal, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Memory(type='{self.memory_type}', content='{self.content[:30]}...')>"


# Index for vector similarity search (cosine distance)
Index(
    "ix_memories_embedding",
    Memory.embedding,
    postgresql_using="ivfflat",
    postgresql_with={"lists": 100},
    postgresql_ops={"embedding": "vector_cosine_ops"},
)
