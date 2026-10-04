"""FastAPI server: serves the Telegram Mini App and JSON API.

Run in polling/development mode:
    python bot_polling.py          # starts aiogram long-polling
    python server.py               # starts web server on :8000 (serves Web App + API)

In production, serve behind HTTPS (nginx/Caddy) and point WEBAPP_URL to your domain.
"""
import asyncio
import json
import hmac
import hashlib
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from bot.config import BOT_TOKEN, DEBUG
from bot.database import db
from bot.services.parser import format_money

WEBAPP_DIR = Path(__file__).parent / "webapp"

app = FastAPI(title="MyLifeStyle API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Telegram Web App initData verification ----
def verify_telegram_init_data(init_data: str, bot_token: str) -> Optional[dict]:
    """Verify Telegram WebApp initData signature. Returns parsed data dict or None."""
    try:
        parsed = dict(chunk.split("=", 1) for chunk in init_data.split("&") if "=" in chunk)
    except ValueError:
        return None
    # URL decode values
    from urllib.parse import unquote
    parsed = {k: unquote(v) for k, v in parsed.items()}
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    if expected_hash != received_hash:
        return None
    if "auth_date" in parsed:
        if abs(int(parsed["auth_date"]) - time.time()) > 86400:
            return None
    user_json = parsed.get("user")
    if user_json:
        try:
            parsed["user"] = json.loads(user_json)
        except json.JSONDecodeError:
            return None
    return parsed


async def get_current_user(init_data: str = Header(None, alias="X-Telegram-Init-Data")):
    """Dependency: verifies Telegram initData and returns the user dict."""
    if not init_data:
        # Allow anonymous calls in debug mode for testing
        if DEBUG:
            # Dev: fall back to a demo user id=1
            return {"id": 1, "first_name": "Dev", "username": "dev"}
        raise HTTPException(401, "Missing X-Telegram-Init-Data header")
    parsed = verify_telegram_init_data(init_data, BOT_TOKEN)
    if not parsed:
        if DEBUG:
            return {"id": 1, "first_name": "Dev", "username": "dev"}
        raise HTTPException(401, "Invalid init data")
    return parsed.get("user") or {"id": 1, "first_name": "Guest"}


# ---- Models ----
class TransactionIn(BaseModel):
    amount: float
    category_id: int
    type: str
    comment: str = ""
    date: Optional[str] = None


class CategoryIn(BaseModel):
    name: str
    type: str


class BudgetIn(BaseModel):
    category_id: int
    limit_amount: float
    month: Optional[str] = None


# ---- API routes ----
@app.get("/app", response_class=HTMLResponse)
async def serve_webapp():
    return FileResponse(WEBAPP_DIR / "index.html")


@app.get("/app/{rest:path}")
async def serve_static(rest: str):
    file_path = WEBAPP_DIR / rest
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    return FileResponse(WEBAPP_DIR / "index.html")


@app.get("/api/me")
async def get_me(request: Request):
    init_data = request.headers.get("x-telegram-init-data")
    user = await get_current_user(init_data)
    await db.get_or_create_user(user["id"], user.get("username", ""), user.get("first_name", ""))
    return {"id": user["id"], "first_name": user.get("first_name", ""),
            "username": user.get("username", "")}


@app.get("/api/categories")
async def list_categories(request: Request, type: str = "expense"):
    init_data = request.headers.get("x-telegram-init-data")
    user = await get_current_user(init_data)
    return await db.get_categories(user["id"], type)


@app.post("/api/categories")
async def create_category(request: Request, data: CategoryIn):
    init_data = request.headers.get("x-telegram-init-data")
    user = await get_current_user(init_data)
    cat_id = await db.add_custom_category(user["id"], data.name, data.type)
    return {"id": cat_id, "name": data.name, "type": data.type}


@app.get("/api/transactions")
async def list_transactions(request: Request, period: str = "month"):
    init_data = request.headers.get("x-telegram-init-data")
    user = await get_current_user(init_data)
    today = date.today()
    if period == "week":
        start = today - timedelta(days=6)
    elif period == "prevmonth":
        first = today.replace(day=1)
        last = first - timedelta(days=1)
        start = last.replace(day=1)
        today = last
    else:
        start = today.replace(day=1)
    return await db.get_transactions(user["id"], start.isoformat(), today.isoformat(), limit=200)


@app.post("/api/transactions")
async def create_transaction(request: Request, data: TransactionIn):
    init_data = request.headers.get("x-telegram-init-data")
    user = await get_current_user(init_data)
    tx_id = await db.add_transaction(
        user_id=user["id"],
        amount=data.amount,
        category_id=data.category_id,
        trans_type=data.type,
        comment=data.comment,
        trans_date=data.date
    )
    tx = await db.get_transaction_by_id(tx_id)
    return tx


@app.delete("/api/transactions/{tx_id}")
async def delete_transaction(tx_id: int, request: Request):
    init_data = request.headers.get("x-telegram-init-data")
    user = await get_current_user(init_data)
    ok = await db.delete_transaction(tx_id)
    if not ok:
        raise HTTPException(404, "Not found")
    return {"deleted": True}


@app.get("/api/summary")
async def summary(request: Request, period: str = "month"):
    init_data = request.headers.get("x-telegram-init-data")
    user = await get_current_user(init_data)
    today = date.today()
    import calendar
    if period == "week":
        start = today - timedelta(days=6)
        end = today
        prev_start = start - timedelta(days=7)
        prev_end = start - timedelta(days=1)
    elif period == "prevmonth":
        first = today.replace(day=1)
        last_prev = first - timedelta(days=1)
        start = last_prev.replace(day=1)
        end = last_prev
        prev_first = (start - timedelta(days=1)).replace(day=1)
        prev_end = start - timedelta(days=1)
    else:
        start = today.replace(day=1)
        end = today
        prev_end = start - timedelta(days=1)
        prev_start = prev_end.replace(day=1)

    inc = await db.get_total(user["id"], "income", start.isoformat(), end.isoformat())
    exp = await db.get_total(user["id"], "expense", start.isoformat(), end.isoformat())
    p_inc = await db.get_total(user["id"], "income", prev_start.isoformat(), prev_end.isoformat())
    p_exp = await db.get_total(user["id"], "expense", prev_start.isoformat(), prev_end.isoformat())
    by_cat = await db.get_summary_by_category(user["id"], "expense", start.isoformat(), end.isoformat())
    daily = await db.get_daily_totals(user["id"], "expense", start.isoformat(), end.isoformat())
    budgets = await db.get_budgets(user["id"], start.strftime("%Y-%m"))

    return {
        "income": inc,
        "expense": exp,
        "balance": inc - exp,
        "prev_income": p_inc,
        "prev_expense": p_exp,
        "prev_balance": p_inc - p_exp,
        "by_category": by_cat,
        "daily": daily,
        "budgets": budgets,
        "period": {"start": start.isoformat(), "end": end.isoformat()}
    }


@app.get("/api/budgets")
async def list_budgets(request: Request):
    init_data = request.headers.get("x-telegram-init-data")
    user = await get_current_user(init_data)
    month = date.today().strftime("%Y-%m")
    return await db.get_budgets(user["id"], month)


@app.post("/api/budgets")
async def set_budget(request: Request, data: BudgetIn):
    init_data = request.headers.get("x-telegram-init-data")
    user = await get_current_user(init_data)
    month = data.month or date.today().strftime("%Y-%m")
    await db.set_budget(user["id"], data.category_id, data.limit_amount, month)
    return {"ok": True}


@app.delete("/api/budgets/{category_id}")
async def remove_budget(category_id: int, request: Request):
    init_data = request.headers.get("x-telegram-init-data")
    user = await get_current_user(init_data)
    month = date.today().strftime("%Y-%m")
    ok = await db.delete_budget(user["id"], category_id, month)
    return {"deleted": ok}


@app.on_event("startup")
async def startup():
    await db.connect()


@app.on_event("shutdown")
async def shutdown():
    await db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=DEBUG)
