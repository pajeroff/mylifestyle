#!/bin/bash
# Convenience script: activates venv and starts both bot (polling) and web server
# using background processes. Stop with Ctrl+C.
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
fi

if [ ! -f .env ]; then
    echo "⚠️  .env не найден — копирую из .env.example. Не забудьте вставить BOT_TOKEN!"
    cp .env.example .env
fi

echo "🚀 Запускаю веб-сервер Mini App (порт 8000)..."
.venv/bin/python server.py &
SERVER_PID=$!

echo "🤖 Запускаю бота (long-polling)..."
.venv/bin/python bot_polling.py &
BOT_PID=$!

trap "echo 'Останавливаю...'; kill $SERVER_PID $BOT_PID 2>/dev/null; exit" INT TERM
wait
