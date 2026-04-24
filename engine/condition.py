from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict

from .db import (
    db_session,
    get_current_day,
    get_save_current_day,
    initialize_schema,
    load_player_condition,
    load_save_player_condition,
    maybe_migrate_legacy_condition_json,
    save_player_condition,
    save_save_player_condition,
    set_current_day,
)
from .models import Club, MatchState, PlayerProfile, current_stamina_from_fatigue

POST_MATCH_RECOVERY = 10.0


def _daily_recovery(profile: PlayerProfile, current_stamina: float) -> float:
    natural_stamina = profile.attributes.get("stamina", 70.0)
    deficit = max(0.0, 100.0 - current_stamina)
    base_recovery = 0.45 + natural_stamina / 160.0
    deficit_factor = max(0.22, min(1.0, deficit / 35.0))
    return base_recovery * deficit_factor


def load_condition_state(path: Path, clubs: Dict[str, Club], save_id: int | None = None) -> int:
    legacy_json = path.with_name("condition_state.json")
    with db_session(path) as conn:
        initialize_schema(conn)
        existing_rows = conn.execute("SELECT COUNT(*) AS count FROM player_condition").fetchone()
        if legacy_json.exists() and existing_rows is not None and int(existing_rows["count"]) == 0:
            maybe_migrate_legacy_condition_json(conn, legacy_json, clubs)
        if save_id is None:
            current_day = get_current_day(conn)
        else:
            current_day = get_save_current_day(conn, save_id)
        for club in clubs.values():
            for player in club.players:
                if save_id is None:
                    saved = load_player_condition(conn, player.id)
                    if saved is None:
                        save_player_condition(conn, player.id, player.current_stamina, current_day)
                        saved = player.current_stamina
                else:
                    saved = load_save_player_condition(conn, save_id, player.id)
                    if saved is None:
                        save_save_player_condition(conn, save_id, player.id, player.current_stamina, current_day)
                        saved = player.current_stamina
                player.current_stamina = max(0.0, min(100.0, float(saved)))
        conn.commit()
        return current_day


def save_condition_state(path: Path, clubs: Dict[str, Club], current_day: int, save_id: int | None = None) -> None:
    with db_session(path) as conn:
        initialize_schema(conn)
        save_condition_state_to_conn(conn, clubs, current_day, save_id=save_id)
        conn.commit()


def save_condition_state_to_conn(conn: sqlite3.Connection, clubs: Dict[str, Club], current_day: int, save_id: int | None = None) -> None:
    if save_id is None:
        set_current_day(conn, current_day)
    for club in clubs.values():
        for player in club.players:
            if save_id is None:
                save_player_condition(conn, player.id, round(player.current_stamina, 2), current_day)
            else:
                save_save_player_condition(conn, save_id, player.id, round(player.current_stamina, 2), current_day)


def advance_condition_days(clubs: Dict[str, Club], days: int) -> None:
    if days <= 0:
        return
    for club in clubs.values():
        for player in club.players:
            for _ in range(days):
                player.current_stamina = min(
                    100.0,
                    player.current_stamina + _daily_recovery(player, player.current_stamina),
                )
                if player.injury_days_remaining > 0:
                    player.injury_days_remaining = max(0, player.injury_days_remaining - 1)


def apply_post_match_condition(state: MatchState) -> None:
    participants = state.home.xi + state.away.xi
    for player in participants:
        final_stamina = current_stamina_from_fatigue(player.fatigue)
        player.profile.current_stamina = min(100.0, final_stamina + 6.0)
