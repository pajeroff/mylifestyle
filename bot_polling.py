"""Run the bot in long-polling mode (good for development, no HTTPS needed)."""
import asyncio
from bot.webhook import bot, dp, on_startup, on_shutdown


async def main():
    await on_startup()
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
