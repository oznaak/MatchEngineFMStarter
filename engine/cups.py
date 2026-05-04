from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta
from typing import Dict, List

CUP_CONFIGS: Dict[str, Dict] = {
    "FA_CUP": {
        "name": "FA Cup",
        "country": "ENG",
        "leagues": ["ENG1", "ENG2"],
        "rounds": [
            {"name": "R3",  "month": 1,  "day": 8,  "legs": 1},
            {"name": "R4",  "month": 1,  "day": 29, "legs": 1},
            {"name": "R5",  "month": 2,  "day": 19, "legs": 1},
            {"name": "QF",  "month": 3,  "day": 18, "legs": 1},
            {"name": "SF",  "month": 4,  "day": 12, "legs": 1, "neutral": True},
            {"name": "F",   "month": 5,  "day": 17, "legs": 1, "neutral": True},
        ],
    },
    "TACA_PT": {
        "name": "Taca de Portugal",
        "country": "PRT",
        "leagues": ["PRT1", "PRT2"],
        "rounds": [
            {"name": "R32", "month": 9,  "day": 20, "legs": 1},
            {"name": "R16", "month": 11, "day": 8,  "legs": 1},
            {"name": "QF",  "month": 1,  "day": 15, "legs": 1},
            {"name": "SF",  "month": 3,  "day": 12, "legs": 1},
            {"name": "F",   "month": 5,  "day": 25, "legs": 1, "neutral": True},
        ],
    },
    "COPA_REY": {
        "name": "Copa del Rey",
        "country": "ESP",
        "leagues": ["ESP1", "ESP2"],
        "rounds": [
            {"name": "R32", "month": 11, "day": 6,  "legs": 1},
            {"name": "R16", "month": 12, "day": 11, "legs": 1},
            {"name": "QF",  "month": 1,  "day": 22, "legs": 2},
            {"name": "SF",  "month": 2,  "day": 19, "legs": 2},
            {"name": "F",   "month": 4,  "day": 26, "legs": 1, "neutral": True},
        ],
    },
    "COUPE_FR": {
        "name": "Coupe de France",
        "country": "FRA",
        "leagues": ["FRA1", "FRA2"],
        "rounds": [
            {"name": "R64", "month": 12, "day": 7,  "legs": 1},
            {"name": "R32", "month": 1,  "day": 11, "legs": 1},
            {"name": "R16", "month": 2,  "day": 8,  "legs": 1},
            {"name": "QF",  "month": 3,  "day": 8,  "legs": 1},
            {"name": "SF",  "month": 4,  "day": 5,  "legs": 1},
            {"name": "F",   "month": 5,  "day": 24, "legs": 1, "neutral": True},
        ],
    },
    "DFB_POKAL": {
        "name": "DFB-Pokal",
        "country": "GER",
        "leagues": ["GER1", "GER2"],
        "rounds": [
            {"name": "R1",  "month": 8,  "day": 16, "legs": 1},
            {"name": "R2",  "month": 10, "day": 29, "legs": 1},
            {"name": "R16", "month": 1,  "day": 21, "legs": 1},
            {"name": "QF",  "month": 2,  "day": 25, "legs": 1},
            {"name": "SF",  "month": 4,  "day": 22, "legs": 1},
            {"name": "F",   "month": 5,  "day": 24, "legs": 1, "neutral": True},
        ],
    },
}


def _round_date(season_year: int, month: int, day: int) -> date:
    year = season_year if month >= 7 else season_year + 1
    return date(year, month, day)


def seed_cup_for_save(conn: sqlite3.Connection, save_id: int, cup_key: str, season_year: int) -> None:
    cfg = CUP_CONFIGS[cup_key]
    comp_id = f"{cup_key}_{season_year}"
    conn.execute(
        "INSERT OR IGNORE INTO competitions (id, name, country, type, season, save_id) VALUES (?, ?, ?, 'cup', ?, ?)",
        (comp_id, cfg["name"], cfg["country"], season_year, save_id),
    )
    all_clubs: List[str] = []
    for league_id in cfg["leagues"]:
        rows = conn.execute(
            "SELECT club_id FROM save_league_clubs WHERE save_id=? AND league_id=? AND season=? ORDER BY club_id",
            (save_id, league_id, season_year),
        ).fetchall()
        if not rows:
            rows = conn.execute(
                "SELECT club_id FROM league_clubs WHERE league_id=? ORDER BY display_order, club_id",
                (league_id,),
            ).fetchall()
        all_clubs.extend(str(r["club_id"]) for r in rows)

    if len(all_clubs) < 2:
        return

    random.shuffle(all_clubs)
    first_round = cfg["rounds"][0]
    round_name = first_round["name"]
    round_date = _round_date(season_year, first_round["month"], first_round["day"])
    is_neutral = int(first_round.get("neutral", False))
    legs = int(first_round.get("legs", 1))

    pairs = [(all_clubs[i], all_clubs[i + 1]) for i in range(0, len(all_clubs) - 1, 2)]
    for slot, (club_a, club_b) in enumerate(pairs):
        conn.execute(
            "INSERT INTO cup_brackets (save_id, competition_id, round, slot, club_a, club_b) VALUES (?, ?, ?, ?, ?, ?)",
            (save_id, comp_id, round_name, slot, club_a, club_b),
        )
        conn.execute(
            "INSERT INTO fixtures (save_id, match_day, fixture_date, home_club_id, away_club_id, competition_id, leg, is_neutral) VALUES (?, 0, ?, ?, ?, ?, 1, ?)",
            (save_id, round_date.isoformat(), club_a, club_b, comp_id, is_neutral),
        )
        if legs == 2:
            leg2_date = round_date + timedelta(days=14)
            conn.execute(
                "INSERT INTO fixtures (save_id, match_day, fixture_date, home_club_id, away_club_id, competition_id, leg, is_neutral) VALUES (?, 0, ?, ?, ?, ?, 2, 0)",
                (save_id, leg2_date.isoformat(), club_b, club_a, comp_id),
            )


