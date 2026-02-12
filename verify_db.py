#!/usr/bin/env python
"""Quick verification script to test database integration."""
import asyncio
import sys
sys.path.insert(0, '/home/shivang/work-tracker')

from app.services.db_service import db_service
import datetime


async def verify_db():
    print("Testing database connectivity...\n")
    
    # Test 1: Log a test expense
    print("1. Testing expense logging...")
    expense = await db_service.log_expense(
        amount=100.50,
        currency="INR",
        category="Test",
        description="Test expense from verification script"
    )
    print(f"   ✓ Created expense: {expense}")
    
    # Test 2: Log a test reminder
    print("\n2. Testing reminder logging...")
    remind_time = datetime.datetime.now() + datetime.timedelta(hours=1)
    reminder = await db_service.log_reminder(
        content="Test reminder",
        remind_at=remind_time,
        chat_id="test_chat"
    )
    print(f"   ✓ Created reminder: {reminder}")
    
    # Test 3: Log a test habit
    print("\n3. Testing habit logging...")
    habit = await db_service.log_habit(habit_name="Test habit")
    print(f"   ✓ Created habit: {habit}")
    
    # Test 4: Log a test journal
    print("\n4. Testing journal logging...")
    journal = await db_service.log_journal(
        content="Test journal entry",
        sentiment="positive"
    )
    print(f"   ✓ Created journal entry: {journal}")
    
    # Test 5: Retrieve data
    print("\n5. Retrieving recent data...")
    expenses = await db_service.get_expenses(limit=5)
    print(f"   ✓ Found {len(expenses)} recent expenses")
    
    reminders = await db_service.get_pending_reminders()
    print(f"   ✓ Found {len(reminders)} pending reminders")
    
    habits = await db_service.get_habits(limit=5)
    print(f"   ✓ Found {len(habits)} recent habits")
    
    journals = await db_service.get_journal_entries(limit=5)
    print(f"   ✓ Found {len(journals)} recent journal entries")
    
    print("\n✓ All database operations successful!")


if __name__ == "__main__":
    asyncio.run(verify_db())
