"""
Memory Service with Vector Embeddings.

Handles:
- Embedding generation via OpenRouter API
- Memory creation for all data types (commits, reminders, expenses, etc.)
- Semantic search and retrieval using pgvector cosine similarity
- Daily summary aggregation
"""
import logging
import httpx
import datetime
from typing import List, Dict, Any, Optional
from app.config import Config
from app.db.models import Commit, Reminder, Expense, Habit, JournalEntry, StatusUpdate, Memory
from app.services.db_service import db_service

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for creating and retrieving vector memories."""
    
    def __init__(self):
        self.embedding_model = "openai/text-embedding-3-small"
        self.embedding_dimension = 1536
        self.api_key = Config.OPENAI_API_KEY
        self.base_url = Config.OPENAI_BASE_URL
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for given text using OpenRouter API.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
            
        Raises:
            Exception: If API call fails
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.embedding_model,
                        "input": text
                    }
                )
                response.raise_for_status()
                data = response.json()
                embedding = data['data'][0]['embedding']
                logger.debug(f"Generated embedding for text (length: {len(text)})")
                return embedding
                
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    # ─── Memory Creation Functions ──────────────────────────────
    
    async def create_commit_memory(self, commit: Commit) -> Memory:
        """
        Create a memory from a commit with rich context.
        
        Args:
            commit: Commit object from database
            
        Returns:
            Created Memory object
        """
        # Format content for embedding
        files = ", ".join(commit.summary.get("files_modified", [])) if commit.summary else ""
        changes = "\n".join(commit.summary.get("key_changes", [])) if commit.summary else ""
        purpose = commit.summary.get("purpose", "") if commit.summary else ""
        
        content = f"""[{commit.created_at.strftime('%Y-%m-%d %H:%M')}] Commit: {commit.title}
Repository: {commit.repo}
Branch: {commit.branch}
Author: {commit.author}
Purpose: {purpose}
Key Changes:
{changes}
Files: {files}"""
        
        # Generate embedding
        embedding = await self.generate_embedding(content)
        
        # Create metadata
        metadata = {
            "repo": commit.repo,
            "sha": commit.sha,
            "branch": commit.branch,
            "author": commit.author,
            "files_count": len(commit.summary.get("files_modified", [])) if commit.summary else 0
        }
        
        # Store in database
        memory = await db_service.store_memory(
            content=content,
            embedding=embedding,
            memory_type="commit",
            metadata=metadata
        )
        
        logger.info(f"Created commit memory: {commit.sha[:7]}")
        return memory
    
    async def create_reminder_memory(self, reminder: Reminder) -> Memory:
        """Create a memory from a reminder."""
        content = f"[{reminder.remind_at.strftime('%Y-%m-%d %H:%M')}] Reminder: {reminder.content}"
        
        embedding = await self.generate_embedding(content)
        
        metadata = {
            "chat_id": reminder.chat_id,
            "is_fired": reminder.is_fired,
            "remind_at": reminder.remind_at.isoformat()
        }
        
        memory = await db_service.store_memory(
            content=content,
            embedding=embedding,
            memory_type="reminder",
            metadata=metadata
        )
        
        logger.info(f"Created reminder memory: {reminder.content[:30]}...")
        return memory
    
    async def create_expense_memory(self, expense: Expense) -> Memory:
        """Create a memory from an expense."""
        content = f"[{expense.created_at.strftime('%Y-%m-%d %H:%M')}] Spent {expense.amount} {expense.currency} on {expense.category}: {expense.description}"
        
        embedding = await self.generate_embedding(content)
        
        metadata = {
            "amount": expense.amount,
            "currency": expense.currency,
            "category": expense.category
        }
        
        memory = await db_service.store_memory(
            content=content,
            embedding=embedding,
            memory_type="expense",
            metadata=metadata
        )
        
        logger.info(f"Created expense memory: {expense.currency} {expense.amount}")
        return memory
    
    async def create_journal_memory(self, journal: JournalEntry) -> Memory:
        """Create a memory from a journal entry."""
        content = f"[{journal.created_at.strftime('%Y-%m-%d %H:%M')}] Journal ({journal.sentiment}): {journal.content}"
        
        embedding = await self.generate_embedding(content)
        
        metadata = {
            "sentiment": journal.sentiment
        }
        
        memory = await db_service.store_memory(
            content=content,
            embedding=embedding,
            memory_type="journal",
            metadata=metadata
        )
        
        logger.info(f"Created journal memory with sentiment: {journal.sentiment}")
        return memory
    
    async def create_habit_memory(self, habit: Habit) -> Memory:
        """Create a memory from a habit log."""
        content = f"[{habit.logged_at.strftime('%Y-%m-%d %H:%M')}] Completed habit: {habit.habit_name}"
        
        embedding = await self.generate_embedding(content)
        
        metadata = {
            "habit_name": habit.habit_name
        }
        
        memory = await db_service.store_memory(
            content=content,
            embedding=embedding,
            memory_type="habit",
            metadata=metadata
        )
        
        logger.info(f"Created habit memory: {habit.habit_name}")
        return memory
    
    async def create_status_memory(self, status: StatusUpdate) -> Memory:
        """Create a memory from a status update."""
        content = f"[{status.created_at.strftime('%Y-%m-%d %H:%M')}] Status: {status.content}"
        
        embedding = await self.generate_embedding(content)
        
        metadata = {
            "source": status.source
        }
        
        memory = await db_service.store_memory(
            content=content,
            embedding=embedding,
            memory_type="status_update",
            metadata=metadata
        )
        
        logger.info(f"Created status update memory from {status.source}")
        return memory
    
    async def create_daily_summary_memory(
        self, 
        date: datetime.date,
        summary_text: str,
        stats: Dict[str, Any]
    ) -> Memory:
        """
        Create a memory for daily summary.
        
        Args:
            date: Date of the summary
            summary_text: LLM-generated summary text
            stats: Dictionary with counts and totals
            
        Returns:
            Created Memory object
        """
        content = f"""Daily Summary for {date.strftime('%Y-%m-%d')}

