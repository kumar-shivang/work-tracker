import asyncio
from telegram_bot import bot

async def main():
    print("Sending check-in message...")
    await bot.send_checkin_message()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
