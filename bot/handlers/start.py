from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from bot.database import db
from bot.keyboards import main_keyboard, webapp_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user = await db.get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or ""
    )
    text = (
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        f"Я <b>MyLifeStyle</b> — твой личный помощник по учёту финансов.\n\n"
        f"📌 <b>Что я умею:</b>\n"
        f"• Записывать доходы и расходы — просто напиши мне сумму (например: «Кофе 250»)\n"
        f"• Показывать статистику и отчёты\n"
        f"• Следить за бюджетами по категориям\n"
        f"• Открываться как мини-приложение прямо в Telegram\n\n"
        f"💡 Просто отправь мне <b>сумму</b> или открой приложение кнопкой ниже:"
    )
    await message.answer(text, reply_markup=main_keyboard())
    await message.answer("📱 Полная версия приложения:", reply_markup=webapp_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "🆘 <b>Как пользоваться:</b>\n\n"
        "<b>1. Быстрое добавление:</b>\n"
        "Просто напиши сумму и что купил, например:\n"
        "• «350 обед в кафе»\n"
        "• «Такси 500 сегодня»\n"
        "• «Продукты 2300 в Магните»\n"
        "• «Получил зп 80000»\n\n"
        "<b>2. Голосовые сообщения:</b>\n"
        "Отправь голосовое — я распознаю и запишу транзакцию (распознавание в веб-версии).\n\n"
        "<b>3. Кнопки меню:</b>\n"
        "💰 Добавить доход / 💸 Добавить расход — пошаговое добавление\n"
        "📊 Статистика — отчёты за месяц\n"
        "🎯 Бюджет — установить лимиты\n"
        "📁 Категории — добавить свои категории\n\n"
        "<b>4. Mini App:</b>\n"
        "Нажми «📱 Открыть приложение» для полной версии с графиками и аналитикой."
    )
    await message.answer(text)


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer("🏠 Главное меню:", reply_markup=main_keyboard())
