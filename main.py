from fastapi import FastAPI
from pydantic import BaseModel
import math
import requests
import os

# =========================
# GLOBAL CONSTANTS
# =========================

LEAGUE_ID = 1          # NFL
TEAM_SEASON = 2024    # Stable roster/team data
STATS_SEASON = 2025   # Current stats season

# =========================
# APP INIT
# =========================

app = FastAPI(title="NFL Player Projection API")

# =========================
# MODELS
# =========================

class PlayerInput(BaseModel):
    routes_l3: float
    routes_season: float
    tprr_l4: float
    tprr_season: float
    catch_rate_season: float
    catch_rate_l4: float
    matchup_factor: float
    line: float

# =========================
# HEALTH CHECK
# =========================

@app.get("/ping")
def ping():
    return {"status": "ok"}

# =========================
# BASIC RECEPTION MODEL
# =========================

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

# =========================
# API-SPORTS HELPERS
# =========================

def api_headers():
    api_key = os.getenv("API_SPORTS_KEY")
    if not api_key:
        raise ValueError("API_SPORTS_KEY not found")
    return {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "v1.american-football.api-sports.io"
    }

# =========================
# TEAMS (STABLE DATA)
# =========================

@app.get("/teams")
def get_teams(season: int = TEAM_SEASON):

    url = "https://v1.american-football.api-sports.io/teams"
    params = {
        "league": LEAGUE_ID,
        "season": season
    }

    response = requests.get(url, headers=api_headers(), params=params)

    if response.status_code != 200:
        return {"error": response.text}

    return response.json()

# =========================
# PLAYER SEARCH (ROSTERS)
# =========================

@app.get("/search/player")
def search_player(
    name: str,
    team: int,
    season: int = TEAM_SEASON
):
    url = "https://v1.american-football.api-sports.io/players"
    params = {
        "search": name,
        "team": team,
        "season": season
    }

    response = requests.get(url, headers=api_headers(), params=params)

    if response.status_code != 200:
        return {"error": response.text}

    return response.json()

# =========================
# RECENT GAMES
# =========================

@app.get("/player/{player_id}/recent-games")
def get_player_recent_games(
    player_id: int,
    games: int = 5,
    season: int = STATS_SEASON
):
    url = "https://v1.american-football.api-sports.io/players/statistics"
    params = {
        "player": player_id,
        "season": season
    }

    response = requests.get(url, headers=api_headers(), params=params)

    if response.status_code != 200:
        return {"error": response.text}

    data = response.json()
    games_data = data.get("response", [])[:games]

    return {
        "player_id": player_id,
        "games_returned": len(games_data),
        "games": games_data
    }

# =========================
# ROLLING STATS
# =========================

@app.get("/player/{player_id}/rolling-stats")
def get_player_rolling_stats(
    player_id: int,
    season: int = STATS_SEASON
):
    url = "https://v1.american-football.api-sports.io/players/statistics"
    params = {
        "player": player_id,
        "season": season
    }

    response = requests.get(url, headers=api_headers(), params=params)

    if response.status_code != 200:
        return {"error": response.text}

    games = response.json().get("response", [])

    if not games:
        return {"note": "No stats available"}

    def avg(v):
        return round(sum(v) / len(v), 2) if v else 0

    recs, yards, pass_yards, targets, attempts = [], [], [], [], []

    for g in games:
        s = g.get("statistics", {})
        r = s.get("receiving", {})
        p = s.get("passing", {})

        recs.append(r.get("receptions", 0))
        yards.append(r.get("yards", 0))
        targets.append(r.get("targets", 0))

        pass_yards.append(p.get("yards", 0))
        attempts.append(p.get("attempts", 0))

    return {
        "player_id": player_id,
        "season": season,
        "games_played": len(games),

        "last_3": {
            "receptions": avg(recs[:3]),
            "targets": avg(targets[:3]),
            "receiving_yards": avg(yards[:3]),
            "passing_yards": avg(pass_yards[:3]),
            "passing_attempts": avg(attempts[:3])
        },

        "last_5": {
            "receptions": avg(recs[:5]),
            "targets": avg(targets[:5]),
            "receiving_yards": avg(yards[:5]),
            "passing_yards": avg(pass_yards[:5]),
            "passing_attempts": avg(attempts[:5])
        },

        "season_avg": {
            "receptions": avg(recs),
            "targets": avg(targets),
            "receiving_yards": avg(yards),
            "passing_yards": avg(pass_yards),
            "passing_attempts": avg(attempts)
        }
    }

# =========================
# FINAL PLAYER PROJECTIONS
# =========================

@app.get("/project/player/{player_id}")
def project_player_props(
    player_id: int,
    season: int = STATS_SEASON
):
    url = "https://v1.american-football.api-sports.io/players/statistics"
    params = {
        "player": player_id,
        "season": season
    }

    response = requests.get(url, headers=api_headers(), params=params)
    games = response.json().get("response", [])

    if not games:
        return {"error": "No stats available"}

    def avg(v):
        return sum(v) / len(v) if v else 0

    recs, yards, pass_yards = [], [], []

    for g in games:
        s = g.get("statistics", {})
        r = s.get("receiving", {})
        p = s.get("passing", {})

        recs.append(r.get("receptions", 0))
        yards.append(r.get("yards", 0))
        pass_yards.append(p.get("yards", 0))

    rec_proj = (
        avg(recs[:3]) * 0.45 +
        avg(recs[:5]) * 0.25 +
        avg(recs) * 0.30
    )

    rec_yards_proj = (
        avg(yards[:3]) * 0.40 +
        avg(yards[:5]) * 0.30 +
        avg(yards) * 0.30
    )

    pass_yards_proj = (
        avg(pass_yards[:3]) * 0.35 +
        avg(pass_yards[:5]) * 0.35 +
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
