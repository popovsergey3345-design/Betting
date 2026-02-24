# config.py
import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "сюда-свой-токен")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://тут-будет-ссылка")
SERVER_HOST = "0.0.0.0"
SERVER_PORT = int(os.getenv("PORT", 8080))
START_BALANCE = 1000