import logging
import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from app.config import Config
from app.services.github import append_to_report

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

from app.services.google_docs import google_doc_client

class TelegramBot:
    def __init__(self):
        self.application = ApplicationBuilder().token(Config.TELEGRAM_BOT_TOKEN).build()
        self.chat_id = Config.MY_TELEGRAM_CHAT_ID
        self._setup_handlers()
        
    def _setup_handlers(self):
        start_handler = CommandHandler('start', self.start)
        message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message)
        
        self.application.add_handler(start_handler)
        self.application.add_handler(message_handler)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="I'm your Personal Assistant bot! I'll check in with you hourly."
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        if user_id != self.chat_id and self.chat_id:
            # Security check: only allow owner to log updates
            # If chat_id isn't set yet, we might want to log it to help setup
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Unauthorized user.")
            return

        message_text = update.message.text
        # We treat any text message as a status update for now
        # Ideally we'd correlate this with a specific check-in request, 
        # but for simplicity, we'll log all text messages as updates.
        
        logger.info(f"Received message from {user_id}: {message_text}")
        
        # Log to report
        self.log_checkin(message_text)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Got it! Logged your status."
        )

    def log_checkin(self, text: str):
        """Append the check-in to the Google Doc."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M")
        
        entry = f"""
🕐 Check-In at {timestamp}

Status: {text}

--------------------------------------------------
"""
        google_doc_client.append_entry(entry)

    async def send_checkin_message(self):
        if not self.chat_id:
            logger.warning("No Chat ID set for Telegram bot.")
            return
            
        try:
            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text="🕐 **Hourly Check-In**\nWhat are you working on right now?"
            )
        except Exception as e:
            logger.error(f"Failed to send check-in: {e}")

    async def initialize(self):
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling() # This runs in background

    async def shutdown(self):
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()

# Singleton instance
bot = TelegramBot()
