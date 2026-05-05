from __future__ import annotations

import json
import math
import random
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List

from .loader import merge_player_attributes
from .models import Club, PlayerProfile, infer_preferred_foot, normalize_player_instruction_map, normalize_preferred_foot, normalize_team_instructions
from .training import (
    PLAYER_TRAINING_FOCUS_OPTIONS,
    TEAM_TRAINING_FOCUS_OPTIONS,
    TRAINING_INTENSITY_OPTIONS,
    default_player_training_focus,
    normalize_player_training_focus,
    normalize_training_focus,
    normalize_training_intensity,
    training_attribute_gain,
    training_stamina_delta,
)

DEFAULT_TACTICS = {
    "tempo": 50.0,
    "width": 50.0,
    "defensive_line": 50.0,
    "pressing": 50.0,
    "directness": 50.0,
    "crossing": 50.0,
    "counter": 50.0,
}

DEFAULT_COLORS = {
    "primary": "#2E3A6A",
    "secondary": "#F5F5F5",
}

DEFAULT_BADGE = {
    "template_id": "1",
    "primary": DEFAULT_COLORS["primary"],
    "secondary": DEFAULT_COLORS["secondary"],
    "border": "#F5F5F5",
}

DEFAULT_LEAGUE = {
    "id": "ENG1",
    "name": "England Division I",
}

DEFAULT_CLUB_MANAGERS = {
    "A": "Mikel Arteta",
    "B": "Michael Carrick",
    "C": "Calum McFarlane",
    "D": "Pep Guardiola",
    "E": "Arne Slot",
    "F": "Roberto De Zerbi",
    "G": "Nuno Espirito Santo",
    "H": "Eddie Howe",
}

SEASON_START_MONTH = 7
SEASON_START_DAY = 7
FIRST_MATCH_MONTH = 8
FIRST_MATCH_DAY = 15

