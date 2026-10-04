import re
from datetime import date, datetime, timedelta
from typing import Optional, Tuple, Dict
from bot.database import db


# Simple rule-based categorization
KEYWORD_RULES_GLOBAL = {
    "expense": {
        "Еда": [
            "еда", "продукты", "магазин", "супермаркет", "пятерочка", "магнит", "ашан",
            "перекресток", "лента", "кафе", "ресторан", "пицца", "суши", "бургер",
            "обед", "ужин", "завтрак", "едадоставка", "додо", "макдак", "kfc",
            "шаурма", "кофе", "шоколад", "хлеб", "молоко", "фрукты", "овощи",
            "продукт", "купилпоесть", "продовольствие"
        ],
        "Транспорт": [
            "транспорт", "автобус", "метро", "такси", "яндекстакси", "убер", "uber",
            "yandex", "бензин", "заправка", "авто", "машина", "парковка", "трамвай",
            "троллейбус", "электричка", "поезд", "самолет", "авиабилет", "билет",
            "проезд", "топливо", "каршеринг", "делимобиль", "яндексго"
        ],
        "Жильё": [
            "аренда", "квартира", "ипотека", "жилье", "арендажилья", "съем", "комната",
            "аренднаяплата", "квартплата"
        ],
        "Коммунальные услуги": [
            "коммуналка", "жкх", "электричество", "газ", "вода", "отопление",
            "коммунальные", "свет", "горячаявода", "холоднаявода"
        ],
        "Связь/Интернет": [
            "связь", "интернет", "мобильный", "телефон", "билайн", "мтс", "мегафон",
            "теле2", "роутер", "подписка", "подписки"
        ],
        "Развлечения": [
            "кино", "театр", "концерт", "развлечения", "игра", "игры", "стим", "steam",
            "нетфликс", "netflix", "спортзал", "фитнес", "бар", "клуб", "досуг",
            "парк", "аттракционы", "отпуск", "путешествие"
        ],
        "Покупки": [
            "покупки", "одежда", "обувь", "вещи", "алиэкспресс", "aliexpress", "озон",
            "ozon", "вайлдберриз", "wildberries", "маркетплейс", "мебель", "техника",
            "электроника", "телефон", "ноутбук"
        ],
        "Здоровье": [
            "здоровье", "аптека", "лекарство", "лекарства", "врач", "больница", "поликлиника",
            "анализы", "стоматолог", "медицина", "таблетки", "витамины"
        ],
        "Образование": [
            "образование", "курс", "курсы", "учеба", "университет", "школа", "книги",
            "книга", "обучение", "учебник", "английский", "skillbox", "geekbrains",
            "coursera", "нетология"
        ],
    },
    "income": {
        "Зарплата": ["зарплата", "зп", "оклад", "аванс", "получка", "работа"],
        "Фриланс": ["фриланс", "фриланс", "заказ", "проект", "удаленка"],
        "Подарок": ["подарок", "подарили", "подарил", "наподарок"],
        "Инвестиции": ["дивиденды", "инвестиции", "купон", "акции", "облигации", "проценты"],
    }
}


