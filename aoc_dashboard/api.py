import logging
import os
from datetime import datetime
from time import time as ts
from typing import List, Optional

import pytz
import requests
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


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
    part_2_average_time: float


class Standings(BaseModel):
    standings: List[MemberStanding]
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


def _get_stars_of_entry(entry, cutoff_time: Optional[datetime]) -> List[int]:
    stars = [0] * 25
    if cutoff_time:
        cutoff_time = cutoff_time.timestamp()

    def _is_star_unlocked(entry, star_num):
        star_num = str(star_num)

        if star_num not in entry:
            return False

        if cutoff_time is None:
            return True

        return cutoff_time >= entry[star_num]["get_star_ts"]

    for d, v in entry["completion_day_level"].items():
        if _is_star_unlocked(v, 2):
            s = 2
        elif _is_star_unlocked(v, 2):
            s = 1
        else:
            s = 0

        stars[int(d) - 1] = s

    return stars


def _get_part_2_average_time(completion_day_level) -> float:
    completed_days = [d for d in completion_day_level.values() if "2" in d]
    if not completed_days:
        return 0

    return sum(
        d["2"]["get_star_ts"] - d["1"]["get_star_ts"] for d in completed_days
    ) / len(completed_days)


def _data_is_up_to_date(fp: str) -> bool:
    return os.path.exists(fp) and (ts() - os.path.getmtime(fp)) < 15 * 60


def _get_standings(year: int) -> Standings:
    fp = os.path.join(CACHE_FOLDER, f"{BOARD_ID}-{year}.json")

    if _data_is_up_to_date(fp):
        return Standings.parse_file(fp)

    logger.info("Refreshing file %s", os.path.basename(fp))
    raw_standings = _download_data(year)

    cutoff_time = (
        datetime(year, 12, 31, 23, 59, 59, 999999, pytz.UTC) if year >= 2021 else None
    )

    members = []

    for k, v in raw_standings["members"].items():
        stars = _get_stars_of_entry(v, cutoff_time)
        members.append(
            MemberStanding(
                id=int(k),
                name=v["name"] or f"anonymous user #{v['id']}",
                position=0,
                stars=stars,
                gold_stars=sum(1 for s in stars if s == 2),
                silver_stars=sum(1 for s in stars if s > 0),
                score=_get_score_of_entry(stars),
                draw_entries=v["stars"],
                last_star_ts=v["last_star_ts"],
                part_2_average_time=_get_part_2_average_time(v["completion_day_level"]),
            )
        )

    members.sort(
        key=lambda m: (
            m.draw_entries,
            m.gold_stars,
            m.silver_stars,
            list(reversed(m.stars)),
            -m.part_2_average_time,
        ),
        reverse=True,
    )

    last_score = (-1, -1)
    last_pos = 0
    for i, m in enumerate(members):
        s = (m.gold_stars, m.silver_stars)
        pos = last_pos if s == last_score else i + 1
        m.position = pos

        last_pos = pos
        last_score = s

    standings = Standings(standings=members, timestamp=datetime.utcnow())

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
async def exception_callback(_: Request, exc: Exception):
    logger.exception(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(exc)}
    )


@app.get("/standings/{year:int}")
async def get_standings_for_year(year: int):
    return _get_standings(year)


@app.get("/standings")
async def get_standings():
    return await get_standings_for_year(CURRENT_YEAR)


@app.get("/")
async def render_standings():
    with open("templates/index.html") as f:
        return HTMLResponse(f.read())
