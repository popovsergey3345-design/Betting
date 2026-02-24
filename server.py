import time
import random
import aiosqlite
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import database as db
from odds_api import get_upcoming_events, get_live_scores

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Кэш в памяти
events_cache = {"events": [], "updated": 0}
CACHE_TTL = 300  # Обновлять каждые 5 минут


class BetRequest(BaseModel):
    user_id: int
    event_id: str
    event_title: str
    pick: str
    pick_label: str
    odds: float
    amount: float


class CashoutRequest(BaseModel):
    user_id: int
    bet_id: int


class QuickBetRequest(BaseModel):
    user_id: int
    game: str
    pick: str
    amount: float


@app.on_event("startup")
async def startup():
    await db.init_db()
    # Загружаем события при старте
    asyncio.create_task(refresh_events())
    # Фоновая задача — проверка результатов
    asyncio.create_task(background_settler())


async def refresh_events():
    """Загрузить свежие события"""
    global events_cache
    try:
        print("🔄 Загружаем события...")
        events = await get_upcoming_events()
        if events:
            events_cache["events"] = events
            events_cache["updated"] = time.time()
            await db.cache_events(events)
            print(f"✅ Загружено {len(events)} событий")
        else:
            # Пробуем из кэша БД
            cached, updated = await db.get_cached_events()
            if cached:
                events_cache["events"] = cached
                events_cache["updated"] = updated
                print(f"📦 Из кэша: {len(cached)} событий")
    except Exception as e:
        print(f"❌ Ошибка загрузки событий: {e}")


async def background_settler():
    """Фоновая задача: проверяем результаты матчей каждые 10 минут"""
    while True:
        await asyncio.sleep(600)  # 10 минут
        try:
            pending = await db.get_pending_bets()
            if not pending:
                continue

            scores = await get_live_scores()
            pending_ids = {b["event_id"] for b in pending}

            for score in scores:
                if score["id"] in pending_ids and score.get("result"):
                    settled = await db.settle_bet(score["id"], score["result"])
                    if settled:
                        print(f"✅ Рассчитан матч {score['id']}: {len(settled)} ставок")

        except Exception as e:
            print(f"⚠️ Ошибка расчёта: {e}")


# --- Страница ---

@app.get("/")
async def root():
    return FileResponse("webapp/index.html")

app.mount("/webapp", StaticFiles(directory="webapp"), name="webapp")


# --- API ---

@app.get("/api/user/{user_id}")
async def get_user(user_id: int, username: str = "player"):
    return await db.get_or_create_user(user_id, username)


@app.get("/api/events")
async def get_events(sport: str = "all"):
    global events_cache

    # Обновляем кэш если устарел
    if time.time() - events_cache["updated"] > CACHE_TTL:
        await refresh_events()

    events = events_cache["events"]

    if sport != "all":
        events = [e for e in events if e["category"] == sport]

    return {
        "events": events,
        "updated": events_cache["updated"],
        "total": len(events)
    }


@app.get("/api/events/refresh")
async def force_refresh():
    await refresh_events()
    return {"message": "OK", "total": len(events_cache["events"])}


@app.post("/api/bet")
async def place_bet(bet: BetRequest):
    if bet.amount < 10:
        raise HTTPException(400, "Минимальная ставка: 10 монет")
    balance = await db.get_balance(bet.user_id)
    if balance < bet.amount:
        raise HTTPException(400, "Недостаточно средств")

    result, msg = await db.place_bet(
        bet.user_id, bet.event_id, bet.event_title,
        bet.pick, bet.pick_label, bet.odds, bet.amount
    )
    if not result:
        raise HTTPException(400, msg)

    new_balance = await db.get_balance(bet.user_id)
    return {"bet": result, "new_balance": new_balance}


@app.post("/api/cashout")
async def cashout(req: CashoutRequest):
    result, msg = await db.cashout_bet(req.bet_id, req.user_id)
    if not result:
        raise HTTPException(400, msg)
    new_balance = await db.get_balance(req.user_id)
    return {"cashout": result, "new_balance": new_balance}


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
        win = req.pick == result_value
        if win: winnings = req.amount * 1.95
    elif req.game == "dice":
        result_value = str(random.randint(1, 6))
        if req.pick in ["low", "high"]:
            v = int(result_value)
            if (req.pick == "low" and v <= 3) or (req.pick == "high" and v >= 4):
                win, winnings = True, req.amount * 1.95
        elif req.pick == result_value:
            win, winnings = True, req.amount * 5.5
    elif req.game == "roulette":
        result_value = str(random.randint(0, 36))
        n = int(result_value)
        red = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
        black = {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35}
        if req.pick == "red" and n in red: win, winnings = True, req.amount * 2
        elif req.pick == "black" and n in black: win, winnings = True, req.amount * 2
        elif req.pick == "green" and n == 0: win, winnings = True, req.amount * 35

    if win:
        await db.update_balance(req.user_id, winnings)
    new_balance = await db.get_balance(req.user_id)
    return {"game": req.game, "pick": req.pick, "result": result_value,
            "win": win, "winnings": round(winnings, 2), "new_balance": round(new_balance, 2)}


@app.get("/api/bets/{user_id}")
async def get_user_bets(user_id: int):
    return {"bets": await db.get_user_bets(user_id)}


@app.get("/api/leaderboard")
async def leaderboard():
    async with aiosqlite.connect(db.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT user_id, username, balance, total_bets, total_wins FROM users ORDER BY balance DESC LIMIT 20"
        )
        return {"leaderboard": [dict(r) for r in await cursor.fetchall()]}
