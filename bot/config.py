import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com")
DATABASE_URL = os.getenv("DATABASE_URL", "database.db")
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "secret")

# Default categories
DEFAULT_CATEGORIES_INCOME = ["Зарплата", "Фриланс", "Подарок", "Инвестиции", "Другое"]
DEFAULT_CATEGORIES_EXPENSE = [
    "Еда", "Транспорт", "Жильё", "Коммунальные услуги", "Связь/Интернет",
    "Развлечения", "Покупки", "Здоровье", "Образование", "Прочее"
]
