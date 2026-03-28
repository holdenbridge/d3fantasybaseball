import logging
import threading
import time
import warnings
from pathlib import Path

import statsapi
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

warnings.filterwarnings("ignore")
log = logging.getLogger(__name__)

CACHE_TTL = 600  # 10 minutes
_cache: dict[str, tuple[float, object]] = {}
_cache_lock = threading.Lock()


def _get_cached(key: str):
    with _cache_lock:
        entry = _cache.get(key)
        if entry and (time.time() - entry[0]) < CACHE_TTL:
            return entry[1]
    return None


def _set_cached(key: str, value: object):
    with _cache_lock:
        _cache[key] = (time.time(), value)


app = FastAPI(title="D3 Baseball Fantasy")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def _prefetch_all():
    """Warm the cache in background threads so the first page load is fast."""
    for name, fn in [
        ("standings", _fetch_standings),
        ("hr_leaders", _fetch_hr_leaders),
        ("k_leaders", _fetch_k_leaders),
        ("war_rookies", _fetch_war_rookies),
    ]:
        try:
            _set_cached(name, fn())
            log.info("Pre-fetched %s", name)
        except Exception:
            log.exception("Pre-fetch failed for %s", name)


@app.on_event("startup")
def startup_prefetch():
    threading.Thread(target=_prefetch_all, daemon=True).start()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


def _fetch_standings():
    raw = statsapi.standings_data(leagueId="103,104", season=2026)
    teams = []
    for division in raw.values():
        for team in division["teams"]:
            teams.append(
                {
                    "name": team["name"],
                    "w": team["w"],
                    "l": team["l"],
                    "team_id": team["team_id"],
                    "division": division["div_name"],
                }
            )
    teams.sort(key=lambda t: t["w"], reverse=True)
    return teams


@app.get("/api/standings")
def standings():
    cached = _get_cached("standings")
    if cached is not None:
        return cached
    data = _fetch_standings()
    _set_cached("standings", data)
    return data


DRAFTED_BATTERS = {
    "Shohei Ohtani": 660271,
    "Aaron Judge": 592450,
    "Cal Raleigh": 663728,
    "Pete Alonso": 624413,
    "Juan Soto": 665742,
    "Nick Kurtz": 701762,
    "Kyle Schwarber": 656941,
    "Junior Caminero": 691406,
}


def _fetch_hr_leaders():
    raw = statsapi.league_leader_data("homeRuns", season=2026, limit=300)
    results = [
        {"rank": r[0], "name": r[1], "team": r[2], "hr": int(r[3])}
        for r in raw
    ]
    found_names = {r["name"] for r in results}
    for name, pid in DRAFTED_BATTERS.items():
        if name not in found_names:
            data = statsapi.get(
                "people",
                {
                    "personIds": pid,
                    "hydrate": "currentTeam,stats(group=[hitting],type=[season],season=2026)",
                },
            )
            people = data.get("people", [])
            if not people:
                continue
            person = people[0]
            team = person.get("currentTeam", {}).get("name", "")
            stats_list = person.get("stats", [])
            hr = 0
            if stats_list and stats_list[0].get("splits"):
                hr = stats_list[0]["splits"][0]["stat"].get("homeRuns", 0)
            results.append({"rank": "-", "name": name, "team": team, "hr": hr})
    return results


@app.get("/api/hr-leaders")
def hr_leaders():
    cached = _get_cached("hr_leaders")
    if cached is not None:
        return cached
    data = _fetch_hr_leaders()
    _set_cached("hr_leaders", data)
    return data


DRAFTED_PITCHERS = {
    "Cole Ragans": 666142,
    "Logan Webb": 657277,
    "Paul Skenes": 694973,
    "Bryan Woo": 693433,
    "Garrett Crochet": 676979,
    "Cristopher Sanchez": 650911,
    "Tarik Skubal": 669373,
    "Dylan Cease": 656302,
}


def _fetch_k_leaders():
    raw = statsapi.league_leader_data(
        "strikeouts", season=2026, limit=300, statGroup="pitching"
    )
    results = [
        {"rank": r[0], "name": r[1], "team": r[2], "k": int(r[3])}
        for r in raw
    ]
    found_names = {r["name"] for r in results}
    for name, pid in DRAFTED_PITCHERS.items():
        if name not in found_names:
            data = statsapi.get(
                "people",
                {
                    "personIds": pid,
                    "hydrate": "currentTeam,stats(group=[pitching],type=[season],season=2026)",
                },
            )
            people = data.get("people", [])
            if not people:
                continue
            person = people[0]
            team = person.get("currentTeam", {}).get("name", "")
            stats_list = person.get("stats", [])
            k = 0
            if stats_list and stats_list[0].get("splits"):
                k = stats_list[0]["splits"][0]["stat"].get("strikeOuts", 0)
            results.append({"rank": "-", "name": name, "team": team, "k": k})
    return results


@app.get("/api/k-leaders")
def k_leaders():
    cached = _get_cached("k_leaders")
    if cached is not None:
        return cached
    data = _fetch_k_leaders()
    _set_cached("k_leaders", data)
    return data


ROOKIES_2026 = [
    "Kevin McGonigle",
    "Kazuma Okamoto",
    "Munetaka Murakami",
    "JJ Wetherholt",
    "Carter Jensen",
    "Samuel Basallo",
    "Konnor Griffin",
    "Sal Stewart",
    "Chase DeLauter",
]


def _fetch_war_rookies():
    try:
        from pybaseball import batting_stats

        bat = batting_stats(2026, qual=0, stat_columns= ["WAR", "OPS"])
    except Exception:
        log.exception("pybaseball fetch failed")
        return []

    rookie_set = set(ROOKIES_2026)
    results = {}

    for _, row in bat.iterrows():
        name = row.get("Name", "")
        if name in rookie_set:
            results[name] = {
                "name": name,
                "team": row.get("Team", ""),
                "war": round(float(row.get("WAR", 0)), 1),
            }

    return sorted(results.values(), key=lambda r: r["war"], reverse=True)


@app.get("/api/war-rookies")
def war_rookies():
    cached = _get_cached("war_rookies")
    if cached is not None:
        return cached
    data = _fetch_war_rookies()
    _set_cached("war_rookies", data)
    return data
