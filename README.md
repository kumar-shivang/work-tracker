# Personal Assistant & Work Tracker

A powerful, Python-based personal assistant designed to automate work tracking and reporting. Originally built as a replacement/supplement for n8n workflows, this assistant integrates with GitHub, Telegram, Email, and Google Docs to keep your productivity on track.

## 🚀 Features

- **GitHub Integration**: Automatically listens for push webhooks and generates human-readable summaries of code changes using LLMs (Grok-1/GPT-4).
- **Telegram Check-ins**: Sends hourly messages during your working hours (e.g., Mon-Fri, 9 AM - 6 PM) to keep you focused and log your progress.
- **Evening Summaries**: At the end of each workday, it compiles all commits and check-ins into a comprehensive report.
- **Multi-Channel Dispatch**: Summaries are sent via Email and logged to a specific Google Doc for long-term tracking.
- **Modular Architecture**: Easy to extend with new services or task types.

## 🛠️ Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) for the web server and webhook endpoints.
- **Scheduling**: [APScheduler](https://apscheduler.agron.i/en/master/) for recurring tasks (check-ins and summaries).
- **Bot Framework**: [python-telegram-bot](https://python-telegram-bot.org/) for interactive messaging.
- **Package Management**: [uv](https://github.com/astral-sh/uv) for fast and reliable dependency management.
- **Validation**: [Pydantic](https://docs.pydantic.dev/) for configuration and data schemas.
- **LLM Support**: Integrated with OpenRouter/OpenAI for intelligent text summarization.

## 📁 Project Structure

```text
.
├── app/
│   ├── core/           # Scheduler and shared logic
│   ├── services/       # GitHub, Telegram, LLM, Email, and Google Docs integrations
│   ├── tasks/          # Scheduled jobs (e.g., evening summaries)
│   ├── config.py       # Pydantic-based configuration management
│   └── main.py         # Application entry point (FastAPI)
├── reports/            # Local storage for generated markdown reports
├── logs/               # Application and service logs
├── start.sh            # Production startup script
└── n8n-assistant.service # systemd service configuration
```

## ⚙️ Setup & Installation

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended)
- A GitHub personal access token (for repository tracking)
- A Telegram Bot token (from @BotFather)
- Google Cloud Service Account (for Google Docs integration)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd n8n
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Configure environment**:
   Create a `.env` file in the root directory (refer to `.env.template` if available, or check `app/config.py` for required keys):
   ```env
   GITHUB_TOKEN=your_token
   TELEGRAM_BOT_TOKEN=your_bot_token
   MY_TELEGRAM_CHAT_ID=your_chat_id
   OPENROUTER_API_KEY=your_key
   GMAIL_USER=your_email@gmail.com
   GMAIL_APP_PASSWORD=your_app_password
   GOOGLE_DOC_ID=your_doc_id
   ```

### Running the App

**Locally**:
```bash
uv run python -m app.main
```

**As a Service (Linux)**:
1. Edit `n8n-assistant.service` to match your paths and user.
2. Copy to `/etc/systemd/system/`.
3. Enable and start:
   ```bash
   sudo systemctl enable n8n-assistant
   sudo systemctl start n8n-assistant
   ```

## 📡 API Endpoints

- `GET /`: Health check.
- `POST /webhook/github`: Entry point for GitHub push webhooks.

---
*Built with ❤️ for productivity.*
