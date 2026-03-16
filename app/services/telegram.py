import logging
import asyncio
import os
import datetime
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import Config
from app.services.github import append_to_report
from app.services.llm import parse_user_intent, generate_conversational_response
from app.services.tools_registry import tools_registry

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

from app.services.google_workspace import workspace_manager
from app.services.db_service import db_service
from app.services.conversation import conversation_context
from app.services.pending_actions import pending_actions
from app.services.memory import memory_service
from app.services.summaries import (
    get_reminders_summary, get_expenses_summary,
    get_habits_summary, get_daily_summary,
    escape_md
)

# ─── Helpers ────────────────────────────────────────────────

def ist_now() -> datetime.datetime:
    """Get current time in IST."""
    ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    return datetime.datetime.now(ist_tz)





class TelegramBot:
    def __init__(self):
        self.application = ApplicationBuilder().token(Config.TELEGRAM_BOT_TOKEN).build()
        self.chat_id = Config.MY_TELEGRAM_CHAT_ID
        self.scheduler = AsyncIOScheduler()
        self.awaiting_checkin_response = False
        self._setup_handlers()
        
    def _setup_handlers(self):
        # ─── Command Handlers ───────────────────────────
        self.application.add_handler(CommandHandler('start', self.cmd_start))
        self.application.add_handler(CommandHandler('help', self.cmd_help))
        self.application.add_handler(CommandHandler('remind', self.cmd_remind))
        self.application.add_handler(CommandHandler('expense', self.cmd_expense))
        self.application.add_handler(CommandHandler('habit', self.cmd_habit))
        self.application.add_handler(CommandHandler('journal', self.cmd_journal))
        self.application.add_handler(CommandHandler('status', self.cmd_status))
        self.application.add_handler(CommandHandler('summary', self.cmd_summary))
        self.application.add_handler(CommandHandler('recall', self.cmd_recall))
        self.application.add_handler(CommandHandler('expenses', self.cmd_expenses))
        self.application.add_handler(CommandHandler('habits', self.cmd_habits))
        self.application.add_handler(CommandHandler('reminders', self.cmd_reminders))

        # ─── Callback / Button Handler ──────────────────
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

        # ─── Free-text Message Handler ──────────────────
        self.application.add_handler(MessageHandler(
            filters.TEXT & (~filters.COMMAND), self.handle_message
        ))

        # ─── Scheduled Jobs ─────────────────────────────
        ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        self.scheduler.add_job(
            self.send_daily_prompt,
            'cron',
            hour=21, minute=0,
            timezone=ist_tz
        )

    # ─── Auth Check ─────────────────────────────────────────
    def _is_owner(self, update: Update) -> bool:
        user_id = str(update.effective_user.id)
        return user_id == self.chat_id or not self.chat_id

    # ════════════════════════════════════════════════════════
    # COMMAND HANDLERS
    # ════════════════════════════════════════════════════════

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome = (
            "👋 *Hey\\! I'm your Personal Assistant bot\\.*\n\n"
            "I can help you with:\n"
            "📝 `/remind` — Set reminders\n"
            "💰 `/expense` — Log expenses\n"
            "✅ `/habit` — Track habits\n"
            "📓 `/journal` — Write journal entries\n"
            "📊 `/summary` — Today's activity summary\n"
            "🔍 `/recall` — Search your memories\n\n"
            "Or just *chat naturally* — I'll figure out what you need\\!"
        )
        keyboard = [[
            InlineKeyboardButton("📊 Summary", callback_data="quick_summary"),
            InlineKeyboardButton("🔍 Recall", callback_data="quick_recall"),
        ], [
            InlineKeyboardButton("📋 Help", callback_data="quick_help"),
        ]]
        await update.message.reply_text(
            welcome,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "📋 *Available Commands*\n\n"
            "*Logging:*\n"
            "  /remind `<text>` — Set a reminder\n"
            "  /expense `<text>` — Log an expense\n"
            "  /habit `<text>` — Log a habit\n"
            "  /journal `<text>` — Write a journal entry\n"
            "  /status `<text>` — Log a status update\n\n"
            "*Viewing:*\n"
            "  /summary — Today's activity summary\n"
            "  /recall `<query>` — Search past memories\n"
            "  /expenses — Recent expenses\n"
            "  /habits — Today's habits\n"
            "  /reminders — Upcoming reminders\n\n"
            "*Or just send a message naturally\\!*\n"
            "_I'll understand what you mean\\._"
        )
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN_V2)

    async def cmd_remind(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update):
            await update.message.reply_text("⛔ Unauthorized.")
            return

        text = " ".join(context.args) if context.args else ""
        if not text:
            await update.message.reply_text(
                "💡 *Usage:* `/remind Take medicine at 8pm`",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

        # Use LLM to parse the reminder
        current_time = ist_now().isoformat()
        intent = await parse_user_intent(f"remind me to {text}", current_time)
        
        if intent.get("type") != "reminder" or not intent.get("datetime"):
            await update.message.reply_text(
                "🤔 I couldn't figure out the time\\. Try: `/remind Call mom at 6pm tomorrow`",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

        # Validate and normalize the time BEFORE storing as action
        reminder_time_str = intent.get("datetime", "")
        content = intent.get("content", text)

        try:
            # Ensure reminder_time_str is a valid string
            if not reminder_time_str or not isinstance(reminder_time_str, str):
                raise ValueError(f"Invalid datetime: {reminder_time_str}")
            
            # Handle common LLM output format issue
            if reminder_time_str.endswith(" IST"):
                reminder_time_str = reminder_time_str.replace(" IST", "+05:30")
            
            dt = datetime.datetime.fromisoformat(reminder_time_str)
            # Update intent with clean ISO string so _execute_reminder doesn't fail
            intent["datetime"] = dt.isoformat()
            time_display = dt.strftime("%b %d, %I:%M %p")
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse reminder time: '{reminder_time_str}'")
            await update.message.reply_text(
                "🤔 I understood the reminder, but I couldn't parse the time effectively.\n"
                "Please try again with a clearer time expression (e.g., 'in 10 minutes' or 'at 5pm')."
            )
            return

        # Store as pending action and show confirmation
        action_id = pending_actions.store(intent)

        keyboard = [[
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{action_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{action_id}"),
        ]]
        await update.message.reply_text(
            f"⏰ *Set reminder:*\n\n"
            f"📝 {escape_md(content)}\n"
            f"🕐 {escape_md(time_display)}\n",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def cmd_expense(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update):
            await update.message.reply_text("⛔ Unauthorized.")
            return

        text = " ".join(context.args) if context.args else ""
        if not text:
            await update.message.reply_text(
                "💡 *Usage:* `/expense 450 lunch at cafe`",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

        current_time = ist_now().isoformat()
        intent = await parse_user_intent(f"spent {text}", current_time)

        if intent.get("type") != "expense" or not intent.get("amount"):
            await update.message.reply_text(
                "🤔 I couldn't parse the expense\\. Try: `/expense 200 INR coffee`",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

        action_id = pending_actions.store(intent)
        amount = intent.get("amount", 0)
        currency = intent.get("currency", "INR")
        category = intent.get("category", "General")
        desc = intent.get("content", text)

        keyboard = [[
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{action_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{action_id}"),
        ]]
        await update.message.reply_text(
            f"💰 *Log expense:*\n\n"
            f"💵 {escape_md(str(currency))} {escape_md(str(amount))}\n"
            f"📂 {escape_md(category)}\n"
            f"📝 {escape_md(desc)}\n",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def cmd_habit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update):
            await update.message.reply_text("⛔ Unauthorized.")
            return

        text = " ".join(context.args) if context.args else ""
        if not text:
            # Show quick-pick buttons for common habits
            keyboard = [[
                InlineKeyboardButton("🏋️ Exercise", callback_data="habit_exercise"),
                InlineKeyboardButton("📖 Reading", callback_data="habit_reading"),
            ], [
                InlineKeyboardButton("🧘 Meditation", callback_data="habit_meditation"),
                InlineKeyboardButton("💧 Water", callback_data="habit_water"),
            ]]
            await update.message.reply_text(
                "✅ *Log a habit:*\nTap below or type `/habit <name>`",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        # Direct log (habits are simple enough to skip confirmation)
        await self._execute_habit(update.effective_chat.id, text, context)

    async def cmd_journal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update):
            await update.message.reply_text("⛔ Unauthorized.")
            return

        text = " ".join(context.args) if context.args else ""
        if not text:
            await update.message.reply_text(
                "📓 *Write your journal entry:*\n_Just reply with your thoughts\\._",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            # Set context flag so next message is treated as journal
            context.user_data["awaiting_journal"] = True
            return

        current_time = ist_now().isoformat()
        intent = await parse_user_intent(text, current_time)
        sentiment = intent.get("sentiment", "neutral")
        
        await self._execute_journal(update.effective_chat.id, text, sentiment, context)

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update):
            await update.message.reply_text("⛔ Unauthorized.")
            return

        text = " ".join(context.args) if context.args else ""
        if not text:
            await update.message.reply_text(
                "💡 *Usage:* `/status Working on the API refactor`",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

        self.log_checkin(f"📝 Status: {text}")
        await db_service.log_status_update(content=text, source="telegram")
        
        keyboard = [[
            InlineKeyboardButton("📊 View Summary", callback_data="quick_summary"),
        ]]
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ Logged status update\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def cmd_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update):
            await update.message.reply_text("⛔ Unauthorized.")
            return

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="📊 _Generating today's summary\\.\\.\\._",
            parse_mode=ParseMode.MARKDOWN_V2
        )

        now = ist_now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

        try:
            summary_text = await get_daily_summary()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=summary_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Couldn't generate summary. Try again later."
            )

    async def cmd_recall(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update):
            await update.message.reply_text("⛔ Unauthorized.")
            return

        query = " ".join(context.args) if context.args else ""
        if not query:
            await update.message.reply_text(
                "🔍 *Usage:* `/recall what did I work on yesterday`",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🔍 _Searching memories\\.\\.\\._",
            parse_mode=ParseMode.MARKDOWN_V2
        )

        try:
            results = await memory_service.search_memories(query=query, limit=5)

            if not results:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="📭 No relevant memories found\\. Try a different query\\.",
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                return

            # Build context with memories and get LLM to answer naturally
            memory_text = "\n".join([
                f"[{r.get('memory_type', 'unknown')}] {r.get('content', '')}"
                for r in results
            ])

            from app.services.llm import answer_recall_question
            answer_data = await answer_recall_question(query, memory_text)
            answer = answer_data.get("answer", "I couldn't find relevant information.")

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🔍 *Recall:* {escape_md(query)}\n\n{escape_md(answer)}",
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.error(f"Error in recall: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Couldn't search memories. Try again later."
            )

    async def cmd_expenses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update):
            await update.message.reply_text("⛔ Unauthorized.")
            return

        try:
            text = await get_expenses_summary(limit=10)
            
            keyboard = [[
                InlineKeyboardButton("➕ Add Expense", callback_data="quick_add_expense"),
            ]]
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Error fetching expenses: {e}")
            await update.message.reply_text("❌ Couldn't fetch expenses.")

    async def cmd_habits(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update):
            await update.message.reply_text("⛔ Unauthorized.")
            return

        try:
            text = await get_habits_summary(limit=20)
            
            keyboard = [[
                InlineKeyboardButton("🏋️ Exercise", callback_data="habit_exercise"),
                InlineKeyboardButton("📖 Reading", callback_data="habit_reading"),
            ], [
                InlineKeyboardButton("🧘 Meditation", callback_data="habit_meditation"),
                InlineKeyboardButton("💧 Water", callback_data="habit_water"),
            ]]
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Error fetching habits: {e}")
            await update.message.reply_text("❌ Couldn't fetch habits.")

    async def cmd_reminders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update):
            await update.message.reply_text("⛔ Unauthorized.")
            return

        try:
            text = await get_reminders_summary()
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.error(f"Error fetching reminders: {e}")
            await update.message.reply_text("❌ Couldn't fetch reminders.")

    # ════════════════════════════════════════════════════════
    # CALLBACK QUERY HANDLER (Inline Buttons)
    # ════════════════════════════════════════════════════════

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()  # Acknowledge the button press

        data = query.data

        # ─── Pending action confirm/cancel ──────────────
        if data.startswith("confirm_"):
            action_id = data[len("confirm_"):]
            action = pending_actions.remove(action_id)
            if not action:
                await query.edit_message_text("⏳ This action has expired. Please try again.")
                return
            await self._execute_action(query.message.chat_id, action, context)
            return

        if data.startswith("cancel_"):
            action_id = data[len("cancel_"):]
            pending_actions.remove(action_id)
            await query.edit_message_text("❌ Cancelled.")
            return

        # ─── Habit quick-pick buttons ───────────────────
        if data.startswith("habit_"):
            habit_name = data[len("habit_"):].replace("_", " ").title()
            await self._execute_habit(query.message.chat_id, habit_name, context)
            await query.edit_message_text(f"✅ Logged habit: {habit_name}")
            return

        # ─── Quick action buttons ───────────────────────
        if data == "quick_summary":
            # Synthesize an Update-like call
            await self._send_summary(query.message.chat_id, context)
            return

        if data == "quick_recall":
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="🔍 What would you like to recall? Reply with your question."
            )
            return

        if data == "quick_help":
            help_text = (
                "📋 Available Commands:\n\n"
                "/remind <text> — Set a reminder\n"
                "/expense <text> — Log an expense\n"
                "/habit <text> — Log a habit\n"
                "/journal <text> — Journal entry\n"
                "/status <text> — Status update\n"
                "/summary — Today's summary\n"
                "/recall <query> — Search memories\n"
                "/expenses — Recent expenses\n"
                "/habits — Today's habits\n"
                "/reminders — Upcoming reminders"
            )
            await context.bot.send_message(chat_id=query.message.chat_id, text=help_text)
            return

        if data == "quick_add_expense":
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="💰 Send me the expense details, e\\.g\\.:\n`/expense 200 coffee at starbucks`",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return

        if data == "quick_view_reminders":
            text = await get_reminders_summary()
            await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
            return

        if data == "quick_view_expenses":
            text = await get_expenses_summary()
            keyboard = [[
                InlineKeyboardButton("➕ Add Expense", callback_data="quick_add_expense"),
            ]]
            await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=InlineKeyboardMarkup(keyboard))
            return

        if data == "quick_view_habits":
            text = await get_habits_summary()
            keyboard = [[
                InlineKeyboardButton("🏋️ Exercise", callback_data="habit_exercise"),
                InlineKeyboardButton("📖 Reading", callback_data="habit_reading"),
            ], [
                InlineKeyboardButton("🧘 Meditation", callback_data="habit_meditation"),
                InlineKeyboardButton("💧 Water", callback_data="habit_water"),
            ]]
            await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=InlineKeyboardMarkup(keyboard))
            return

        # ─── Daily prompt buttons ───────────────────────
        if data == "prompt_journal":
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="📓 _How was your day? Reply with your thoughts\\._",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            context.user_data["awaiting_journal"] = True
            return

        if data == "prompt_summary":
            await self._send_summary(query.message.chat_id, context)
            return

        # ─── Check-in Ignore ────────────────────────────
        if data == "ignore_checkin":
            self.awaiting_checkin_response = False
            await query.edit_message_text("🚫 Check-in ignored.")
            return

    # ════════════════════════════════════════════════════════
    # FREE-TEXT MESSAGE HANDLER (Conversational)
    # ════════════════════════════════════════════════════════

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update):
            await update.message.reply_text("⛔ Unauthorized.")
            return

        message_text = update.message.text
        chat_id = str(update.effective_chat.id)

        # ─── Check for awaiting journal ─────────────────
        if context.user_data.get("awaiting_journal"):
            context.user_data["awaiting_journal"] = False
            current_time = ist_now().isoformat()
            intent = await parse_user_intent(message_text, current_time)
            sentiment = intent.get("sentiment", "neutral")
            await self._execute_journal(update.effective_chat.id, message_text, sentiment, context)
            return

        # ─── Check for awaiting hourly check-in response ─
        if self.awaiting_checkin_response:
            self.awaiting_checkin_response = False
            # Log directly to work tracker and DB
            self.log_checkin(f"📝 Status: {message_text}")
            await db_service.log_status_update(content=message_text, source="telegram")
            
            keyboard = [[
                InlineKeyboardButton("📊 View Summary", callback_data="quick_summary"),
            ]]
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ Logged work status: {message_text}",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        # ─── Conversational flow ────────────────────────
        # 1. Add user message to conversation context
        conversation_context.add_message(chat_id, "user", message_text)

        # 2. Build enriched context with history + memories
        context_messages = await conversation_context.build_context(chat_id, message_text)

        # 3. Get conversational response from LLM
        response = await generate_conversational_response(context_messages)
        
        # ─── Tool Execution Loop ────────────────────────
        # Check if LLM wants to call a tool
        tool_call = response.get("tool_call")
        if tool_call:
            tool_name = tool_call.get("function_name")
            tool_args = tool_call.get("arguments", {})
            
            # Notify user that we are checking something
            status_msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🔍 _Checking {tool_name.replace('_', ' ')}\\.\\.\\._",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            
            # Execute tool
            tool_output = await tools_registry.execute(tool_name, tool_args)
            
            # Add tool output to context and ask again
            context_messages.append({
                "role": "system", 
                "content": f"Tool '{tool_name}' output:\n{tool_output}\n\nUser's original message was: {message_text}. Now answer the user based on this tool output."
            })
            
            # Get final response
            response = await generate_conversational_response(context_messages)
            
            # Delete status message
            try:
                await status_msg.delete()
            except:
                pass

        response_text = response.get("response_text", "")
        action = response.get("action")

        # 4. Add assistant reply to conversation history
        conversation_context.add_message(chat_id, "assistant", response_text)

        # 5. Handle action if detected
        if action and action.get("type") and action["type"] != "none":
            action_id = pending_actions.store(action)

            keyboard = [[
                InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{action_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{action_id}"),
            ]]
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=response_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            # Pure conversational reply (chat, question, or anything else)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=response_text,
            )

    # ════════════════════════════════════════════════════════
    # ACTION EXECUTORS
    # ════════════════════════════════════════════════════════

    async def _execute_action(self, chat_id: int, action: dict, context):
        """Execute a confirmed action."""
        action_type = action.get("type")

        if action_type == "reminder":
            await self._execute_reminder(chat_id, action, context)
        elif action_type == "expense":
            await self._execute_expense(chat_id, action, context)
        elif action_type == "habit":
            await self._execute_habit(chat_id, action.get("content", "Unknown"), context)
        elif action_type == "journal":
            await self._execute_journal(
                chat_id, action.get("content", ""),
                action.get("sentiment", "neutral"), context
            )
        elif action_type == "status_update":
            content = action.get("content", "")
            self.log_checkin(f"📝 Status: {content}")
            await db_service.log_status_update(content=content, source="telegram")
            await context.bot.send_message(chat_id=chat_id, text="✅ Status logged.")
        else:
            await context.bot.send_message(chat_id=chat_id, text="✅ Done.")

    async def _execute_reminder(self, chat_id: int, action: dict, context):
        content = action.get("content", "")
        reminder_time_str = action.get("datetime", "")
        ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

        try:
            # Ensure reminder_time_str is a valid string
            if not reminder_time_str or not isinstance(reminder_time_str, str):
                raise ValueError(f"Invalid datetime: {reminder_time_str}")
            
            reminder_time = datetime.datetime.fromisoformat(reminder_time_str)
            if reminder_time.tzinfo is None:
                reminder_time = reminder_time.replace(tzinfo=ist_tz)
            
            now = datetime.datetime.now(ist_tz)

            if reminder_time < now:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⏰ That time has passed! Here's your reminder now: {content}"
                )
                return

            await db_service.log_reminder(
                content=content,
                remind_at=reminder_time,
                chat_id=str(chat_id)
            )

            self.scheduler.add_job(
                self.send_reminder,
                'date',
                run_date=reminder_time,
                args=[chat_id, content]
            )

            time_display = reminder_time.strftime("%b %d, %I:%M %p")
            keyboard = [[
                InlineKeyboardButton("⏰ View Reminders", callback_data="quick_view_reminders"),
            ]]
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ Reminder set for {time_display}: {content}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except ValueError:
            logger.error(f"Error parsing reminder time: {reminder_time_str}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Couldn't parse the time. Please try again."
            )

    async def _execute_expense(self, chat_id: int, action: dict, context):
        amount = action.get("amount", 0)
        currency = action.get("currency", "INR")
        category = action.get("category", "General")
        desc = action.get("content", "")

        await db_service.log_expense(
            amount=amount, currency=currency,
            category=category, description=desc
        )

        # Also log to Sheets
        now = ist_now()
        workspace_manager.append_row(
            "PersonalLife", "Expenses",
            [now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), amount, currency, category, desc]
        )

        keyboard = [[
            InlineKeyboardButton("💰 View Expenses", callback_data="quick_view_expenses"),
            InlineKeyboardButton("➕ Add Another", callback_data="quick_add_expense"),
        ]]
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Logged: {currency} {amount} for {category}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _execute_habit(self, chat_id: int, habit_name: str, context):
        await db_service.log_habit(habit_name=habit_name)

        # Also log to Sheets
        now = ist_now()
        workspace_manager.append_row(
            "PersonalLife", "Habits",
            [now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), habit_name, "Done"]
        )

        keyboard = [[
            InlineKeyboardButton("✅ View Habits", callback_data="quick_view_habits"),
            InlineKeyboardButton("➕ Log Another", callback_data="quick_log_habit"),
        ]]
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Logged habit: {habit_name}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _execute_journal(self, chat_id: int, content: str, sentiment: str, context):
        await db_service.log_journal(content=content, sentiment=sentiment)

        # Also log to Sheets
        now = ist_now()
        workspace_manager.append_row(
            "PersonalLife", "Journal",
            [now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), sentiment, content]
        )

        sentiment_emoji = {"positive": "😊", "neutral": "😐", "negative": "😔"}.get(sentiment, "📝")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{sentiment_emoji} Journal entry saved. Take care!"
        )

    # ════════════════════════════════════════════════════════
    # HELPER: Send summary (reused by command + callback)
    # ════════════════════════════════════════════════════════

    async def _send_summary(self, chat_id: int, context):
        """Send today's activity summary to a chat."""
        now = ist_now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

        try:
            memories = await memory_service.retrieve_by_date_range(
                start_date=start_of_day,
                end_date=now,
                limit=20
            )

            if not memories:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="📭 No activities logged yet today."
                )
                return

            by_type = {}
            for m in memories:
                mt = m.memory_type or "other"
                by_type.setdefault(mt, []).append(m.content)

            type_emoji = {
                "commit": "💻", "expense": "💰", "habit": "✅",
                "journal": "📓", "reminder": "⏰", "status_update": "📝",
            }

            summary_parts = [f"📊 Today's Summary — {now.strftime('%b %d, %A')}\n"]
            for mtype, items in by_type.items():
                emoji = type_emoji.get(mtype, "📌")
                summary_parts.append(f"\n{emoji} {mtype.replace('_', ' ').title()} ({len(items)})")
                for item in items[:5]:
                    short = item[:100] + "..." if len(item) > 100 else item
                    summary_parts.append(f"  • {short}")

            await context.bot.send_message(
                chat_id=chat_id,
                text="\n".join(summary_parts)
            )
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Couldn't generate summary."
            )

    # ════════════════════════════════════════════════════════
    # OUTGOING MESSAGES (Scheduled + Reminders)
    # ════════════════════════════════════════════════════════

    def log_checkin(self, text: str):
        """Append the check-in to the Google Doc."""
        timestamp = ist_now().strftime("%H:%M")
        entry = f"{timestamp} - {text}"
        workspace_manager.append_to_doc("WorkTracker", entry)

    async def send_checkin_message(self):
        if not self.chat_id:
            logger.warning("No Chat ID set for Telegram bot.")
            return

        try:
            keyboard = [[
                InlineKeyboardButton("📊 Summary", callback_data="quick_summary"),
                InlineKeyboardButton("📝 Log Status", callback_data="quick_log_status"),
                InlineKeyboardButton("🚫 Ignore", callback_data="ignore_checkin"),
            ]]
            self.awaiting_checkin_response = True
            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text="🕐 *Hourly Check\\-In*\nWhat are you working on right now?",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Failed to send check-in: {e}")

    async def send_daily_prompt(self):
        if not self.chat_id:
            return

        try:
            keyboard = [[
                InlineKeyboardButton("📓 Journal", callback_data="prompt_journal"),
                InlineKeyboardButton("📊 Summary", callback_data="prompt_summary"),
            ], [
                InlineKeyboardButton("✅ Log Habit", callback_data="quick_log_habit"),
                InlineKeyboardButton("💰 Log Expense", callback_data="quick_add_expense"),
            ]]
            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text="🌙 *Daily Reflection*\nHow was your day?",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Failed to send daily prompt: {e}")

    async def send_reminder(self, chat_id: int, text: str):
        try:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=f"🔔 *REMINDER:* {escape_md(text)}",
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.error(f"Failed to send reminder: {e}")

    # ════════════════════════════════════════════════════════
    # LIFECYCLE
    # ════════════════════════════════════════════════════════

    async def initialize(self):
        await self.application.initialize()

        # Register slash command menu in Telegram
        await self.application.bot.set_my_commands([
            BotCommand("start", "Welcome & capabilities"),
            BotCommand("help", "Show all commands"),
            BotCommand("remind", "Set a reminder"),
            BotCommand("expense", "Log an expense"),
            BotCommand("habit", "Log a habit"),
            BotCommand("journal", "Write a journal entry"),
            BotCommand("status", "Log a status update"),
            BotCommand("summary", "Today's activity summary"),
            BotCommand("recall", "Search past memories"),
            BotCommand("expenses", "View recent expenses"),
            BotCommand("habits", "View today's habits"),
            BotCommand("reminders", "View upcoming reminders"),
        ])

        self.scheduler.start()
        await self.application.start()
        await self.application.updater.start_polling()

    async def shutdown(self):
        self.scheduler.shutdown()
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()


# Singleton instance
bot = TelegramBot()