{summary_text}

Statistics:
- Commits: {stats.get('num_commits', 0)}
- Expenses: {stats.get('num_expenses', 0)} ({stats.get('total_expenses', 0)} {stats.get('currency', 'INR')})
- Journal entries: {stats.get('num_journals', 0)}
- Habits logged: {stats.get('num_habits', 0)}
- Status updates: {stats.get('num_status', 0)}"""
        
        embedding = await self.generate_embedding(content)
        
        metadata = {
            "date": date.isoformat(),
            **stats
        }
        
        memory = await db_service.store_memory(
            content=content,
            embedding=embedding,
            memory_type="daily_summary",
            metadata=metadata
        )
        
        logger.info(f"Created daily summary memory for {date}")
        return memory
    
    # ─── Retrieval Functions ────────────────────────────────────
    
    async def search_memories(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search memories using semantic similarity.
        
        Args:
            query: Search query text
            memory_type: Optional filter by memory type
            limit: Maximum number of results
            
        Returns:
            List of memory dictionaries with content, metadata, and similarity scores
        """
        # Generate embedding for query
        query_embedding = await self.generate_embedding(query)
        
        # Search using db_service
        results = await db_service.search_memories(
            query_embedding=query_embedding,
            memory_type=memory_type,
            limit=limit
        )
        
        logger.info(f"Search query '{query}' returned {len(results)} results")
        return results
    
    async def retrieve_by_date_range(
        self,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        memory_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Memory]:
        """
        Retrieve memories within a date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            memory_type: Optional filter by memory type
            limit: Maximum number of results
            
        Returns:
            List of Memory objects
        """
        from sqlalchemy import select
        from app.db.connection import async_session
        
        async with async_session() as session:
            query = (
                select(Memory)
                .where(Memory.created_at >= start_date)
                .where(Memory.created_at <= end_date)
                .order_by(Memory.created_at.desc())
                .limit(limit)
            )
            
            if memory_type:
                query = query.where(Memory.memory_type == memory_type)
            
            result = await session.execute(query)
            memories = result.scalars().all()
            
        logger.info(f"Retrieved {len(memories)} memories from {start_date} to {end_date}")
        return memories


# Singleton instance
memory_service = MemoryService()
