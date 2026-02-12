import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import datetime
import json

# Mock Config before importing modules that use it
import sys
from app.config import Config
Config.TELEGRAM_BOT_TOKEN = "test_token"
Config.MY_TELEGRAM_CHAT_ID = "123456"

from app.services.telegram import TelegramBot

class TestPersonalFeatures(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Mock Workspace Manager
        self.mock_workspace_patcher = patch('app.services.telegram.workspace_manager')
        self.mock_workspace = self.mock_workspace_patcher.start()
        
        # Mock LLM send_request
        self.mock_llm_patcher = patch('app.services.llm.send_request')
        self.mock_llm = self.mock_llm_patcher.start()

        # Initialize Bot (mocking application builder)
        with patch('app.services.telegram.ApplicationBuilder') as mock_app_builder:
            mock_app = MagicMock()
            mock_app_builder.return_value.token.return_value.build.return_value = mock_app
            self.bot = TelegramBot()

    async def asyncTearDown(self):
        self.mock_workspace_patcher.stop()
        self.mock_llm_patcher.stop()

    async def test_expense_intent(self):
        # Mock LLM response for expense (Two steps)
        self.mock_llm.side_effect = [
            json.dumps({"intent_type": "expense"}), # Step 1: Classify
            json.dumps({                            # Step 2: Extract
                "type": "expense",
                "amount": 15,
                "currency": "USD",
                "category": "Food",
                "content": "Lunch"
            })
        ]

        # Create mock update
        mock_update = MagicMock()
        mock_update.effective_user.id = "123456"
        mock_update.effective_chat.id = "123456"
        mock_update.message.text = "Lunch $15"
        mock_context = MagicMock()
        mock_context.bot.send_message = AsyncMock()

        # Run handler
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.side_effect = ["2024-05-23", "12:00:00"]
            mock_datetime.now.return_value.isoformat.return_value = "2024-05-23T12:00:00+05:30"
            await self.bot.handle_message(mock_update, mock_context)

        # Verify Workspace Manager append_row
        self.mock_workspace.append_row.assert_called_with(
            "PersonalLife",
            "Expenses", 
            ["2024-05-23", "12:00:00", 15, "USD", "Food", "Lunch"]
        )

    async def test_habit_intent(self):
        # Mock LLM response for habit
        self.mock_llm.side_effect = [
            json.dumps({"intent_type": "habit"}),
            json.dumps({
                "type": "habit",
                "content": "Gym"
            })
        ]

        # Create mock update
        mock_update = MagicMock()
        mock_update.effective_user.id = "123456"
        mock_update.effective_chat.id = "123456"
        mock_update.message.text = "Gym done"
        mock_context = MagicMock()
        mock_context.bot.send_message = AsyncMock()

        # Run handler
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.side_effect = ["2024-05-23", "12:00:00"]
            mock_datetime.now.return_value.isoformat.return_value = "2024-05-23T12:00:00+05:30"
            await self.bot.handle_message(mock_update, mock_context)

        # Verify Workspace Manager append_row
        self.mock_workspace.append_row.assert_called_with(
            "PersonalLife",
            "Habits", 
            ["2024-05-23", "12:00:00", "Gym", "Done"]
        )

    async def test_journal_intent(self):
        # Mock LLM response for journal
        self.mock_llm.side_effect = [
            json.dumps({"intent_type": "journal"}),
            json.dumps({
                "type": "journal",
                "content": "Had a productive day.",
                "sentiment": "positive"
            })
        ]

        # Create mock update
        mock_update = MagicMock()
        mock_update.effective_user.id = "123456"
        mock_update.effective_chat.id = "123456"
        mock_update.message.text = "Had a productive day."
        mock_context = MagicMock()
        mock_context.bot.send_message = AsyncMock()

        # Run handler
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.side_effect = ["2024-05-23", "12:00:00"]
            mock_datetime.now.return_value.isoformat.return_value = "2024-05-23T12:00:00+05:30"
            await self.bot.handle_message(mock_update, mock_context)

        # Verify Workspace Manager append_row
        self.mock_workspace.append_row.assert_called_with(
            "PersonalLife",
            "Journal", 
            ["2024-05-23", "12:00:00", "positive", "Had a productive day."]
        )

    async def test_reminder_missing_datetime(self):
        # Mock LLM response for reminder with missing datetime
        self.mock_llm.side_effect = [
            json.dumps({"intent_type": "reminder"}),
            json.dumps({
                "type": "reminder",
                "content": "Check emails",
                "datetime": ""
            })
        ]

        # Create mock update
        mock_update = MagicMock()
        mock_update.effective_user.id = "123456"
        mock_update.effective_chat.id = "123456"
        mock_update.message.text = "Remind me check emails"
        mock_context = MagicMock()
        # Mock send_message to verify error response
        mock_context.bot.send_message = AsyncMock()

        # Run handler
        await self.bot.handle_message(mock_update, mock_context)

        # Verify bot sends error message instead of crashing
        mock_context.bot.send_message.assert_called_with(
            chat_id="123456",
            text="I understood you want a reminder, but I couldn't figure out the time. Please try again."
        )

    async def test_reminder_success(self):
        # Mock LLM response for successful reminder
        self.mock_llm.side_effect = [
            json.dumps({"intent_type": "reminder"}),
            json.dumps({
                "type": "reminder",
                "content": "Meeting",
                "datetime": "2024-05-24T10:00:00+05:30"
            })
        ]

        # Create mock update
        mock_update = MagicMock()
        mock_update.effective_user.id = "123456"
        mock_update.effective_chat.id = "123456"
        mock_update.message.text = "Remind me of meeting tomorrow at 10am"
        mock_context = MagicMock()
        mock_context.bot.send_message = AsyncMock()

        # Run handler
        # We need to ensure datetime.datetime.now() returns a fixed time
        # And datetime.datetime.fromisoformat works as expected or returns a fixed time
        
        real_datetime = datetime.datetime
        
        with patch('datetime.datetime') as mock_datetime:
            # Set fixed "now"
            fixed_now = real_datetime(2024, 5, 23, 9, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
            mock_datetime.now.return_value = fixed_now
            
            # Make fromisoformat return a real datetime (or compatible object)
            # Since we are mocking the class, we can just use side_effect to delegate to real fromisoformat
            mock_datetime.fromisoformat.side_effect = real_datetime.fromisoformat
            
            # We need to mock scheduler.add_job
            self.bot.scheduler = MagicMock()
            
            await self.bot.handle_message(mock_update, mock_context)

        # Verify scheduler check
        self.bot.scheduler.add_job.assert_called()
        
        # Verify confirmation message
        mock_context.bot.send_message.assert_called()
        args, kwargs = mock_context.bot.send_message.call_args
        self.assertIn("I've set a reminder", kwargs['text'])

if __name__ == '__main__':
    unittest.main()
