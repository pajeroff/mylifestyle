from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from datetime import date
from bot.database import db
from bot.keyboards import main_keyboard, cancel_keyboard, categories_inline
from bot.services.parser import extract_amount, format_money

router = Router()


class AddTransaction(StatesGroup):
    waiting_type = State()
    waiting_amount = State()
    waiting_category = State()
    waiting_comment = State()


@router.message(F.text.in_({"💰 Добавить доход", "💸 Добавить расход"}))
async def start_add(message: Message, state: FSMContext):
    trans_type = "income" if "доход" in message.text else "expense"
    await state.set_state(AddTransaction.waiting_amount)
    await state.update_data(trans_type=trans_type)
    label = "дохода" if trans_type == "income" else "расхода"
    await message.answer(
        f"Введите сумму {label} (только число, например 1500):",
        reply_markup=cancel_keyboard()
    )


@router.message(AddTransaction.waiting_amount, F.text == "❌ Отмена")
async def cancel_add(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Добавление отменено.", reply_markup=main_keyboard())


@router.message(AddTransaction.waiting_amount)
async def process_amount(message: Message, state: FSMContext):
    text = message.text.replace(',', '.').strip()
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректное положительное число.")
        return

    data = await state.get_data()
    trans_type = data["trans_type"]
    await state.update_data(amount=amount)

    categories = await db.get_categories(message.from_user.id, trans_type)
    await state.set_state(AddTransaction.waiting_category)

    label = "дохода" if trans_type == "income" else "расхода"
    await message.answer(
        f"Сумма: <b>{format_money(amount)}</b>\nВыберите категорию {label}:",
        reply_markup=categories_inline(categories)
    )


@router.callback_query(AddTransaction.waiting_category, F.data.startswith("cat_"))
async def process_category(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[1])
    category = await db.get_category_by_id(category_id)
    await state.update_data(category_id=category_id, category_name=category["name"])
    await state.set_state(AddTransaction.waiting_comment)
    await callback.message.edit_text(
        f"Категория: <b>{category['name']}</b>\nВведите комментарий (можно пропустить, отправив «-»):"
    )
    await callback.answer()


@router.message(AddTransaction.waiting_comment)
async def process_comment(message: Message, state: FSMContext):
    comment = message.text.strip()
    if comment in ("-", "—", "нет", "пропустить"):
        comment = ""

    data = await state.get_data()
    trans_date = date.today().isoformat()

    tx_id = await db.add_transaction(
        user_id=message.from_user.id,
        amount=data["amount"],
        category_id=data["category_id"],
        trans_type=data["trans_type"],
        comment=comment,
        trans_date=trans_date
    )

    emoji = "💸" if data["trans_type"] == "expense" else "💰"
    type_label = "Расход" if data["trans_type"] == "expense" else "Доход"
    comment_text = f"\n📝 {comment}" if comment else ""

    await state.clear()
    await message.answer(
        f"{emoji} <b>{type_label} добавлен!</b>\n"
        f"💵 Сумма: <b>{format_money(data['amount'])}</b>\n"
        f"📂 Категория: {data['category_name']}"
        f"{comment_text}\n"
        f"📅 Дата: {trans_date}",
        reply_markup=main_keyboard()
    )
