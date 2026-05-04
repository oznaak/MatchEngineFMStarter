from __future__ import annotations

import sqlite3
from typing import Dict, List

# (auto_relegated, playoff_relegated, auto_promoted, playoff_promoted)
RELEGATION_RULES: Dict[str, tuple] = {
    "ENG1": (3, 0, 0, 0),
    "ENG2": (0, 0, 2, 4),
    "ESP1": (3, 0, 0, 0),
    "ESP2": (0, 0, 2, 4),
    "FRA1": (1, 2, 0, 0),
    "FRA2": (0, 0, 2, 0),
    "GER1": (2, 1, 0, 0),
    "GER2": (0, 0, 2, 0),
    "PRT1": (2, 2, 0, 0),
    "PRT2": (0, 0, 2, 0),
}

TIER_PAIRS = [
    ("ENG1", "ENG2"),
    ("ESP1", "ESP2"),
    ("FRA1", "FRA2"),
    ("GER1", "GER2"),
    ("PRT1", "PRT2"),
]


def get_promotion_relegation_plan(
    top_league_id: str,
    bottom_league_id: str,
    top_standings: List[Dict],
    bottom_standings: List[Dict],
) -> List[Dict]:
    plan: List[Dict] = []
    top_sorted = sorted(top_standings, key=lambda r: int(r.get("position", 99)))
    bot_sorted = sorted(bottom_standings, key=lambda r: int(r.get("position", 99)))
    top_rules = RELEGATION_RULES.get(top_league_id, (3, 0, 0, 0))
    bot_rules = RELEGATION_RULES.get(bottom_league_id, (0, 0, 2, 0))
    auto_rel = top_rules[0]
    playoff_rel = top_rules[1]
    auto_prom = bot_rules[2]
    playoff_prom = bot_rules[3]

    for club in top_sorted[-auto_rel:] if auto_rel else []:
        plan.append({"club_id": club["club_id"], "action": "relegate",
                     "from_league": top_league_id, "to_league": bottom_league_id})

    if playoff_rel > 0:
        start = -(auto_rel + playoff_rel) if auto_rel else -playoff_rel
        end = -auto_rel if auto_rel else None
        for club in top_sorted[start:end]:
            plan.append({"club_id": club["club_id"], "action": "relegate_playoff",
                         "from_league": top_league_id, "to_league": bottom_league_id})

    for club in bot_sorted[:auto_prom]:
        plan.append({"club_id": club["club_id"], "action": "promote_auto",
                     "from_league": bottom_league_id, "to_league": top_league_id})

    if playoff_prom > 0:
        for club in bot_sorted[auto_prom:auto_prom + playoff_prom]:
            plan.append({"club_id": club["club_id"], "action": "promote_playoff",
                         "from_league": bottom_league_id, "to_league": top_league_id})

    return plan


def apply_promotion_relegation(conn: sqlite3.Connection, save_id: int, season_year: int) -> None:
    from .db import load_save_standings

    next_season = season_year + 1

    # First seed next season's save_league_clubs as a copy of current season
    existing = conn.execute(
        "SELECT league_id, club_id FROM save_league_clubs WHERE save_id=? AND season=?",
        (save_id, season_year),
    ).fetchall()
    conn.executemany(
        "INSERT OR IGNORE INTO save_league_clubs (save_id, league_id, club_id, season) VALUES (?, ?, ?, ?)",
        [(save_id, str(r["league_id"]), str(r["club_id"]), next_season) for r in existing],
    )

    for top_id, bot_id in TIER_PAIRS:
        top_comp = f"{top_id}_{season_year}"
        bot_comp = f"{bot_id}_{season_year}"
        top_standings = load_save_standings(conn, save_id, competition_id=top_comp)
        bot_standings = load_save_standings(conn, save_id, competition_id=bot_comp)
        if not top_standings or not bot_standings:
            continue
        plan = get_promotion_relegation_plan(top_id, bot_id, top_standings, bot_standings)
        for move in plan:
            club_id = move["club_id"]
            action = move["action"]
            from_league = move["from_league"]
            to_league = move["to_league"]
            if action in ("relegate", "promote_auto"):
                conn.execute(
                    "DELETE FROM save_league_clubs WHERE save_id=? AND league_id=? AND club_id=? AND season=?",
                    (save_id, from_league, club_id, next_season),
                )
                conn.execute(
                    "INSERT OR IGNORE INTO save_league_clubs (save_id, league_id, club_id, season) VALUES (?, ?, ?, ?)",
                    (save_id, to_league, club_id, next_season),
                )
