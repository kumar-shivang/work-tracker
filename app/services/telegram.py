import logging
import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import Config
from app.services.github import append_to_report
from app.services.llm import parse_user_intent
import datetime

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

from app.services.google_workspace import workspace_manager

class TelegramBot:
    def __init__(self):
        self.application = ApplicationBuilder().token(Config.TELEGRAM_BOT_TOKEN).build()
        self.chat_id = Config.MY_TELEGRAM_CHAT_ID
        self.scheduler = AsyncIOScheduler()
        self._setup_handlers()
        
    def _setup_handlers(self):
        start_handler = CommandHandler('start', self.start)
        message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message)
        
        self.application.add_handler(start_handler)
        self.application.add_handler(message_handler)

        # Schedule daily prompt at 9 PM IST
        import datetime
        ist_offset = datetime.timedelta(hours=5, minutes=30)
        ist_tz = datetime.timezone(ist_offset)
        
        self.scheduler.add_job(
            self.send_daily_prompt,
            'cron',
            hour=21,
            minute=0,
            timezone=ist_tz
        )

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
        
        # Interpret intent
        ist_offset = datetime.timedelta(hours=5, minutes=30)
        ist_tz = datetime.timezone(ist_offset)
        current_time = datetime.datetime.now(ist_tz).isoformat()
        intent = parse_user_intent(message_text, current_time)
        
        if intent.get("type") == "reminder":
            reminder_text = intent.get("content")
            reminder_time_str = intent.get("datetime")
            
            if not reminder_time_str:
                 await context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text="I understood you want a reminder, but I couldn't figure out the time. Please try again."
                )
                 return

            try:
                reminder_time = datetime.datetime.fromisoformat(reminder_time_str)
                if reminder_time < datetime.datetime.now(ist_tz):
                     await context.bot.send_message(
                        chat_id=update.effective_chat.id, 
                        text=f"The time {reminder_time.strftime('%H:%M')} has already passed. I'll remind you now: {reminder_text}"
                    )
                else:
                    self.scheduler.add_job(
                        self.send_reminder,
                        'date',
                        run_date=reminder_time,
                        args=[update.effective_chat.id, reminder_text]
                    )
                    
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id, 
                        text=f"I've set a reminder for {reminder_time.strftime('%Y-%m-%d %H:%M')}: {reminder_text}"
                    )
            except ValueError:
                 await context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text="I couldn't understand the time for the reminder. Please try again."
                )
        
        elif intent.get("type") == "expense":
            amount = intent.get("amount")
            currency = intent.get("currency", "INR")
            category = intent.get("category", "General")
            desc = intent.get("content")
            
            # Log to Sheets
            ist_offset = datetime.timedelta(hours=5, minutes=30)
            ist_tz = datetime.timezone(ist_offset)
            now = datetime.datetime.now(ist_tz)
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")

            workspace_manager.append_row(
                "PersonalLife", 
                "Expenses",
                [date_str, time_str, amount, currency, category, desc]
            )
             
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f"Logged expense: {currency} {amount} for {category}."
            )

        elif intent.get("type") == "habit":
            habit = intent.get("content")
            
            # Log to Sheets
            ist_offset = datetime.timedelta(hours=5, minutes=30)
            ist_tz = datetime.timezone(ist_offset)
            now = datetime.datetime.now(ist_tz)
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")

            workspace_manager.append_row(
                "PersonalLife", 
                "Habits",
                [date_str, time_str, habit, "Done"]
            )
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f"Great job! Logged habit: {habit}"
            )

        elif intent.get("type") == "journal":
            entry = intent.get("content")
            sentiment = intent.get("sentiment", "neutral")
            
            # Log to Sheets
            ist_offset = datetime.timedelta(hours=5, minutes=30)
            ist_tz = datetime.timezone(ist_offset)
            now = datetime.datetime.now(ist_tz)
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")

            workspace_manager.append_row(
                "PersonalLife", 
                "Journal",
                [date_str, time_str, sentiment, entry]
            )
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="Saved your journal entry. Have a good rest!"
            )
            
        else:
            # Assume status update
            logger.info(f"Received message from {user_id}: {message_text}")
            
            # Log to report
            self.log_checkin(f"📝 Status: {message_text}")
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="Got it! Logged your status."
            )

    def log_checkin(self, text: str):
        """Append the check-in to the Google Doc."""
        import datetime
        ist_offset = datetime.timedelta(hours=5, minutes=30)
        ist_tz = datetime.timezone(ist_offset)
        timestamp = datetime.datetime.now(ist_tz).strftime("%H:%M")
        
        entry = f"{timestamp} - {text}"
        workspace_manager.append_to_doc("WorkTracker", entry)

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

    async def send_daily_prompt(self):
        if not self.chat_id:
            return
        
        try:
            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text="🌙 **Daily Reflection**\nHow was your day? (Reply to log in journal)"
            )
        except Exception as e:
            logger.error(f"Failed to send daily prompt: {e}")

    async def send_reminder(self, chat_id: int, text: str):
        try:
             await self.application.bot.send_message(
                chat_id=chat_id,
                text=f"🔔 **REMINDER**: {text}"
            )
        except Exception as e:
            logger.error(f"Failed to send reminder: {e}")

    async def initialize(self):
        await self.application.initialize()
        self.scheduler.start()
        await self.application.start()
        await self.application.updater.start_polling() # This runs in background

    async def shutdown(self):
        self.scheduler.shutdown()
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()

# Singleton instance
bot = TelegramBot()
