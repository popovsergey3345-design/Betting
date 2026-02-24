# odds_api.py
import aiohttp
import asyncio
from datetime import datetime, timezone
from config import ODDS_API_KEY, SPORTS, SPORT_NAMES


BASE_URL = "https://api.the-odds-api.com/v4"


async def fetch_json(url, params):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                remaining = resp.headers.get("x-requests-remaining", "?")
                print(f"📡 API запрос OK. Осталось запросов: {remaining}")
                return data
            else:
                text = await resp.text()
                print(f"❌ API ошибка {resp.status}: {text}")
                return None


async def get_upcoming_events():
    """Получить все предстоящие матчи с коэффициентами"""
    all_events = []

    for sport_key in SPORTS:
        try:
            url = f"{BASE_URL}/sports/{sport_key}/odds/"
            params = {
                "apiKey": ODDS_API_KEY,
                "regions": "eu",
                "markets": "h2h,totals",
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            }

            data = await fetch_json(url, params)
            if not data:
                continue

            for game in data:
                event = parse_event(game, sport_key)
                if event:
                    all_events.append(event)

        except Exception as e:
            print(f"⚠️ Ошибка загрузки {sport_key}: {e}")
            continue

    # Сортируем по дате
    all_events.sort(key=lambda x: x["commence_time"])
    return all_events


async def get_live_scores():
    """Получить результаты завершённых матчей"""
    all_scores = []

    for sport_key in SPORTS:
        try:
            url = f"{BASE_URL}/sports/{sport_key}/scores/"
            params = {
                "apiKey": ODDS_API_KEY,
                "daysFrom": 3,
                "dateFormat": "iso",
            }

            data = await fetch_json(url, params)
            if not data:
                continue

            for game in data:
                if game.get("completed"):
                    score_info = {
                        "id": game["id"],
                        "completed": True,
                        "scores": game.get("scores"),
                        "home_team": game.get("home_team"),
                        "away_team": game.get("away_team"),
                    }

                    # Определяем победителя
                    scores = game.get("scores")
                    if scores and len(scores) == 2:
                        s0 = int(scores[0].get("score", 0))
                        s1 = int(scores[1].get("score", 0))
                        if s0 > s1:
                            score_info["winner"] = scores[0]["name"]
                            score_info["result"] = "team_a" if scores[0]["name"] == game["home_team"] else "team_b"
                        elif s1 > s0:
                            score_info["winner"] = scores[1]["name"]
                            score_info["result"] = "team_b" if scores[1]["name"] == game["away_team"] else "team_a"
                        else:
                            score_info["winner"] = "draw"
                            score_info["result"] = "draw"
                        score_info["score_text"] = f"{s0}:{s1}"

                    all_scores.append(score_info)

        except Exception as e:
            print(f"⚠️ Ошибка загрузки счёта {sport_key}: {e}")
            continue

    return all_scores


def parse_event(game, sport_key):
    """Преобразовать данные API в наш формат"""
    try:
        # Находим лучшие коэффициенты
        odds_a = 0
        odds_draw = 0
        odds_b = 0
        total_line = 0
        total_over = 0
        total_under = 0

        home_team = game.get("home_team", "")
        away_team = game.get("away_team", "")

        for bookmaker in game.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"] == "h2h":
                    for outcome in market.get("outcomes", []):
                        if outcome["name"] == home_team:
                            odds_a = max(odds_a, outcome["price"])
                        elif outcome["name"] == away_team:
                            odds_b = max(odds_b, outcome["price"])
                        elif outcome["name"] == "Draw":
                            odds_draw = max(odds_draw, outcome["price"])

                elif market["key"] == "totals":
                    for outcome in market.get("outcomes", []):
                        if outcome["name"] == "Over":
                            total_over = outcome["price"]
                            total_line = outcome.get("point", 2.5)
                        elif outcome["name"] == "Under":
                            total_under = outcome["price"]
            # Берём только первого букмекера с данными
            if odds_a > 0:
                break

        if odds_a == 0 or odds_b == 0:
            return None

        # Определяем категорию
        category = "football"
        if "basketball" in sport_key:
            category = "basketball"
        elif "tennis" in sport_key:
            category = "tennis"
        elif "hockey" in sport_key or "ice" in sport_key:
            category = "hockey"
        elif "mma" in sport_key:
            category = "mma"

        # Без ничьей для баскетбола, тенниса, MMA
        if category in ["basketball", "tennis", "mma"]:
            odds_draw = 0

        league_name = SPORT_NAMES.get(sport_key, sport_key)

        return {
            "id": game["id"],
            "title": f"{home_team} vs {away_team}",
            "league": league_name,
            "sport_key": sport_key,
            "category": category,
            "team_a": home_team,
            "team_b": away_team,
            "odds_a": round(odds_a, 2),
            "odds_draw": round(odds_draw, 2),
            "odds_b": round(odds_b, 2),
            "total_line": total_line,
            "total_over": round(total_over, 2) if total_over else 0,
            "total_under": round(total_under, 2) if total_under else 0,
            "commence_time": game.get("commence_time", ""),
            "status": "upcoming",
        }

    except Exception as e:
        print(f"⚠️ Ошибка парсинга: {e}")
        return None


async def get_available_sports():
    """Получить список доступных видов спорта"""
    url = f"{BASE_URL}/sports/"
    params = {"apiKey": ODDS_API_KEY}
    data = await fetch_json(url, params)
    if data:
        active = [s for s in data if s.get("active")]
        return active
    return []
