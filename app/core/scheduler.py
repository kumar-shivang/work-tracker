from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.telegram import bot
from app.config import Config
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=Config.TIMEZONE)

async def check_in_job():
    logger.info("Triggering hourly check-in...")
    await bot.send_checkin_message()

from app.tasks.evening_summary import generate_and_send_summary

# Schedule the job
# Runs Mon-Fri, 9 AM to 6 PM
# Schedule the job
scheduler.add_job(
    check_in_job, 
    'cron', 
    day_of_week=Config.CHECKIN_DAYS, 
    hour=f"{Config.CHECKIN_START_HOUR}-{Config.CHECKIN_END_HOUR}", 
    minute=0
)

# Evening email
scheduler.add_job(
    generate_and_send_summary, 
    'cron', 
    hour=Config.SUMMARY_HOUR, 
    minute=Config.SUMMARY_MINUTE, 
    day_of_week=Config.SUMMARY_DAYS
)

def start_scheduler():
    scheduler.start()
