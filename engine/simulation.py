from __future__ import annotations

import math
import random
import sqlite3

BASE_GOALS = 1.35
HOME_ADVANTAGE = 1.2


def _poisson_sample(lam: float) -> int:
    if lam <= 0:
        return 0
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1


def _club_avg_ovr(conn: sqlite3.Connection, club_id: str) -> float:
    rows = conn.execute(
        "SELECT ovr FROM players WHERE club_id = ? LIMIT 25",
        (club_id,)
    ).fetchall()
    if not rows:
        return 65.0
    return sum(int(r["ovr"]) for r in rows) / len(rows)


def _update_standings(
    conn: sqlite3.Connection,
    save_id: int,
    competition_id: str,
    season: int,
    home_id: str,
    away_id: str,
    home_goals: int,
    away_goals: int,
) -> None:
    if not competition_id:
        return
    for club_id, gf, ga in ((home_id, home_goals, away_goals), (away_id, away_goals, home_goals)):
        won = 1 if gf > ga else 0
        drawn = 1 if gf == ga else 0
        lost = 1 if gf < ga else 0
        pts = 3 if won else (1 if drawn else 0)
        conn.execute(
            """
            INSERT INTO standings
                (save_id, competition_id, club_id, season, played, won, drawn, lost, gf, ga, points)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(save_id, competition_id, club_id, season) DO UPDATE SET
                played  = played  + 1,
                won     = won     + excluded.won,
                drawn   = drawn   + excluded.drawn,
                lost    = lost    + excluded.lost,
                gf      = gf      + excluded.gf,
                ga      = ga      + excluded.ga,
                points  = points  + excluded.points
            """,
            (save_id, competition_id, club_id, season, won, drawn, lost, gf, ga, pts),
        )


def simulate_ai_fixture(conn: sqlite3.Connection, save_id: int, fixture_id: int) -> None:
    row = conn.execute(
        "SELECT home_club_id, away_club_id, competition_id FROM fixtures WHERE id = ? AND save_id = ?",
        (fixture_id, save_id),
    ).fetchone()
    if row is None:
        return

    home_id = str(row["home_club_id"])
    away_id = str(row["away_club_id"])
    competition_id = str(row["competition_id"] or "")

    home_str = _club_avg_ovr(conn, home_id) / 75.0
    away_str = _club_avg_ovr(conn, away_id) / 75.0
    safe_away = max(away_str, 0.5)
    safe_home_def = max(home_str, 0.5)

    lam_home = (home_str / safe_away) * BASE_GOALS * HOME_ADVANTAGE
    lam_away = (away_str / safe_home_def) * BASE_GOALS

    home_goals = _poisson_sample(lam_home)
    away_goals = _poisson_sample(lam_away)

    conn.execute(
        "UPDATE fixtures SET played=1, home_goals=?, away_goals=? WHERE id=?",
        (home_goals, away_goals, fixture_id),
    )

    season_row = conn.execute(
        "SELECT season_year FROM saves WHERE id=?", (save_id,)
    ).fetchone()
    season = int(season_row["season_year"]) if season_row else 2025

    _update_standings(conn, save_id, competition_id, season, home_id, away_id, home_goals, away_goals)


def simulate_ai_transfers(conn: sqlite3.Connection, save_id: int) -> None:
    clubs = conn.execute(
        "SELECT DISTINCT club_id FROM save_league_clubs WHERE save_id=?",
        (save_id,)
    ).fetchall()
    for club_row in clubs:
        club_id = str(club_row["club_id"])
        count_row = conn.execute(
            "SELECT COUNT(*) AS c FROM players WHERE club_id=?", (club_id,)
        ).fetchone()
        if count_row and int(count_row["c"]) < 16:
            _sign_random_player(conn, save_id, club_id)


def _sign_random_player(conn: sqlite3.Connection, save_id: int, club_id: str) -> None:
    all_league_clubs = conn.execute(
        "SELECT DISTINCT club_id FROM save_league_clubs WHERE save_id=?", (save_id,)
    ).fetchall()
    league_club_ids = {str(r["club_id"]) for r in all_league_clubs}
    if not league_club_ids:
        return
    candidate = conn.execute(
        "SELECT id FROM players WHERE club_id NOT IN ({}) ORDER BY RANDOM() LIMIT 1".format(
            ",".join("?" * len(league_club_ids))
        ),
        list(league_club_ids),
    ).fetchone()
    if candidate:
        conn.execute(
            "UPDATE players SET club_id=? WHERE id=?",
            (club_id, str(candidate["id"])),
        )
