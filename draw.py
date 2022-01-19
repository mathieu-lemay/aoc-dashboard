#! /usr/bin/env python
import json
import os
import random
from datetime import datetime
from time import sleep
from time import time as ts
from typing import List, Optional

import pytz
import requests
from pydantic import BaseModel, Field

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

        return entry[star_num]["get_star_ts"] < cutoff_time

    for d, v in entry["completion_day_level"].items():
        if _is_star_unlocked(v, 2):
            s = 2
        elif _is_star_unlocked(v, 1):
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


def _get_standings(year: int):
    fp = os.path.join(CACHE_FOLDER, f"{BOARD_ID}-{year}-raw.json")

    if _data_is_up_to_date(fp):
        with open(fp) as f:
            raw_standings = json.load(f)
    else:
        raw_standings = _download_data(year)
        with open(fp, "w") as f:
            json.dump(raw_standings, f)

    cutoff_time = (
        pytz.timezone("America/Montreal").localize(datetime(year + 1, 1, 1))
        if year >= 2021
        else None
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
                draw_entries=sum(stars),
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

    for i, m in enumerate(members):
        m.position = i + 1

    return members


def draw(coupons):
    sleep(1)
    print(".", end="", flush=True)
    sleep(1)
    print(".", end="", flush=True)
    sleep(1)
    random.shuffle(coupons)  # Probably not necessary but whatevs 🤷
    winner = random.choice(coupons)
    print(f" {winner}")

    return winner


standings = _get_standings(2021)

for s in standings:
    print(f"{s.position:-2d}. {s.name}: {s.draw_entries}")


coupons = []
exclusions = ["William Cantin"]
for s in standings[2:]:
    if s.name in exclusions:
        continue

    coupons += [s.name] * s.draw_entries

random.shuffle(coupons)

input("\nPress enter to draw the first winner")
winner = draw(coupons)

coupons = [c for c in coupons if c != winner]

input("\nPress enter to draw the second winner")
winner = draw(coupons)
coupons = [c for c in coupons if c != winner]

input("\nPress enter to draw the third winner")
winner = draw(coupons)
