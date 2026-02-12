from contextlib import asynccontextmanager
import logging
from logging.handlers import RotatingFileHandler
import os

# Configure logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
handler = RotatingFileHandler(f"{log_dir}/app.log", maxBytes=10*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Configure root logger
logging.basicConfig(level=logging.INFO, handlers=[handler, logging.StreamHandler()])
logging.getLogger("httpx").setLevel(logging.WARNING) # Reduce noise

from app.config import Config
from fastapi import FastAPI, Request, BackgroundTasks
import uvicorn
from app.services.github import handle_github_webhook
from app.services.telegram import bot
from app.core.scheduler import start_scheduler, scheduler
from app.db.init_db import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Initializing Database...")
    await init_db()
    
    print("Starting Telegram Bot...")
    await bot.initialize()
    
    print("Starting Scheduler...")
    start_scheduler()
    
    yield
    
    # Shutdown
    print("Shutting down...")
    await bot.shutdown()
    scheduler.shutdown()

app = FastAPI(title="Personal Assistant", lifespan=lifespan)

@app.get("/")
def read_root():
    return {"status": "running", "service": "n8n-replacement"}

@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    background_tasks.add_task(handle_github_webhook, payload)
    return {"status": "received"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=Config.API_PORT, reload=False) # Reload false for bot stability
