import aiosqlite
import os
import time
from config import START_BALANCE

DB_PATH = os.path.join("data", "betting.db")


async def init_db():
    os.makedirs("data", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance REAL DEFAULT 1000,
                total_bets INTEGER DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                total_profit REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_id TEXT,
                event_title TEXT,
                pick TEXT,
                pick_label TEXT,
                odds REAL,
                amount REAL,
                potential_win REAL,
                result TEXT DEFAULT 'pending',
                cashout_available INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cached_events (
                id TEXT PRIMARY KEY,
                data TEXT,
                updated_at REAL
            )
        """)
        await db.commit()


async def get_or_create_user(user_id, username=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = await cursor.fetchone()
        if not user:
            await db.execute(
                "INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)",
                (user_id, username, START_BALANCE)
            )
            await db.commit()
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = await cursor.fetchone()
        return dict(user)


async def get_balance(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0


async def update_balance(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )
        await db.commit()


async def place_bet(user_id, event_id, event_title, pick, pick_label, odds, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        balance = await get_balance(user_id)
        if balance < amount:
            return None, "Недостаточно средств"

        potential_win = round(amount * odds, 2)
        await db.execute(
            """INSERT INTO bets 
            (user_id, event_id, event_title, pick, pick_label, odds, amount, potential_win)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, event_id, event_title, pick, pick_label, odds, amount, potential_win)
        )
        await db.execute(
            "UPDATE users SET balance = balance - ?, total_bets = total_bets + 1 WHERE user_id = ?",
            (amount, user_id)
        )
        await db.commit()
        return {
            "event": event_title,
            "pick": pick_label,
            "odds": odds,
            "amount": amount,
            "potential_win": potential_win
        }, "OK"


async def cashout_bet(bet_id, user_id):
    """Кэшаут — забрать часть выигрыша досрочно"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM bets WHERE id = ? AND user_id = ? AND result = 'pending'",
            (bet_id, user_id)
        )
        bet = await cursor.fetchone()
        if not bet:
            return None, "Ставка не найдена"

        bet = dict(bet)
        if not bet["cashout_available"]:
            return None, "Кэшаут недоступен"

        # Кэшаут = 70-85% от суммы ставки
        import random
        cashout_percent = random.uniform(0.70, 0.85)
        cashout_amount = round(bet["amount"] * cashout_percent, 2)

        await db.execute(
            "UPDATE bets SET result = 'cashout', cashout_available = 0 WHERE id = ?",
            (bet_id,)
        )
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (cashout_amount, user_id)
        )
        await db.commit()
        return {"cashout_amount": cashout_amount, "bet_id": bet_id}, "OK"


async def settle_bet(event_id, result):
    """Рассчитать ставки после завершения матча"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM bets WHERE event_id = ? AND result = 'pending'",
            (event_id,)
        )
        bets = await cursor.fetchall()
        settled = []

        for bet in bets:
            bet = dict(bet)
            if bet["pick"] == result:
                # Выигрыш
                await db.execute("UPDATE bets SET result = 'win' WHERE id = ?", (bet["id"],))
                await db.execute(
                    "UPDATE users SET balance = balance + ?, total_wins = total_wins + 1, total_profit = total_profit + ? WHERE user_id = ?",
                    (bet["potential_win"], bet["potential_win"] - bet["amount"], bet["user_id"])
                )
                settled.append({"bet_id": bet["id"], "result": "win", "user_id": bet["user_id"]})
            else:
                await db.execute("UPDATE bets SET result = 'lose' WHERE id = ?", (bet["id"],))
                await db.execute(
                    "UPDATE users SET total_profit = total_profit - ? WHERE user_id = ?",
                    (bet["amount"], bet["user_id"])
                )
                settled.append({"bet_id": bet["id"], "result": "lose", "user_id": bet["user_id"]})

        await db.commit()
        return settled


async def get_user_bets(user_id, limit=30):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM bets WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )
        return [dict(r) for r in await cursor.fetchall()]


async def get_pending_bets():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT DISTINCT event_id FROM bets WHERE result = 'pending'")
        return [dict(r) for r in await cursor.fetchall()]


# --- Кэш событий ---

async def cache_events(events):
    import json
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cached_events")
        for evt in events:
            await db.execute(
                "INSERT OR REPLACE INTO cached_events (id, data, updated_at) VALUES (?, ?, ?)",
                (evt["id"], json.dumps(evt, ensure_ascii=False), time.time())
            )
        await db.commit()


async def get_cached_events():
    import json
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT data, updated_at FROM cached_events")
        rows = await cursor.fetchall()
        if not rows:
            return None, 0
        events = [json.loads(r[0]) for r in rows]
        updated = rows[0][1] if rows else 0
        return events, updated
