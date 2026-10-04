from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date
from bot.database import db
from bot.keyboards import main_keyboard, cancel_keyboard
from bot.services.parser import format_money

router = Router()


class SetBudget(StatesGroup):
    waiting_category = State()
    waiting_limit = State()


def progress_bar(pct: float, length: int = 10) -> str:
    filled = int(length * min(pct / 100, 1.0))
    return "█" * filled + "░" * (length - filled)


@router.message(F.text == "🎯 Бюджет")
async def show_budget(message: Message):
    month = date.today().strftime("%Y-%m")
    budgets = await db.get_budgets(message.from_user.id, month)

    # Calculate month totals
    from datetime import datetime
    year, mon = map(int, month.split("-"))
    import calendar
    last_day = calendar.monthrange(year, mon)[1]
    start_date = f"{month}-01"
    end_date = f"{month}-{last_day:02d}"
    total_spent = await db.get_total(message.from_user.id, "expense", start_date, end_date)
    total_income = await db.get_total(message.from_user.id, "income", start_date, end_date)

    text = f"🎯 <b>Бюджет на {month}</b>\n\n"
    text += f"💰 Доход: <b>{format_money(total_income)}</b>\n"
    text += f"💸 Расход: <b>{format_money(total_spent)}</b>\n"
    text += f"💼 Баланс: <b>{format_money(total_income - total_spent)}</b>\n\n"

    if budgets:
        text += "<b>Лимиты по категориям:</b>\n"
        for b in budgets:
            pct = (b["spent"] / b["limit_amount"] * 100) if b["limit_amount"] > 0 else 0
            emoji = "🟢" if pct < 70 else ("🟡" if pct < 100 else "🔴")
            bar = progress_bar(pct)
            text += (
                f"\n{emoji} <b>{b['category_name']}</b>\n"
                f"{bar} {pct:.0f}%\n"
                f"{format_money(b['spent'])} / {format_money(b['limit_amount'])}\n"
            )
    else:
        text += "ℹ️ У вас не установлено ни одного лимита.\n"

    # Categories for new budget
    cats = await db.get_categories(message.from_user.id, "expense")
    existing = {b["category_id"] for b in budgets}
    builder = InlineKeyboardBuilder()
    for c in cats:
        if c["id"] not in existing:
            builder.button(text=f"➕ {c['name']}", callback_data=f"budget_{c['id']}")
    builder.adjust(2)

    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("budget_"))
async def ask_budget_limit(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[1])
    cat = await db.get_category_by_id(category_id)
    await state.set_state(SetBudget.waiting_limit)
    await state.update_data(category_id=category_id, category_name=cat["name"])
    await callback.message.answer(
        f"Установите месячный лимит для категории «{cat['name']}» (введите сумму):",
        reply_markup=cancel_keyboard()
    )
    await callback.answer()


@router.message(SetBudget.waiting_limit, F.text == "❌ Отмена")
async def cancel_budget(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено.", reply_markup=main_keyboard())


@router.message(SetBudget.waiting_limit)
async def set_budget(message: Message, state: FSMContext):
    text = message.text.replace(',', '.').strip()
    try:
        limit = float(text)
        if limit <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректную сумму.")
        return

    data = await state.get_data()
    month = date.today().strftime("%Y-%m")
    await db.set_budget(message.from_user.id, data["category_id"], limit, month)
    await state.clear()
    await message.answer(
        f"✅ Лимит для «{data['category_name']}» установлен: <b>{format_money(limit)}</b> на {month}",
        reply_markup=main_keyboard()
    )
