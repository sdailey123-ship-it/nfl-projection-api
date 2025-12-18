from fastapi import FastAPI
from pydantic import BaseModel
import math

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

    poisson_cdf = sum(math.exp(-lam) * lam**k / math.factorial(k) for k in range(L+1))
    prob_over = 1 - poisson_cdf

    return {
        "projection": round(rec_proj, 2),
        "over_probability": round(prob_over, 3)
    }
