import asyncio
import logging
from sqlalchemy import Column, Integer, String, text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import Config

# Minimal setup to test connection + basic table creation
engine = create_async_engine(Config.DATABASE_URL, echo=True)

class Base(DeclarativeBase):
    pass

class TestTable(Base):
    __tablename__ = "test_verification"
    id = Column(Integer, primary_key=True)
    name = Column(String)

async def verify():
    print("--- Verifying Basic DB Operations ---")
    async with engine.begin() as conn:
        print("1. Dropping test table if exists...")
        await conn.run_sync(Base.metadata.drop_all)
        
        print("2. Creating test table...")
        await conn.run_sync(Base.metadata.create_all)
        print("   ✓ Table created")
    
    async with engine.connect() as conn:
        print("3. Inserting data...")
        await conn.execute(
            text("INSERT INTO test_verification (name) VALUES ('working')")
        )
        await conn.commit()
        print("   ✓ Inserted")
        
        print("4. querying data...")
        result = await conn.execute(text("SELECT name FROM test_verification"))
        row = result.fetchone()
        print(f"   ✓ Retrieved: {row[0]}")
        assert row[0] == "working"

    print("\n--- SUCCESS: Database is functional! ---")
    print("(Note: Vector features require postgresql-16-pgvector extension)")

if __name__ == "__main__":
    asyncio.run(verify())
