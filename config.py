import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")

SERVER_HOST = "0.0.0.0"
SERVER_PORT = int(os.getenv("PORT", 8080))
START_BALANCE = 1000

# Какие виды спорта загружать
SPORTS = [
    "soccer_epl",              # Английская Премьер-Лига
    "soccer_spain_la_liga",    # Ла Лига
    "soccer_germany_bundesliga",  # Бундеслига
    "soccer_italy_serie_a",    # Серия А
    "soccer_france_ligue_one", # Лига 1
    "soccer_uefa_champs_league",  # Лига Чемпионов
    "basketball_nba",          # NBA
    "tennis_atp_french_open",  # Теннис ATP
    "icehockey_nhl",           # NHL
    "mma_mixed_martial_arts",  # UFC
]

SPORT_NAMES = {
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Премьер-Лига",
    "soccer_spain_la_liga": "🇪🇸 Ла Лига",
    "soccer_germany_bundesliga": "🇩🇪 Бундеслига",
    "soccer_italy_serie_a": "🇮🇹 Серия А",
    "soccer_france_ligue_one": "🇫🇷 Лига 1",
    "soccer_uefa_champs_league": "🏆 Лига Чемпионов",
    "basketball_nba": "🏀 NBA",
    "tennis_atp_french_open": "🎾 ATP",
    "icehockey_nhl": "🏒 NHL",
    "mma_mixed_martial_arts": "🥊 UFC",
}
