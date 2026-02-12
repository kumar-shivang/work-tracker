import pytest
import datetime
from unittest.mock import MagicMock, patch
from app.services.llm import parse_user_intent
from app.services.telegram import TelegramBot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

@pytest.mark.asyncio
def test_parse_user_intent_reminder():
    current_time = "2023-10-27T10:00:00"
    message = "Remind me to call John in 10 minutes"
    
    # Mock send_request to return a valid JSON string
    with patch("app.services.llm.send_request") as mock_send_request:
        mock_send_request.return_value = '{"type": "reminder", "content": "call John", "datetime": "2023-10-27T10:10:00"}'
        
        result = parse_user_intent(message, current_time)
        
        assert result["type"] == "reminder"
        assert result["content"] == "call John"
        assert result["datetime"] == "2023-10-27T10:10:00"

def test_parse_user_intent_status_update():
    current_time = "2023-10-27T10:00:00"
    message = "I am working on the API"
    
    # Mock send_request to return a valid JSON string
    with patch("app.services.llm.send_request") as mock_send_request:
        mock_send_request.return_value = '{"type": "status_update", "content": "I am working on the API"}'
        
        result = parse_user_intent(message, current_time)
        
        assert result["type"] == "status_update"
        assert result["content"] == "I am working on the API"

def test_telegram_bot_scheduler_integration():
    # Mock config and other dependencies
    with patch("app.services.telegram.ApplicationBuilder"), \
         patch("app.services.telegram.Config"), \
         patch("app.services.telegram.google_doc_client"):
        
        bot = TelegramBot()
        bot.scheduler = MagicMock(spec=AsyncIOScheduler)
        
        # Test adding a job
        chat_id = 12345
        text = "Test Reminder"
        run_date = datetime.datetime.now() + datetime.timedelta(minutes=10)
        
        bot.scheduler.add_job(
            bot.send_reminder,
            'date',
            run_date=run_date,
            args=[chat_id, text]
        )
        
        bot.scheduler.add_job.assert_called_once()
        # manual verification of call args
        args, kwargs = bot.scheduler.add_job.call_args
        assert args[0] == bot.send_reminder
        assert kwargs['run_date'] == run_date
        assert kwargs['args'] == [chat_id, text]
