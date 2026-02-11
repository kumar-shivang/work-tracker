import asyncio
from evening_summary import generate_and_send_summary

async def main():
    print("Triggering evening summary...")
    await generate_and_send_summary()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