BADGE_TEMPLATES = {
    "1": {
        "name": "Classic Split Shield",
        "svg": """<svg width="114.4" height="148.8" viewBox="0 0 114.4 148.8" xmlns="http://www.w3.org/2000/svg"><defs><clipPath id="shield-clip"><path d="M57.2,0L0,10.6c0,0,0,17.2,0,31.9c0,80.2,57.2,106.3,57.2,106.3s57.2-26.1,57.2-106.3c0-14.6,0-31.9,0-31.9L57.2,0z" /></clipPath></defs><g clip-path="url(#shield-clip)"><rect x="0" y="0" width="57.2" height="148.8" fill="{primary}" /><rect x="57.2" y="0" width="57.2" height="148.8" fill="{secondary}" /></g><path d="M57.2,0L0,10.6c0,0,0,17.2,0,31.9c0,80.2,57.2,106.3,57.2,106.3s57.2-26.1,57.2-106.3c0-14.6,0-31.9,0-31.9L57.2,0z" fill="none" stroke="{border}" stroke-width="2" /></svg>""",
    },
    "2": {
        "name": "Round Crown Shield",
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000"><path d="m814.1 159.6.9-2.1c-112.4 43.1-209.4 21-300.6-57.6L500 87.5l-14.4 12.4c-91.2 78.6-188.2 100.7-300.6 57.6 52.8 125.4-2.8 215.4-46.8 343.2-12.5 36.4-11.3 96.2 4.8 131 70.6 153 354.6 270.8 354.6 270.8s287.8-115 359-269.2c16-34.9 17.4-94.7 5-131-43.7-127.5-99.8-217.8-47.5-342.7Z" fill="{primary}"/></svg>""",
    },
    "3": {
        "name": "Tall Heritage Shield",
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000"><path d="M800 147.5c-97.7 43.1-208.2 21-287.5-57.6L500 77.5l-12.5 12.4c-79.3 78.6-189.8 100.7-287.5 57.6v427.8c0 188.4 134 346 298 347.2 166.6 1.3 302-153.7 302-345v-430Z" fill="{primary}"/></svg>""",
    },
    "4": {
        "name": "Tower Shield",
        "svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000"><path d="M500 70 150 175.3v217.1C150 785 500 930 500 930s350-145 350-537.6V175.2L500 70Z" fill="{primary}"/></svg>""",
    },
}

DEFAULT_CLUB_BADGES = {
    "A": {"template_id": "1", "primary": "#C62828", "secondary": "#F5F5F5", "border": "#F5F5F5"},
    "B": {"template_id": "1", "primary": "#F5F5F5", "secondary": "#A61C1C", "border": "#F5F5F5"},
    "C": {"template_id": "2", "primary": "#2457C5", "secondary": "#F5F5F5", "border": "#F5F5F5"},
    "D": {"template_id": "3", "primary": "#2E6FD8", "secondary": "#F5F5F5", "border": "#F5F5F5"},
}

DEFAULT_APP_OPTIONS = {
    "resolution": "1560x900",
    "window_mode": "windowed",
    "display": "0",
    "language": "english",
    "bind_menu": "escape",
    "bind_pause": "space",
    "bind_start": "enter",
    "bind_speed_x1": "1",
    "bind_speed_x2": "2",
    "bind_speed_x4": "4",
    "bind_speed_x8": "8",
}

DEFAULT_OPTION_CHOICES = {
    "resolution": [
        ("1280x720", "1280 x 720", 1),
        ("1560x900", "1560 x 900", 2),
        ("1920x1080", "1920 x 1080", 3),
    ],
    "window_mode": [
        ("windowed", "Windowed", 1),
        ("fullscreen", "Fullscreen", 2),
    ],
    "language": [
        ("english", "English", 1),
    ],
    "bind_menu": [
        ("escape", "Esc", 1),
        ("tab", "Tab", 2),
        ("m", "M", 3),
    ],
    "bind_pause": [
        ("space", "Space", 1),
        ("p", "P", 2),
        ("enter", "Enter", 3),
    ],
    "bind_start": [
        ("enter", "Enter", 1),
        ("space", "Space", 2),
        ("s", "S", 3),
    ],
    "bind_speed_x1": [
        ("1", "1", 1),
        ("q", "Q", 2),
        ("z", "Z", 3),
    ],
    "bind_speed_x2": [
        ("2", "2", 1),
        ("w", "W", 2),
        ("x", "X", 3),
    ],
    "bind_speed_x4": [
        ("4", "4", 1),
        ("e", "E", 2),
        ("c", "C", 3),
    ],
    "bind_speed_x8": [
        ("8", "8", 1),
        ("r", "R", 2),
        ("v", "V", 3),
    ],
}


def connect_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_session(path: Path):
    conn = connect_db(path)
    try:
        yield conn
    finally:
        conn.close()


def initialize_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS clubs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            manager_name TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS club_tactics (
            club_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value REAL NOT NULL,
            PRIMARY KEY (club_id, key),
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        );

        CREATE TABLE IF NOT EXISTS club_colors (
            club_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            PRIMARY KEY (club_id, key),
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        );

        CREATE TABLE IF NOT EXISTS badge_templates (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            svg TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS club_badges (
            club_id TEXT PRIMARY KEY,
            template_id TEXT NOT NULL,
            primary_color TEXT NOT NULL,
            secondary_color TEXT NOT NULL,
            border_color TEXT NOT NULL,
            FOREIGN KEY (club_id) REFERENCES clubs(id),
            FOREIGN KEY (template_id) REFERENCES badge_templates(id)
        );

        CREATE TABLE IF NOT EXISTS players (
            id TEXT PRIMARY KEY,
            club_id TEXT NOT NULL,
            name TEXT NOT NULL,
            position TEXT NOT NULL,
            ovr INTEGER NOT NULL,
            preferred_foot TEXT NOT NULL DEFAULT 'right',
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        );

        CREATE TABLE IF NOT EXISTS player_attributes (
            player_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value REAL NOT NULL,
            PRIMARY KEY (player_id, key),
            FOREIGN KEY (player_id) REFERENCES players(id)
        );

        CREATE TABLE IF NOT EXISTS player_condition (
            player_id TEXT PRIMARY KEY,
            current_stamina REAL NOT NULL,
            updated_day INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (player_id) REFERENCES players(id)
        );

        CREATE TABLE IF NOT EXISTS save_player_condition (
            save_id INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            current_stamina REAL NOT NULL,
            updated_day INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (save_id, player_id),
            FOREIGN KEY (save_id) REFERENCES saves(id),
            FOREIGN KEY (player_id) REFERENCES players(id)
        );

        CREATE TABLE IF NOT EXISTS save_player_status (
            save_id INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            yellow_card_count INTEGER NOT NULL DEFAULT 0,
            suspension_matches_remaining INTEGER NOT NULL DEFAULT 0,
            suspension_reason TEXT NOT NULL DEFAULT '',
            injury_days_remaining INTEGER NOT NULL DEFAULT 0,
            injury_count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (save_id, player_id),
            FOREIGN KEY (save_id) REFERENCES saves(id),
            FOREIGN KEY (player_id) REFERENCES players(id)
        );

        CREATE TABLE IF NOT EXISTS save_player_attributes (
            save_id INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value REAL NOT NULL,
            PRIMARY KEY (save_id, player_id, key),
            FOREIGN KEY (save_id) REFERENCES saves(id),
            FOREIGN KEY (player_id) REFERENCES players(id)
        );

        CREATE TABLE IF NOT EXISTS save_training_settings (
            save_id INTEGER NOT NULL,
            club_id TEXT NOT NULL,
            team_focus TEXT NOT NULL DEFAULT 'balanced',
            intensity TEXT NOT NULL DEFAULT 'normal',
            updated_day INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (save_id, club_id),
            FOREIGN KEY (save_id) REFERENCES saves(id),
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        );

        CREATE TABLE IF NOT EXISTS save_player_training (
            save_id INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            focus TEXT NOT NULL DEFAULT 'auto',
            updated_day INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (save_id, player_id),
            FOREIGN KEY (save_id) REFERENCES saves(id),
            FOREIGN KEY (player_id) REFERENCES players(id)
        );

        CREATE TABLE IF NOT EXISTS save_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            save_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            date_text TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'info',
            dedupe_key TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (save_id) REFERENCES saves(id)
        );

        CREATE TABLE IF NOT EXISTS save_club_setups (
            save_id INTEGER NOT NULL,
            club_id TEXT NOT NULL,
            formation TEXT NOT NULL DEFAULT '4-3-3',
            xi_json TEXT NOT NULL DEFAULT '[]',
            bench_json TEXT NOT NULL DEFAULT '[]',
            instructions_json TEXT NOT NULL DEFAULT '{}',
            player_instructions_json TEXT NOT NULL DEFAULT '{}',
            PRIMARY KEY (save_id, club_id),
            FOREIGN KEY (save_id) REFERENCES saves(id),
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        );

        CREATE TABLE IF NOT EXISTS leagues (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS league_clubs (
            league_id TEXT NOT NULL,
            club_id TEXT NOT NULL,
            display_order INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (league_id, club_id),
            FOREIGN KEY (league_id) REFERENCES leagues(id),
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        );

        CREATE TABLE IF NOT EXISTS managers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS saves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_id INTEGER NOT NULL,
            league_id TEXT NOT NULL,
            club_id TEXT NOT NULL,
            current_day INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (manager_id) REFERENCES managers(id),
            FOREIGN KEY (league_id) REFERENCES leagues(id),
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        );

        CREATE TABLE IF NOT EXISTS fixtures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            save_id INTEGER NOT NULL,
            match_day INTEGER NOT NULL,
            fixture_date TEXT,
            home_club_id TEXT NOT NULL,
            away_club_id TEXT NOT NULL,
            played INTEGER NOT NULL DEFAULT 0,
            home_goals INTEGER,
            away_goals INTEGER,
            report_json TEXT,
            FOREIGN KEY (save_id) REFERENCES saves(id),
            FOREIGN KEY (home_club_id) REFERENCES clubs(id),
            FOREIGN KEY (away_club_id) REFERENCES clubs(id)
        );

        CREATE TABLE IF NOT EXISTS app_options (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS option_choices (
            option_key TEXT NOT NULL,
            value TEXT NOT NULL,
            label TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (option_key, value)
        );

        CREATE TABLE IF NOT EXISTS save_player_club (
            save_id INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            club_id TEXT NOT NULL,
            PRIMARY KEY (save_id, player_id),
            FOREIGN KEY (save_id) REFERENCES saves(id)
        );

        CREATE TABLE IF NOT EXISTS transfer_market (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            save_id INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            listed_club_id TEXT NOT NULL,
            asking_price INTEGER NOT NULL DEFAULT 0,
            listed_date TEXT NOT NULL,
            window_type TEXT NOT NULL,
            season_year INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'available',
            is_user_listed INTEGER NOT NULL DEFAULT 0,
            UNIQUE(save_id, player_id, season_year, window_type),
            FOREIGN KEY (save_id) REFERENCES saves(id),
            FOREIGN KEY (player_id) REFERENCES players(id)
        );

        CREATE TABLE IF NOT EXISTS transfer_offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            save_id INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            offer_amount INTEGER NOT NULL,
            offer_number INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'pending',
            created_date TEXT NOT NULL,
            response_date TEXT,
            window_type TEXT NOT NULL,
            season_year INTEGER NOT NULL,
            FOREIGN KEY (save_id) REFERENCES saves(id),
            FOREIGN KEY (player_id) REFERENCES players(id)
        );

        CREATE TABLE IF NOT EXISTS player_contracts (
            save_id INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            club_id TEXT NOT NULL,
            weekly_wage INTEGER NOT NULL DEFAULT 0,
            contract_years INTEGER NOT NULL DEFAULT 1,
            start_date TEXT,
            PRIMARY KEY (save_id, player_id),
            FOREIGN KEY (save_id) REFERENCES saves(id)
        );

        CREATE TABLE IF NOT EXISTS save_finances (
            save_id INTEGER PRIMARY KEY,
            balance INTEGER NOT NULL DEFAULT 25000000,
            transfer_budget INTEGER NOT NULL DEFAULT 10000000,
            wage_budget_weekly INTEGER NOT NULL DEFAULT 500000,
            season_income_matchday INTEGER NOT NULL DEFAULT 0,
            season_income_sponsor INTEGER NOT NULL DEFAULT 0,
            season_income_transfers INTEGER NOT NULL DEFAULT 0,
            season_expenses_wages INTEGER NOT NULL DEFAULT 0,
            season_expenses_transfers INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (save_id) REFERENCES saves(id)
        );

        CREATE TABLE IF NOT EXISTS finance_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            save_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            amount INTEGER NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            transaction_date TEXT NOT NULL,
            FOREIGN KEY (save_id) REFERENCES saves(id)
        );

        CREATE INDEX IF NOT EXISTS idx_fixtures_save_id ON fixtures(save_id);
        CREATE INDEX IF NOT EXISTS idx_fixtures_save_date ON fixtures(save_id, fixture_date);
        CREATE INDEX IF NOT EXISTS idx_save_messages_save_id ON save_messages(save_id);
        CREATE INDEX IF NOT EXISTS idx_transfer_market_save_id ON transfer_market(save_id);
        CREATE INDEX IF NOT EXISTS idx_transfer_offers_save_id ON transfer_offers(save_id);
        CREATE INDEX IF NOT EXISTS idx_finance_transactions_save_id ON finance_transactions(save_id);
        CREATE INDEX IF NOT EXISTS idx_players_club_id ON players(club_id);
        CREATE INDEX IF NOT EXISTS idx_save_player_club_save_id ON save_player_club(save_id);

        CREATE TABLE IF NOT EXISTS club_staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            save_id INTEGER NOT NULL,
            staff_type TEXT NOT NULL,
            quality TEXT NOT NULL,
            UNIQUE(save_id, staff_type)
        );

        CREATE TABLE IF NOT EXISTS player_scouting (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            save_id INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            season_year INTEGER NOT NULL,
            revealed_pct INTEGER NOT NULL DEFAULT 50,
            UNIQUE(save_id, player_id, season_year)
        );

        CREATE TABLE IF NOT EXISTS pending_scout_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            save_id INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            player_name TEXT NOT NULL,
            due_date TEXT NOT NULL,
            scout_quality TEXT NOT NULL,
            pct_min INTEGER NOT NULL,
            pct_max INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS competitions (
            id          TEXT NOT NULL,
            name        TEXT NOT NULL,
            country     TEXT NOT NULL,
            type        TEXT NOT NULL,
            season      INTEGER NOT NULL,
            save_id     INTEGER NOT NULL,
            PRIMARY KEY (id, save_id),
            FOREIGN KEY (save_id) REFERENCES saves(id)
        );

        CREATE TABLE IF NOT EXISTS cup_brackets (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            save_id         INTEGER NOT NULL,
            competition_id  TEXT NOT NULL,
            round           TEXT NOT NULL,
            slot            INTEGER NOT NULL,
            club_a          TEXT,
            club_b          TEXT,
            score_a_leg1    INTEGER,
            score_b_leg1    INTEGER,
            score_a_leg2    INTEGER,
            score_b_leg2    INTEGER,
            winner          TEXT,
            FOREIGN KEY (save_id) REFERENCES saves(id)
        );

        CREATE TABLE IF NOT EXISTS save_league_clubs (
            save_id     INTEGER NOT NULL,
            league_id   TEXT NOT NULL,
            club_id     TEXT NOT NULL,
            season      INTEGER NOT NULL,
            PRIMARY KEY (save_id, league_id, club_id, season),
            FOREIGN KEY (save_id) REFERENCES saves(id)
        );

        CREATE TABLE IF NOT EXISTS standings (
            save_id         INTEGER NOT NULL,
            competition_id  TEXT NOT NULL,
            club_id         TEXT NOT NULL,
            season          INTEGER NOT NULL,
            played          INTEGER DEFAULT 0,
            won             INTEGER DEFAULT 0,
            drawn           INTEGER DEFAULT 0,
            lost            INTEGER DEFAULT 0,
            gf              INTEGER DEFAULT 0,
            ga              INTEGER DEFAULT 0,
            points          INTEGER DEFAULT 0,
            PRIMARY KEY (save_id, competition_id, club_id, season),
            FOREIGN KEY (save_id) REFERENCES saves(id)
        );

        CREATE INDEX IF NOT EXISTS idx_standings_save_comp ON standings(save_id, competition_id);
        CREATE INDEX IF NOT EXISTS idx_cup_brackets_save_comp ON cup_brackets(save_id, competition_id);
        CREATE INDEX IF NOT EXISTS idx_save_league_clubs_save ON save_league_clubs(save_id, league_id);
        """
    )
    _ensure_column(conn, "saves", "season_year", "INTEGER")
    _ensure_column(conn, "saves", "current_date", "TEXT")
    _ensure_column(conn, "saves", "season_completed", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "fixtures", "fixture_date", "TEXT")
    _ensure_column(conn, "fixtures", "report_json", "TEXT")
    _ensure_column(conn, "clubs", "manager_name", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "save_club_setups", "instructions_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(conn, "save_club_setups", "player_instructions_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(conn, "save_player_status", "suspension_reason", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "players", "preferred_foot", "TEXT NOT NULL DEFAULT 'right'")
    _ensure_column(conn, "players", "age", "INTEGER NOT NULL DEFAULT 22")
    _ensure_column(conn, "transfer_offers", "offered_wage", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "transfer_offers", "offered_contract_years", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "transfer_offers", "player_response_date", "TEXT")
    _ensure_column(conn, "transfer_offers", "offering_club_id", "TEXT")
    _ensure_column(conn, "transfer_offers", "negotiation_attempt", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(conn, "save_messages", "is_read", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "fixtures", "competition_id", "TEXT")
    _ensure_column(conn, "fixtures", "leg", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(conn, "fixtures", "is_neutral", "INTEGER NOT NULL DEFAULT 0")
    _backfill_player_feet(conn)
    _backfill_player_attributes(conn)
    _backfill_club_managers(conn)
    _backfill_calendar_fields(conn)
    _backfill_player_ages(conn)
    conn.commit()


def bootstrap_database(conn: sqlite3.Connection) -> None:
    initialize_schema(conn)
    _ensure_default_badges(conn)
    _ensure_default_league(conn)
    _ensure_default_options(conn)
    conn.commit()


def current_season_year() -> int:
    return date.today().year


def season_start_date(year: int) -> date:
    return date(year, SEASON_START_MONTH, SEASON_START_DAY)


def first_match_date(year: int) -> date:
    return date(year, FIRST_MATCH_MONTH, FIRST_MATCH_DAY)


def format_game_date(date_text: str | None) -> str:
    if not date_text:
        return ""
    return date.fromisoformat(date_text).strftime("%d %b %Y").upper()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    names = {str(row["name"]) for row in rows}
    if column not in names:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _backfill_calendar_fields(conn: sqlite3.Connection) -> None:
    save_rows = conn.execute(
        """
        SELECT id, current_day, season_year, saves.current_date AS current_date, created_at
        FROM saves
        """
    ).fetchall()
    year_by_save: Dict[int, int] = {}
    for row in save_rows:
        save_id = int(row["id"])
        season_year = int(row["season_year"]) if row["season_year"] is not None else 0
        if season_year <= 0:
            created_at = str(row["created_at"] or "")
            if len(created_at) >= 4 and created_at[:4].isdigit():
                season_year = int(created_at[:4])
            else:
                season_year = current_season_year()
            conn.execute("UPDATE saves SET season_year = ? WHERE id = ?", (season_year, save_id))
        year_by_save[save_id] = season_year
        if not row["current_date"]:
            current_day = int(row["current_day"] or 0)
            current_date = season_start_date(season_year) + timedelta(days=current_day)
            conn.execute(
                "UPDATE saves SET current_date = ? WHERE id = ?",
                (current_date.isoformat(), save_id),
            )

    fixture_rows = conn.execute(
        """
        SELECT id, save_id, match_day, fixture_date
        FROM fixtures
        """
    ).fetchall()
    for row in fixture_rows:
        if row["fixture_date"]:
            continue
        save_id = int(row["save_id"])
        match_day = int(row["match_day"])
        season_year = year_by_save.get(save_id, current_season_year())
        fixture_date = first_match_date(season_year) + timedelta(days=(match_day - 1) * 7)
        conn.execute(
            "UPDATE fixtures SET fixture_date = ? WHERE id = ?",
            (fixture_date.isoformat(), int(row["id"])),
        )


def _backfill_player_feet(conn: sqlite3.Connection) -> None:
    rows = conn.execute("SELECT id, name, position, preferred_foot FROM players").fetchall()
    for row in rows:
        raw_value = row["preferred_foot"]
        current = normalize_preferred_foot(raw_value)
        inferred = infer_preferred_foot(str(row["name"]), str(row["position"]))
        if raw_value is None or str(raw_value).strip().lower() not in {"left", "right"} or (current == "right" and inferred == "left"):
            conn.execute(
                "UPDATE players SET preferred_foot = ? WHERE id = ?",
                (inferred, str(row["id"])),
            )


def _backfill_player_attributes(conn: sqlite3.Connection) -> None:
    players = conn.execute("SELECT id, name, position, ovr FROM players").fetchall()
    attr_rows = conn.execute("SELECT player_id, key, value FROM player_attributes").fetchall()
    attrs_by_player: Dict[str, Dict[str, float]] = {}
    for row in attr_rows:
        attrs_by_player.setdefault(str(row["player_id"]), {})[str(row["key"])] = float(row["value"])
    upserts: list[tuple[str, str, float]] = []
    for row in players:
        player_id = str(row["id"])
        merged = merge_player_attributes(
            int(row["ovr"]),
            str(row["position"]),
            attrs_by_player.get(player_id, {}),
            player_id=player_id,
            name=str(row["name"]),
        )
        for key, value in merged.items():
            upserts.append((player_id, key, float(value)))
    if upserts:
        conn.executemany(
            """
            INSERT INTO player_attributes (player_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id, key) DO UPDATE SET value=excluded.value
            """,
            upserts,
        )


def _backfill_player_ages(conn: sqlite3.Connection) -> None:
    rows = conn.execute("SELECT id, ovr, age FROM players").fetchall()
    updates = []
    for row in rows:
        if int(row["age"] or 0) != 22:
            continue
        player_id = str(row["id"])
        ovr = int(row["ovr"])
        h = sum(ord(c) for c in player_id) % 100
        # Derive age: higher OVR skews older; add deterministic noise
        base_age = 17 + max(0, (ovr - 55)) // 4
        age = max(17, min(36, base_age + (h % 9) - 4))
        updates.append((age, player_id))
    if updates:
        conn.executemany("UPDATE players SET age = ? WHERE id = ?", updates)


def _backfill_club_managers(conn: sqlite3.Connection) -> None:
    rows = conn.execute("SELECT id, manager_name FROM clubs").fetchall()
    for row in rows:
        club_id = str(row["id"])
        manager_name = str(row["manager_name"] or "").strip()
        default = DEFAULT_CLUB_MANAGERS.get(club_id, "")
        if not manager_name and default:
            conn.execute(
                "UPDATE clubs SET manager_name = ? WHERE id = ?",
                (default, club_id),
            )


def _ensure_default_badges(conn: sqlite3.Connection) -> None:
    conn.executemany(
        """
        INSERT INTO badge_templates (id, name, svg) VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            svg=excluded.svg
        """,
        [(template_id, template["name"], template["svg"]) for template_id, template in BADGE_TEMPLATES.items()],
    )
    club_rows = conn.execute("SELECT id FROM clubs ORDER BY id").fetchall()
    if not club_rows:
        return
    color_rows = conn.execute("SELECT club_id, key, value FROM club_colors").fetchall()
    colors_by_club: Dict[str, Dict[str, str]] = {}
    for row in color_rows:
        colors_by_club.setdefault(str(row["club_id"]), dict(DEFAULT_COLORS))[str(row["key"])] = str(row["value"])
    badge_rows = conn.execute("SELECT club_id FROM club_badges").fetchall()
    existing = {str(row["club_id"]) for row in badge_rows}
    next_template = 1
    for row in club_rows:
        club_id = str(row["id"])
        if club_id in existing:
            continue
        defaults = dict(DEFAULT_CLUB_BADGES.get(club_id, {}))
        colors = colors_by_club.get(club_id, DEFAULT_COLORS)
        template_id = defaults.get("template_id")
        if template_id is None:
            template_id = str(next_template)
            next_template = 1 + (next_template % len(BADGE_TEMPLATES))
        conn.execute(
            """
            INSERT INTO club_badges (club_id, template_id, primary_color, secondary_color, border_color)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                club_id,
                str(template_id),
                str(defaults.get("primary", colors.get("primary", DEFAULT_BADGE["primary"]))),
                str(defaults.get("secondary", colors.get("secondary", DEFAULT_BADGE["secondary"]))),
                str(defaults.get("border", DEFAULT_BADGE["border"])),
            ),
        )


def _ensure_default_league(conn: sqlite3.Connection) -> None:
    club_rows = conn.execute("SELECT id FROM clubs ORDER BY id").fetchall()
    if not club_rows:
        return
    conn.execute(
        """
        INSERT INTO leagues (id, name) VALUES (?, ?)
        ON CONFLICT(id) DO UPDATE SET name=excluded.name
        """,
        (DEFAULT_LEAGUE["id"], DEFAULT_LEAGUE["name"]),
    )
    current = conn.execute(
        "SELECT COUNT(*) AS count FROM league_clubs WHERE league_id = ?",
        (DEFAULT_LEAGUE["id"],),
    ).fetchone()
    if current is None or int(current["count"]) == 0:
        conn.executemany(
            """
            INSERT INTO league_clubs (league_id, club_id, display_order)
            VALUES (?, ?, ?)
            ON CONFLICT(league_id, club_id) DO UPDATE SET display_order=excluded.display_order
            """,
            [
                (DEFAULT_LEAGUE["id"], str(row["id"]), idx)
                for idx, row in enumerate(club_rows, start=1)
            ],
        )


def _ensure_default_options(conn: sqlite3.Connection) -> None:
    for key, value in DEFAULT_APP_OPTIONS.items():
        conn.execute(
            """
            INSERT INTO app_options (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO NOTHING
            """,
            (key, value),
        )
    for option_key, choices in DEFAULT_OPTION_CHOICES.items():
        conn.executemany(
            """
            INSERT INTO option_choices (option_key, value, label, sort_order)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(option_key, value) DO UPDATE SET
                label=excluded.label,
                sort_order=excluded.sort_order
            """,
            [(option_key, value, label, sort_order) for value, label, sort_order in choices],
        )


def load_clubs_from_db(conn: sqlite3.Connection, save_id: int | None = None) -> Dict[str, Club]:
    club_rows = conn.execute("SELECT id, name, manager_name FROM clubs ORDER BY id").fetchall()
    tactic_rows = conn.execute("SELECT club_id, key, value FROM club_tactics").fetchall()
    color_rows = conn.execute("SELECT club_id, key, value FROM club_colors").fetchall()
    badge_rows = conn.execute(
        """
        SELECT club_id, template_id, primary_color, secondary_color, border_color
        FROM club_badges
        """
    ).fetchall()
    if save_id is None:
        player_rows = conn.execute(
            """
            SELECT p.id, p.club_id, p.name, p.position, p.ovr, pc.current_stamina
                 , p.preferred_foot
            FROM players p
            LEFT JOIN player_condition pc ON pc.player_id = p.id
            ORDER BY p.club_id, p.id
            """
        ).fetchall()
    else:
        seed_save_player_status_defaults(conn, save_id)
        player_rows = conn.execute(
            """
            SELECT p.id, p.club_id, p.name, p.position, p.ovr, spc.current_stamina,
                   p.preferred_foot,
                   sps.yellow_card_count,
                   sps.suspension_matches_remaining,
                   sps.suspension_reason,
                   sps.injury_days_remaining,
                   sps.injury_count
            FROM players p
            LEFT JOIN save_player_condition spc
              ON spc.player_id = p.id AND spc.save_id = ?
            LEFT JOIN save_player_status sps
              ON sps.player_id = p.id AND sps.save_id = ?
            ORDER BY p.club_id, p.id
            """,
            (int(save_id), int(save_id)),
        ).fetchall()
    if save_id is None:
        attribute_rows = conn.execute("SELECT player_id, key, value FROM player_attributes").fetchall()
    else:
        attribute_rows = conn.execute(
            """
            SELECT p.id AS player_id, pa.key, COALESCE(spa.value, pa.value) AS value
            FROM players p
            LEFT JOIN player_attributes pa ON pa.player_id = p.id
            LEFT JOIN save_player_attributes spa
              ON spa.save_id = ? AND spa.player_id = p.id AND spa.key = pa.key
            """,
            (int(save_id),),
        ).fetchall()
    alt_pos_rows = conn.execute("SELECT player_id, position FROM player_alt_positions").fetchall()
    alt_positions_by_player: Dict[str, List[str]] = {}
    for row in alt_pos_rows:
        alt_positions_by_player.setdefault(str(row["player_id"]), []).append(str(row["position"]))
    setup_rows = conn.execute(
        """
        SELECT save_id, club_id, formation, xi_json, bench_json, instructions_json, player_instructions_json
        FROM save_club_setups
        WHERE ? IS NOT NULL AND save_id = ?
        """,
        (None if save_id is None else int(save_id), None if save_id is None else int(save_id)),
    ).fetchall() if save_id is not None else []

    tactics_by_club: Dict[str, Dict[str, float]] = {}
    for row in tactic_rows:
        tactics_by_club.setdefault(str(row["club_id"]), dict(DEFAULT_TACTICS))[str(row["key"])] = float(row["value"])

    colors_by_club: Dict[str, Dict[str, str]] = {}
    for row in color_rows:
        colors_by_club.setdefault(str(row["club_id"]), dict(DEFAULT_COLORS))[str(row["key"])] = str(row["value"])

    badges_by_club: Dict[str, Dict[str, str]] = {}
    for row in badge_rows:
        badges_by_club[str(row["club_id"])] = {
            "template_id": str(row["template_id"]),
            "primary": str(row["primary_color"]),
            "secondary": str(row["secondary_color"]),
            "border": str(row["border_color"]),
        }

    attrs_by_player: Dict[str, Dict[str, float]] = {}
    for row in attribute_rows:
        attrs_by_player.setdefault(str(row["player_id"]), {})[str(row["key"])] = float(row["value"])

    setups_by_club: Dict[str, dict] = {}
    for row in setup_rows:
        club_id = str(row["club_id"])
        try:
            xi_ids = [str(player_id) for player_id in json.loads(str(row["xi_json"] or "[]"))]
        except json.JSONDecodeError:
            xi_ids = []
        try:
            bench_ids = [str(player_id) for player_id in json.loads(str(row["bench_json"] or "[]"))]
        except json.JSONDecodeError:
            bench_ids = []
        try:
            instructions = normalize_team_instructions(json.loads(str(row["instructions_json"] or "{}")))
        except json.JSONDecodeError:
            instructions = normalize_team_instructions(None)
        try:
            player_instructions = normalize_player_instruction_map(json.loads(str(row["player_instructions_json"] or "{}")))
        except json.JSONDecodeError:
            player_instructions = {}
        setups_by_club[club_id] = {
            "formation": str(row["formation"] or "4-3-3"),
            "lineup_xi": xi_ids,
            "lineup_bench": bench_ids,
            "instructions": instructions,
            "player_instructions": player_instructions,
        }

    # Transfer overrides: players moved to a new club within this save
    transfer_club_overrides: Dict[str, str] = {}
    if save_id is not None:
        override_rows = conn.execute(
            "SELECT player_id, club_id FROM save_player_club WHERE save_id = ?",
            (int(save_id),),
        ).fetchall()
        transfer_club_overrides = {str(r["player_id"]): str(r["club_id"]) for r in override_rows}

    players_by_club: Dict[str, List[PlayerProfile]] = {}
    for row in player_rows:
        player_id = str(row["id"])
        club_id = transfer_club_overrides.get(player_id, str(row["club_id"]))
        players_by_club.setdefault(club_id, []).append(
            PlayerProfile(
                id=player_id,
                name=str(row["name"]),
                position=str(row["position"]),
                ovr=int(row["ovr"]),
                attributes=merge_player_attributes(
                    int(row["ovr"]),
                    str(row["position"]),
                    dict(attrs_by_player.get(player_id, {})),
                    player_id=player_id,
                    name=str(row["name"]),
                ),
                preferred_foot=normalize_preferred_foot(row["preferred_foot"]),
                current_stamina=float(row["current_stamina"]) if row["current_stamina"] is not None else 100.0,
                yellow_card_count=int(row["yellow_card_count"] or 0) if "yellow_card_count" in row.keys() else 0,
                suspension_matches_remaining=int(row["suspension_matches_remaining"] or 0) if "suspension_matches_remaining" in row.keys() else 0,
                injury_days_remaining=int(row["injury_days_remaining"] or 0) if "injury_days_remaining" in row.keys() else 0,
                injury_count=int(row["injury_count"] or 0) if "injury_count" in row.keys() else 0,
                age=int(row["age"] or 0) if "age" in row.keys() else 0,
                alt_positions=list(alt_positions_by_player.get(player_id, [])),
            )
        )

    clubs: Dict[str, Club] = {}
    for row in club_rows:
        club_id = str(row["id"])
        clubs[club_id] = Club(
            id=club_id,
            name=str(row["name"]),
            manager_name=str(row["manager_name"] or ""),
            players=list(players_by_club.get(club_id, [])),
            tactics=dict(tactics_by_club.get(club_id, DEFAULT_TACTICS)),
            colors=dict(colors_by_club.get(club_id, DEFAULT_COLORS)),
            badge=dict(badges_by_club.get(club_id, DEFAULT_BADGE)),
            formation=str(setups_by_club.get(club_id, {}).get("formation", "4-3-3")),
            lineup_xi=list(setups_by_club.get(club_id, {}).get("lineup_xi", [])),
            lineup_bench=list(setups_by_club.get(club_id, {}).get("lineup_bench", [])),
            instructions=dict(setups_by_club.get(club_id, {}).get("instructions", normalize_team_instructions(None))),
            player_instructions=dict(setups_by_club.get(club_id, {}).get("player_instructions", {})),
        )
    return clubs


def seed_save_club_setups(conn: sqlite3.Connection, save_id: int) -> None:
    from .loader import pick_best_xi

    row = conn.execute(
        "SELECT COUNT(*) AS count FROM save_club_setups WHERE save_id = ?",
        (int(save_id),),
    ).fetchone()
    if row is not None and int(row["count"] or 0) > 0:
        return

    clubs = load_clubs_from_db(conn, save_id=save_id)
    for club in clubs.values():
        xi, bench = pick_best_xi(club, formation_name=club.formation)
        conn.execute(
            """
            INSERT INTO save_club_setups (save_id, club_id, formation, xi_json, bench_json, instructions_json, player_instructions_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(save_id, club_id) DO NOTHING
            """,
            (
                int(save_id),
                club.id,
                str(club.formation or "4-3-3"),
                json.dumps([player.id for player in xi]),
                json.dumps([player.id for player in bench]),
                json.dumps(normalize_team_instructions(getattr(club, "instructions", None))),
                json.dumps(normalize_player_instruction_map(getattr(club, "player_instructions", None))),
            ),
        )


def load_save_club_setups(conn: sqlite3.Connection, save_id: int) -> Dict[str, dict]:
    seed_save_club_setups(conn, save_id)
    rows = conn.execute(
        """
        SELECT club_id, formation, xi_json, bench_json, instructions_json, player_instructions_json
        FROM save_club_setups
        WHERE save_id = ?
        """,
        (int(save_id),),
    ).fetchall()
    setups: Dict[str, dict] = {}
    for row in rows:
        club_id = str(row["club_id"])
        try:
            xi_ids = [str(player_id) for player_id in json.loads(str(row["xi_json"] or "[]"))]
        except json.JSONDecodeError:
            xi_ids = []
        try:
            bench_ids = [str(player_id) for player_id in json.loads(str(row["bench_json"] or "[]"))]
        except json.JSONDecodeError:
            bench_ids = []
        try:
            instructions = normalize_team_instructions(json.loads(str(row["instructions_json"] or "{}")))
        except json.JSONDecodeError:
            instructions = normalize_team_instructions(None)
        try:
            player_instructions = normalize_player_instruction_map(json.loads(str(row["player_instructions_json"] or "{}")))
        except json.JSONDecodeError:
            player_instructions = {}
        setups[club_id] = {
            "formation": str(row["formation"] or "4-3-3"),
            "xi_ids": xi_ids,
            "bench_ids": bench_ids,
            "instructions": instructions,
            "player_instructions": player_instructions,
        }
    return setups


def save_save_club_setup(
    conn: sqlite3.Connection,
    save_id: int,
    club_id: str,
    formation: str,
    xi_ids: List[str],
    bench_ids: List[str],
    instructions: Dict[str, str] | None = None,
    player_instructions: Dict[str, Dict[str, int]] | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO save_club_setups (save_id, club_id, formation, xi_json, bench_json, instructions_json, player_instructions_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(save_id, club_id) DO UPDATE SET
            formation=excluded.formation,
            xi_json=excluded.xi_json,
            bench_json=excluded.bench_json,
            instructions_json=excluded.instructions_json,
            player_instructions_json=excluded.player_instructions_json
        """,
        (
            int(save_id),
            club_id,
            str(formation or "4-3-3"),
            json.dumps(list(xi_ids)),
            json.dumps(list(bench_ids)),
            json.dumps(normalize_team_instructions(instructions)),
            json.dumps(normalize_player_instruction_map(player_instructions)),
        ),
    )


def list_leagues(conn: sqlite3.Connection) -> List[dict]:
    rows = conn.execute("SELECT id, name FROM leagues ORDER BY name").fetchall()
    return [{"id": str(row["id"]), "name": str(row["name"])} for row in rows]


def list_league_clubs(conn: sqlite3.Connection, league_id: str) -> List[dict]:
    rows = conn.execute(
        """
        SELECT c.id, c.name, c.manager_name,
               cc.value AS primary_color, cs.value AS secondary_color,
               cb.template_id, cb.primary_color AS badge_primary, cb.secondary_color AS badge_secondary,
               cb.border_color AS badge_border,
               COUNT(p.id) AS players_count, ROUND(AVG(p.ovr), 1) AS avg_ovr
        FROM league_clubs lc
        JOIN clubs c ON c.id = lc.club_id
        LEFT JOIN club_colors cc ON cc.club_id = c.id AND cc.key = 'primary'
        LEFT JOIN club_colors cs ON cs.club_id = c.id AND cs.key = 'secondary'
        LEFT JOIN club_badges cb ON cb.club_id = c.id
        LEFT JOIN players p ON p.club_id = c.id
        WHERE lc.league_id = ?
        GROUP BY c.id, c.name, c.manager_name, lc.display_order, cc.value, cs.value,
                 cb.template_id, cb.primary_color, cb.secondary_color, cb.border_color
        ORDER BY lc.display_order, c.name
        """,
        (league_id,),
    ).fetchall()
    clubs: List[dict] = []
    for row in rows:
        clubs.append(
            {
                "id": str(row["id"]),
                "name": str(row["name"]),
                "manager_name": str(row["manager_name"] or ""),
                "primary_color": str(row["primary_color"] or DEFAULT_COLORS["primary"]),
                "secondary_color": str(row["secondary_color"] or DEFAULT_COLORS["secondary"]),
                "badge_template_id": str(row["template_id"] or DEFAULT_BADGE["template_id"]),
                "badge_primary": str(row["badge_primary"] or row["primary_color"] or DEFAULT_BADGE["primary"]),
                "badge_secondary": str(row["badge_secondary"] or row["secondary_color"] or DEFAULT_BADGE["secondary"]),
                "badge_border": str(row["badge_border"] or DEFAULT_BADGE["border"]),
                "players_count": int(row["players_count"] or 0),
                "avg_ovr": float(row["avg_ovr"] or 0.0),
            }
        )
    return clubs


def list_club_players(conn: sqlite3.Connection, club_id: str, save_id: int | None = None) -> List[dict]:
    if save_id is None:
        attribute_rows = conn.execute(
            """
            SELECT p.id AS player_id, pa.key, pa.value
            FROM players p
            LEFT JOIN player_attributes pa ON pa.player_id = p.id
            WHERE p.club_id = ?
            """,
            (club_id,),
        ).fetchall()
    else:
        attribute_rows = conn.execute(
            """
            SELECT p.id AS player_id, pa.key, COALESCE(spa.value, pa.value) AS value
            FROM players p
            LEFT JOIN player_attributes pa ON pa.player_id = p.id
            LEFT JOIN save_player_attributes spa
              ON spa.save_id = ? AND spa.player_id = p.id AND spa.key = pa.key
            LEFT JOIN save_player_club spcl
              ON spcl.save_id = ? AND spcl.player_id = p.id
            WHERE COALESCE(spcl.club_id, p.club_id) = ?
            """,
            (int(save_id), int(save_id), club_id),
        ).fetchall()
    attrs_by_player: Dict[str, Dict[str, float]] = {}
    for row in attribute_rows:
        if row["key"] is None:
            continue
        attrs_by_player.setdefault(str(row["player_id"]), {})[str(row["key"])] = float(row["value"])
    if save_id is None:
        rows = conn.execute(
            """
            SELECT p.id, p.name, p.position, p.ovr, p.age, pc.current_stamina
                 , p.preferred_foot
            FROM players p
            LEFT JOIN player_condition pc ON pc.player_id = p.id
            WHERE p.club_id = ?
            ORDER BY CASE p.position
                WHEN 'GK' THEN 1
                WHEN 'LB' THEN 2
                WHEN 'CB' THEN 3
                WHEN 'RB' THEN 4
                WHEN 'DM' THEN 5
                WHEN 'CM' THEN 6
                WHEN 'AM' THEN 7
                WHEN 'LW' THEN 8
                WHEN 'ST' THEN 9
                WHEN 'RW' THEN 10
                ELSE 99
            END, p.id
            """,
            (club_id,),
        ).fetchall()
    else:
        seed_save_player_status_defaults(conn, save_id)
        rows = conn.execute(
            """
            SELECT p.id, p.name, p.position, p.ovr, p.age, spc.current_stamina,
                   p.preferred_foot,
                   sps.yellow_card_count,
                   sps.suspension_matches_remaining,
                   sps.suspension_reason,
                   sps.injury_days_remaining,
                   sps.injury_count
            FROM players p
            LEFT JOIN save_player_condition spc
              ON spc.player_id = p.id AND spc.save_id = ?
            LEFT JOIN save_player_status sps
              ON sps.player_id = p.id AND sps.save_id = ?
            LEFT JOIN save_player_club spcl
              ON spcl.player_id = p.id AND spcl.save_id = ?
            WHERE COALESCE(spcl.club_id, p.club_id) = ?
            ORDER BY CASE p.position
                WHEN 'GK' THEN 1
                WHEN 'LB' THEN 2
                WHEN 'CB' THEN 3
                WHEN 'RB' THEN 4
                WHEN 'DM' THEN 5
                WHEN 'CM' THEN 6
                WHEN 'AM' THEN 7
                WHEN 'LW' THEN 8
                WHEN 'ST' THEN 9
                WHEN 'RW' THEN 10
                ELSE 99
            END, p.id
            """,
            (int(save_id), int(save_id), int(save_id), club_id),
        ).fetchall()
    alt_pos_rows = conn.execute(
        "SELECT player_id, position FROM player_alt_positions WHERE player_id IN "
        f"(SELECT id FROM players WHERE club_id = ?)",
        (club_id,),
    ).fetchall()
    alt_positions_by_player: Dict[str, List[str]] = {}
    for ap_row in alt_pos_rows:
        alt_positions_by_player.setdefault(str(ap_row["player_id"]), []).append(str(ap_row["position"]))
    return [
        {
            "id": str(row["id"]),
            "name": str(row["name"]),
            "position": str(row["position"]),
            "ovr": int(row["ovr"]),
            "age": int(row["age"]) if row["age"] is not None else 22,
            "preferred_foot": normalize_preferred_foot(row["preferred_foot"]),
            "current_stamina": float(row["current_stamina"]) if row["current_stamina"] is not None else 100.0,
            "yellow_card_count": int(row["yellow_card_count"] or 0) if "yellow_card_count" in row.keys() else 0,
            "suspension_matches_remaining": int(row["suspension_matches_remaining"] or 0) if "suspension_matches_remaining" in row.keys() else 0,
            "suspension_reason": str(row["suspension_reason"] or "") if "suspension_reason" in row.keys() else "",
            "injury_days_remaining": int(row["injury_days_remaining"] or 0) if "injury_days_remaining" in row.keys() else 0,
            "injury_count": int(row["injury_count"] or 0) if "injury_count" in row.keys() else 0,
            "available": (
                (int(row["suspension_matches_remaining"] or 0) if "suspension_matches_remaining" in row.keys() else 0) <= 0
                and (int(row["injury_days_remaining"] or 0) if "injury_days_remaining" in row.keys() else 0) <= 0
            ),
            "attributes": merge_player_attributes(
                int(row["ovr"]),
                str(row["position"]),
                dict(attrs_by_player.get(str(row["id"]), {})),
                player_id=str(row["id"]),
                name=str(row["name"]),
            ),
            "alt_positions": list(alt_positions_by_player.get(str(row["id"]), [])),
        }
        for row in rows
    ]


def _season_player_totals(conn: sqlite3.Connection, save_id: int) -> Dict[str, Dict[str, int]]:
    rows = conn.execute(
        """
        SELECT report_json
        FROM fixtures
        WHERE save_id = ? AND played = 1 AND report_json IS NOT NULL
        """,
        (int(save_id),),
    ).fetchall()
    totals: Dict[str, Dict[str, int]] = {}
    for row in rows:
        try:
            report = json.loads(str(row["report_json"]))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        player_stats = report.get("player_stats", {})
        for player_id, stats in player_stats.items():
            if not isinstance(stats, dict):
                continue
            minutes = float(stats.get("minutes", 0.0) or 0.0)
            if minutes <= 0.01:
                continue
            entry = totals.setdefault(str(player_id), {"apps": 0, "goals": 0, "assists": 0})
            entry["apps"] += 1
            entry["goals"] += int(float(stats.get("goals", 0.0) or 0.0))
            entry["assists"] += int(float(stats.get("assists", 0.0) or 0.0))
    return totals


def _report_player_rating_from_stats(stats: dict) -> float:
    minutes = float(stats.get("minutes", 0.0) or 0.0)
    if minutes <= 0.01:
        return 0.0
    rating = 6.0
    rating += float(stats.get("goals", 0.0) or 0.0) * 0.75
    rating += float(stats.get("assists", 0.0) or 0.0) * 0.45
    rating += float(stats.get("shots_on_target", 0.0) or 0.0) * 0.08
    rating += float(stats.get("tackles", 0.0) or 0.0) * 0.08
    rating += float(stats.get("interceptions", 0.0) or 0.0) * 0.08
    rating += float(stats.get("clearances", 0.0) or 0.0) * 0.04
    rating += float(stats.get("goalkeeper_saves", 0.0) or 0.0) * 0.18
    rating -= float(stats.get("goalkeeper_goals_conceded", 0.0) or 0.0) * 0.18
    rating -= float(stats.get("yellow_cards", 0.0) or 0.0) * 0.2
    rating -= float(stats.get("red_cards", 0.0) or 0.0) * 1.0
    attempts = float(stats.get("passes_attempted", 0.0) or 0.0)
    if attempts >= 8.0:
        completed = float(stats.get("passes_completed", 0.0) or 0.0)
        rating += ((completed / max(1.0, attempts)) - 0.72) * 0.9
    return max(1.0, min(10.0, round(rating, 2)))


def _season_player_rating_form(conn: sqlite3.Connection, save_id: int) -> Dict[str, Dict[str, object]]:
    player_club_rows = conn.execute("SELECT id, club_id FROM players").fetchall()
    club_by_player = {str(row["id"]): str(row["club_id"]) for row in player_club_rows}
    rows = conn.execute(
        """
        SELECT id, fixture_date, home_club_id, away_club_id, report_json
        FROM fixtures
        WHERE save_id = ? AND played = 1 AND report_json IS NOT NULL AND report_json != ''
        ORDER BY fixture_date, id
        """,
        (int(save_id),),
    ).fetchall()
    form_by_player: Dict[str, List[dict]] = {}
    for row in rows:
        try:
            report = json.loads(str(row["report_json"]))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        player_stats = report.get("player_stats", {})
        if not isinstance(player_stats, dict):
            continue
        home = report.get("home", {}) if isinstance(report.get("home"), dict) else {}
        away = report.get("away", {}) if isinstance(report.get("away"), dict) else {}
        home_id = str(home.get("id") or row["home_club_id"])
        away_id = str(away.get("id") or row["away_club_id"])
        home_name = str(home.get("name") or row["home_club_id"])
        away_name = str(away.get("name") or row["away_club_id"])
        fixture_label = f"{home_name} vs {away_name}"
        for player_id, stats in player_stats.items():
            if not isinstance(stats, dict) or float(stats.get("minutes", 0.0) or 0.0) <= 0.01:
                continue
            side = str(stats.get("side") or "")
            if not side:
                players = report.get("players", {})
                if isinstance(players, dict):
                    if any(str(player.get("id")) == str(player_id) for player in players.get("home", []) if isinstance(player, dict)):
                        side = "home"
                    elif any(str(player.get("id")) == str(player_id) for player in players.get("away", []) if isinstance(player, dict)):
                        side = "away"
            if not side:
                club_id = club_by_player.get(str(player_id))
                if club_id == home_id:
                    side = "home"
                elif club_id == away_id:
                    side = "away"
            opponent_id = away_id if side == "home" else home_id if side == "away" else ""
            opponent_name = away_name if side == "home" else home_name if side == "away" else ""
            entry = {
                "fixture_id": int(row["id"]),
                "fixture_label": fixture_label,
                "fixture_date": str(row["fixture_date"] or ""),
                "fixture_date_label": format_game_date(str(row["fixture_date"] or "")),
                "opponent_id": opponent_id,
                "opponent_name": opponent_name,
                "rating": _report_player_rating_from_stats(stats),
                "minutes": float(stats.get("minutes", 0.0) or 0.0),
            }
            form_by_player.setdefault(str(player_id), []).append(entry)
    result: Dict[str, Dict[str, object]] = {}
    for player_id, entries in form_by_player.items():
        ratings = [float(entry["rating"]) for entry in entries if float(entry.get("rating", 0.0) or 0.0) > 0.0]
        recent = entries[-5:]
        recent_ratings = [float(entry["rating"]) for entry in recent if float(entry.get("rating", 0.0) or 0.0) > 0.0]
        result[player_id] = {
            "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0.0,
            "recent_form_rating": round(sum(recent_ratings) / len(recent_ratings), 2) if recent_ratings else 0.0,
            "recent_ratings": recent,
        }
    return result


def load_app_options(conn: sqlite3.Connection) -> Dict[str, str]:
    rows = conn.execute("SELECT key, value FROM app_options").fetchall()
    options = dict(DEFAULT_APP_OPTIONS)
    for row in rows:
        options[str(row["key"])] = str(row["value"])
    return options


def list_option_choices(conn: sqlite3.Connection, option_key: str) -> List[dict]:
    rows = conn.execute(
        """
        SELECT value, label
        FROM option_choices
        WHERE option_key = ?
        ORDER BY sort_order, label
        """,
        (option_key,),
    ).fetchall()
    return [{"value": str(row["value"]), "label": str(row["label"])} for row in rows]


def save_app_option(conn: sqlite3.Connection, option_key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO app_options (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """,
        (option_key, value),
    )


def get_current_day(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT value FROM metadata WHERE key = 'current_day'").fetchone()
    if row is None:
        return 0
    return int(row["value"])


def set_current_day(conn: sqlite3.Connection, current_day: int) -> None:
    set_metadata(conn, "current_day", str(int(current_day)))


def get_save_current_day(conn: sqlite3.Connection, save_id: int) -> int:
    row = conn.execute("SELECT current_day FROM saves WHERE id = ?", (int(save_id),)).fetchone()
    if row is None:
        return 0
    return int(row["current_day"] or 0)


def get_metadata(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
    if row is None:
        return None
    return str(row["value"])


def set_metadata(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO metadata (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """,
        (key, value),
    )


def load_player_condition(conn: sqlite3.Connection, player_id: str) -> float | None:
    row = conn.execute(
        "SELECT current_stamina FROM player_condition WHERE player_id = ?",
        (player_id,),
    ).fetchone()
    if row is None:
        return None
    return float(row["current_stamina"])


def load_save_player_condition(conn: sqlite3.Connection, save_id: int, player_id: str) -> float | None:
    row = conn.execute(
        "SELECT current_stamina FROM save_player_condition WHERE save_id = ? AND player_id = ?",
        (int(save_id), player_id),
    ).fetchone()
    if row is None:
        return None
    return float(row["current_stamina"])


def save_player_condition(conn: sqlite3.Connection, player_id: str, stamina: float, current_day: int) -> None:
    conn.execute(
        """
        INSERT INTO player_condition (player_id, current_stamina, updated_day)
        VALUES (?, ?, ?)
        ON CONFLICT(player_id) DO UPDATE SET
            current_stamina=excluded.current_stamina,
            updated_day=excluded.updated_day
        """,
        (player_id, float(stamina), int(current_day)),
    )


def save_save_player_condition(conn: sqlite3.Connection, save_id: int, player_id: str, stamina: float, current_day: int) -> None:
    conn.execute(
        """
        INSERT INTO save_player_condition (save_id, player_id, current_stamina, updated_day)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(save_id, player_id) DO UPDATE SET
            current_stamina=excluded.current_stamina,
            updated_day=excluded.updated_day
        """,
        (int(save_id), player_id, float(stamina), int(current_day)),
    )


def seed_save_player_condition_from_global(conn: sqlite3.Connection, save_id: int, clubs: Dict[str, Club], current_day: int) -> None:
    row = conn.execute(
        "SELECT COUNT(*) AS count FROM save_player_condition WHERE save_id = ?",
        (int(save_id),),
    ).fetchone()
    if row is not None and int(row["count"] or 0) > 0:
        return
    for club in clubs.values():
        for player in club.players:
            saved = load_player_condition(conn, player.id)
            stamina = player.current_stamina if saved is None else float(saved)
            save_save_player_condition(conn, save_id, player.id, stamina, current_day)


def seed_save_player_condition_defaults(conn: sqlite3.Connection, save_id: int) -> None:
    row = conn.execute(
        "SELECT COUNT(*) AS count FROM save_player_condition WHERE save_id = ?",
        (int(save_id),),
    ).fetchone()
    if row is not None and int(row["count"] or 0) > 0:
        return
    current_day = get_save_current_day(conn, save_id)
    conn.execute(
        """
        INSERT INTO save_player_condition (save_id, player_id, current_stamina, updated_day)
        SELECT ?, p.id, 100.0, ?
        FROM players p
        """,
        (int(save_id), int(current_day)),
    )


def seed_save_player_status_defaults(conn: sqlite3.Connection, save_id: int) -> None:
    row = conn.execute(
        "SELECT COUNT(*) AS count FROM save_player_status WHERE save_id = ?",
        (int(save_id),),
    ).fetchone()
    if row is not None and int(row["count"] or 0) > 0:
        return
    conn.execute(
        """
        INSERT INTO save_player_status (
            save_id, player_id, yellow_card_count,
            suspension_matches_remaining, suspension_reason, injury_days_remaining, injury_count
        )
        SELECT ?, p.id, 0, 0, '', 0, 0
        FROM players p
        """,
        (int(save_id),),
    )


def seed_save_training_defaults(conn: sqlite3.Connection, save_id: int, club_id: str | None = None) -> None:
    if club_id is None:
        club_rows = conn.execute("SELECT DISTINCT club_id FROM players").fetchall()
        club_ids = [str(row["club_id"]) for row in club_rows]
    else:
        club_ids = [str(club_id)]
    for target_club_id in club_ids:
        conn.execute(
            """
            INSERT INTO save_training_settings (save_id, club_id, team_focus, intensity, updated_day)
            VALUES (?, ?, 'balanced', 'normal', 0)
            ON CONFLICT(save_id, club_id) DO NOTHING
            """,
            (int(save_id), target_club_id),
        )
    players = conn.execute(
        """
        SELECT p.id, p.name, p.position, p.ovr
        FROM players p
        WHERE ? IS NULL OR p.club_id = ?
        """,
        (club_id, club_id),
    ).fetchall()
    if not players:
        return
    attr_rows = conn.execute("SELECT player_id, key, value FROM player_attributes").fetchall()
    attrs_by_player: Dict[str, Dict[str, float]] = {}
    for row in attr_rows:
        attrs_by_player.setdefault(str(row["player_id"]), {})[str(row["key"])] = float(row["value"])
    entries = []
    for row in players:
        profile = PlayerProfile(
            id=str(row["id"]),
            name=str(row["name"]),
            position=str(row["position"]),
            ovr=int(row["ovr"]),
            attributes=merge_player_attributes(
                int(row["ovr"]),
                str(row["position"]),
                attrs_by_player.get(str(row["id"]), {}),
                player_id=str(row["id"]),
                name=str(row["name"]),
            ),
        )
        entries.append((int(save_id), profile.id, default_player_training_focus(profile), 0))
    conn.executemany(
        """
        INSERT INTO save_player_training (save_id, player_id, focus, updated_day)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(save_id, player_id) DO NOTHING
        """,
        entries,
    )


def load_save_training(conn: sqlite3.Connection, save_id: int, club_id: str) -> dict:
    seed_save_training_defaults(conn, save_id, club_id)
    row = conn.execute(
        """
        SELECT team_focus, intensity, updated_day
        FROM save_training_settings
        WHERE save_id = ? AND club_id = ?
        """,
        (int(save_id), str(club_id)),
    ).fetchone()
    player_rows = conn.execute(
        """
        SELECT p.id, COALESCE(spt.focus, 'auto') AS focus
        FROM players p
        LEFT JOIN save_player_training spt
          ON spt.save_id = ? AND spt.player_id = p.id
        LEFT JOIN save_player_club spcl
          ON spcl.save_id = ? AND spcl.player_id = p.id
        WHERE COALESCE(spcl.club_id, p.club_id) = ?
        ORDER BY p.id
        """,
        (int(save_id), int(save_id), str(club_id)),
    ).fetchall()
    return {
        "team_focus": normalize_training_focus(row["team_focus"] if row else "balanced"),
        "intensity": normalize_training_intensity(row["intensity"] if row else "normal"),
        "focus_options": [
            {"value": key, "label": str(value["label"])}
            for key, value in TEAM_TRAINING_FOCUS_OPTIONS.items()
        ],
        "intensity_options": [
            {"value": key, "label": str(value["label"])}
            for key, value in TRAINING_INTENSITY_OPTIONS.items()
        ],
        "player_focus_options": [
            {"value": key, "label": str(value["label"])}
            for key, value in PLAYER_TRAINING_FOCUS_OPTIONS.items()
        ],
        "player_focuses": {
            str(player["id"]): normalize_player_training_focus(player["focus"])
            for player in player_rows
        },
    }


def save_training_settings(conn: sqlite3.Connection, save_id: int, club_id: str, team_focus: str, intensity: str) -> None:
    focus = normalize_training_focus(team_focus)
    normalized_intensity = normalize_training_intensity(intensity)
    conn.execute(
        """
        INSERT INTO save_training_settings (save_id, club_id, team_focus, intensity, updated_day)
        VALUES (?, ?, ?, ?, 0)
        ON CONFLICT(save_id, club_id) DO UPDATE SET
            team_focus=excluded.team_focus,
            intensity=excluded.intensity
        """,
        (int(save_id), str(club_id), focus, normalized_intensity),
    )


def save_player_training_focus(conn: sqlite3.Connection, save_id: int, player_id: str, focus: str) -> None:
    normalized = normalize_player_training_focus(focus)
    conn.execute(
        """
        INSERT INTO save_player_training (save_id, player_id, focus, updated_day)
        VALUES (?, ?, ?, 0)
        ON CONFLICT(save_id, player_id) DO UPDATE SET focus=excluded.focus
        """,
        (int(save_id), str(player_id), normalized),
    )


def _save_training_attribute(conn: sqlite3.Connection, save_id: int, player_id: str, key: str, value: float) -> None:
    conn.execute(
        """
        INSERT INTO save_player_attributes (save_id, player_id, key, value)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(save_id, player_id, key) DO UPDATE SET value=excluded.value
        """,
        (int(save_id), str(player_id), str(key), round(float(value), 3)),
    )


def apply_training_day(conn: sqlite3.Connection, save_id: int, club_id: str, current_day: int, clubs: Dict[str, Club] | None = None) -> dict:
    seed_save_player_condition_defaults(conn, save_id)
    seed_save_player_status_defaults(conn, save_id)
    seed_save_training_defaults(conn, save_id, club_id)
    clubs = clubs if clubs is not None else load_clubs_from_db(conn, save_id=save_id)
    club = clubs.get(str(club_id))
    if club is None:
        return {"players_trained": 0, "attributes_changed": 0, "stamina_cost": 0.0}
    training = load_save_training(conn, save_id, club_id)
    team_focus = normalize_training_focus(training["team_focus"])
    intensity = normalize_training_intensity(training["intensity"])
    team_attrs = set(TEAM_TRAINING_FOCUS_OPTIONS[team_focus]["attributes"])
    players_trained = 0
    attributes_changed = 0
    stamina_cost = 0.0
    notable_gains: List[dict] = []
    pending_attr_writes: list[tuple] = []
    pending_stamina_writes: list[tuple] = []
    for player in club.players:
        if not player.is_available:
            continue
        player_focus = normalize_player_training_focus(training["player_focuses"].get(player.id), player)
        focus_attrs = tuple(PLAYER_TRAINING_FOCUS_OPTIONS[player_focus]["attributes"]) or tuple(team_attrs)
        attrs_to_train = sorted(set(team_attrs).union(focus_attrs))
        for attr in attrs_to_train:
            current = float(player.attributes.get(attr, player.ovr))
            gain = training_attribute_gain(
                player,
                attr,
                focus_match=attr in focus_attrs,
                intensity=intensity,
                current_day=int(current_day),
            )
            if gain <= 0.0:
                continue
            updated = min(99.0, current + gain)
            pending_attr_writes.append((int(save_id), str(player.id), str(attr), round(float(updated), 3)))
            if int(updated) > int(current) and int(updated) % 5 == 0:
                notable_gains.append({
                    "player_name": player.name,
                    "attr": attr,
                    "old_val": int(current),
                    "new_val": int(updated),
                })
            player.attributes[attr] = updated
            attributes_changed += 1
        delta = training_stamina_delta(player, team_focus, intensity)
        if delta < 0:
            next_stamina = max(35.0, player.current_stamina + delta)
            stamina_cost += max(0.0, player.current_stamina - next_stamina)
            player.current_stamina = next_stamina
            pending_stamina_writes.append((int(save_id), player.id, round(next_stamina, 2), int(current_day)))
        players_trained += 1
    if pending_attr_writes:
        conn.executemany(
            """
            INSERT INTO save_player_attributes (save_id, player_id, key, value)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(save_id, player_id, key) DO UPDATE SET value=excluded.value
            """,
            pending_attr_writes,
        )
    if pending_stamina_writes:
        conn.executemany(
            """
            INSERT INTO save_player_condition (save_id, player_id, current_stamina, updated_day)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(save_id, player_id) DO UPDATE SET
                current_stamina=excluded.current_stamina,
                updated_day=excluded.updated_day
            """,
            pending_stamina_writes,
        )
    return {
        "players_trained": players_trained,
        "attributes_changed": attributes_changed,
        "stamina_cost": round(stamina_cost, 2),
        "notable_gains": notable_gains,
    }


def advance_save_player_status_days(conn: sqlite3.Connection, save_id: int, days: int) -> None:
    if days <= 0:
        return
    seed_save_player_status_defaults(conn, save_id)
    conn.execute(
        """
        UPDATE save_player_status
        SET injury_days_remaining = MAX(0, injury_days_remaining - ?)
        WHERE save_id = ?
        """,
        (int(days), int(save_id)),
    )


def _fixture_club_ids(conn: sqlite3.Connection, fixture_id: int) -> tuple[int, str, str] | None:
    row = conn.execute(
        "SELECT save_id, home_club_id, away_club_id FROM fixtures WHERE id = ?",
        (int(fixture_id),),
    ).fetchone()
    if row is None:
        return None
    return int(row["save_id"]), str(row["home_club_id"]), str(row["away_club_id"])


def _decrement_served_suspensions(conn: sqlite3.Connection, save_id: int, club_ids: tuple[str, str]) -> None:
    seed_save_player_status_defaults(conn, save_id)
    conn.execute(
        """
        UPDATE save_player_status
        SET suspension_matches_remaining = MAX(0, suspension_matches_remaining - 1),
            suspension_reason = CASE WHEN suspension_matches_remaining <= 1 THEN '' ELSE suspension_reason END
        WHERE save_id = ?
          AND suspension_matches_remaining > 0
          AND player_id IN (
              SELECT id FROM players WHERE club_id IN (?, ?)
          )
        """,
        (int(save_id), club_ids[0], club_ids[1]),
    )


def apply_match_report_player_status(conn: sqlite3.Connection, save_id: int, report: dict) -> None:
    seed_save_player_status_defaults(conn, save_id)
    player_stats = report.get("player_stats", {})
    if not isinstance(player_stats, dict):
        player_stats = {}
    injuries = report.get("injuries", {})
    if not isinstance(injuries, dict):
        injuries = {}
    for player_id, stats in player_stats.items():
        if not isinstance(stats, dict):
            continue
        yellow_cards = int(float(stats.get("yellow_cards", 0.0) or 0.0))
        straight_red = int(float(stats.get("straight_red_cards", 0.0) or 0.0))
        second_yellow_red = int(float(stats.get("second_yellow_red_cards", 0.0) or 0.0))
        if yellow_cards > 0:
            row = conn.execute(
                "SELECT yellow_card_count FROM save_player_status WHERE save_id = ? AND player_id = ?",
                (int(save_id), str(player_id)),
            ).fetchone()
            current = int(row["yellow_card_count"] or 0) if row is not None else 0
            total = current + yellow_cards
            bans = total // 5
            remaining_yellows = total % 5
            conn.execute(
                """
                INSERT INTO save_player_status (save_id, player_id, yellow_card_count, suspension_matches_remaining, suspension_reason)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(save_id, player_id) DO UPDATE SET
                    yellow_card_count=excluded.yellow_card_count,
                    suspension_matches_remaining=save_player_status.suspension_matches_remaining + excluded.suspension_matches_remaining,
                    suspension_reason=CASE
                        WHEN excluded.suspension_matches_remaining > 0 THEN 'yellow_accumulation'
                        ELSE save_player_status.suspension_reason
                    END
                """,
                (int(save_id), str(player_id), remaining_yellows, bans, "yellow_accumulation" if bans > 0 else ""),
            )
        red_ban = 2 if straight_red > 0 else 1 if second_yellow_red > 0 or int(float(stats.get("red_cards", 0.0) or 0.0)) > 0 else 0
        if red_ban > 0:
            conn.execute(
                """
                UPDATE save_player_status
                SET suspension_matches_remaining = suspension_matches_remaining + ?,
                    suspension_reason = 'red_card'
                WHERE save_id = ? AND player_id = ?
                """,
                (red_ban, int(save_id), str(player_id)),
            )
    for player_id, injury in injuries.items():
        if not isinstance(injury, dict):
            continue
        days = max(1, int(injury.get("days", 1) or 1))
        conn.execute(
            """
            UPDATE save_player_status
            SET injury_days_remaining = MAX(injury_days_remaining, ?),
                injury_count = injury_count + 1
            WHERE save_id = ? AND player_id = ?
            """,
            (days, int(save_id), str(player_id)),
        )


def normalize_new_save_player_condition(conn: sqlite3.Connection, save_id: int) -> None:
    save_row = conn.execute(
        "SELECT current_day FROM saves WHERE id = ?",
        (int(save_id),),
    ).fetchone()
    if save_row is None:
        return
    current_day = int(save_row["current_day"] or 0)
    played_row = conn.execute(
        "SELECT COUNT(*) AS count FROM fixtures WHERE save_id = ? AND played = 1",
        (int(save_id),),
    ).fetchone()
    if played_row is not None and int(played_row["count"] or 0) > 0:
        return
    if current_day != 0:
        avg_row = conn.execute(
            "SELECT AVG(current_stamina) AS avg_stamina FROM save_player_condition WHERE save_id = ?",
            (int(save_id),),
        ).fetchone()
        avg_stamina = float(avg_row["avg_stamina"] or 100.0) if avg_row else 100.0
        if avg_stamina >= 60.0:
            return
        conn.execute(
            """
            UPDATE save_player_condition
            SET current_stamina = MAX(current_stamina, 86.0)
            WHERE save_id = ?
            """,
            (int(save_id),),
        )
        return
    conn.execute(
        """
        UPDATE save_player_condition
        SET current_stamina = 100.0,
            updated_day = 0
        WHERE save_id = ?
        """,
        (int(save_id),),
    )


def add_save_message(
    conn: sqlite3.Connection,
    save_id: int,
    category: str,
    title: str,
    body: str,
    date_text: str,
    severity: str = "info",
    dedupe_key: str | None = None,
) -> int | None:
    dedupe = str(dedupe_key or "")
    if dedupe:
        existing = conn.execute(
            "SELECT id FROM save_messages WHERE save_id = ? AND dedupe_key = ?",
            (int(save_id), dedupe),
        ).fetchone()
        if existing is not None:
            return None
    cursor = conn.execute(
        """
        INSERT INTO save_messages (save_id, category, title, body, date_text, severity, dedupe_key)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(save_id),
            str(category or "info"),
            str(title or "MESSAGE"),
            str(body or ""),
            str(date_text or ""),
            str(severity or "info"),
            dedupe,
        ),
    )
    return int(cursor.lastrowid)


def list_save_messages(conn: sqlite3.Connection, save_id: int, limit: int = 10, offset: int = 0) -> List[dict]:
    rows = conn.execute(
        """
        SELECT id, category, title, body, date_text, severity, created_at, is_read
        FROM save_messages
        WHERE save_id = ?
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        (int(save_id), int(limit), int(offset)),
    ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "category": str(row["category"]),
            "title": str(row["title"]),
            "body": str(row["body"]),
            "date_text": str(row["date_text"]),
            "date_label": format_game_date(str(row["date_text"])) if row["date_text"] else "",
            "severity": str(row["severity"]),
            "created_at": str(row["created_at"]),
            "is_read": bool(row["is_read"]),
        }
        for row in rows
    ]


def count_save_messages(conn: sqlite3.Connection, save_id: int) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM save_messages WHERE save_id = ?", (int(save_id),)).fetchone()
    return int(row["c"]) if row else 0


def count_unread_messages(conn: sqlite3.Connection, save_id: int) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM save_messages WHERE save_id = ? AND is_read = 0", (int(save_id),)).fetchone()
    return int(row["c"]) if row else 0


def mark_message_read(conn: sqlite3.Connection, save_id: int, message_id: int) -> None:
    conn.execute(
        "UPDATE save_messages SET is_read = 1 WHERE id = ? AND save_id = ?",
        (int(message_id), int(save_id)),
    )


def _daily_recovery_for_profile(profile: PlayerProfile) -> float:
    natural_stamina = profile.attributes.get("stamina", 70.0)
    deficit = max(0.0, 100.0 - profile.current_stamina)
    base_recovery = 0.45 + natural_stamina / 160.0
    deficit_factor = max(0.22, min(1.0, deficit / 35.0))
    return base_recovery * deficit_factor


def _advance_club_condition_one_day(clubs: Dict[str, Club]) -> None:
    for club in clubs.values():
        for player in club.players:
            player.current_stamina = min(100.0, player.current_stamina + _daily_recovery_for_profile(player))
            if player.injury_days_remaining > 0:
                player.injury_days_remaining = max(0, player.injury_days_remaining - 1)


def _save_condition_for_clubs(conn: sqlite3.Connection, save_id: int, clubs: Dict[str, Club], current_day: int) -> None:
    conn.executemany(
        """
        INSERT INTO save_player_condition (save_id, player_id, current_stamina, updated_day)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(save_id, player_id) DO UPDATE SET
            current_stamina=excluded.current_stamina,
            updated_day=excluded.updated_day
        """,
        [
            (int(save_id), player.id, round(player.current_stamina, 2), int(current_day))
            for club in clubs.values()
            for player in club.players
        ],
    )


def _create_daily_save_messages(
    conn: sqlite3.Connection,
    save_id: int,
    club_id: str,
    current_date: str,
    training_result: dict,
) -> None:
    next_day = date.fromisoformat(current_date) + timedelta(days=1)
    fixture = conn.execute(
        """
        SELECT f.fixture_date, f.home_club_id, f.away_club_id, hc.name AS home_name, ac.name AS away_name
        FROM fixtures f
        JOIN clubs hc ON hc.id = f.home_club_id
        JOIN clubs ac ON ac.id = f.away_club_id
        WHERE f.save_id = ?
          AND f.played = 0
          AND (f.home_club_id = ? OR f.away_club_id = ?)
          AND f.fixture_date = ?
        ORDER BY f.id
        LIMIT 1
        """,
        (int(save_id), str(club_id), str(club_id), next_day.isoformat()),
    ).fetchone()
    if fixture is not None:
        add_save_message(
            conn,
            save_id,
            "matchday",
            "MATCH TOMORROW",
            f"{fixture['home_name']} vs {fixture['away_name']} is scheduled for {format_game_date(str(fixture['fixture_date']))}.",
            current_date,
            "warning",
            f"match_tomorrow:{fixture['fixture_date']}:{fixture['home_club_id']}:{fixture['away_club_id']}",
        )

    for gain in list(training_result.get("notable_gains", [])):
        attr_label = str(gain["attr"]).replace("_", " ").title()
        add_save_message(
            conn,
            save_id,
            "training",
            "ATTRIBUTE BOOST",
            f"{gain['player_name']} improved {attr_label} to {gain['new_val']}.",
            current_date,
            "success",
            f"training_gain:{current_date}:{gain['player_name']}:{gain['attr']}",
        )

    tired_rows = conn.execute(
        """
        SELECT p.name, spc.current_stamina
        FROM players p
        JOIN save_player_condition spc ON spc.player_id = p.id AND spc.save_id = ?
        WHERE p.club_id = ? AND spc.current_stamina < 55.0
        ORDER BY spc.current_stamina ASC, p.name
        LIMIT 4
        """,
        (int(save_id), str(club_id)),
    ).fetchall()
    if tired_rows:
        names = ", ".join(str(row["name"]) for row in tired_rows[:3])
        add_save_message(
            conn,
            save_id,
            "medical",
            "PLAYERS NEED REST",
            f"{names} are showing fatigue risk. Consider lighter training or rotation.",
            current_date,
            "warning",
            f"tired:{current_date}",
        )


def complete_season_if_due(conn: sqlite3.Connection, save_id: int) -> bool:
    save_row = conn.execute(
        "SELECT season_year, saves.current_date AS current_date, season_completed FROM saves WHERE id = ?",
        (int(save_id),),
    ).fetchone()
    if save_row is None or int(save_row["season_completed"] or 0) == 1:
        return False
    counts = conn.execute(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN played = 0 THEN 1 ELSE 0 END) AS unplayed,
               MAX(fixture_date) AS final_date
        FROM fixtures
        WHERE save_id = ?
        """,
        (int(save_id),),
    ).fetchone()
    if counts is None or int(counts["total"] or 0) == 0 or int(counts["unplayed"] or 0) > 0:
        return False
    current_date = date.fromisoformat(str(save_row["current_date"]))
    final_date = date.fromisoformat(str(counts["final_date"]))
    if current_date <= final_date:
        return False
    standings = load_save_standings(conn, save_id)
    if not standings:
        return False
    champion = standings[0]
    title = f"{str(champion['club_name']).upper()} CHAMPIONS"
    body = (
        f"{champion['club_name']} win the league with {champion['points']} points, "
        f"{champion['wins']} wins and a {champion['goal_difference']:+d} goal difference."
    )
    add_save_message(
        conn,
        save_id,
        "season",
        title,
        body,
        str(save_row["current_date"]),
        "success",
        f"season_complete:{save_row['season_year']}",
    )
    from .promotion import apply_promotion_relegation
    apply_promotion_relegation(conn, save_id, int(save_row["season_year"]))
    conn.execute("UPDATE saves SET season_completed = 1 WHERE id = ?", (int(save_id),))
    return True


def start_next_season_if_ready(conn: sqlite3.Connection, save_id: int) -> bool:
    row = conn.execute(
        "SELECT league_id, season_year, season_completed FROM saves WHERE id = ?",
        (int(save_id),),
    ).fetchone()
    if row is None or int(row["season_completed"] or 0) != 1:
        return False
    next_year = int(row["season_year"] or current_season_year()) + 1
    start_date = season_start_date(next_year)
    conn.execute("DELETE FROM fixtures WHERE save_id = ?", (int(save_id),))
    conn.execute(
        """
        UPDATE saves
        SET season_year = ?, current_day = 0, current_date = ?, season_completed = 0
        WHERE id = ?
        """,
        (next_year, start_date.isoformat(), int(save_id)),
    )
    conn.execute(
        """
        UPDATE save_player_status
        SET yellow_card_count = 0,
            suspension_reason = CASE WHEN suspension_matches_remaining > 0 THEN suspension_reason ELSE '' END
        WHERE save_id = ?
        """,
        (int(save_id),),
    )
    _seed_save_league_clubs(conn, save_id, next_year)
    all_leagues = conn.execute("SELECT id FROM leagues").fetchall()
    for league_row in all_leagues:
        _seed_fixtures_for_save(conn, save_id, str(league_row["id"]), next_year)
    from .cups import seed_cup_for_save, CUP_CONFIGS
    for cup_key in CUP_CONFIGS:
        seed_cup_for_save(conn, save_id, cup_key, next_year)
    add_save_message(
        conn,
        save_id,
        "season",
        f"{next_year} SEASON READY",
        "The new season fixture list has been generated. The squad reports back on 07 Jul.",
        start_date.isoformat(),
        "info",
        f"season_start:{next_year}",
    )
    return True


def trigger_totw_for_match_day(conn: sqlite3.Connection, save_id: int, fixture_date: str, managed_club_id: str | None) -> None:
    """Call after all fixtures on a match day are saved (e.g. after forfeit).
    Uses virtual date = fixture_date + 2 so the 2-day-later check triggers immediately."""
    try:
        from datetime import date as _d, timedelta as _td
        virtual_date = (_d.fromisoformat(fixture_date) + _td(days=2)).isoformat()
        _maybe_generate_team_of_the_week(conn, save_id, virtual_date, managed_club_id)
    except Exception:
        pass


def _maybe_generate_team_of_the_week(
    conn: sqlite3.Connection,
    save_id: int,
    current_date: str,
    managed_club_id: str | None,
) -> None:
    """2 days after every fully-completed matchweek, post a TOTW news message."""
    from datetime import date as _date, timedelta as _td
    try:
        today = _date.fromisoformat(current_date)
    except ValueError:
        return
    two_days_ago = (today - _td(days=2)).isoformat()
    # Find the last completed match_day where all fixtures are played and last date = two_days_ago
    mw_row = conn.execute(
        """
        SELECT match_day, MAX(fixture_date) AS last_date, COUNT(*) AS total,
               SUM(CASE WHEN played = 1 THEN 1 ELSE 0 END) AS played_count
        FROM fixtures
        WHERE save_id = ?
        GROUP BY match_day
        HAVING total = played_count AND last_date = ?
        ORDER BY match_day DESC
        LIMIT 1
        """,
        (int(save_id), two_days_ago),
    ).fetchone()
    if not mw_row:
        return
    match_day = int(mw_row["match_day"])
    dedupe_key = f"totw:{save_id}:{match_day}"
    if conn.execute(
        "SELECT id FROM save_messages WHERE save_id = ? AND dedupe_key = ?",
        (int(save_id), dedupe_key),
    ).fetchone():
        return

    # Load all fixture reports for this match_day
    fixture_rows = conn.execute(
        "SELECT report_json FROM fixtures WHERE save_id = ? AND match_day = ? AND played = 1 AND report_json IS NOT NULL",
        (int(save_id), match_day),
    ).fetchall()

    # Build player → best rating from this matchweek + their position + name + club
    player_info: Dict[str, Dict] = {}
    for fr_row in fixture_rows:
        try:
            report = json.loads(str(fr_row["report_json"]))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        home_id = str(report.get("home", {}).get("id", ""))
        away_id = str(report.get("away", {}).get("id", ""))
        for side_key, club_id in (("home", home_id), ("away", away_id)):
            side_players = report.get("players", {}).get(side_key, [])
            for pl in side_players:
                pid = str(pl.get("id", ""))
                pos = str(pl.get("position", "MF"))
                name = str(pl.get("name", pid))
                stats = report.get("player_stats", {}).get(pid, {})
                rating = _report_player_rating_from_stats(stats)
                if rating <= 0.01:
                    continue
                prev = player_info.get(pid)
                if prev is None or rating > prev["rating"]:
                    player_info[pid] = {
                        "id": pid,
                        "name": name,
                        "position": pos,
                        "rating": rating,
                        "club_id": club_id,
                    }

    if not player_info:
        return

    # Pick best players by TOTW formation: GK(1) CB(2) FB(2) DM(1) CM/AM(2) W(2) ST(2)
    _POS_SLOT = {
        "GK": "GK",
        "CB": "CB", "LB": "FB", "RB": "FB",
        "DM": "DM",
        "CM": "CM", "AM": "CM",
        "LW": "WG", "RW": "WG",
        "ST": "ST",
    }
    _SLOT_QUOTA = {"GK": 1, "CB": 2, "FB": 2, "DM": 1, "CM": 2, "WG": 2, "ST": 2}
    slots: Dict[str, list] = {s: [] for s in _SLOT_QUOTA}
    ranked = sorted(player_info.values(), key=lambda p: p["rating"], reverse=True)
    for p in ranked:
        slot = _POS_SLOT.get(str(p["position"]).upper(), "CM")
        quota = _SLOT_QUOTA.get(slot, 2)
        if len(slots[slot]) < quota:
            slots[slot].append(p)

    totw_players = [p for pl in slots.values() for p in pl]
    if not totw_players:
        return

    club_names: Dict[str, str] = {}
    club_badge_info: Dict[str, dict] = {}
    for row in conn.execute("""
        SELECT c.id, c.name,
               cb.template_id AS badge_template_id,
               cb.primary_color AS badge_primary,
               cb.secondary_color AS badge_secondary,
               cb.border_color AS badge_border
        FROM clubs c
        LEFT JOIN club_badges cb ON cb.club_id = c.id
    """).fetchall():
        cid = str(row["id"])
        club_names[cid] = str(row["name"])
        club_badge_info[cid] = {
            "badge_template_id": str(row["badge_template_id"] or "1"),
            "badge_primary": str(row["badge_primary"] or "#2E3A6A"),
            "badge_secondary": str(row["badge_secondary"] or "#F5F5F5"),
            "badge_border": str(row["badge_border"] or "#F5F5F5"),
        }

    # Load OVR for players
    player_ovr_map: Dict[str, int] = {}
    all_pids = [p["id"] for p in totw_players]
    if all_pids:
        placeholders = ",".join("?" * len(all_pids))
        for row in conn.execute(f"SELECT id, ovr FROM players WHERE id IN ({placeholders})", all_pids).fetchall():
            player_ovr_map[str(row["id"])] = int(row["ovr"])

    # Build structured body for visual rendering
    managed_in_totw = [p for p in totw_players if str(p.get("club_id", "")) == str(managed_club_id or "")]
    players_for_body = []
    for slot_name in ("GK", "FB", "CB", "DM", "CM", "WG", "ST"):
        for p in slots.get(slot_name, []):
            cid = str(p.get("club_id", ""))
            club = club_names.get(cid, "")
            badge = club_badge_info.get(cid, {})
            players_for_body.append({
                "id": str(p["id"]),
                "name": str(p["name"]),
                "position": str(p["position"]),
                "rating": round(float(p["rating"]), 1),
                "ovr": player_ovr_map.get(str(p["id"]), 70),
                "club": club,
                "club_id": cid,
                "badge_template_id": badge.get("badge_template_id", "1"),
                "badge_primary": badge.get("badge_primary", "#2E3A6A"),
                "badge_secondary": badge.get("badge_secondary", "#F5F5F5"),
                "badge_border": badge.get("badge_border", "#F5F5F5"),
                "slot": slot_name,
                "is_managed": cid == str(managed_club_id or ""),
            })
    body = json.dumps({"type": "totw", "match_day": match_day, "players": players_for_body})
    title = f"TEAM OF THE WEEK — MATCHWEEK {match_day}"
    add_save_message(
        conn, save_id, "totw",
        title, body, current_date, "info", dedupe_key,
    )


def advance_save_one_day(conn: sqlite3.Connection, save_id: int, managed_club_id: str | None) -> dict:
    if start_next_season_if_ready(conn, save_id):
        conn.commit()
        row = conn.execute("SELECT current_day, saves.current_date AS current_date, season_year FROM saves WHERE id = ?", (int(save_id),)).fetchone()
        return {
            "current_day": int(row["current_day"]),
            "current_date": str(row["current_date"]),
            "season_year": int(row["season_year"]),
            "season_started": True,
        }
    save_row = conn.execute("SELECT current_day FROM saves WHERE id = ?", (int(save_id),)).fetchone()
    if save_row is None:
        return {"current_day": 0, "current_date": "", "season_year": 0}
    next_day = int(save_row["current_day"]) + 1
    clubs = load_clubs_from_db(conn, save_id=save_id)
    training_result = {"players_trained": 0, "attributes_changed": 0, "stamina_cost": 0.0}
    if managed_club_id:
        training_result = apply_training_day(conn, save_id, str(managed_club_id), next_day, clubs=clubs)
    _advance_club_condition_one_day(clubs)
    advance_save_player_status_days(conn, save_id, 1)
    _save_condition_for_clubs(conn, save_id, clubs, next_day)
    set_save_current_day(conn, save_id, next_day)
    updated = conn.execute(
        "SELECT current_day, saves.current_date AS current_date, season_year FROM saves WHERE id = ?",
        (int(save_id),),
    ).fetchone()
    current_date_str = str(updated["current_date"])
    season_year_val = int(updated["season_year"])

    # Simulate all non-user AI fixtures scheduled for today (batch — 3 DB ops total)
    from .simulation import simulate_all_ai_fixtures, simulate_ai_transfers
    managed_id_str = str(managed_club_id or "")
    ai_fixture_rows = conn.execute(
        """
        SELECT id, home_club_id, away_club_id, competition_id FROM fixtures
        WHERE save_id = ? AND played = 0 AND fixture_date = ?
          AND home_club_id != ? AND away_club_id != ?
        """,
        (save_id, current_date_str, managed_id_str, managed_id_str),
    ).fetchall()
    simulate_all_ai_fixtures(conn, save_id, ai_fixture_rows, season_year_val)

    # Weekly AI transfers every 7 days
    if next_day % 7 == 0:
        simulate_ai_transfers(conn, save_id)
    from .cups import advance_cup_rounds
    advance_cup_rounds(conn, save_id, current_date_str)

    _create_daily_save_messages(conn, save_id, str(managed_club_id or ""), current_date_str, training_result)
    _maybe_generate_team_of_the_week(conn, save_id, current_date_str, managed_club_id)
    completed = complete_season_if_due(conn, save_id)
    for scout_result in check_and_complete_scout_tasks(conn, save_id, current_date_str):
        pname = str(scout_result["player_name"]).upper()
        gain = int(scout_result["gain"])
        new_pct = int(scout_result["new_pct"])
        add_save_message(
            conn, save_id, "scouting",
            f"SCOUT REPORT: {pname}",
            f"Your scout returned with new info on {pname}. Attribute knowledge +{gain}% (now {new_pct}% known).",
            current_date_str,
            severity="info",
            dedupe_key=f"scout:{save_id}:{scout_result['player_id']}:{current_date_str}",
        )

    if managed_club_id:
        window_open, window_type = get_transfer_window_status(current_date_str)
        standings = load_save_standings(conn, save_id)
        club_pos = next((int(s.get("position", 4)) for s in standings if str(s.get("club_id", "")) == str(managed_club_id)), 4)
        if window_open:
            _ai_populate_transfer_market(conn, save_id, current_date_str, window_type, season_year_val, str(managed_club_id))
            resolve_pending_transfer_offers(conn, save_id, current_date_str, club_pos)
        club_row = conn.execute("SELECT name FROM clubs WHERE id = ?", (str(managed_club_id),)).fetchone()
        club_name = str(club_row["name"]) if club_row else str(managed_club_id)
        resolve_pending_player_negotiations(conn, save_id, current_date_str, str(managed_club_id), club_name, club_pos)
        _ai_make_offers_on_user_listings(conn, save_id, current_date_str, str(managed_club_id), season_year_val)
        # Weekly finances: every 7 days apply sponsor income and wages
        if next_day % 7 == 0:
            apply_weekly_finances(conn, save_id, str(managed_club_id), current_date_str, club_pos)

    conn.commit()
    return {
        "current_day": int(updated["current_day"]),
        "current_date": current_date_str,
        "season_year": season_year_val,
        "season_completed": completed,
        "training": training_result,
    }


def maybe_migrate_legacy_condition_json(conn: sqlite3.Connection, json_path: Path, clubs: Dict[str, Club]) -> bool:
    if not json_path.exists():
        return False
    raw = json.loads(json_path.read_text(encoding="utf-8"))
    current_day = int(raw.get("current_day", 0))
    players = raw.get("players", {})
    for club in clubs.values():
        for player in club.players:
            value = players.get(player.id, {}).get("current_stamina")
            if value is not None:
                save_player_condition(conn, player.id, float(value), current_day)
    set_current_day(conn, current_day)
    conn.commit()
    return True


def list_save_games(conn: sqlite3.Connection) -> List[dict]:
    rows = conn.execute(
        """
        SELECT s.id, m.name AS manager_name, l.name AS league_name, c.name AS club_name, s.created_at
        FROM saves s
        JOIN managers m ON m.id = s.manager_id
        JOIN leagues l ON l.id = s.league_id
        JOIN clubs c ON c.id = s.club_id
        ORDER BY s.id DESC
        """
    ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "manager_name": str(row["manager_name"]),
            "league_name": str(row["league_name"]),
            "club_name": str(row["club_name"]),
            "created_at": str(row["created_at"]),
        }
        for row in rows
    ]


def create_save_game(conn: sqlite3.Connection, manager_name: str, league_id: str, club_id: str) -> int:
    season_year = current_season_year()
    start_date = season_start_date(season_year)
    cursor = conn.execute("INSERT INTO managers (name) VALUES (?)", (manager_name.strip(),))
    manager_id = int(cursor.lastrowid)
    cursor = conn.execute(
        """
        INSERT INTO saves (manager_id, league_id, club_id, current_day, season_year, current_date)
        VALUES (?, ?, ?, 0, ?, ?)
        """,
        (manager_id, league_id, club_id, season_year, start_date.isoformat()),
    )
    save_id = int(cursor.lastrowid)
    _seed_save_league_clubs(conn, save_id, season_year)
    all_leagues = conn.execute("SELECT id FROM leagues").fetchall()
    for league_row in all_leagues:
        _seed_fixtures_for_save(conn, save_id, str(league_row["id"]), season_year)
    from .cups import seed_cup_for_save, CUP_CONFIGS
    for cup_key in CUP_CONFIGS:
        seed_cup_for_save(conn, save_id, cup_key, season_year)
    seed_save_player_condition_defaults(conn, save_id)
    seed_save_player_status_defaults(conn, save_id)
    seed_save_club_setups(conn, save_id)
    seed_save_training_defaults(conn, save_id, club_id)
    add_save_message(
        conn,
        save_id,
        "board",
        "BOARD WELCOME",
        "The board expects steady progress and a competitive season.",
        start_date.isoformat(),
        "info",
        f"board_welcome:{season_year}",
    )
    set_metadata(conn, "active_save_id", str(save_id))
    conn.commit()
    return save_id


def load_active_save_id(conn: sqlite3.Connection) -> int | None:
    value = get_metadata(conn, "active_save_id")
    if value is None:
        return None
    return int(value)


def set_active_save_id(conn: sqlite3.Connection, save_id: int) -> None:
    set_metadata(conn, "active_save_id", str(int(save_id)))


def clear_active_save_id(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM metadata WHERE key = 'active_save_id'")


def delete_save_game(conn: sqlite3.Connection, save_id: int) -> None:
    row = conn.execute(
        "SELECT manager_id FROM saves WHERE id = ?",
        (int(save_id),),
    ).fetchone()
    if row is None:
        return
    manager_id = int(row["manager_id"])
    conn.execute("DELETE FROM fixtures WHERE save_id = ?", (int(save_id),))
    conn.execute("DELETE FROM save_player_condition WHERE save_id = ?", (int(save_id),))
    conn.execute("DELETE FROM save_player_status WHERE save_id = ?", (int(save_id),))
    conn.execute("DELETE FROM save_player_attributes WHERE save_id = ?", (int(save_id),))
    conn.execute("DELETE FROM save_training_settings WHERE save_id = ?", (int(save_id),))
    conn.execute("DELETE FROM save_player_training WHERE save_id = ?", (int(save_id),))
    conn.execute("DELETE FROM save_club_setups WHERE save_id = ?", (int(save_id),))
    conn.execute("DELETE FROM save_messages WHERE save_id = ?", (int(save_id),))
    conn.execute("DELETE FROM cup_brackets WHERE save_id = ?", (int(save_id),))
    conn.execute("DELETE FROM competitions WHERE save_id = ?", (int(save_id),))
    conn.execute("DELETE FROM save_league_clubs WHERE save_id = ?", (int(save_id),))
    conn.execute("DELETE FROM standings WHERE save_id = ?", (int(save_id),))
    conn.execute("DELETE FROM club_staff WHERE save_id = ?", (int(save_id),))
    conn.execute("DELETE FROM player_scouting WHERE save_id = ?", (int(save_id),))
    conn.execute("DELETE FROM pending_scout_tasks WHERE save_id = ?", (int(save_id),))
    conn.execute("DELETE FROM saves WHERE id = ?", (int(save_id),))
    remaining = conn.execute(
        "SELECT COUNT(*) AS count FROM saves WHERE manager_id = ?",
        (manager_id,),
    ).fetchone()
    if remaining is not None and int(remaining["count"]) == 0:
        conn.execute("DELETE FROM managers WHERE id = ?", (manager_id,))
    active_save_id = get_metadata(conn, "active_save_id")
    if active_save_id is not None and int(active_save_id) == int(save_id):
        clear_active_save_id(conn)


def load_save_overview(conn: sqlite3.Connection, save_id: int, news_page: int = 0) -> dict | None:
    seed_save_player_condition_defaults(conn, save_id)
    seed_save_player_status_defaults(conn, save_id)
    seed_save_club_setups(conn, save_id)
    seed_save_training_defaults(conn, save_id)
    normalize_new_save_player_condition(conn, save_id)
    conn.commit()
    save_row = conn.execute(
        """
        SELECT s.id, s.current_day, s.current_date, s.season_year,
               m.name AS manager_name, l.id AS league_id, l.name AS league_name,
               c.id AS club_id, c.name AS club_name
        FROM saves s
        JOIN managers m ON m.id = s.manager_id
        JOIN leagues l ON l.id = s.league_id
        JOIN clubs c ON c.id = s.club_id
        WHERE s.id = ?
        """,
        (save_id,),
    ).fetchone()
    if save_row is None:
        return None
    league_id = str(save_row["league_id"])
    club_id = str(save_row["club_id"])
    clubs = list_league_clubs(conn, league_id)
    club_setups = load_save_club_setups(conn, save_id)
    players_by_club = {club["id"]: list_club_players(conn, club["id"], save_id=save_id) for club in clubs}
    season_totals = _season_player_totals(conn, save_id)
    rating_forms = _season_player_rating_form(conn, save_id)
    for club_players in players_by_club.values():
        for player in club_players:
            totals = season_totals.get(player["id"], {})
            player["apps"] = int(totals.get("apps", 0))
            player["goals"] = int(totals.get("goals", 0))
            player["assists"] = int(totals.get("assists", 0))
            form = rating_forms.get(player["id"], {})
            player["avg_rating"] = float(form.get("avg_rating", 0.0) or 0.0)
            player["recent_form_rating"] = float(form.get("recent_form_rating", 0.0) or 0.0)
            player["recent_ratings"] = list(form.get("recent_ratings", []))
    next_fixture = get_next_fixture_for_save(conn, save_id, club_id)
    current_date = str(save_row["current_date"] or season_start_date(int(save_row["season_year"] or current_season_year())).isoformat())
    today_fixture = get_playable_fixture_for_save(conn, save_id, club_id, current_date)
    fixtures = list_save_fixtures(conn, save_id)
    current_fixture = today_fixture or next_fixture
    if current_fixture:
        current_gameweek = int(current_fixture.get("gameweek", current_fixture.get("match_day", 1)) or 1)
    else:
        current_gameweek = max((int(fixture.get("gameweek", fixture.get("match_day", 1)) or 1) for fixture in fixtures), default=1)
    return {
        "save_id": int(save_row["id"]),
        "current_day": int(save_row["current_day"]),
        "current_date": current_date,
        "current_date_label": format_game_date(current_date),
        "season_year": int(save_row["season_year"] or current_season_year()),
        "manager_name": str(save_row["manager_name"]),
        "league_id": league_id,
        "league_name": str(save_row["league_name"]),
        "club_id": club_id,
        "club_name": str(save_row["club_name"]),
        "clubs": clubs,
        "club_setups": club_setups,
        "players_by_club": players_by_club,
        "standings": load_save_standings(conn, save_id),
        "fixtures": fixtures,
        "current_gameweek": current_gameweek,
        "next_fixture": next_fixture,
        "today_fixture": today_fixture,
        "training": load_save_training(conn, save_id, club_id),
        "messages": list_save_messages(conn, save_id, limit=10, offset=max(0, int(news_page)) * 10),
        "messages_total": count_save_messages(conn, save_id),
        "messages_unread": count_unread_messages(conn, save_id),
        "messages_page": max(0, int(news_page)),
        "finances": get_save_finances(conn, save_id),
    }


def list_save_fixtures(conn: sqlite3.Connection, save_id: int) -> List[dict]:
    rows = conn.execute(
        """
        SELECT f.id, f.match_day, f.fixture_date, f.home_club_id, f.away_club_id,
               hc.name AS home_name, ac.name AS away_name,
               f.played, f.home_goals, f.away_goals, f.report_json
        FROM fixtures f
        JOIN clubs hc ON hc.id = f.home_club_id
        JOIN clubs ac ON ac.id = f.away_club_id
        WHERE f.save_id = ?
        ORDER BY f.fixture_date, f.id
        """,
        (save_id,),
    ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "match_day": int(row["match_day"]),
            "gameweek": int(row["match_day"]),
            "fixture_date": str(row["fixture_date"] or ""),
            "fixture_date_label": format_game_date(str(row["fixture_date"] or "")),
            "home_club_id": str(row["home_club_id"]),
            "away_club_id": str(row["away_club_id"]),
            "home_name": str(row["home_name"]),
            "away_name": str(row["away_name"]),
            "played": bool(row["played"]),
            "home_goals": None if row["home_goals"] is None else int(row["home_goals"]),
            "away_goals": None if row["away_goals"] is None else int(row["away_goals"]),
            "has_report": bool(row["report_json"]),
        }
        for row in rows
    ]


def get_next_fixture_for_save(conn: sqlite3.Connection, save_id: int, club_id: str) -> dict | None:
    row = conn.execute(
        """
        SELECT f.id, f.match_day, f.fixture_date, f.home_club_id, f.away_club_id,
               hc.name AS home_name, ac.name AS away_name
        FROM fixtures f
        JOIN clubs hc ON hc.id = f.home_club_id
        JOIN clubs ac ON ac.id = f.away_club_id
        WHERE f.save_id = ?
          AND f.played = 0
          AND (f.home_club_id = ? OR f.away_club_id = ?)
        ORDER BY f.fixture_date, f.id
        LIMIT 1
        """,
        (save_id, club_id, club_id),
    ).fetchone()
    if row is None:
        return None
    return {
        "id": int(row["id"]),
        "match_day": int(row["match_day"]),
        "fixture_date": str(row["fixture_date"] or ""),
        "fixture_date_label": format_game_date(str(row["fixture_date"] or "")),
        "home_club_id": str(row["home_club_id"]),
        "away_club_id": str(row["away_club_id"]),
        "home_name": str(row["home_name"]),
        "away_name": str(row["away_name"]),
    }


def get_playable_fixture_for_save(conn: sqlite3.Connection, save_id: int, club_id: str, current_date: str) -> dict | None:
    row = conn.execute(
        """
        SELECT f.id, f.match_day, f.fixture_date, f.home_club_id, f.away_club_id,
               hc.name AS home_name, ac.name AS away_name
        FROM fixtures f
        JOIN clubs hc ON hc.id = f.home_club_id
        JOIN clubs ac ON ac.id = f.away_club_id
        WHERE f.save_id = ?
          AND f.played = 0
          AND (f.home_club_id = ? OR f.away_club_id = ?)
          AND f.fixture_date <= ?
        ORDER BY f.fixture_date, f.id
        LIMIT 1
        """,
        (save_id, club_id, club_id, current_date),
    ).fetchone()
    if row is None:
        return None
    return {
        "id": int(row["id"]),
        "match_day": int(row["match_day"]),
        "fixture_date": str(row["fixture_date"] or ""),
        "fixture_date_label": format_game_date(str(row["fixture_date"] or "")),
        "home_club_id": str(row["home_club_id"]),
        "away_club_id": str(row["away_club_id"]),
        "home_name": str(row["home_name"]),
        "away_name": str(row["away_name"]),
    }


def list_matchday_fixtures(conn: sqlite3.Connection, save_id: int, match_day: int) -> List[dict]:
    rows = conn.execute(
        """
        SELECT id, fixture_date, home_club_id, away_club_id
        FROM fixtures
        WHERE save_id = ? AND match_day = ?
        ORDER BY id
        """,
        (save_id, match_day),
    ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "fixture_date": str(row["fixture_date"] or ""),
            "home_club_id": str(row["home_club_id"]),
            "away_club_id": str(row["away_club_id"]),
        }
        for row in rows
    ]


def save_fixture_result(
    conn: sqlite3.Connection,
    fixture_id: int,
    home_goals: int,
    away_goals: int,
    report: dict | None = None,
) -> None:
    fixture_meta = _fixture_club_ids(conn, fixture_id)
    if fixture_meta is not None:
        save_id, home_club_id, away_club_id = fixture_meta
        _decrement_served_suspensions(conn, save_id, (home_club_id, away_club_id))
    conn.execute(
        """
        UPDATE fixtures
        SET played = 1,
            home_goals = ?,
            away_goals = ?,
            report_json = ?
        WHERE id = ?
        """,
        (
            int(home_goals),
            int(away_goals),
            json.dumps(report, separators=(",", ":"), ensure_ascii=True) if report is not None else None,
            int(fixture_id),
        ),
    )
    # Update pre-aggregated standings
    if fixture_meta is not None:
        fid_row = conn.execute(
            "SELECT competition_id FROM fixtures WHERE id=?", (int(fixture_id),)
        ).fetchone()
        comp_id = str(fid_row["competition_id"] or "") if fid_row else ""
        if comp_id:
            from .simulation import _update_standings
            season_row = conn.execute(
                "SELECT season_year FROM saves WHERE id=?", (fixture_meta[0],)
            ).fetchone()
            season = int(season_row["season_year"]) if season_row else 2025
            _update_standings(
                conn, fixture_meta[0], comp_id, season,
                str(fixture_meta[1]), str(fixture_meta[2]),
                int(home_goals), int(away_goals),
            )

    if report is not None and fixture_meta is not None:
        apply_match_report_player_status(conn, fixture_meta[0], report)


def get_fixture_report(conn: sqlite3.Connection, fixture_id: int) -> dict | None:
    row = conn.execute(
        "SELECT report_json FROM fixtures WHERE id = ?",
        (int(fixture_id),),
    ).fetchone()
    if row is None or not row["report_json"]:
        return None
    try:
        return json.loads(str(row["report_json"]))
    except json.JSONDecodeError:
        return None


def set_save_current_day(conn: sqlite3.Connection, save_id: int, current_day: int) -> None:
    row = conn.execute("SELECT season_year FROM saves WHERE id = ?", (int(save_id),)).fetchone()
    if row is None:
        return
    season_year = int(row["season_year"] or current_season_year())
    current_date = season_start_date(season_year) + timedelta(days=int(current_day))
    conn.execute(
        """
        UPDATE saves
        SET current_day = ?, current_date = ?
        WHERE id = ?
        """,
        (int(current_day), current_date.isoformat(), int(save_id)),
    )


def load_save_standings(conn: sqlite3.Connection, save_id: int, competition_id: str | None = None) -> List[dict]:
    save_row = conn.execute(
        "SELECT league_id, season_year FROM saves WHERE id = ?", (save_id,)
    ).fetchone()
    if save_row is None:
        return []
    league_id = str(save_row["league_id"])
    season_year = int(save_row["season_year"] or current_season_year())

    if competition_id is None:
        competition_id = f"{league_id}_{season_year}"

    # Derive league_id from competition_id for club list lookup
    comp_league_id = competition_id.split("_")[0] if "_" in competition_id else league_id

    clubs_rows = conn.execute(
        """
        SELECT slc.club_id, c.name
        FROM save_league_clubs slc
        JOIN clubs c ON c.id = slc.club_id
        WHERE slc.save_id = ? AND slc.league_id = ? AND slc.season = ?
        ORDER BY slc.club_id
        """,
        (save_id, comp_league_id, season_year),
    ).fetchall()
    if not clubs_rows:
        clubs_rows = conn.execute(
            """
            SELECT lc.club_id, c.name
            FROM league_clubs lc
            JOIN clubs c ON c.id = lc.club_id
            WHERE lc.league_id = ?
            ORDER BY lc.display_order, lc.club_id
            """,
            (comp_league_id,),
        ).fetchall()

    table = {
        str(row["club_id"]): {
            "club_id": str(row["club_id"]),
            "club_name": str(row["name"]),
            "played": 0, "wins": 0, "draws": 0, "losses": 0,
            "goals_for": 0, "goals_against": 0, "goal_difference": 0,
            "points": 0, "recent_form": [], "next_fixture": None,
        }
        for row in clubs_rows
    }
    club_names = {str(r["club_id"]): str(r["name"]) for r in clubs_rows}

    played_rows = conn.execute(
        """
        SELECT id, fixture_date, home_club_id, away_club_id, home_goals, away_goals
        FROM fixtures
        WHERE save_id = ? AND played = 1
          AND (competition_id = ? OR (competition_id IS NULL AND ? LIKE 'ENG1%'))
        ORDER BY fixture_date, id
        """,
        (save_id, competition_id, competition_id),
    ).fetchall()
    for row in played_rows:
        home_id = str(row["home_club_id"])
        away_id = str(row["away_club_id"])
        if home_id not in table or away_id not in table:
            continue
        home_goals = int(row["home_goals"] or 0)
        away_goals = int(row["away_goals"] or 0)
        home = table[home_id]
        away = table[away_id]
        home["played"] += 1
        away["played"] += 1
        home["goals_for"] += home_goals
        home["goals_against"] += away_goals
        away["goals_for"] += away_goals
        away["goals_against"] += home_goals
        if home_goals > away_goals:
            home["wins"] += 1; away["losses"] += 1
            home["points"] += 3
            home_result, away_result = "W", "L"
        elif away_goals > home_goals:
            away["wins"] += 1; home["losses"] += 1
            away["points"] += 3
            home_result, away_result = "L", "W"
        else:
            home["draws"] += 1; away["draws"] += 1
            home["points"] += 1; away["points"] += 1
            home_result, away_result = "D", "D"
        base = {
            "fixture_id": int(row["id"]),
            "fixture_date": str(row["fixture_date"] or ""),
            "fixture_date_label": format_game_date(str(row["fixture_date"] or "")),
            "home_club_id": home_id, "away_club_id": away_id,
            "home_name": club_names.get(home_id, home_id),
            "away_name": club_names.get(away_id, away_id),
            "home_goals": home_goals, "away_goals": away_goals,
        }
        home["recent_form"].append({**base, "result": home_result, "opponent_id": away_id, "opponent_name": club_names.get(away_id, away_id)})
        away["recent_form"].append({**base, "result": away_result, "opponent_id": home_id, "opponent_name": club_names.get(home_id, home_id)})

    next_rows = conn.execute(
        """
        SELECT id, fixture_date, home_club_id, away_club_id
        FROM fixtures
        WHERE save_id = ? AND played = 0
          AND (competition_id = ? OR (competition_id IS NULL AND ? LIKE 'ENG1%'))
        ORDER BY fixture_date, id
        """,
        (save_id, competition_id, competition_id),
    ).fetchall()
    for row in next_rows:
        home_id = str(row["home_club_id"])
        away_id = str(row["away_club_id"])
        for club_id, opponent_id, venue in ((home_id, away_id, "HOME"), (away_id, home_id, "AWAY")):
            if club_id not in table or table[club_id]["next_fixture"] is not None:
                continue
            table[club_id]["next_fixture"] = {
                "fixture_id": int(row["id"]),
                "fixture_date": str(row["fixture_date"] or ""),
                "fixture_date_label": format_game_date(str(row["fixture_date"] or "")),
                "home_club_id": home_id, "away_club_id": away_id,
                "home_name": club_names.get(home_id, home_id),
                "away_name": club_names.get(away_id, away_id),
                "opponent_id": opponent_id,
                "opponent_name": club_names.get(opponent_id, opponent_id),
                "venue": venue,
            }

    standings = list(table.values())
    for row in standings:
        row["goal_difference"] = row["goals_for"] - row["goals_against"]
        row["recent_form"] = list(row.get("recent_form", []))[-4:]
    standings.sort(key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"], r["club_name"]))
    for i, row in enumerate(standings):
        row["position"] = i + 1
    return standings


def load_all_competitions(conn: sqlite3.Connection, save_id: int) -> List[dict]:
    save_row = conn.execute(
        "SELECT season_year, league_id FROM saves WHERE id=?", (save_id,)
    ).fetchone()
    if save_row is None:
        return []
    season_year = int(save_row["season_year"])

    comp_rows = conn.execute(
        "SELECT id, name, country, type, season FROM competitions WHERE save_id=? ORDER BY type, country, name",
        (save_id,),
    ).fetchall()
    existing_ids = {str(r["id"]) for r in comp_rows}

    result: List[dict] = []

    # Cup competitions
    for row in comp_rows:
        comp_id = str(row["id"])
        entry = {
            "id": comp_id,
            "name": str(row["name"]),
            "country": str(row["country"]),
            "type": str(row["type"]),
            "season": int(row["season"]),
        }
        if str(row["type"]) == "cup":
            round_row = conn.execute(
                """
                SELECT cb.round FROM cup_brackets cb
                JOIN fixtures f ON f.save_id=cb.save_id AND f.competition_id=cb.competition_id
                  AND (f.home_club_id=cb.club_a OR f.home_club_id=cb.club_b)
                WHERE cb.save_id=? AND cb.competition_id=? AND f.played=0
                ORDER BY f.fixture_date LIMIT 1
                """,
                (save_id, comp_id),
            ).fetchone()
            entry["current_round"] = str(round_row["round"]) if round_row else "F"
            recent = conn.execute(
                """
                SELECT hc.name AS home_name, ac.name AS away_name, f.home_goals, f.away_goals
                FROM fixtures f
                JOIN clubs hc ON hc.id=f.home_club_id
                JOIN clubs ac ON ac.id=f.away_club_id
                WHERE f.save_id=? AND f.competition_id=? AND f.played=1
                ORDER BY f.fixture_date DESC LIMIT 4
                """,
                (save_id, comp_id),
            ).fetchall()
            entry["recent_results"] = [
                {
                    "home_name": str(r["home_name"]),
                    "away_name": str(r["away_name"]),
                    "home_goals": int(r["home_goals"] or 0),
                    "away_goals": int(r["away_goals"] or 0),
                }
                for r in recent
            ]
        result.append(entry)

    # League competitions (derived from fixtures, no competitions table row)
    league_rows = conn.execute("SELECT id, name FROM leagues ORDER BY id").fetchall()
    for lg in league_rows:
        lid = str(lg["id"])
        comp_id = f"{lid}_{season_year}"
        if comp_id in existing_ids:
            continue
        fix_count = conn.execute(
            "SELECT COUNT(*) AS c FROM fixtures WHERE save_id=? AND competition_id=?",
            (save_id, comp_id),
        ).fetchone()
        if not fix_count or int(fix_count["c"]) == 0:
            continue
        played = conn.execute(
            "SELECT COUNT(*) AS c FROM fixtures WHERE save_id=? AND competition_id=? AND played=1",
            (save_id, comp_id),
        ).fetchone()
        entry = {
            "id": comp_id,
            "name": str(lg["name"]),
            "country": lid[:3],
            "type": "league",
            "season": season_year,
            "matchday_played": int(played["c"]) if played else 0,
            "matchday_total": int(fix_count["c"]),
        }
        top3 = conn.execute(
            """
            SELECT c.name, s.points
            FROM standings s JOIN clubs c ON c.id=s.club_id
            WHERE s.save_id=? AND s.competition_id=?
            ORDER BY s.points DESC, (s.gf - s.ga) DESC LIMIT 3
            """,
            (save_id, comp_id),
        ).fetchall()
        entry["top3"] = [{"name": str(r["name"]), "points": int(r["points"])} for r in top3]
        result.append(entry)

    # Enrich cups with top3 from standings if available
    for entry in result:
        if entry["type"] == "league" and "top3" not in entry:
            comp_id = entry["id"]
            top3 = conn.execute(
                """
                SELECT c.name, s.points
                FROM standings s JOIN clubs c ON c.id=s.club_id
                WHERE s.save_id=? AND s.competition_id=?
                ORDER BY s.points DESC, (s.gf - s.ga) DESC LIMIT 3
                """,
                (save_id, comp_id),
            ).fetchall()
            entry["top3"] = [{"name": str(r["name"]), "points": int(r["points"])} for r in top3]

    return result


def load_cup_bracket(conn: sqlite3.Connection, save_id: int, competition_id: str) -> dict:
    rows = conn.execute(
        """
        SELECT cb.round, cb.slot, cb.club_a, cb.club_b, cb.winner,
               cb.score_a_leg1, cb.score_b_leg1, cb.score_a_leg2, cb.score_b_leg2,
               ca.name AS name_a, cb2.name AS name_b
        FROM cup_brackets cb
        LEFT JOIN clubs ca ON ca.id=cb.club_a
        LEFT JOIN clubs cb2 ON cb2.id=cb.club_b
        WHERE cb.save_id=? AND cb.competition_id=?
        ORDER BY cb.round, cb.slot
        """,
        (save_id, competition_id),
    ).fetchall()
    bracket: dict = {}
    for row in rows:
        rnd = str(row["round"])
        if rnd not in bracket:
            bracket[rnd] = []
        bracket[rnd].append({
            "slot": int(row["slot"]),
            "club_a": str(row["club_a"] or ""),
            "club_b": str(row["club_b"] or ""),
            "name_a": str(row["name_a"] or row["club_a"] or "TBD"),
            "name_b": str(row["name_b"] or row["club_b"] or "TBD"),
            "winner": str(row["winner"] or ""),
            "score_a_leg1": row["score_a_leg1"],
            "score_b_leg1": row["score_b_leg1"],
            "score_a_leg2": row["score_a_leg2"],
            "score_b_leg2": row["score_b_leg2"],
        })
    return bracket


def _seed_save_league_clubs(conn: sqlite3.Connection, save_id: int, season_year: int) -> None:
    rows = conn.execute("SELECT league_id, club_id FROM league_clubs").fetchall()
    conn.executemany(
        """
        INSERT OR IGNORE INTO save_league_clubs (save_id, league_id, club_id, season)
        VALUES (?, ?, ?, ?)
        """,
        [(save_id, str(r["league_id"]), str(r["club_id"]), season_year) for r in rows],
    )


def _seed_fixtures_for_save(
    conn: sqlite3.Connection,
    save_id: int,
    league_id: str,
    season_year: int,
    competition_id: str | None = None,
) -> None:
    if competition_id is None:
        competition_id = f"{league_id}_{season_year}"
    club_rows = conn.execute(
        """
        SELECT club_id
        FROM save_league_clubs
        WHERE save_id = ? AND league_id = ? AND season = ?
        ORDER BY club_id
        """,
        (save_id, league_id, season_year),
    ).fetchall()
    if not club_rows:
        club_rows = conn.execute(
            "SELECT club_id FROM league_clubs WHERE league_id = ? ORDER BY display_order, club_id",
            (league_id,),
        ).fetchall()
    club_ids = [str(row["club_id"]) for row in club_rows]
    if len(club_ids) < 2:
        return
    match_day = 1
    fixture_rows: List[tuple] = []
    match_date = first_match_date(season_year)
    matches_per_round = max(1, len(club_ids) // 2)
    for home_id, away_id in _generate_double_round_robin(club_ids):
        fixture_rows.append((save_id, match_day, match_date.isoformat(), home_id, away_id, competition_id))
        if len(fixture_rows) % matches_per_round == 0:
            match_day += 1
            match_date += timedelta(days=7)
    conn.executemany(
        """
        INSERT INTO fixtures (save_id, match_day, fixture_date, home_club_id, away_club_id, competition_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        fixture_rows,
    )


def _generate_double_round_robin(club_ids: List[str]) -> List[tuple[str, str]]:
    if len(club_ids) < 2:
        return []
    ids = list(club_ids)
    if len(ids) % 2 == 1:
        ids.append("_BYE_")
    pairings: List[List[tuple[str, str]]] = []
    rotating = ids[:]
    rounds = len(rotating) - 1
    half = len(rotating) // 2
    for round_index in range(rounds):
        matchups: List[tuple[str, str]] = []
        left = rotating[:half]
        right = list(reversed(rotating[half:]))
        for idx, (home_id, away_id) in enumerate(zip(left, right)):
            if "_BYE_" in (home_id, away_id):
                continue
            if round_index % 2 == 0:
                matchups.append((home_id, away_id))
            else:
                matchups.append((away_id, home_id))
        pairings.append(matchups)
        rotating = [rotating[0]] + [rotating[-1]] + rotating[1:-1]
    second_leg = [[(away_id, home_id) for home_id, away_id in round_pair] for round_pair in pairings]
    flat: List[tuple[str, str]] = []
    for round_pair in pairings + second_leg:
        flat.extend(round_pair)
    return flat


# ---------------------------------------------------------------------------
# Transfer system helpers
# ---------------------------------------------------------------------------

def get_transfer_window_status(current_date: str) -> tuple[bool, str]:
    """Returns (is_open, window_type). window_type: 'summer'|'winter'|''."""
    if not current_date:
        return False, ""
    try:
        d = date.fromisoformat(current_date)
    except ValueError:
        return False, ""
    m, day = d.month, d.day
    if (m == 7 and day >= 7) or m == 8 or (m == 9 and day == 1):
        return True, "summer"
    if m == 1:
        return True, "winter"
    return False, ""


def _compute_asking_price(ovr: int) -> int:
    base = max(500_000, int((max(0, ovr - 55) ** 2.3) * 55_000))
    return round(base / 500_000) * 500_000


def _ai_populate_transfer_market(
    conn: sqlite3.Connection,
    save_id: int,
    current_date: str,
    window_type: str,
    season_year: int,
    managed_club_id: str,
) -> None:
    existing = conn.execute(
        "SELECT COUNT(*) AS c FROM transfer_market WHERE save_id = ? AND season_year = ? AND window_type = ? AND is_user_listed = 0",
        (int(save_id), int(season_year), window_type),
    ).fetchone()
    if existing and int(existing["c"]) > 0:
        return

    club_rows = conn.execute("SELECT id FROM clubs ORDER BY id").fetchall()
    for club_row in club_rows:
        club_id = str(club_row["id"])
        if club_id == managed_club_id:
            continue
        players = conn.execute(
            "SELECT p.id, p.position, p.ovr FROM players p WHERE p.club_id = ? ORDER BY p.ovr DESC",
            (club_id,),
        ).fetchall()
        transferred_away = set(
            str(r["player_id"]) for r in conn.execute(
                "SELECT player_id FROM save_player_club WHERE save_id = ? AND club_id != ?",
                (int(save_id), club_id),
            ).fetchall()
        )
        transferred_in = set(
            str(r["player_id"]) for r in conn.execute(
                "SELECT player_id FROM save_player_club WHERE save_id = ? AND club_id = ?",
                (int(save_id), club_id),
            ).fetchall()
        )
        roster = [p for p in players if str(p["id"]) not in transferred_away]
        for pid in transferred_in:
            extra = conn.execute("SELECT id, position, ovr FROM players WHERE id = ?", (pid,)).fetchone()
            if extra:
                roster.append(extra)
        roster = sorted(roster, key=lambda p: int(p["ovr"]), reverse=True)

        pos_counts: Dict[str, int] = {}
        for p in roster:
            pos_counts[str(p["position"])] = pos_counts.get(str(p["position"]), 0) + 1

        excess = []
        pos_seen: Dict[str, int] = {}
        for idx, p in enumerate(roster):
            pos = str(p["position"])
            pos_seen[pos] = pos_seen.get(pos, 0) + 1
            if idx >= 11 and (pos_seen[pos] > 1 or pos_counts.get(pos, 0) >= 3):
                excess.append(p)

        listed = 0
        random.shuffle(excess)
        for p in excess:
            if listed >= 3:
                break
            if random.random() > 0.30:
                continue
            try:
                conn.execute(
                    """
                    INSERT INTO transfer_market
                        (save_id, player_id, listed_club_id, asking_price, listed_date, window_type, season_year, status, is_user_listed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'available', 0)
                    ON CONFLICT(save_id, player_id, season_year, window_type) DO NOTHING
                    """,
                    (int(save_id), str(p["id"]), club_id, _compute_asking_price(int(p["ovr"])), current_date, window_type, int(season_year)),
                )
                listed += 1
            except sqlite3.IntegrityError:
                pass


def _ai_make_offers_on_user_listings(
    conn: sqlite3.Connection,
    save_id: int,
    current_date: str,
    managed_club_id: str,
    season_year: int,
) -> None:
    """Each day there's a 15% chance per user-listed player that an AI club makes an offer."""
    listings = conn.execute(
        """
        SELECT tm.player_id, tm.asking_price, tm.window_type, tm.season_year,
               p.ovr, p.name AS player_name
        FROM transfer_market tm
        JOIN players p ON p.id = tm.player_id
        WHERE tm.save_id = ? AND tm.listed_club_id = ? AND tm.is_user_listed = 1 AND tm.status = 'available'
        """,
        (int(save_id), managed_club_id),
    ).fetchall()
    if not listings:
        return
    club_rows = conn.execute("SELECT id, name FROM clubs WHERE id != ? ORDER BY RANDOM()", (managed_club_id,)).fetchall()
    if not club_rows:
        return
    for listing in listings:
        if random.random() > 0.15:
            continue
        existing = conn.execute(
            "SELECT COUNT(*) AS c FROM transfer_offers WHERE save_id = ? AND player_id = ? AND season_year = ? AND window_type = ? AND status != 'rejected'",
            (int(save_id), str(listing["player_id"]), int(listing["season_year"]), str(listing["window_type"])),
        ).fetchone()
        if existing and int(existing["c"]) > 0:
            continue
        asking = int(listing["asking_price"])
        ratio = random.uniform(0.75, 1.10)
        offer_amt = round(asking * ratio / 500_000) * 500_000
        buyer_club = random.choice(club_rows)
        response_days = random.randint(1, 2)
        resp_date = (date.fromisoformat(current_date) + timedelta(days=response_days)).isoformat()
        try:
            conn.execute(
                """
                INSERT INTO transfer_offers (save_id, player_id, offer_amount, offer_number, status, created_date, response_date, window_type, season_year, offering_club_id)
                VALUES (?, ?, ?, 1, 'pending_user_accept', ?, ?, ?, ?, ?)
                """,
                (int(save_id), str(listing["player_id"]), offer_amt, current_date, resp_date, str(listing["window_type"]), int(listing["season_year"]), str(buyer_club["id"])),
            )
            add_save_message(
                conn, save_id, "transfers",
                "TRANSFER OFFER RECEIVED",
                f"{str(buyer_club['name'])} have made an offer of £{offer_amt // 1_000_000}M for {str(listing['player_name'])}. Go to Transfers > Talks to respond.",
                current_date, "info",
                f"ai_offer:{save_id}:{listing['player_id']}:{current_date}",
            )
        except sqlite3.IntegrityError:
            pass


def get_transfer_market_listings(conn: sqlite3.Connection, save_id: int) -> List[dict]:
    rows = conn.execute(
        """
        SELECT tm.id, tm.player_id, tm.listed_club_id, tm.asking_price, tm.listed_date,
               tm.window_type, tm.season_year, tm.status, tm.is_user_listed,
               p.name AS player_name, p.position, p.ovr, p.age,
               c.name AS club_name,
               (SELECT COUNT(*) FROM transfer_offers to2
                WHERE to2.save_id = tm.save_id AND to2.player_id = tm.player_id
                  AND to2.window_type = tm.window_type AND to2.season_year = tm.season_year) AS offer_count
        FROM transfer_market tm
        JOIN players p ON p.id = tm.player_id
        JOIN clubs c ON c.id = tm.listed_club_id
        WHERE tm.save_id = ? AND tm.status = 'available'
        ORDER BY p.ovr DESC
        """,
        (int(save_id),),
    ).fetchall()
    return [dict(r) for r in rows]


def get_user_transfer_listings(conn: sqlite3.Connection, save_id: int, managed_club_id: str) -> List[dict]:
    rows = conn.execute(
        """
        SELECT tm.id, tm.player_id, tm.asking_price, tm.listed_date,
               tm.window_type, tm.season_year, tm.status,
               p.name AS player_name, p.position, p.ovr, p.age,
               (SELECT COUNT(*) FROM transfer_offers to2
                WHERE to2.save_id = tm.save_id AND to2.player_id = tm.player_id
                  AND to2.window_type = tm.window_type AND to2.season_year = tm.season_year) AS offer_count
        FROM transfer_market tm
        JOIN players p ON p.id = tm.player_id
        WHERE tm.save_id = ? AND tm.listed_club_id = ? AND tm.is_user_listed = 1 AND tm.status = 'available'
        ORDER BY tm.id DESC
        """,
        (int(save_id), managed_club_id),
    ).fetchall()
    return [dict(r) for r in rows]


def list_player_for_transfer(
    conn: sqlite3.Connection,
    save_id: int,
    player_id: str,
    club_id: str,
    current_date: str,
    season_year: int,
    window_type: str,
    custom_price: int | None = None,
) -> bool:
    existing = conn.execute(
        "SELECT id FROM transfer_market WHERE save_id = ? AND player_id = ? AND season_year = ? AND window_type = ? AND status = 'available'",
        (int(save_id), player_id, int(season_year), window_type),
    ).fetchone()
    if existing:
        return False
    player_row = conn.execute("SELECT ovr FROM players WHERE id = ?", (player_id,)).fetchone()
    if player_row is None:
        return False
    market_price = _compute_asking_price(int(player_row["ovr"]))
    if custom_price is not None:
        # Anti-farming cap: max 4× market value
        max_allowed = market_price * 4
        asking = max(500_000, min(custom_price, max_allowed))
        asking = round(asking / 500_000) * 500_000
    else:
        asking = market_price
    conn.execute(
        """
        INSERT INTO transfer_market
            (save_id, player_id, listed_club_id, asking_price, listed_date, window_type, season_year, status, is_user_listed)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'available', 1)
        ON CONFLICT(save_id, player_id, season_year, window_type) DO UPDATE SET status='available', asking_price=excluded.asking_price
        """,
        (int(save_id), player_id, club_id, asking, current_date, window_type, int(season_year)),
    )
    return True


def make_transfer_offer(
    conn: sqlite3.Connection,
    save_id: int,
    player_id: str,
    offer_amount: int,
    window_type: str,
    season_year: int,
    current_date: str,
) -> dict:
    existing_offers = conn.execute(
        "SELECT COUNT(*) AS c FROM transfer_offers WHERE save_id = ? AND player_id = ? AND season_year = ? AND window_type = ?",
        (int(save_id), player_id, int(season_year), window_type),
    ).fetchone()
    count = int(existing_offers["c"]) if existing_offers else 0
    if count >= 3:
        return {"ok": False, "error": "max_offers_reached"}
    listing = conn.execute(
        "SELECT id, asking_price FROM transfer_market WHERE save_id = ? AND player_id = ? AND season_year = ? AND window_type = ? AND status = 'available'",
        (int(save_id), player_id, int(season_year), window_type),
    ).fetchone()
    if listing is None:
        return {"ok": False, "error": "not_listed"}
    response_days = random.randint(2, 4)
    resp_date = (date.fromisoformat(current_date) + timedelta(days=response_days)).isoformat()
    cur = conn.execute(
        """
        INSERT INTO transfer_offers (save_id, player_id, offer_amount, offer_number, status, created_date, response_date, window_type, season_year)
        VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?)
        """,
        (int(save_id), player_id, int(offer_amount), count + 1, current_date, resp_date, window_type, int(season_year)),
    )
    return {"ok": True, "offer_id": cur.lastrowid}


def withdraw_transfer_listing(conn: sqlite3.Connection, save_id: int, listing_id: int) -> None:
    conn.execute(
        "UPDATE transfer_market SET status = 'withdrawn' WHERE id = ? AND save_id = ?",
        (int(listing_id), int(save_id)),
    )


def resolve_pending_transfer_offers(
    conn: sqlite3.Connection,
    save_id: int,
    current_date: str,
    user_league_position: int = 4,
) -> None:
    offers = conn.execute(
        """
        SELECT to2.id, to2.player_id, to2.offer_amount, to2.offer_number,
               to2.window_type, to2.season_year,
               p.name AS player_name, p.ovr,
               tm.asking_price, tm.listed_club_id,
               c.name AS club_name
        FROM transfer_offers to2
        JOIN players p ON p.id = to2.player_id
        JOIN transfer_market tm ON tm.save_id = to2.save_id
            AND tm.player_id = to2.player_id
            AND tm.season_year = to2.season_year
            AND tm.window_type = to2.window_type
        JOIN clubs c ON c.id = tm.listed_club_id
        WHERE to2.save_id = ? AND to2.status = 'pending'
          AND to2.response_date <= ?
        """,
        (int(save_id), current_date),
    ).fetchall()

    num_clubs = max(1, conn.execute("SELECT COUNT(*) AS c FROM clubs").fetchone()["c"])
    prestige_bonus = max(0.0, (num_clubs - user_league_position) / max(1, num_clubs - 1))

    for offer in offers:
        asking = int(offer["asking_price"])
        amount = int(offer["offer_amount"])
        ratio = amount / max(1, asking)
        accept_prob = min(0.92, max(0.04,
            0.75 * (ratio ** 1.4)
            + 0.15 * prestige_bonus
            + 0.10 * random.random()
        ))
        accepted = random.random() < accept_prob
        offer_num = int(offer["offer_number"])
        player_name = str(offer["player_name"])
        club_name = str(offer["club_name"])

        if accepted:
            conn.execute(
                "UPDATE transfer_offers SET status = 'accepted', response_date = ? WHERE id = ?",
                (current_date, int(offer["id"])),
            )
            add_save_message(
                conn, save_id, "transfers",
                "OFFER ACCEPTED",
                f"{club_name} accepted your offer for {player_name}. Negotiate contract terms.",
                current_date, "success",
                f"offer_accepted:{offer['id']}",
            )
        else:
            conn.execute(
                "UPDATE transfer_offers SET status = 'rejected', response_date = ? WHERE id = ?",
                (current_date, int(offer["id"])),
            )
            if offer_num >= 3:
                add_save_message(
                    conn, save_id, "transfers",
                    "OFFER REJECTED",
                    f"{club_name} rejected your final offer for {player_name}. No more offers this window.",
                    current_date, "warning",
                    f"offer_final_rejected:{offer['id']}",
                )
            else:
                add_save_message(
                    conn, save_id, "transfers",
                    "OFFER REJECTED",
                    f"{club_name} rejected your offer for {player_name}. {3 - offer_num} offer(s) remaining.",
                    current_date, "warning",
                    f"offer_rejected:{offer['id']}",
                )


def get_all_user_offers(conn: sqlite3.Connection, save_id: int) -> List[dict]:
    rows = conn.execute(
        """
        SELECT to2.id, to2.player_id, to2.offer_amount, to2.offer_number,
               to2.status, to2.created_date, to2.response_date,
               to2.window_type, to2.season_year,
               p.name AS player_name, p.ovr, p.position, p.age,
               tm.asking_price, tm.listed_club_id,
               c.name AS club_name,
               cb.template_id AS badge_template_id,
               cb.primary_color AS badge_primary,
               cb.secondary_color AS badge_secondary,
               cb.border_color AS badge_border
        FROM transfer_offers to2
        JOIN players p ON p.id = to2.player_id
        LEFT JOIN transfer_market tm ON tm.save_id = to2.save_id
            AND tm.player_id = to2.player_id
            AND tm.season_year = to2.season_year
            AND tm.window_type = to2.window_type
        LEFT JOIN clubs c ON c.id = tm.listed_club_id
        LEFT JOIN club_badges cb ON cb.club_id = tm.listed_club_id
        WHERE to2.save_id = ?
          AND to2.status NOT IN ('completed', 'expired')
        ORDER BY to2.id DESC
        """,
        (int(save_id),),
    ).fetchall()
    return [dict(r) for r in rows]


def get_accepted_offers(conn: sqlite3.Connection, save_id: int) -> List[dict]:
    rows = conn.execute(
        """
        SELECT to2.id, to2.player_id, to2.offer_amount, to2.window_type, to2.season_year,
               p.name AS player_name, p.ovr, p.position, p.age,
               tm.listed_club_id,
               c.name AS club_name
        FROM transfer_offers to2
        JOIN players p ON p.id = to2.player_id
        JOIN transfer_market tm ON tm.save_id = to2.save_id
            AND tm.player_id = to2.player_id
            AND tm.season_year = to2.season_year
            AND tm.window_type = to2.window_type
        JOIN clubs c ON c.id = tm.listed_club_id
        WHERE to2.save_id = ? AND to2.status = 'accepted'
        ORDER BY to2.id
        """,
        (int(save_id),),
    ).fetchall()
    return [dict(r) for r in rows]


def submit_player_negotiation(
    conn: sqlite3.Connection,
    save_id: int,
    offer_id: int,
    weekly_wage: int,
    contract_years: int,
    current_date: str,
) -> dict:
    """Store player negotiation terms; player responds in 2-3 days."""
    response_days = random.randint(2, 3)
    player_resp_date = (date.fromisoformat(current_date) + timedelta(days=response_days)).isoformat()
    conn.execute(
        """
        UPDATE transfer_offers
        SET status = 'negotiating', offered_wage = ?, offered_contract_years = ?, player_response_date = ?
        WHERE id = ? AND save_id = ?
        """,
        (int(weekly_wage), int(contract_years), player_resp_date, int(offer_id), int(save_id)),
    )
    return {"ok": True, "player_response_date": player_resp_date}


def resolve_pending_player_negotiations(
    conn: sqlite3.Connection,
    save_id: int,
    current_date: str,
    to_club_id: str,
    to_club_name: str,
    user_league_position: int = 4,
) -> None:
    """Called daily — resolve any player negotiations where response_date has passed."""
    rows = conn.execute(
        """
        SELECT to2.id, to2.player_id, to2.offered_wage, to2.offered_contract_years,
               p.name AS player_name, p.ovr
        FROM transfer_offers to2
        JOIN players p ON p.id = to2.player_id
        WHERE to2.save_id = ? AND to2.status = 'negotiating'
          AND to2.player_response_date IS NOT NULL
          AND to2.player_response_date <= ?
        """,
        (int(save_id), current_date),
    ).fetchall()
    for row in rows:
        result = complete_transfer(
            conn, save_id, int(row["id"]), str(row["player_id"]),
            to_club_id, to_club_name,
            int(row["offered_wage"]), int(row["offered_contract_years"]),
            current_date, int(row["ovr"]), user_league_position,
        )
        if result.get("ok"):
            # Deduct transfer fee from balance
            offer_row = conn.execute(
                "SELECT offer_amount FROM transfer_offers WHERE id = ?", (int(row["id"]),)
            ).fetchone()
            if offer_row:
                apply_transfer_fee(conn, save_id, int(offer_row["offer_amount"]), "out", str(row["player_name"]), current_date)


def complete_transfer(
    conn: sqlite3.Connection,
    save_id: int,
    offer_id: int,
    player_id: str,
    to_club_id: str,
    to_club_name: str,
    weekly_wage: int,
    contract_years: int,
    current_date: str,
    player_ovr: int,
    user_league_position: int = 4,
) -> dict:
    num_clubs = max(1, conn.execute("SELECT COUNT(*) AS c FROM clubs").fetchone()["c"])
    prestige = max(0.0, (num_clubs - user_league_position) / max(1, num_clubs - 1))
    market_rate = player_ovr * 600
    wage_ratio = min(3.0, weekly_wage / max(1, market_rate))
    accept_prob = min(0.97, max(0.05,
        0.50 * wage_ratio
        + 0.30 * prestige
        + 0.20 * random.uniform(0.5, 1.5)
    ))
    player_accepts = random.random() < accept_prob
    player_row = conn.execute("SELECT name FROM players WHERE id = ?", (player_id,)).fetchone()
    player_name = str(player_row["name"]) if player_row else player_id

    if not player_accepts:
        attempt_row = conn.execute("SELECT negotiation_attempt FROM transfer_offers WHERE id = ?", (int(offer_id),)).fetchone()
        current_attempt = int(attempt_row["negotiation_attempt"]) if attempt_row else 1
        if current_attempt < 3:
            conn.execute(
                "UPDATE transfer_offers SET status = 'accepted', negotiation_attempt = ? WHERE id = ?",
                (current_attempt + 1, int(offer_id)),
            )
            remaining = 3 - current_attempt
            add_save_message(
                conn, save_id, "transfers",
                "PLAYER REJECTED TERMS",
                f"{player_name} rejected the offer. {remaining} attempt{'s' if remaining != 1 else ''} remaining — try higher wage or longer contract.",
                current_date, "warning",
                f"player_rejected:{offer_id}:{current_attempt}",
            )
            return {"ok": False, "reason": "player_rejected", "retries_left": remaining}
        conn.execute(
            "UPDATE transfer_offers SET status = 'negotiating_failed' WHERE id = ?",
            (int(offer_id),),
        )
        add_save_message(
            conn, save_id, "transfers",
            "PLAYER REJECTED TERMS — DEAL DEAD",
            f"{player_name} rejected all contract offers. The deal is off.",
            current_date, "warning",
            f"player_rejected_final:{offer_id}",
        )
        return {"ok": False, "reason": "player_rejected", "retries_left": 0}

    conn.execute(
        """
        INSERT INTO save_player_club (save_id, player_id, club_id)
        VALUES (?, ?, ?)
        ON CONFLICT(save_id, player_id) DO UPDATE SET club_id = excluded.club_id
        """,
        (int(save_id), player_id, to_club_id),
    )
    conn.execute(
        """
        INSERT INTO player_contracts (save_id, player_id, club_id, weekly_wage, contract_years, start_date)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(save_id, player_id) DO UPDATE SET
            club_id = excluded.club_id,
            weekly_wage = excluded.weekly_wage,
            contract_years = excluded.contract_years,
            start_date = excluded.start_date
        """,
        (int(save_id), player_id, to_club_id, int(weekly_wage), int(contract_years), current_date),
    )
    conn.execute(
        "UPDATE transfer_offers SET status = 'completed' WHERE id = ?",
        (int(offer_id),),
    )
    conn.execute(
        "UPDATE transfer_market SET status = 'sold' WHERE save_id = ? AND player_id = ?",
        (int(save_id), player_id),
    )
    add_save_message(
        conn, save_id, "transfers",
        "TRANSFER COMPLETE",
        f"{player_name} has joined {to_club_name} on a {contract_years}-year contract.",
        current_date, "success",
        f"transfer_done:{offer_id}",
    )
    return {"ok": True, "player_name": player_name}


def get_inbound_transfer_offers(conn: sqlite3.Connection, save_id: int, managed_club_id: str) -> List[dict]:
    """AI offers to buy user-listed players (pending_user_accept status)."""
    rows = conn.execute(
        """
        SELECT to2.id, to2.player_id, to2.offer_amount, to2.created_date,
               to2.window_type, to2.season_year, to2.offering_club_id,
               p.name AS player_name, p.position, p.ovr, p.age,
               oc.name AS offering_club_name,
               cb.template_id AS badge_template_id,
               cb.primary_color AS badge_primary,
               cb.secondary_color AS badge_secondary,
               cb.border_color AS badge_border
        FROM transfer_offers to2
        JOIN players p ON p.id = to2.player_id
        JOIN transfer_market tm ON tm.save_id = to2.save_id
            AND tm.player_id = to2.player_id
            AND tm.season_year = to2.season_year
            AND tm.window_type = to2.window_type
        LEFT JOIN clubs oc ON oc.id = to2.offering_club_id
        LEFT JOIN club_badges cb ON cb.club_id = to2.offering_club_id
        WHERE to2.save_id = ? AND to2.status = 'pending_user_accept'
          AND tm.listed_club_id = ?
        ORDER BY to2.id DESC
        """,
        (int(save_id), managed_club_id),
    ).fetchall()
    return [dict(r) for r in rows]


def accept_inbound_offer(conn: sqlite3.Connection, save_id: int, offer_id: int, current_date: str, managed_club_id: str) -> dict:
    """User accepts an AI inbound offer — sell the player, receive transfer fee."""
    row = conn.execute(
        """
        SELECT to2.player_id, to2.offer_amount, to2.window_type, to2.season_year,
               p.name AS player_name
        FROM transfer_offers to2
        JOIN players p ON p.id = to2.player_id
        WHERE to2.id = ? AND to2.save_id = ? AND to2.status = 'pending_user_accept'
        """,
        (int(offer_id), int(save_id)),
    ).fetchone()
    if not row:
        return {"ok": False, "error": "not_found"}
    player_id = str(row["player_id"])
    amount = int(row["offer_amount"])
    player_name = str(row["player_name"])
    conn.execute("UPDATE transfer_offers SET status = 'completed' WHERE id = ?", (int(offer_id),))
    conn.execute(
        "UPDATE transfer_market SET status = 'sold' WHERE save_id = ? AND player_id = ?",
        (int(save_id), player_id),
    )
    # Move player to a placeholder club (remove from user's squad)
    conn.execute(
        """
        INSERT INTO save_player_club (save_id, player_id, club_id)
        VALUES (?, ?, 'SOLD')
        ON CONFLICT(save_id, player_id) DO UPDATE SET club_id = 'SOLD'
        """,
        (int(save_id), player_id),
    )
    apply_transfer_fee(conn, save_id, amount, "in", player_name, current_date)
    add_save_message(
        conn, save_id, "transfers",
        "PLAYER SOLD",
        f"{player_name} has been sold for £{amount // 1_000_000}M." if amount >= 1_000_000 else f"{player_name} has been sold for £{amount // 1_000}K.",
        current_date, "success",
        f"sold:{save_id}:{player_id}:{current_date}",
    )
    return {"ok": True, "player_name": player_name, "amount": amount}


def decline_inbound_offer(conn: sqlite3.Connection, save_id: int, offer_id: int) -> None:
    conn.execute(
        "UPDATE transfer_offers SET status = 'rejected' WHERE id = ? AND save_id = ?",
        (int(offer_id), int(save_id)),
    )


def load_transfer_data(conn: sqlite3.Connection, save_id: int, managed_club_id: str) -> dict:
    market = get_transfer_market_listings(conn, save_id)
    listings = get_user_transfer_listings(conn, save_id, managed_club_id)
    accepted = get_accepted_offers(conn, save_id)
    my_offers = get_all_user_offers(conn, save_id)
    inbound_offers = get_inbound_transfer_offers(conn, save_id, managed_club_id)
    listed_ids = {str(r["player_id"]) for r in market + listings}
    pending_offer_player_ids = {
        str(o["player_id"]) for o in my_offers
        if str(o.get("status", "")) in ("pending", "accepted", "negotiating")
    }
    # Players where user has used all 3 offers and all are rejected (no more offers this window)
    exhausted_offer_player_ids: set[str] = set()
    for listing in market:
        pid = str(listing["player_id"])
        if pid in pending_offer_player_ids:
            continue
        window_type = str(listing.get("window_type", ""))
        season_year = int(listing.get("season_year", 0))
        row = conn.execute(
            "SELECT COUNT(*) AS total, SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) AS rejected_count FROM transfer_offers WHERE save_id=? AND player_id=? AND window_type=? AND season_year=?",
            (int(save_id), pid, window_type, season_year),
        ).fetchone()
        if row and int(row["total"]) >= 3 and int(row["rejected_count"] or 0) >= 3:
            exhausted_offer_player_ids.add(pid)
    return {
        "market": market,
        "user_listings": listings,
        "accepted_offers": accepted,
        "my_offers": my_offers,
        "inbound_offers": inbound_offers,
        "listed_player_ids": list(listed_ids),
        "pending_offer_player_ids": list(pending_offer_player_ids),
        "exhausted_offer_player_ids": list(exhausted_offer_player_ids),
    }


# ---------------------------------------------------------------------------
# Club Finances
# ---------------------------------------------------------------------------

def _ensure_save_finances(conn: sqlite3.Connection, save_id: int) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO save_finances (save_id) VALUES (?)
        """,
        (int(save_id),),
    )


def get_save_finances(conn: sqlite3.Connection, save_id: int) -> dict:
    _ensure_save_finances(conn, save_id)
    row = conn.execute(
        "SELECT * FROM save_finances WHERE save_id = ?",
        (int(save_id),),
    ).fetchone()
    if row is None:
        return {
            "balance": 25_000_000,
            "transfer_budget": 10_000_000,
            "wage_budget_weekly": 500_000,
            "season_income_matchday": 0,
            "season_income_sponsor": 0,
            "season_income_transfers": 0,
            "season_expenses_wages": 0,
            "season_expenses_transfers": 0,
        }
    return dict(row)


def _log_finance_transaction(
    conn: sqlite3.Connection,
    save_id: int,
    category: str,
    amount: int,
    description: str,
    transaction_date: str,
) -> None:
    conn.execute(
        "INSERT INTO finance_transactions (save_id, category, amount, description, transaction_date) VALUES (?, ?, ?, ?, ?)",
        (int(save_id), category, int(amount), description, transaction_date),
    )


def apply_matchday_revenue(
    conn: sqlite3.Connection,
    save_id: int,
    is_home: bool,
    current_date: str,
    club_league_position: int = 4,
) -> int:
    _ensure_save_finances(conn, save_id)
    # Home gates earn more; away games earn nothing (simplification)
    if not is_home:
        return 0
    # £150K base + bonus for larger clubs (proxy: lower position = more fans)
    gate_revenue = max(100_000, 400_000 - (club_league_position - 1) * 30_000)
    conn.execute(
        """
        UPDATE save_finances
        SET balance = balance + ?,
            season_income_matchday = season_income_matchday + ?
        WHERE save_id = ?
        """,
        (gate_revenue, gate_revenue, int(save_id)),
    )
    _log_finance_transaction(conn, save_id, "matchday", gate_revenue, "Matchday gate revenue", current_date)
    return gate_revenue


def apply_weekly_finances(
    conn: sqlite3.Connection,
    save_id: int,
    club_id: str,
    current_date: str,
    club_league_position: int = 4,
) -> None:
    _ensure_save_finances(conn, save_id)
    # Sponsor income: £200K/wk for mid-table, scales with position
    sponsor_weekly = max(100_000, 350_000 - (club_league_position - 1) * 30_000)
    # Wage bill: sum of player contracts for this club in this save, fallback default
    wage_row = conn.execute(
        "SELECT COALESCE(SUM(weekly_wage), 0) AS total FROM player_contracts WHERE save_id = ? AND club_id = ?",
        (int(save_id), club_id),
    ).fetchone()
    wage_bill = int(wage_row["total"] or 0)
    if wage_bill == 0:
        wage_bill = 50_000  # default squad wage bill before any contracts are signed
    net = sponsor_weekly - wage_bill
    conn.execute(
        """
        UPDATE save_finances
        SET balance = balance + ?,
            season_income_sponsor = season_income_sponsor + ?,
            season_expenses_wages = season_expenses_wages + ?
        WHERE save_id = ?
        """,
        (net, sponsor_weekly, wage_bill, int(save_id)),
    )
    _log_finance_transaction(conn, save_id, "sponsor", sponsor_weekly, "Weekly sponsorship income", current_date)
    _log_finance_transaction(conn, save_id, "wages", -wage_bill, "Weekly player wages", current_date)


def apply_transfer_fee(
    conn: sqlite3.Connection,
    save_id: int,
    amount: int,
    direction: str,  # "in" or "out"
    player_name: str,
    current_date: str,
) -> None:
    _ensure_save_finances(conn, save_id)
    if direction == "in":
        conn.execute(
            "UPDATE save_finances SET balance = balance + ?, transfer_budget = transfer_budget + ?, season_income_transfers = season_income_transfers + ? WHERE save_id = ?",
            (amount, amount, amount, int(save_id)),
        )
        _log_finance_transaction(conn, save_id, "transfer_in", amount, f"Transfer fee received: {player_name}", current_date)
    else:
        conn.execute(
            "UPDATE save_finances SET balance = balance - ?, transfer_budget = MAX(0, transfer_budget - ?), season_expenses_transfers = season_expenses_transfers + ? WHERE save_id = ?",
            (amount, amount, amount, int(save_id)),
        )
        _log_finance_transaction(conn, save_id, "transfer_out", -amount, f"Transfer fee paid: {player_name}", current_date)


def get_finance_transactions(conn: sqlite3.Connection, save_id: int, limit: int = 20) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM finance_transactions WHERE save_id = ? ORDER BY id DESC LIMIT ?",
        (int(save_id), int(limit)),
    ).fetchall()
    return [dict(r) for r in rows]


STAFF_WEEKLY_SALARIES: dict[str, dict[str, int]] = {
    "scout": {"average": 500, "good": 1500, "best": 3500},
    "physio": {"average": 500, "good": 1500, "best": 3500},
    "academy_coach": {"average": 600, "good": 1800, "best": 4000},
    "assistant_coach": {"average": 700, "good": 2000, "best": 5000},
}

SCOUT_DAYS: dict[str, int] = {"average": 10, "good": 8, "best": 7}
SCOUT_PCT_RANGE: dict[str, tuple[int, int]] = {
    "average": (15, 25),
    "good": (19, 35),
    "best": (25, 50),
}


def get_club_staff(conn: sqlite3.Connection, save_id: int) -> dict[str, str]:
    rows = conn.execute(
        "SELECT staff_type, quality FROM club_staff WHERE save_id = ?",
        (int(save_id),),
    ).fetchall()
    return {str(r["staff_type"]): str(r["quality"]) for r in rows}


def set_club_staff(conn: sqlite3.Connection, save_id: int, staff_type: str, quality: str) -> None:
    conn.execute(
        """
        INSERT INTO club_staff (save_id, staff_type, quality)
        VALUES (?, ?, ?)
        ON CONFLICT(save_id, staff_type) DO UPDATE SET quality=excluded.quality
        """,
        (int(save_id), str(staff_type), str(quality)),
    )


def get_player_scouting_pct(conn: sqlite3.Connection, save_id: int, player_id: str, season_year: int) -> int:
    row = conn.execute(
        "SELECT revealed_pct FROM player_scouting WHERE save_id=? AND player_id=? AND season_year=?",
        (int(save_id), str(player_id), int(season_year)),
    ).fetchone()
    return int(row["revealed_pct"]) if row else 50


def submit_scout_task(
    conn: sqlite3.Connection,
    save_id: int,
    player_id: str,
    player_name: str,
    due_date: str,
    scout_quality: str,
    pct_min: int,
    pct_max: int,
) -> bool:
    save_row = conn.execute("SELECT season_year FROM saves WHERE id=?", (int(save_id),)).fetchone()
    season_year = int(save_row["season_year"]) if save_row else 0
    if get_player_scouting_pct(conn, save_id, player_id, season_year) >= 100:
        return False
    conn.execute(
        """
        INSERT INTO pending_scout_tasks (save_id, player_id, player_name, due_date, scout_quality, pct_min, pct_max)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (int(save_id), str(player_id), str(player_name), str(due_date), str(scout_quality), int(pct_min), int(pct_max)),
    )
    return True


def check_and_complete_scout_tasks(conn: sqlite3.Connection, save_id: int, current_date: str) -> list[dict]:
    import random as _random
    rows = conn.execute(
        "SELECT * FROM pending_scout_tasks WHERE save_id=? AND due_date <= ?",
        (int(save_id), str(current_date)),
    ).fetchall()
    completed = []
    for row in rows:
        player_id = str(row["player_id"])
        player_name = str(row["player_name"])
        pct_min = int(row["pct_min"])
        pct_max = int(row["pct_max"])
        save_row = conn.execute("SELECT season_year FROM saves WHERE id=?", (int(save_id),)).fetchone()
        season_year = int(save_row["season_year"]) if save_row else 0
        current_pct = get_player_scouting_pct(conn, save_id, player_id, season_year)
        if current_pct < 100:
            gain = _random.randint(pct_min, pct_max)
            new_pct = min(100, current_pct + gain)
            conn.execute(
                """
                INSERT INTO player_scouting (save_id, player_id, season_year, revealed_pct)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(save_id, player_id, season_year) DO UPDATE SET revealed_pct=excluded.revealed_pct
                """,
                (int(save_id), str(player_id), int(season_year), int(new_pct)),
            )
            completed.append({
                "player_id": player_id,
                "player_name": player_name,
                "old_pct": current_pct,
                "new_pct": new_pct,
                "gain": new_pct - current_pct,
            })
        conn.execute("DELETE FROM pending_scout_tasks WHERE id=?", (int(row["id"]),))
    return completed


def has_pending_scout_task(conn: sqlite3.Connection, save_id: int, player_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM pending_scout_tasks WHERE save_id=? AND player_id=? LIMIT 1",
        (save_id, player_id),
    ).fetchone()
    return row is not None


def get_all_scouting_data(conn: sqlite3.Connection, save_id: int, season_year: int) -> list[dict]:
    """Return combined list of all scouted/active-scout entries for a save."""
    rows = conn.execute(
        "SELECT player_id, revealed_pct FROM player_scouting WHERE save_id=? AND season_year=?",
        (save_id, season_year),
    ).fetchall()
    pct_map: dict[str, int] = {str(r["player_id"]): int(r["revealed_pct"]) for r in rows}

    pending_rows = conn.execute(
        "SELECT player_id, player_name, due_date, scout_quality FROM pending_scout_tasks WHERE save_id=?",
        (save_id,),
    ).fetchall()
    pending_map: dict[str, dict] = {
        str(r["player_id"]): {
            "player_name": str(r["player_name"]),
            "due_date": str(r["due_date"]),
            "scout_quality": str(r["scout_quality"]),
        }
        for r in pending_rows
    }

    entries: list[dict] = []
    seen: set[str] = set()

    for pid, info in pending_map.items():
        seen.add(pid)
        entries.append({
            "player_id": pid,
            "player_name": info["player_name"],
            "revealed_pct": pct_map.get(pid, 50),
            "is_pending": True,
            "due_date": info["due_date"],
            "scout_quality": info["scout_quality"],
        })

    for pid, pct in pct_map.items():
        if pid in seen:
            continue
        entries.append({
            "player_id": pid,
            "player_name": pid,
            "revealed_pct": pct,
            "is_pending": False,
            "due_date": None,
            "scout_quality": None,
        })

    return entries
