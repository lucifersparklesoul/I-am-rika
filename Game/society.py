"""
Society Builder — a small idle/incremental city-building game playable
entirely through bot commands.

Mechanics:
- Each Telegram user has their own society: gold, food, population, and
  buildings (house / farm / market).
- Resources accrue passively over real time. Calling collect() applies
  whatever has accumulated since the last check.
- Population grows when there's a food surplus and shrinks (starves) if
  food runs out, so players need to balance farms against population.

State is kept in memory and resets if the bot restarts — swap `_societies`
for a real database (SQLite, Redis, etc.) if you want it to persist.
"""

import math
import time

BUILDINGS = {
    "house": {
        "cost_gold": 50,
        "cost_food": 20,
        "desc": "+10 max population",
    },
    "farm": {
        "cost_gold": 80,
        "cost_food": 0,
        "desc": "+10 food/hour",
    },
    "market": {
        "cost_gold": 0,
        "cost_food": 60,
        "desc": "+8 gold/hour",
    },
}

BASE_FOOD_PER_HOUR = 5
BASE_GOLD_PER_HOUR = 2
BASE_MAX_POPULATION = 10
POP_GROWTH_RATE = 0.1  # fraction of the population gap that grows per hour when fed
COST_SCALING = 1.15  # each additional building of a type costs 15% more
MAX_OFFLINE_HOURS = 48  # cap idle production so long absences don't break the economy

_societies: dict[int, dict] = {}


def _new_society(name: str) -> dict:
    return {
        "name": name,
        "gold": 100.0,
        "food": 50.0,
        "population": 5,
        "buildings": {"house": 0, "farm": 0, "market": 0},
        "last_collect": time.time(),
    }


def get_society(user_id: int, default_name: str) -> dict:
    if user_id not in _societies:
        _societies[user_id] = _new_society(default_name)
    return _societies[user_id]


def rename_society(user_id: int, name: str) -> None:
    if user_id in _societies:
        _societies[user_id]["name"] = name


def max_population(soc: dict) -> int:
    return BASE_MAX_POPULATION + soc["buildings"]["house"] * 10


def food_rate(soc: dict) -> float:
    return BASE_FOOD_PER_HOUR + soc["buildings"]["farm"] * 10


def gold_rate(soc: dict) -> float:
    return BASE_GOLD_PER_HOUR + soc["buildings"]["market"] * 8


def collect(user_id: int, default_name: str) -> dict:
    """Applies idle production since the last collect and returns a delta summary."""
    soc = get_society(user_id, default_name)
    now = time.time()
    hours = (now - soc["last_collect"]) / 3600
    hours = max(0.0, min(hours, MAX_OFFLINE_HOURS))
    soc["last_collect"] = now

    result = {"hours": hours, "food_delta": 0.0, "gold_delta": 0.0, "pop_delta": 0, "starved": False}
    if hours <= 0:
        return result

    food_produced = food_rate(soc) * hours
    gold_produced = gold_rate(soc) * hours
    upkeep = soc["population"] * hours
    net_food = food_produced - upkeep

    if soc["food"] + net_food < 0:
        deficit = abs(soc["food"] + net_food)
        result["starved"] = True
        lost = min(soc["population"], max(1, math.ceil(deficit / 10)))
        soc["population"] = max(0, soc["population"] - lost)
        soc["food"] = 0.0
        result["pop_delta"] = -lost
    else:
        soc["food"] += net_food
        cap = max_population(soc)
        if soc["population"] < cap and soc["food"] > 0:
            growth = (cap - soc["population"]) * POP_GROWTH_RATE * hours
            grown = math.floor(min(growth, cap - soc["population"]))
            if grown > 0:
                soc["population"] += grown
                result["pop_delta"] = grown

    soc["gold"] += gold_produced
    result["food_delta"] = net_food
    result["gold_delta"] = gold_produced
    return result


def build_cost(soc: dict, building: str) -> tuple[int, int]:
    count = soc["buildings"][building]
    base = BUILDINGS[building]
    gold = round(base["cost_gold"] * (COST_SCALING**count))
    food = round(base["cost_food"] * (COST_SCALING**count))
    return gold, food


def build(user_id: int, default_name: str, building: str) -> dict:
    building = building.lower()
    if building not in BUILDINGS:
        return {"ok": False, "reason": "unknown"}

    soc = get_society(user_id, default_name)
    gold_cost, food_cost = build_cost(soc, building)

    if soc["gold"] < gold_cost or soc["food"] < food_cost:
        return {"ok": False, "reason": "resources", "gold_cost": gold_cost, "food_cost": food_cost}

    soc["gold"] -= gold_cost
    soc["food"] -= food_cost
    soc["buildings"][building] += 1

    return {
        "ok": True,
        "gold_cost": gold_cost,
        "food_cost": food_cost,
        "count": soc["buildings"][building],
    }


def leaderboard(limit: int = 5) -> list[tuple[int, dict]]:
    ranked = sorted(_societies.items(), key=lambda kv: kv[1]["population"], reverse=True)
    return ranked[:limit]