def advance_cup_rounds(conn: sqlite3.Connection, save_id: int, current_date_str: str) -> None:
    season_row = conn.execute("SELECT season_year FROM saves WHERE id=?", (save_id,)).fetchone()
    if season_row is None:
        return
    season_year = int(season_row["season_year"])

    for cup_key, cfg in CUP_CONFIGS.items():
        comp_id = f"{cup_key}_{season_year}"
        rounds = cfg["rounds"]
        for r_idx in range(len(rounds) - 1):
            round_name = rounds[r_idx]["name"]
            next_round_cfg = rounds[r_idx + 1]
            next_round_name = next_round_cfg["name"]

            bracket_count = conn.execute(
                "SELECT COUNT(*) AS c FROM cup_brackets WHERE save_id=? AND competition_id=? AND round=?",
                (save_id, comp_id, round_name),
            ).fetchone()
            if not bracket_count or int(bracket_count["c"]) == 0:
                continue

            next_exists = conn.execute(
                "SELECT COUNT(*) AS c FROM cup_brackets WHERE save_id=? AND competition_id=? AND round=?",
                (save_id, comp_id, next_round_name),
            ).fetchone()
            if int(next_exists["c"]) > 0:
                continue

            unplayed = conn.execute(
                """
                SELECT COUNT(*) AS c FROM fixtures f
                WHERE f.save_id=? AND f.competition_id=? AND f.played=0
                  AND (f.home_club_id IN (
                        SELECT club_a FROM cup_brackets WHERE save_id=? AND competition_id=? AND round=?
                        UNION SELECT club_b FROM cup_brackets WHERE save_id=? AND competition_id=? AND round=?
                      ))
                """,
                (save_id, comp_id, save_id, comp_id, round_name, save_id, comp_id, round_name),
            ).fetchone()
            if int(unplayed["c"]) > 0:
                continue

            _seed_next_cup_round(conn, save_id, comp_id, round_name, next_round_cfg, season_year)


def _seed_next_cup_round(
    conn: sqlite3.Connection,
    save_id: int,
    comp_id: str,
    completed_round: str,
    next_round_cfg: Dict,
    season_year: int,
) -> None:
    brackets = conn.execute(
        "SELECT slot, club_a, club_b, winner FROM cup_brackets WHERE save_id=? AND competition_id=? AND round=? ORDER BY slot",
        (save_id, comp_id, completed_round),
    ).fetchall()
    winners: List[str] = []
    for b in brackets:
        winner = str(b["winner"] or "")
        if not winner:
            fx = conn.execute(
                """
                SELECT home_club_id, away_club_id, home_goals, away_goals FROM fixtures
                WHERE save_id=? AND competition_id=? AND played=1
                  AND (home_club_id=? OR away_club_id=?)
                ORDER BY leg DESC, id DESC LIMIT 1
                """,
                (save_id, comp_id, str(b["club_a"]), str(b["club_a"])),
            ).fetchone()
            if fx:
                hg = int(fx["home_goals"] or 0)
                ag = int(fx["away_goals"] or 0)
                winner = str(fx["home_club_id"]) if hg >= ag else str(fx["away_club_id"])
                conn.execute(
                    "UPDATE cup_brackets SET winner=? WHERE save_id=? AND competition_id=? AND round=? AND slot=?",
                    (winner, save_id, comp_id, completed_round, int(b["slot"])),
                )
        if winner:
            winners.append(winner)

    if len(winners) < 2:
        return

    random.shuffle(winners)
    next_round_name = next_round_cfg["name"]
    next_date = _round_date(season_year, next_round_cfg["month"], next_round_cfg["day"])
    is_neutral = int(next_round_cfg.get("neutral", False))
    legs = int(next_round_cfg.get("legs", 1))

    pairs = [(winners[i], winners[i + 1]) for i in range(0, len(winners) - 1, 2)]
    for slot, (club_a, club_b) in enumerate(pairs):
        conn.execute(
            "INSERT INTO cup_brackets (save_id, competition_id, round, slot, club_a, club_b) VALUES (?, ?, ?, ?, ?, ?)",
            (save_id, comp_id, next_round_name, slot, club_a, club_b),
        )
        conn.execute(
            "INSERT INTO fixtures (save_id, match_day, fixture_date, home_club_id, away_club_id, competition_id, leg, is_neutral) VALUES (?, 0, ?, ?, ?, ?, 1, ?)",
            (save_id, next_date.isoformat(), club_a, club_b, comp_id, is_neutral),
        )
        if legs == 2:
            leg2_date = next_date + timedelta(days=14)
            conn.execute(
                "INSERT INTO fixtures (save_id, match_day, fixture_date, home_club_id, away_club_id, competition_id, leg, is_neutral) VALUES (?, 0, ?, ?, ?, ?, 2, 0)",
                (save_id, leg2_date.isoformat(), club_b, club_a, comp_id),
            )
