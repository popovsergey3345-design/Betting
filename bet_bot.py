import asyncio
import logging
from threading import Thread

import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from config import BOT_TOKEN, WEBAPP_URL, SERVER_HOST, SERVER_PORT
from server import app as fastapi_app
import database as db

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = await db.get_or_create_user(message.from_user.id, message.from_user.first_name)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Открыть BetMachine", web_app=WebAppInfo(url=WEBAPP_URL))],
    ])
    await message.answer(
        f"🎰 <b>BetMachine — Реальные матчи!</b>\n\n"
        f"Привет, <b>{message.from_user.first_name}</b>!\n\n"
        f"💰 Баланс: <b>{int(user['balance'])}</b> монет\n\n"
        f"⚽ Реальные матчи с реальными коэффициентами\n"
        f"🎲 Быстрые игры: монетка, кости, рулетка\n"
        f"💸 Кэшаут — забери выигрыш досрочно\n\n"
        f"👇 Нажми чтобы начать:",
        reply_markup=keyboard, parse_mode="HTML"
    )


@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    user = await db.get_or_create_user(message.from_user.id)
    await message.answer(f"💰 Баланс: <b>{int(user['balance'])}</b> монет", parse_mode="HTML")


def run_server():
    uvicorn.run(fastapi_app, host=SERVER_HOST, port=SERVER_PORT)


async def main():
    await db.init_db()
    server_thread = Thread(target=run_server, daemon=True)
    server_thread.start()
    print(f"✅ Сервер: http://localhost:{SERVER_PORT}")
    print("✅ Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
