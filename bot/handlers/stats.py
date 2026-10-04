from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date, timedelta
import calendar
from bot.database import db
from bot.keyboards import main_keyboard, webapp_keyboard
from bot.services.parser import format_money

router = Router()


@router.message(F.text == "📊 Статистика")
async def stats_menu(message: Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 За этот месяц", callback_data="stats_month")
    builder.button(text="📆 За прошлый месяц", callback_data="stats_prevmonth")
    builder.button(text="🗓️ За 7 дней", callback_data="stats_week")
    builder.button(text="📱 Подробнее в приложении", callback_data="stats_webapp")
    builder.adjust(2)
    await message.answer("📊 <b>Выберите период для отчёта:</b>", reply_markup=builder.as_markup())


def get_period_range(period: str):
    today = date.today()
    if period == "week":
        start = today - timedelta(days=6)
        end = today
        label = "последние 7 дней"
    elif period == "prevmonth":
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        start = last_prev.replace(day=1)
        end = last_prev
        label = start.strftime("%B %Y")
    else:  # month
        start = today.replace(day=1)
        end = today
        label = today.strftime("%B %Y")
    return start, end, label


@router.callback_query(F.data.startswith("stats_"))
async def show_stats(callback: CallbackQuery):
    period = callback.data.split("_", 1)[1]
    if period == "webapp":
        await callback.message.answer(
            "📱 Откройте мини-приложение для подробной аналитики с графиками:",
            reply_markup=webapp_keyboard()
        )
        await callback.answer()
        return

    start, end, label = get_period_range(period)
    user_id = callback.from_user.id

    total_income = await db.get_total(user_id, "income", start.isoformat(), end.isoformat())
    total_expense = await db.get_total(user_id, "expense", start.isoformat(), end.isoformat())
    by_cat = await db.get_summary_by_category(user_id, "expense", start.isoformat(), end.isoformat())
    daily = await db.get_daily_totals(user_id, "expense", start.isoformat(), end.isoformat())

    text = f"📊 <b>Отчёт: {label}</b>\n\n"
    text += f"💰 Доход: <b>{format_money(total_income)}</b>\n"
    text += f"💸 Расход: <b>{format_money(total_expense)}</b>\n"
    text += f"💼 Баланс: <b>{format_money(total_income - total_expense)}</b>\n\n"

    if by_cat:
        text += "<b>Расходы по категориям:</b>\n"
        bars = "▁▂▃▄▅▆▇█"
        max_total = max(c["total"] for c in by_cat) if by_cat else 1
        for c in by_cat:
            pct = c["total"] / max_total
            bar = bars[min(int(pct * (len(bars) - 1)), len(bars) - 1)]
            pct_of_total = (c["total"] / total_expense * 100) if total_expense > 0 else 0
            text += f"  {bar} {c['name']}: {format_money(c['total'])} ({pct_of_total:.0f}%)\n"
    else:
        text += "ℹ️ За этот период нет расходов."

    text += "\n<i>За подробной аналитикой с графиками откройте 📱 мини-приложение.</i>"
    await callback.message.edit_text(text)
    await callback.answer()
