import aiosqlite
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from bot.config import DATABASE_URL, DEFAULT_CATEGORIES_EXPENSE, DEFAULT_CATEGORIES_INCOME


class Database:
    def __init__(self, db_path: str = DATABASE_URL):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self):
        if self.conn:
            await self.conn.close()

    async def _create_tables(self):
        await self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                currency TEXT DEFAULT '₽'
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                is_default INTEGER DEFAULT 0,
                UNIQUE(user_id, name, type)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                comment TEXT,
                date TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (category_id) REFERENCES categories(id)
            );

            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                limit_amount REAL NOT NULL,
                month TEXT NOT NULL,
                UNIQUE(user_id, category_id, month),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (category_id) REFERENCES categories(id)
            );

            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                UNIQUE(user_id, keyword),
                FOREIGN KEY (category_id) REFERENCES categories(id)
            );

            CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
            CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
            CREATE INDEX IF NOT EXISTS idx_categories_user ON categories(user_id);
            CREATE INDEX IF NOT EXISTS idx_budgets_user ON budgets(user_id);
        """)
        await self.conn.commit()
        await self._seed_default_categories_global()

    async def _seed_default_categories_global(self):
        # Default categories with user_id=NULL (global defaults)
        for name in DEFAULT_CATEGORIES_EXPENSE:
            await self.conn.execute(
                "INSERT OR IGNORE INTO categories (user_id, name, type, is_default) VALUES (NULL, ?, 'expense', 1)",
                (name,)
            )
        for name in DEFAULT_CATEGORIES_INCOME:
            await self.conn.execute(
                "INSERT OR IGNORE INTO categories (user_id, name, type, is_default) VALUES (NULL, ?, 'income', 1)",
                (name,)
            )
        await self.conn.commit()

    async def get_or_create_user(self, user_id: int, username: str, first_name: str) -> Dict:
        cursor = await self.conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        await self.conn.execute(
            "INSERT INTO users (id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name)
        )
        await self.conn.commit()
        cursor = await self.conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        )
        return dict(await cursor.fetchone())

    async def get_categories(self, user_id: int, trans_type: str) -> List[Dict]:
        cursor = await self.conn.execute(
            "SELECT * FROM categories WHERE (user_id = ? OR user_id IS NULL) AND type = ? ORDER BY is_default DESC, name",
            (user_id, trans_type)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_category_by_id(self, category_id: int) -> Optional[Dict]:
        cursor = await self.conn.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def add_custom_category(self, user_id: int, name: str, trans_type: str) -> int:
        cursor = await self.conn.execute(
            "INSERT OR IGNORE INTO categories (user_id, name, type, is_default) VALUES (?, ?, ?, 0)",
            (user_id, name, trans_type)
        )
        await self.conn.commit()
        cursor = await self.conn.execute(
            "SELECT id FROM categories WHERE (user_id = ? OR user_id IS NULL) AND name = ? AND type = ?",
            (user_id, name, trans_type)
        )
        row = await cursor.fetchone()
        return row["id"] if row else None

    async def add_transaction(self, user_id: int, amount: float, category_id: int,
                              trans_type: str, comment: str = "", trans_date: str = None) -> int:
        if not trans_date:
            trans_date = date.today().isoformat()
        cursor = await self.conn.execute(
            """INSERT INTO transactions (user_id, amount, category_id, type, comment, date)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, amount, category_id, trans_type, comment, trans_date)
        )
        await self.conn.commit()
        return cursor.lastrowid

    async def get_transactions(self, user_id: int, start_date: str = None,
                               end_date: str = None, limit: int = 100) -> List[Dict]:
        query = "SELECT t.*, c.name as category_name FROM transactions t JOIN categories c ON t.category_id = c.id WHERE t.user_id = ?"
        params = [user_id]
        if start_date:
            query += " AND t.date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND t.date <= ?"
            params.append(end_date)
        query += " ORDER BY t.date DESC, t.id DESC LIMIT ?"
        params.append(limit)
        cursor = await self.conn.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_transaction_by_id(self, tx_id: int) -> Optional[Dict]:
        cursor = await self.conn.execute(
            "SELECT t.*, c.name as category_name FROM transactions t JOIN categories c ON t.category_id = c.id WHERE t.id = ?",
            (tx_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def delete_transaction(self, tx_id: int) -> bool:
        cursor = await self.conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        await self.conn.commit()
        return cursor.rowcount > 0

    async def get_summary_by_category(self, user_id: int, trans_type: str,
                                       start_date: str, end_date: str) -> List[Dict]:
        query = """SELECT c.name, c.id, SUM(t.amount) as total
                   FROM transactions t JOIN categories c ON t.category_id = c.id
                   WHERE t.user_id = ? AND t.type = ? AND t.date >= ? AND t.date <= ?
                   GROUP BY c.id, c.name ORDER BY total DESC"""
        cursor = await self.conn.execute(query, (user_id, trans_type, start_date, end_date))
        return [dict(r) for r in await cursor.fetchall()]

    async def get_daily_totals(self, user_id: int, trans_type: str,
                                start_date: str, end_date: str) -> List[Dict]:
        query = """SELECT date, SUM(amount) as total FROM transactions
                   WHERE user_id = ? AND type = ? AND date >= ? AND date <= ?
                   GROUP BY date ORDER BY date"""
        cursor = await self.conn.execute(query, (user_id, trans_type, start_date, end_date))
        return [dict(r) for r in await cursor.fetchall()]

    async def get_total(self, user_id: int, trans_type: str,
                         start_date: str, end_date: str) -> float:
        cursor = await self.conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = ? AND type = ? AND date >= ? AND date <= ?",
            (user_id, trans_type, start_date, end_date)
        )
        row = await cursor.fetchone()
        return row["total"]

    async def set_budget(self, user_id: int, category_id: int, limit_amount: float, month: str) -> int:
        cursor = await self.conn.execute(
            """INSERT INTO budgets (user_id, category_id, limit_amount, month)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, category_id, month) DO UPDATE SET limit_amount = excluded.limit_amount""",
            (user_id, category_id, limit_amount, month)
        )
        await self.conn.commit()
        return cursor.lastrowid

    async def get_budgets(self, user_id: int, month: str) -> List[Dict]:
        query = """SELECT b.*, c.name as category_name,
                   COALESCE((SELECT SUM(t.amount) FROM transactions t
                             WHERE t.user_id = b.user_id AND t.category_id = b.category_id
                             AND t.type = 'expense' AND t.date LIKE ?), 0) as spent
                   FROM budgets b JOIN categories c ON b.category_id = c.id
                   WHERE b.user_id = ? AND b.month = ?"""
        month_pattern = f"{month}%"
        cursor = await self.conn.execute(query, (month_pattern, user_id, month))
        return [dict(r) for r in await cursor.fetchall()]

    async def delete_budget(self, user_id: int, category_id: int, month: str) -> bool:
        cursor = await self.conn.execute(
            "DELETE FROM budgets WHERE user_id = ? AND category_id = ? AND month = ?",
            (user_id, category_id, month)
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def add_keyword(self, user_id: int, category_id: int, keyword: str):
        await self.conn.execute(
            "INSERT OR REPLACE INTO keywords (user_id, category_id, keyword) VALUES (?, ?, ?)",
            (user_id, category_id, keyword.lower().strip())
        )
        await self.conn.commit()

    async def find_category_by_keyword(self, user_id: int, text: str, trans_type: str) -> Optional[Dict]:
        words = text.lower().split()
        for word in words:
            cursor = await self.conn.execute(
                """SELECT c.* FROM keywords k JOIN categories c ON k.category_id = c.id
                   WHERE (k.user_id = ? OR k.user_id IS NULL) AND c.type = ? AND k.keyword = ?""",
                (user_id, trans_type, word)
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)
        return None


db = Database()
