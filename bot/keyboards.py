from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup,
    InlineKeyboardButton, WebAppInfo
)
from bot.config import WEBAPP_URL


def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Добавить доход"), KeyboardButton(text="💸 Добавить расход")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📁 Категории")],
            [KeyboardButton(text="🎯 Бюджет"), KeyboardButton(text="📱 Открыть приложение",
               web_app=WebAppInfo(url=WEBAPP_URL + "/app"))]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие или напишите сумму..."
    )


def cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )


def webapp_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="📱 Открыть MyLifeStyle",
            web_app=WebAppInfo(url=WEBAPP_URL + "/app")
        )
    ]])


def categories_inline(categories, callback_prefix="cat_"):
    kb = []
    row = []
    for i, cat in enumerate(categories):
        btn = InlineKeyboardButton(
            text=cat["name"],
            callback_data=f"{callback_prefix}{cat['id']}"
        )
        row.append(btn)
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    return InlineKeyboardMarkup(inline_keyboard=kb)
