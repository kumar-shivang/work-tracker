#!/usr/bin/env python3
"""Quick check of memories in database."""
import asyncio
from app.db.connection import async_session
from app.db.models import Memory
from sqlalchemy import select, func


async def check_memories():
    async with async_session() as session:
        # Count total
        count_result = await session.execute(select(func.count()).select_from(Memory))
        total = count_result.scalar()
        
        print(f"\nTotal memories: {total}")
        
        # Count by type
        types_result = await session.execute(
            select(Memory.memory_type, func.count())
            .group_by(Memory.memory_type)
        )
        
        print("\nMemories by type:")
        for memory_type, count in types_result.all():
            print(f"  {memory_type}: {count}")


if __name__ == "__main__":
    asyncio.run(check_memories())
