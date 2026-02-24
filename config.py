import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")

SERVER_HOST = "0.0.0.0"
SERVER_PORT = int(os.getenv("PORT", 8080))
START_BALANCE = 1000

SPORTS = [
    "soccer_epl",
    "soccer_spain_la_liga",
    "soccer_uefa_champs_league",
    "basketball_nba",
    "tennis_atp_french_open",
]

SPORT_NAMES = {
    "soccer_epl": "🏴 Премьер-Лига",
    "soccer_spain_la_liga": "🇪🇸 Ла Лига",
    "soccer_uefa_champs_league": "🏆 Лига Чемпионов",
    "basketball_nba": "🏀 NBA",
    "tennis_atp_french_open": "🎾 ATP",
}
