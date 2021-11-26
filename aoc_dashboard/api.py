import logging
import os
from datetime import datetime
from time import time as ts
from typing import Dict, List

import requests
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


logger = logging.getLogger(__name__)

CURRENT_YEAR = datetime.now().year
BOARD_ID = 642101
SESSION_COOKIE = os.getenv("SESSION_COOKIE")
CACHE_FOLDER = os.getenv("CACHE_FOLDER", "./cache")


class MemberStanding(BaseModel):
    id_: int = Field(alias="id")
    name: str
    position: int
    stars: List[int]
    score: int
    gold_stars: int
    silver_stars: int
    draw_entries: int
    last_star_ts: int


class Standings(BaseModel):
    standings: Dict[str, MemberStanding]
    timestamp: datetime


def _download_data(year: int) -> dict:
    url = f"https://adventofcode.com/{year}/leaderboard/private/view/{BOARD_ID}.json"

    resp = requests.get(url, cookies={"session": SESSION_COOKIE})
    resp.raise_for_status()

    if resp.headers["Content-Type"] != "application/json":
        raise Exception("Unable to fetch standings from advent-of-code")

    return resp.json()


def _get_score_of_entry(stars: List[int]) -> int:
    score_map = {2: 3, 1: 1, 0: 0}
    return sum(score_map[i] for i in stars)


def _get_stars_of_entry(entry) -> List[int]:
    stars = []

    for v in entry["completion_day_level"].values():
        if "2" in v:
            stars.append(2)
        elif "1" in v:
            stars.append(1)
        else:
            stars.append(0)

    return stars


def _data_is_up_to_date(fp: str) -> bool:
    return os.path.exists(fp) and (ts() - os.path.getmtime(fp)) < 15 * 60


def _get_standings(year: int) -> Standings:
    fp = os.path.join(CACHE_FOLDER, f"{BOARD_ID}-{year}.json")

    if _data_is_up_to_date(fp):
        return Standings.parse_file(fp)

    logger.info("Refreshing file %s", os.path.basename(fp))
    raw_standings = _download_data(year)

    members = []

    for k, v in raw_standings["members"].items():
        stars = _get_stars_of_entry(v)
        members.append(
            MemberStanding(
                id=int(k),
                name=v["name"],
                position=0,
                stars=stars,
                gold_stars=sum(1 for s in stars if s == 2),
                silver_stars=sum(1 for s in stars if s > 0),
                score=_get_score_of_entry(stars),
                draw_entries=v["stars"],
                last_star_ts=v["last_star_ts"],
            )
        )

    members.sort(
        key=lambda m: (-m.draw_entries, -m.gold_stars, -m.silver_stars, m.last_star_ts)
    )

    last_score = (-1, -1)
    last_pos = 0
    for i, m in enumerate(members):
        s = (m.gold_stars, m.silver_stars)
        pos = last_pos if s == last_score else i + 1
        m.position = pos

        last_pos = pos
        last_score = s

    standings = Standings(
        standings={m.id_: m for m in members}, timestamp=datetime.utcnow()
    )

    with open(fp, "w") as f:
        f.write(standings.json(by_alias=True))

    return standings


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def exception_callback(_request: Request, exc: Exception):
    logger.exception(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(exc)}
    )


@app.get("/standings/{year:int}")
async def get_standings_for_year(year: int):
    standings = _get_standings(year)
    return standings


@app.get("/standings")
async def get_standings():
    return await get_standings_for_year(CURRENT_YEAR)


@app.get("/{year:int}")
async def render_standings_for_year(request: Request, year):
    standings = _get_standings(year)
    return templates.TemplateResponse(
        "standings.html", {"request": request, "year": year, "standings": standings}
    )


@app.get("/")
async def render_standings(request: Request):
    return await render_standings_for_year(request, CURRENT_YEAR)
