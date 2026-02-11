import asyncio
from unittest.mock import MagicMock, AsyncMock
from app.services.telegram import bot
from telegram import Update, User, Message, Chat
import os
import datetime

async def test_handle_message():
    print("Testing handle_message logic...")
    
    # Mock Update object
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = int(bot.chat_id) if bot.chat_id else 12345
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = int(bot.chat_id) if bot.chat_id else 12345
    update.message = MagicMock(spec=Message)
    update.message.text = "Working on Phase 2 verification"
    
    # Mock Context
    context = MagicMock()
    context.bot.send_message = AsyncMock()
    
    # Run handler
    await bot.handle_message(update, context)
    
    # Check if report file was created
    today = datetime.datetime.now().strftime("%d-%m-%Y")
    report_file = os.path.join("reports", f"{today}.md")
    
    if os.path.exists(report_file):
        with open(report_file, "r") as f:
            content = f.read()
            if "Working on Phase 2 verification" in content:
                print("SUCCESS: Message logged to report.")
            else:
                print("FAILURE: Message not found in report.")
                print("Content:", content)
    else:
        print(f"FAILURE: Report file {report_file} not found.")

if __name__ == "__main__":
    asyncio.run(test_handle_message())
