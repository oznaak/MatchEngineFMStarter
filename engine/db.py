from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List

from .loader import merge_player_attributes
from .models import Club, PlayerProfile, infer_preferred_foot, normalize_player_instruction_map, normalize_preferred_foot, normalize_team_instructions

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
            name TEXT NOT NULL
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
        """
    )
    _ensure_column(conn, "saves", "season_year", "INTEGER")
    _ensure_column(conn, "saves", "current_date", "TEXT")
    _ensure_column(conn, "fixtures", "fixture_date", "TEXT")
    _ensure_column(conn, "fixtures", "report_json", "TEXT")
    _ensure_column(conn, "save_club_setups", "instructions_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(conn, "save_club_setups", "player_instructions_json", "TEXT NOT NULL DEFAULT '{}'")
    _ensure_column(conn, "players", "preferred_foot", "TEXT NOT NULL DEFAULT 'right'")
    _backfill_player_feet(conn)
    _backfill_player_attributes(conn)
    _backfill_calendar_fields(conn)
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
        SELECT id, current_day, season_year, current_date, created_at
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
    club_rows = conn.execute("SELECT id, name FROM clubs ORDER BY id").fetchall()
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
        player_rows = conn.execute(
            """
            SELECT p.id, p.club_id, p.name, p.position, p.ovr, spc.current_stamina
                 , p.preferred_foot
            FROM players p
            LEFT JOIN save_player_condition spc
              ON spc.player_id = p.id AND spc.save_id = ?
            ORDER BY p.club_id, p.id
            """,
            (int(save_id),),
        ).fetchall()
    attribute_rows = conn.execute("SELECT player_id, key, value FROM player_attributes").fetchall()
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

    players_by_club: Dict[str, List[PlayerProfile]] = {}
    for row in player_rows:
        player_id = str(row["id"])
        club_id = str(row["club_id"])
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
            )
        )

    clubs: Dict[str, Club] = {}
    for row in club_rows:
        club_id = str(row["id"])
        clubs[club_id] = Club(
            id=club_id,
            name=str(row["name"]),
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
        SELECT c.id, c.name, cc.value AS primary_color, cs.value AS secondary_color,
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
        GROUP BY c.id, c.name, lc.display_order, cc.value, cs.value,
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
    attribute_rows = conn.execute(
        """
        SELECT p.id AS player_id, pa.key, pa.value
        FROM players p
        LEFT JOIN player_attributes pa ON pa.player_id = p.id
        WHERE p.club_id = ?
        """,
        (club_id,),
    ).fetchall()
    attrs_by_player: Dict[str, Dict[str, float]] = {}
    for row in attribute_rows:
        if row["key"] is None:
            continue
        attrs_by_player.setdefault(str(row["player_id"]), {})[str(row["key"])] = float(row["value"])
    if save_id is None:
        rows = conn.execute(
            """
            SELECT p.id, p.name, p.position, p.ovr, pc.current_stamina
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
        rows = conn.execute(
            """
            SELECT p.id, p.name, p.position, p.ovr, spc.current_stamina
                 , p.preferred_foot
            FROM players p
            LEFT JOIN save_player_condition spc
              ON spc.player_id = p.id AND spc.save_id = ?
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
            (int(save_id), club_id),
        ).fetchall()
    return [
        {
            "id": str(row["id"]),
            "name": str(row["name"]),
            "position": str(row["position"]),
            "ovr": int(row["ovr"]),
            "preferred_foot": normalize_preferred_foot(row["preferred_foot"]),
            "current_stamina": float(row["current_stamina"]) if row["current_stamina"] is not None else 100.0,
            "attributes": merge_player_attributes(
                int(row["ovr"]),
                str(row["position"]),
                dict(attrs_by_player.get(str(row["id"]), {})),
                player_id=str(row["id"]),
                name=str(row["name"]),
            ),
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


def normalize_new_save_player_condition(conn: sqlite3.Connection, save_id: int) -> None:
    save_row = conn.execute(
        "SELECT current_day FROM saves WHERE id = ?",
        (int(save_id),),
    ).fetchone()
    if save_row is None or int(save_row["current_day"] or 0) != 0:
        return
    played_row = conn.execute(
        "SELECT COUNT(*) AS count FROM fixtures WHERE save_id = ? AND played = 1",
        (int(save_id),),
    ).fetchone()
    if played_row is not None and int(played_row["count"] or 0) > 0:
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
    _seed_fixtures_for_save(conn, save_id, league_id, season_year)
    seed_save_player_condition_defaults(conn, save_id)
    seed_save_club_setups(conn, save_id)
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
    conn.execute("DELETE FROM save_club_setups WHERE save_id = ?", (int(save_id),))
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


def load_save_overview(conn: sqlite3.Connection, save_id: int) -> dict | None:
    seed_save_player_condition_defaults(conn, save_id)
    seed_save_club_setups(conn, save_id)
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
    for club_players in players_by_club.values():
        for player in club_players:
            totals = season_totals.get(player["id"], {})
            player["apps"] = int(totals.get("apps", 0))
            player["goals"] = int(totals.get("goals", 0))
            player["assists"] = int(totals.get("assists", 0))
    next_fixture = get_next_fixture_for_save(conn, save_id, club_id)
    current_date = str(save_row["current_date"] or season_start_date(int(save_row["season_year"] or current_season_year())).isoformat())
    today_fixture = get_playable_fixture_for_save(conn, save_id, club_id, current_date)
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
        "fixtures": list_save_fixtures(conn, save_id),
        "next_fixture": next_fixture,
        "today_fixture": today_fixture,
    }


def list_save_fixtures(conn: sqlite3.Connection, save_id: int) -> List[dict]:
    rows = conn.execute(
        """
        SELECT f.id, f.match_day, f.fixture_date, hc.name AS home_name, ac.name AS away_name,
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
            "fixture_date": str(row["fixture_date"] or ""),
            "fixture_date_label": format_game_date(str(row["fixture_date"] or "")),
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


def load_save_standings(conn: sqlite3.Connection, save_id: int) -> List[dict]:
    save_row = conn.execute("SELECT league_id FROM saves WHERE id = ?", (save_id,)).fetchone()
    if save_row is None:
        return []
    clubs = list_league_clubs(conn, str(save_row["league_id"]))
    table = {
        club["id"]: {
            "club_id": club["id"],
            "club_name": club["name"],
            "played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_difference": 0,
            "points": 0,
        }
        for club in clubs
    }

    rows = conn.execute(
        """
        SELECT home_club_id, away_club_id, home_goals, away_goals
        FROM fixtures
        WHERE save_id = ? AND played = 1
        """,
        (save_id,),
    ).fetchall()
    for row in rows:
        home_id = str(row["home_club_id"])
        away_id = str(row["away_club_id"])
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
            home["wins"] += 1
            away["losses"] += 1
            home["points"] += 3
        elif away_goals > home_goals:
            away["wins"] += 1
            home["losses"] += 1
            away["points"] += 3
        else:
            home["draws"] += 1
            away["draws"] += 1
            home["points"] += 1
            away["points"] += 1

    standings = list(table.values())
    for row in standings:
        row["goal_difference"] = row["goals_for"] - row["goals_against"]
    standings.sort(
        key=lambda row: (
            -row["points"],
            -row["goal_difference"],
            -row["goals_for"],
            row["club_name"],
        )
    )
    return standings


def _seed_fixtures_for_save(conn: sqlite3.Connection, save_id: int, league_id: str, season_year: int) -> None:
    club_rows = conn.execute(
        """
        SELECT club_id
        FROM league_clubs
        WHERE league_id = ?
        ORDER BY display_order, club_id
        """,
        (league_id,),
    ).fetchall()
    club_ids = [str(row["club_id"]) for row in club_rows]
    match_day = 1
    fixture_rows: List[tuple[int, int, str, str, str]] = []
    match_date = first_match_date(season_year)
    matches_per_round = max(1, len(club_ids) // 2)
    for home_id, away_id in _generate_double_round_robin(club_ids):
        fixture_rows.append((save_id, match_day, match_date.isoformat(), home_id, away_id))
        if len(fixture_rows) % matches_per_round == 0:
            match_day += 1
            match_date += timedelta(days=7)
    conn.executemany(
        """
        INSERT INTO fixtures (save_id, match_day, fixture_date, home_club_id, away_club_id)
        VALUES (?, ?, ?, ?, ?)
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
