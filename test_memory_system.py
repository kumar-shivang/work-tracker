#!/usr/bin/env python3
"""
Test script for memory system.
Tests embedding generation, memory creation, and semantic search.
"""
import asyncio
import datetime
from app.services.memory import memory_service
from app.services.db_service import db_service


async def test_embedding_generation():
    """Test that embeddings are generated correctly."""
    print("\n" + "="*60)
    print("TEST 1: Embedding Generation")
    print("="*60)
    
    test_text = "I spent 500 INR on groceries at the local market"
    
    try:
        embedding = await memory_service.generate_embedding(test_text)
        print(f"✓ Successfully generated embedding")
        print(f"  Dimension: {len(embedding)}")
        print(f"  First 5 values: {embedding[:5]}")
        
        assert len(embedding) == 1536, "Embedding dimension should be 1536"
        print("✓ Embedding dimension is correct (1536)")
        
        return True
    except Exception as e:
        print(f"✗ Failed to generate embedding: {e}")
        return False


async def test_memory_creation():
    """Test creating memories for different data types."""
    print("\n" + "="*60)
    print("TEST 2: Memory Creation")
    print("="*60)
    
    # Test creating an expense memory
    try:
        expense = await db_service.log_expense(
            amount=500.0,
            currency="INR",
            category="Groceries",
            description="Weekly groceries from local market"
        )
        print(f"✓ Created expense: {expense.description}")
        
        # Wait a moment for memory to be created
        await asyncio.sleep(2)
        
        # Query memories to see if it was created
        result = await db_service.search_memories(
            query_embedding=await memory_service.generate_embedding("groceries"),
            memory_type="expense",
            limit=5
        )
        
        if result:
            print(f"✓ Found {len(result)} expense memories in database")
            print(f"  Most recent: {result[0]['content'][:80]}...")
        else:
            print("⚠ No expense memories found (may take a moment to create)")
        
        return True
    except Exception as e:
        print(f"✗ Failed to create memory: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_semantic_search():
    """Test semantic search functionality."""
    print("\n" + "="*60)
    print("TEST 3: Semantic Search")
    print("="*60)
    
    test_queries = [
        ("What did I spend money on?", "expense"),
        ("What code changes were made?", "commit"),
        ("What did I write in my journal?", "journal"),
    ]
    
    for query, expected_type in test_queries:
        print(f"\nQuery: '{query}'")
        print(f"Expected type: {expected_type}")
        
        try:
            results = await memory_service.search_memories(
                query=query,
                memory_type=expected_type,
                limit=3
            )
            
            if results:
                print(f"✓ Found {len(results)} results")
                for i, result in enumerate(results, 1):
                    print(f"  {i}. [{result['memory_type']}] {result['content'][:60]}...")
                    print(f"     Distance: {result['distance']:.4f}")
            else:
                print(f"  No results found (database may be empty)")
                
        except Exception as e:
            print(f"✗ Search failed: {e}")
    
    return True


async def test_date_range_retrieval():
    """Test retrieving memories by date range."""
    print("\n" + "="*60)
    print("TEST 4: Date Range Retrieval")
    print("="*60)
    
    # Get today's memories
    ist_offset = datetime.timedelta(hours=5, minutes=30)
    ist_tz = datetime.timezone(ist_offset)
    now = datetime.datetime.now(ist_tz)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59)
    
    try:
        memories = await memory_service.retrieve_by_date_range(
            start_date=start_of_day,
            end_date=end_of_day,
            limit=10
        )
        
        print(f"✓ Found {len(memories)} memories from today")
        
        # Group by type
        by_type = {}
        for mem in memories:
            by_type[mem.memory_type] = by_type.get(mem.memory_type, 0) + 1
        
        if by_type:
            print("  Breakdown by type:")
            for mem_type, count in by_type.items():
                print(f"    - {mem_type}: {count}")
        
        return True
    except Exception as e:
        print(f"✗ Date range retrieval failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*70)
    print(" MEMORY SYSTEM VERIFICATION TEST SUITE")
    print("="*70)
    
    results = []
    
    # Test 1: Embedding generation
    results.append(await test_embedding_generation())
    
    # Test 2: Memory creation
    results.append(await test_memory_creation())
    
    # Test 3: Semantic search
    results.append(await test_semantic_search())
    
    # Test 4: Date range retrieval
    results.append(await test_date_range_retrieval())
    
    # Summary
    print("\n" + "="*70)
    print(" TEST SUMMARY")
    print("="*70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total} tests")
    
    if passed == total:
        print("✓ All tests passed!")
    else:
        print(f"⚠ {total - passed} test(s) failed")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
