from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.database import db
from bot.keyboards import main_keyboard, cancel_keyboard

router = Router()


class AddCategory(StatesGroup):
    waiting_type = State()
    waiting_name = State()


@router.message(F.text == "📁 Категории")
async def list_categories(message: Message):
    income_cats = await db.get_categories(message.from_user.id, "income")
    expense_cats = await db.get_categories(message.from_user.id, "expense")

    text = "📂 <b>Ваши категории</b>\n\n"
    text += "💸 <b>Расходы:</b>\n" + "\n".join(f"  • {c['name']}{' 🔹' if c['is_default'] else ''}" for c in expense_cats)
    text += "\n\n💰 <b>Доходы:</b>\n" + "\n".join(f"  • {c['name']}{' 🔹' if c['is_default'] else ''}" for c in income_cats)
    text += "\n\n<i>🔹 — стандартная категория</i>"

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить категорию расхода", callback_data="addcat_expense")
    builder.button(text="➕ Добавить категорию дохода", callback_data="addcat_income")
    builder.adjust(1)

    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("addcat_"))
async def ask_category_name(callback: CallbackQuery, state: FSMContext):
    trans_type = callback.data.split("_")[1]
    await state.set_state(AddCategory.waiting_name)
    await state.update_data(trans_type=trans_type)
    label = "дохода" if trans_type == "income" else "расхода"
    await callback.message.answer(
        f"Введите название новой категории {label}:",
        reply_markup=cancel_keyboard()
    )
    await callback.answer()


@router.message(AddCategory.waiting_name, F.text == "❌ Отмена")
async def cancel_category(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено.", reply_markup=main_keyboard())


@router.message(AddCategory.waiting_name)
async def add_category(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) > 30:
        await message.answer("❌ Название слишком длинное (макс. 30 символов).")
        return
    data = await state.get_data()
    trans_type = data["trans_type"]
    cat_id = await db.add_custom_category(message.from_user.id, name, trans_type)
    await state.clear()
    if cat_id:
        await message.answer(f"✅ Категория «{name}» добавлена!", reply_markup=main_keyboard())
    else:
        await message.answer(f"❌ Категория «{name}» уже существует.", reply_markup=main_keyboard())
