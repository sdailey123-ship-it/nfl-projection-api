from fastapi import FastAPI
from pydantic import BaseModel
import math
import requests
import os

STATS_SEASON = 2025
TEAM_SEASON = 2024

app = FastAPI()

class PlayerInput(BaseModel):
    routes_l3: float
    routes_season: float
    tprr_l4: float
    tprr_season: float
    catch_rate_season: float
    catch_rate_l4: float
    matchup_factor: float
    line: float

@app.post("/project/receptions")
def project_receptions(p: PlayerInput):

    routes_proj = (0.6 * p.routes_l3) + (0.4 * p.routes_season)
    tprr_proj = (0.6 * p.tprr_l4) + (0.4 * p.tprr_season)
    targets_proj = routes_proj * tprr_proj

    catch_rate_proj = (0.7 * p.catch_rate_season) + (0.3 * p.catch_rate_l4)

    rec_proj = targets_proj * catch_rate_proj * p.matchup_factor

    L = math.floor(p.line)
    lam = rec_proj

    poisson_cdf = sum(
        math.exp(-lam) * lam**k / math.factorial(k)
        for k in range(L + 1)
    )
    prob_over = 1 - poisson_cdf

    return {
        "projection": round(rec_proj, 2),
        "over_probability": round(prob_over, 3)
    }

@app.get("/player/{player_id}/recent-games")
def get_player_recent_games(
    player_id: int,
    games: int = 5,
    season: int = 2024
):
    api_key = os.getenv("API_SPORTS_KEY")

    if not api_key:
        return {"error": "API key not found"}

    url = "https://v1.american-football.api-sports.io/players/statistics"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "v1.american-football.api-sports.io"
    }

    params = {
        "player": player_id,
        "season": season,
        "league": 1
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        return {
            "error": "API request failed",
            "status": response.status_code,
            "details": response.text
        }

    data = response.json()
    games_data = data.get("response", [])[:games]

    return {
        "player_id": player_id,
        "games_returned": len(games_data),
        "games": games_data
    }

@app.get("/ping")
def ping():
    return {"status": "ok"}
@app.get("/search/player")
def search_player(name: str, season: int = 2024):
    api_key = os.getenv("API_SPORTS_KEY")

    if not api_key:
        return {"error": "API key not found"}

    url = "https://v1.american-football.api-sports.io/players"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "v1.american-football.api-sports.io"
    }

    params = {
        "search": name,
        "season": season,
        "league": 1
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        return {
            "error": "API request failed",
            "status": response.status_code,
            "details": response.text
        }

    data = response.json()
    return data
@app.get("/teams")
def get_teams(season: int = 2024):
    api_key = os.getenv("API_SPORTS_KEY")

    if not api_key:
        return {"error": "API key not found"}

    url = "https://v1.american-football.api-sports.io/teams"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "v1.american-football.api-sports.io"
    }

    params = {
        "league": 1,   # NFL
        "season": season
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        return {
            "error": "API request failed",
            "status": response.status_code,
            "details": response.text
        }

    return response.json()
@app.get("/player/{player_id}/rolling-stats")
def get_player_rolling_stats(
    player_id: int,
    season: int = STATS_SEASON
):
    api_key = os.getenv("API_SPORTS_KEY")

    if not api_key:
        return {"error": "API key not found"}

    url = "https://v1.american-football.api-sports.io/players/statistics"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "v1.american-football.api-sports.io"
    }

    params = {
        "player": player_id,
        "season": season
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        return {
            "error": "API request failed",
            "status": response.status_code,
            "details": response.text
        }

    data = response.json()
    games = data.get("response", [])

    if not games:
        return {
            "player_id": player_id,
            "season": season,
            "note": "No stats available"
        }

    def avg(values):
        return round(sum(values) / len(values), 2) if values else 0

    # Extract stats per game
    recs = []
    targets = []
    rec_yards = []
    pass_yards = []
    pass_attempts = []

    for g in games:
        stats = g.get("statistics", {})

        receiving = stats.get("receiving", {})
        passing = stats.get("passing", {})

        recs.append(receiving.get("receptions", 0))
        targets.append(receiving.get("targets", 0))
        rec_yards.append(receiving.get("yards", 0))

        pass_yards.append(passing.get("yards", 0))
        pass_attempts.append(passing.get("attempts", 0))

    return {
        "player_id": player_id,
        "season": season,
        "games_played": len(games),

        "last_3": {
            "receptions": avg(recs[:3]),
            "targets": avg(targets[:3]),
            "receiving_yards": avg(rec_yards[:3]),
            "passing_yards": avg(pass_yards[:3]),
            "passing_attempts": avg(pass_attempts[:3])
        },

        "last_5": {
            "receptions": avg(recs[:5]),
            "targets": avg(targets[:5]),
            "receiving_yards": avg(rec_yards[:5]),
            "passing_yards": avg(pass_yards[:5]),
            "passing_attempts": avg(pass_attempts[:5])
        },

        "season_avg": {
            "receptions": avg(recs),
            "targets": avg(targets),
            "receiving_yards": avg(rec_yards),
            "passing_yards": avg(pass_yards),
            "passing_attempts": avg(pass_attempts)
        }
    }
    @app.get("/project/player/{player_id}")
def project_player_props(
    player_id: int,
    season: int = STATS_SEASON
):
    api_key = os.getenv("API_SPORTS_KEY")

    url = "https://v1.american-football.api-sports.io/players/statistics"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "v1.american-football.api-sports.io"
    }

    params = {
        "player": player_id,
        "season": season
    }

    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    games = data.get("response", [])

    if not games:
        return {"error": "No stats available"}

    def avg(values):
        return sum(values) / len(values) if values else 0

    # Extract per-game stats
    recs, yards, pass_yards = [], [], []

    for g in games:
        stats = g.get("statistics", {})
        receiving = stats.get("receiving", {})
        passing = stats.get("passing", {})

        recs.append(receiving.get("receptions", 0))
        yards.append(receiving.get("yards", 0))
        pass_yards.append(passing.get("yards", 0))

    last3 = slice(0, 3)
    last5 = slice(0, 5)

    # Receptions projection
    rec_proj = (
        avg(recs[last3]) * 0.45 +
        avg(recs[last5]) * 0.25 +
        avg(recs) * 0.30
    )

    # Receiving yards projection
    rec_yards_proj = (
        avg(yards[last3]) * 0.40 +
        avg(yards[last5]) * 0.30 +
        avg(yards) * 0.30
    )

    # Passing yards projection
    pass_yards_proj = (
        avg(pass_yards[last3]) * 0.35 +
        avg(pass_yards[last5]) * 0.35 +
        avg(pass_yards) * 0.30
    )

    return {
        "player_id": player_id,
        "season": season,
        "projections": {
            "receptions": round(rec_proj, 2),
            "receiving_yards": round(rec_yards_proj, 1),
            "passing_yards": round(pass_yards_proj, 1)
        }
    }


