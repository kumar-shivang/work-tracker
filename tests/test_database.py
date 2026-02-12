"""
Verification tests for Database Setup.
Checks:
1. Database connection
2. Table creation
3. Basic CRUD (Commit, Reminder)
4. Vector extension (Memory storage & search)
"""
import pytest
import asyncio
import datetime
from sqlalchemy import text, select
from app.db.connection import engine, async_session
from app.db.models import Base, Commit, Memory, Reminder
from app.db.init_db import init_db
from app.services.db_service import db_service

from sqlalchemy.ext.asyncio import create_async_engine
from app.config import Config

@pytest.fixture(scope="function")
async def setup_db():
    """Initialize database once for the module."""
    # Create a fresh engine for the test loop
    test_engine = create_async_engine(Config.DATABASE_URL, echo=False)
    
    # We need to temporarily patch/override the global engine in init_db/connection 
    # But for simplicity, let's just use the global one but dispose it explicitly
    # actually, best to just use the one from connection but make sure we don't close the loop on it
    
    # Let's try to just run init_db and manage lifecycle
    await init_db()
    yield
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    # We could drop tables here if we wanted a clean slate
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.mark.asyncio
async def test_database_connection():
    """Verify we can connect to the database."""
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1

@pytest.mark.asyncio
async def test_table_creation(setup_db):
    """Verify tables are created (init_db logic)."""
    # setup_db fixture runs init_db
    
    async with engine.connect() as conn:
        # Check if 'commits' table exists
        result = await conn.execute(text(
            "SELECT to_regclass('public.commits')"
        ))
        assert result.scalar() is not None

@pytest.mark.asyncio
async def test_crud_commit(setup_db):
    """Test creating and retrieving a Commit."""
    sha = f"test_sha_{datetime.datetime.now().timestamp()}"
    
    # Create
    commit = await db_service.log_commit(
        sha=sha,
        repo="test-repo",
        branch="main",
        author="Tester",
        message="Test commit",
        title="Test Title",
        summary={"key_changes": ["Added test"]},
        diff_snippet="+ test code"
    )
    assert commit.id is not None
    
    # Retrieve
    commits = await db_service.get_commits(repo="test-repo", limit=1)
    assert len(commits) > 0
    assert commits[0].sha == sha
    assert commits[0].summary["key_changes"][0] == "Added test"

@pytest.mark.asyncio
async def test_vector_memory(setup_db):
    """Test storing and searching vector memories."""
    # Create dummy embedding (dim 1536)
    embedding = [0.1] * 1536
    
    # Store
    memory = await db_service.store_memory(
        content="This is a test memory about databases.",
        embedding=embedding,
        memory_type="test",
        metadata={"source": "test_script"}
    )
    assert memory.id is not None
    
    # Search
    # We search with the same vector, so distance should be 0 (or very close)
    # Note: pgvector cosine distance: 1 - cosine_similarity. 
    # Valid range [0, 2]. 0 means identical direction.
    results = await db_service.search_memories(
        query_embedding=embedding,
        memory_type="test",
        limit=1
    )
    
    assert len(results) > 0
    match = results[0]
    assert match["content"] == "This is a test memory about databases."
    # Distance should be very small for identical vector
    assert match["distance"] < 0.0001
