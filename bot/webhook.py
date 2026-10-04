from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, WebhookInfo
from bot.config import BOT_TOKEN, WEBHOOK_SECRET
from bot.database import db
from bot.handlers.start import router as start_router
from bot.handlers.add_transaction import router as add_router
from bot.handlers.quick_add import router as quick_router
from bot.handlers.categories import router as cat_router
from bot.handlers.budget import router as budget_router
from bot.handlers.stats import router as stats_router


bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Register routers
dp.include_router(start_router)
dp.include_router(add_router)
dp.include_router(cat_router)
dp.include_router(budget_router)
dp.include_router(stats_router)
dp.include_router(quick_router)  # must be last, as it's catch-all


async def set_bot_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="menu", description="Главное меню"),
        BotCommand(command="help", description="Помощь"),
    ])


async def on_startup():
    await db.connect()
    await set_bot_commands()


async def on_shutdown():
    await db.close()
