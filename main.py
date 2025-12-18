from fastapi import FastAPI
from pydantic import BaseModel
import math
import requests
import os

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

