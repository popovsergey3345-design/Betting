# server.py
import random
import aiosqlite

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import database as db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Модели данных ---

class BetRequest(BaseModel):
    user_id: int
    event_id: str
    event_title: str
    pick: str
    pick_label: str
    odds: float
    amount: float


class QuickBetRequest(BaseModel):
    user_id: int
    game: str
    pick: str
    amount: float


# --- Запуск ---

@app.on_event("startup")
async def startup():
    await db.init_db()
    await db.seed_events()


# --- Главная страница ---

@app.get("/")
async def root():
    return FileResponse("webapp/index.html")


app.mount("/webapp", StaticFiles(directory="webapp"), name="webapp")


# --- API ---

@app.get("/api/user/{user_id}")
async def get_user(user_id: int, username: str = "player"):
    user = await db.get_or_create_user(user_id, username)
    return user


@app.get("/api/events")
async def get_events():
    events = await db.get_events("open")
    return {"events": events}


@app.post("/api/bet")
async def place_bet(bet: BetRequest):
    if bet.amount < 10:
        raise HTTPException(400, "Минимальная ставка: 10 монет")

    balance = await db.get_balance(bet.user_id)
    if balance < bet.amount:
        raise HTTPException(400, "Недостаточно средств")

    result, msg = await db.place_bet(
        bet.user_id, bet.event_id, bet.event_title,
        bet.pick, bet.odds, bet.amount
    )
    if result is None:
        raise HTTPException(400, msg)

    new_balance = await db.get_balance(bet.user_id)
    return {"bet": result, "new_balance": new_balance}


@app.post("/api/quick-bet")
async def quick_bet(req: QuickBetRequest):
    if req.amount < 10:
        raise HTTPException(400, "Минимальная ставка: 10 монет")

    balance = await db.get_balance(req.user_id)
    if balance < req.amount:
        raise HTTPException(400, "Недостаточно средств")

    await db.update_balance(req.user_id, -req.amount)

    win = False
    winnings = 0
    result_value = ""

    if req.game == "coinflip":
        result_value = random.choice(["heads", "tails"])
        win = (req.pick == result_value)
        if win:
            winnings = req.amount * 1.95

    elif req.game == "dice":
        result_value = str(random.randint(1, 6))
        if req.pick in ["low", "high"]:
            dice_val = int(result_value)
            if req.pick == "low" and dice_val <= 3:
                win = True
                winnings = req.amount * 1.95
            elif req.pick == "high" and dice_val >= 4:
                win = True
                winnings = req.amount * 1.95
        else:
            if req.pick == result_value:
                win = True
                winnings = req.amount * 5.5

    elif req.game == "roulette":
        result_value = str(random.randint(0, 36))
        roulette_num = int(result_value)
        red = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
        black = {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35}
        if req.pick == "red" and roulette_num in red:
            win, winnings = True, req.amount * 2.0
        elif req.pick == "black" and roulette_num in black:
            win, winnings = True, req.amount * 2.0
        elif req.pick == "green" and roulette_num == 0:
            win, winnings = True, req.amount * 35.0

    if win:
        await db.update_balance(req.user_id, winnings)

    new_balance = await db.get_balance(req.user_id)
    return {
        "game": req.game,
        "pick": req.pick,
        "result": result_value,
        "win": win,
        "winnings": round(winnings, 2),
        "new_balance": round(new_balance, 2)
    }


@app.get("/api/bets/{user_id}")
async def get_user_bets(user_id: int):
    bets = await db.get_user_bets(user_id)
    return {"bets": bets}


@app.get("/api/leaderboard")
async def leaderboard():
    async with aiosqlite.connect(db.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT user_id, username, balance, total_bets, total_wins FROM users ORDER BY balance DESC LIMIT 20"
        )
        rows = await cursor.fetchall()
        return {"leaderboard": [dict(r) for r in rows]}