from aiogram import Router, F, types
from aiogram.types import Message
from datetime import date, timedelta
from bot.database import db
from bot.services.parser import parse_text_transaction, format_money
from bot.keyboards import main_keyboard

router = Router()


@router.message(F.text & ~F.text.startswith("/") & ~F.text.in_(
    {"💰 Добавить доход", "💸 Добавить расход", "📊 Статистика",
     "📁 Категории", "🎯 Бюджет", "❌ Отмена", "📱 Открыть приложение"}
))
async def quick_add_transaction(message: Message):
    """Parse free-text message as a transaction."""
    parsed = await parse_text_transaction(message.text, message.from_user.id)
    if not parsed:
        await message.answer(
            "🤔 Не смог распознать сумму. Попробуй написать по-другому, например:\n"
            "• «Кофе 250»\n"
            "• «Продукты 3000 в Пятерочке»\n"
            "• «Получил 15000 за фриланс»\n\n"
            "Или используй кнопки меню 👇"
        )
        return

    tx_id = await db.add_transaction(
        user_id=message.from_user.id,
        amount=parsed["amount"],
        category_id=parsed["category_id"],
        trans_type=parsed["type"],
        comment=parsed["comment"],
        trans_date=parsed["date"]
    )

    emoji = "💸" if parsed["type"] == "expense" else "💰"
    type_label = "Расход" if parsed["type"] == "expense" else "Доход"
    cat_label = parsed["category_name"] or "Прочее"
    comment = f"\n📝 {parsed['comment']}" if parsed["comment"] else ""

    budget_warning = ""
    if parsed["type"] == "expense":
        # Check budget warning for this month
        month = date.today().strftime("%Y-%m")
        budgets = await db.get_budgets(message.from_user.id, month)
        for b in budgets:
            if b["category_id"] == parsed["category_id"] and b["limit_amount"] > 0:
                pct = b["spent"] / b["limit_amount"] * 100
                if pct >= 100:
                    budget_warning = f"\n\n⚠️ <b>Бюджет по категории «{b['category_name']}» превышен!</b> (потрачено {pct:.0f}%)"
                elif pct >= 80:
                    budget_warning = f"\n\n⚠️ Приближаешься к лимиту по «{b['category_name']}» — {pct:.0f}%"

    text = (
        f"{emoji} <b>{type_label} добавлен!</b>\n"
        f"💵 Сумма: <b>{format_money(parsed['amount'])}</b>\n"
        f"📂 Категория: {cat_label}"
        f"{comment}\n"
        f"📅 Дата: {parsed['date']}"
        f"{budget_warning}"
    )
    await message.answer(text, reply_markup=main_keyboard())
