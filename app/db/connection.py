"""
Database connection management.
Provides async SQLAlchemy engine and session factory.
"""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import Config

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    Config.DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def get_engine():
    return engine


async def get_session() -> AsyncSession:
    """FastAPI dependency for getting a DB session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
