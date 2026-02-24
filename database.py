# database.py
import aiosqlite
import os
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
                odds REAL,
                amount REAL,
                potential_win REAL,
                result TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                title TEXT,
                category TEXT,
                team_a TEXT,
                team_b TEXT,
                odds_a REAL,
                odds_draw REAL,
                odds_b REAL,
                status TEXT DEFAULT 'open',
                result TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def get_or_create_user(user_id, username=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        )
        user = await cursor.fetchone()
        if not user:
            await db.execute(
                "INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)",
                (user_id, username, START_BALANCE)
            )
            await db.commit()
            cursor = await db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            )
            user = await cursor.fetchone()
        return dict(user)


async def get_balance(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT balance FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def update_balance(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )
        await db.commit()


async def place_bet(user_id, event_id, event_title, pick, odds, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        balance = await get_balance(user_id)
        if balance < amount:
            return None, "Недостаточно средств"

        potential_win = round(amount * odds, 2)

        await db.execute(
            """INSERT INTO bets 
            (user_id, event_id, event_title, pick, odds, amount, potential_win)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, event_id, event_title, pick, odds, amount, potential_win)
        )
        await db.execute(
            "UPDATE users SET balance = balance - ?, total_bets = total_bets + 1 WHERE user_id = ?",
            (amount, user_id)
        )
        await db.commit()
        return {
            "event": event_title,
            "pick": pick,
            "odds": odds,
            "amount": amount,
            "potential_win": potential_win
        }, "OK"


async def get_user_bets(user_id, limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM bets WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_events(status="open"):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM events WHERE status = ?", (status,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def add_event(event_id, title, category, team_a, team_b,
                    odds_a, odds_draw, odds_b):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO events 
            (id, title, category, team_a, team_b, odds_a, odds_draw, odds_b)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (event_id, title, category, team_a, team_b,
             odds_a, odds_draw, odds_b)
        )
        await db.commit()


async def seed_events():
    events = [
        ("evt_1", "Реал Мадрид vs Барселона", "football",
         "Реал Мадрид", "Барселона", 2.10, 3.40, 3.20),
        ("evt_2", "Ман Сити vs Ливерпуль", "football",
         "Ман Сити", "Ливерпуль", 1.85, 3.60, 4.00),
        ("evt_3", "Лейкерс vs Уорриорз", "basketball",
         "Лейкерс", "Уорриорз", 1.95, 0, 1.90),
        ("evt_4", "Джокович vs Алькараз", "tennis",
         "Джокович", "Алькараз", 2.20, 0, 1.70),
        ("evt_5", "ПСЖ vs Бавария", "football",
         "ПСЖ", "Бавария", 2.50, 3.30, 2.80),
    ]
    for evt in events:
        await add_event(*evt)