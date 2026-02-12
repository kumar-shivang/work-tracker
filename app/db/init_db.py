"""
Database initialization.
Creates all tables and enables required extensions.
"""
import logging
from sqlalchemy import text
from app.db.connection import engine
from app.db.models import Base

logger = logging.getLogger(__name__)


async def init_db():
    """Initialize the database: enable extensions and create all tables."""
    async with engine.begin() as conn:
        # Enable pgvector extension
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("pgvector extension enabled")
        except Exception as e:
            logger.warning(f"Could not enable pgvector extension: {e}")
            logger.warning("Vector memory features will not be available")

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified successfully")