def extract_amount(text: str) -> Optional[float]:
    """Extract monetary amount from text."""
    text = text.replace(',', '.')
    # Match patterns like "1000", "1 000", "1000.50", "1 000,50"
    # First try with thousand separator
    patterns = [
        r'(\d{1,3}(?:\s\d{3})+(?:\.\d{1,2})?)',  # 1 000 or 1 000.50
        r'(\d+(?:\.\d{1,2})?)',                   # 1000 or 1000.50
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            num_str = match.group(1).replace(' ', '').replace(',', '.')
            try:
                return float(num_str)
            except ValueError:
                continue
    return None


def detect_transaction_type(text: str) -> str:
    """Detect if it's income or expense based on keywords."""
    income_keywords = ["пришло", "получил", "поступило", "зарплата", "зп", "доход",
                       "заработал", "перевели", "пополнение", "начислили", "прибыль",
                       "+"]
    expense_keywords = ["потратил", "купил", "оплатил", "заплатил", "списание",
                        "расход", "ушло", "стоимость", "потратила", "купила",
                        "-", "оплата"]

    text_lower = text.lower()
    for kw in income_keywords:
        if kw in text_lower:
            return "income"
    return "expense"  # default


def guess_category(text: str, trans_type: str) -> Optional[str]:
    """Guess category name using global keyword rules."""
    text_lower = text.lower()
    rules = KEYWORD_RULES_GLOBAL.get(trans_type, {})
    for cat_name, keywords in rules.items():
        for kw in keywords:
            if kw in text_lower:
                return cat_name
    return None


def extract_date(text: str) -> Optional[str]:
    """Extract date from text. Returns ISO format or None."""
    text_lower = text.lower()
    today = date.today()

    if "сегодня" in text_lower:
        return today.isoformat()
    if "вчера" in text_lower:
        return (today - timedelta(days=1)).isoformat()
    if "позавчера" in text_lower:
        return (today - timedelta(days=2)).isoformat()

    # DD.MM or DD.MM.YYYY
    match = re.search(r'(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?', text)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3)) if match.group(3) else today.year
        if year < 100:
            year += 2000
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            pass
    return today.isoformat()


def extract_comment(text: str, amount: float) -> str:
    """Remove amount and date from text to get comment."""
    comment = text
    # Remove amount
    comment = re.sub(r'\d{1,3}(?:\s\d{3})+(?:\.\d{1,2})?', '', comment)
    comment = re.sub(r'\d+(?:\.\d{1,2})?', '', comment)
    # Remove date patterns
    comment = re.sub(r'\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?', '', comment)
    # Remove known keywords
    skip_words = ["сегодня", "вчера", "позавчера", "потратил", "купил", "оплатил",
                  "заплатил", "пришло", "получил", "поступило", "на", "руб", "р", "₽",
                  "рублей", "рубля", "потратила", "купила", "прибыль", "доход", "расход"]
    for w in skip_words:
        comment = re.sub(r'\b' + re.escape(w) + r'\b', '', comment, flags=re.IGNORECASE)
    comment = re.sub(r'[,\s]+', ' ', comment).strip()
    return comment[:200]


async def parse_text_transaction(text: str, user_id: int) -> Optional[Dict]:
    """Parse a free-form text message into a transaction dict."""
    amount = extract_amount(text)
    if not amount:
        return None

    trans_type = detect_transaction_type(text)
    trans_date = extract_date(text)
    comment = extract_comment(text, amount)

    # Try to find category: first from user keywords, then global rules
    category = await db.find_category_by_keyword(user_id, text, trans_type)
    category_id = None
    category_name = None
    if category:
        category_id = category["id"]
        category_name = category["name"]
    else:
        guessed = guess_category(text, trans_type)
        if guessed:
            # Find this category in DB
            cats = await db.get_categories(user_id, trans_type)
            for c in cats:
                if c["name"] == guessed:
                    category_id = c["id"]
                    category_name = c["name"]
                    break
        if not category_id:
            # Default fallback
            fallback_name = "Прочее" if trans_type == "expense" else "Другое"
            cats = await db.get_categories(user_id, trans_type)
            for c in cats:
                if c["name"] == fallback_name:
                    category_id = c["id"]
                    category_name = c["name"]
                    break

    return {
        "amount": amount,
        "type": trans_type,
        "category_id": category_id,
        "category_name": category_name,
        "comment": comment,
        "date": trans_date
    }


def format_money(amount: float, currency: str = "₽") -> str:
    """Format money amount for display."""
    if amount == int(amount):
        return f"{int(amount):,} {currency}".replace(",", " ")
    return f"{amount:,.2f} {currency}".replace(",", " ")
