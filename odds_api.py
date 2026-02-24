import aiohttp
import asyncio
from config import ODDS_API_KEY, SPORTS, SPORT_NAMES

BASE_URL = "https://api.the-odds-api.com/v4"


async def fetch_json(url, params):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                remaining = resp.headers.get("x-requests-remaining", "?")
                print(f"📡 OK. Осталось запросов: {remaining}")
                return data
            elif resp.status == 429:
                print("⚠️ Слишком частые запросы, пропускаем...")
                return None
            else:
                text = await resp.text()
                print(f"❌ API ошибка {resp.status}: {text}")
                return None


async def get_upcoming_events():
    all_events = []

    for sport_key in SPORTS:
        try:
            url = f"{BASE_URL}/sports/{sport_key}/odds/"
            params = {
                "apiKey": ODDS_API_KEY,
                "regions": "eu",
                "markets": "h2h",
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            }

            data = await fetch_json(url, params)
            if data:
                for game in data:
                    event = parse_event(game, sport_key)
                    if event:
                        all_events.append(event)

            # Пауза между запросами чтобы не получить 429
            await asyncio.sleep(1.5)

        except Exception as e:
            print(f"⚠️ Ошибка {sport_key}: {e}")
            continue

    all_events.sort(key=lambda x: x["commence_time"])
    print(f"✅ Загружено {len(all_events)} событий")
    return all_events


async def get_live_scores():
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
            if data:
                for game in data:
                    if game.get("completed"):
                        score_info = {
                            "id": game["id"],
                            "completed": True,
                            "home_team": game.get("home_team"),
                            "away_team": game.get("away_team"),
                        }

                        scores = game.get("scores")
                        if scores and len(scores) == 2:
                            s0 = int(scores[0].get("score", 0))
                            s1 = int(scores[1].get("score", 0))
                            if s0 > s1:
                                score_info["result"] = "team_a" if scores[0]["name"] == game["home_team"] else "team_b"
                            elif s1 > s0:
                                score_info["result"] = "team_b" if scores[1]["name"] == game["away_team"] else "team_a"
                            else:
                                score_info["result"] = "draw"
                            score_info["score_text"] = f"{s0}:{s1}"

                        all_scores.append(score_info)

            await asyncio.sleep(1.5)

        except Exception as e:
            print(f"⚠️ Ошибка счёта {sport_key}: {e}")
            continue

    return all_scores


def parse_event(game, sport_key):
    try:
        odds_a = 0
        odds_draw = 0
        odds_b = 0
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
            if odds_a > 0:
                break

        if odds_a == 0 or odds_b == 0:
            return None

        category = "football"
        if "basketball" in sport_key:
            category = "basketball"
        elif "tennis" in sport_key:
            category = "tennis"
        elif "hockey" in sport_key or "ice" in sport_key:
            category = "hockey"
        elif "mma" in sport_key:
            category = "mma"

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
            "commence_time": game.get("commence_time", ""),
            "status": "upcoming",
        }

    except Exception as e:
        print(f"⚠️ Ошибка парсинга: {e}")
        return None
