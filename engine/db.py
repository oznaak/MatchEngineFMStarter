from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List

from .loader import merge_player_attributes
from .models import Club, PlayerProfile

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

        CREATE TABLE IF NOT EXISTS players (
            id TEXT PRIMARY KEY,
            club_id TEXT NOT NULL,
            name TEXT NOT NULL,
            position TEXT NOT NULL,
            ovr INTEGER NOT NULL,
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
        """
    )
    conn.commit()


def db_has_seed_data(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT COUNT(*) AS count FROM clubs").fetchone()
    return row is not None and int(row["count"]) > 0


def import_league_json_to_db(conn: sqlite3.Connection, json_path: Path, *, seed_conditions: bool) -> None:
    raw = json.loads(json_path.read_text(encoding="utf-8"))
    club_rows = []
    tactic_rows = []
    color_rows = []
    player_rows = []
    attribute_rows = []
    condition_rows = []

    for club_data in raw["clubs"]:
        club_id = club_data["id"].upper()
        club_rows.append((club_id, club_data["name"]))

        tactics = dict(DEFAULT_TACTICS)
        tactics.update({k: float(v) for k, v in club_data.get("tactics", {}).items() if k in DEFAULT_TACTICS})
        for key, value in tactics.items():
            tactic_rows.append((club_id, key, float(value)))

        colors = dict(DEFAULT_COLORS)
        colors.update({k: v for k, v in club_data.get("colors", {}).items() if k in DEFAULT_COLORS and isinstance(v, str) and v})
        for key, value in colors.items():
            color_rows.append((club_id, key, value))

        for player in club_data["players"]:
            player_id = player["id"]
            player_rows.append((player_id, club_id, player["name"], player["position"], int(player["ovr"])))
            attributes = merge_player_attributes(int(player["ovr"]), player["position"], player.get("attributes"))
            for key, value in attributes.items():
                attribute_rows.append((player_id, key, float(value)))
            if seed_conditions:
                condition_rows.append((player_id, float(player.get("current_stamina", 100.0)), 0))

    conn.executemany(
        "INSERT INTO clubs (id, name) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET name=excluded.name",
        club_rows,
    )
    conn.executemany(
        """
        INSERT INTO club_tactics (club_id, key, value) VALUES (?, ?, ?)
        ON CONFLICT(club_id, key) DO UPDATE SET value=excluded.value
        """,
        tactic_rows,
    )
    conn.executemany(
        """
        INSERT INTO club_colors (club_id, key, value) VALUES (?, ?, ?)
        ON CONFLICT(club_id, key) DO UPDATE SET value=excluded.value
        """,
        color_rows,
    )
    conn.executemany(
        """
        INSERT INTO players (id, club_id, name, position, ovr)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            club_id=excluded.club_id,
            name=excluded.name,
            position=excluded.position,
            ovr=excluded.ovr
        """,
        player_rows,
    )
    conn.executemany(
        """
        INSERT INTO player_attributes (player_id, key, value) VALUES (?, ?, ?)
        ON CONFLICT(player_id, key) DO UPDATE SET value=excluded.value
        """,
        attribute_rows,
    )
    if condition_rows:
        conn.executemany(
            """
            INSERT INTO player_condition (player_id, current_stamina, updated_day)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET
                current_stamina=excluded.current_stamina,
                updated_day=excluded.updated_day
            """,
            condition_rows,
        )
    conn.commit()


def bootstrap_database(conn: sqlite3.Connection, json_path: Path) -> None:
    initialize_schema(conn)
    import_league_json_to_db(conn, json_path, seed_conditions=not db_has_seed_data(conn))


def load_clubs_from_db(conn: sqlite3.Connection) -> Dict[str, Club]:
    club_rows = conn.execute("SELECT id, name FROM clubs ORDER BY id").fetchall()
    tactic_rows = conn.execute("SELECT club_id, key, value FROM club_tactics").fetchall()
    color_rows = conn.execute("SELECT club_id, key, value FROM club_colors").fetchall()
    player_rows = conn.execute(
        """
        SELECT p.id, p.club_id, p.name, p.position, p.ovr, pc.current_stamina
        FROM players p
        LEFT JOIN player_condition pc ON pc.player_id = p.id
        ORDER BY p.club_id, p.id
        """
    ).fetchall()
    attribute_rows = conn.execute("SELECT player_id, key, value FROM player_attributes").fetchall()

    tactics_by_club: Dict[str, Dict[str, float]] = {}
    for row in tactic_rows:
        tactics_by_club.setdefault(str(row["club_id"]), dict(DEFAULT_TACTICS))[str(row["key"])] = float(row["value"])

    colors_by_club: Dict[str, Dict[str, str]] = {}
    for row in color_rows:
        colors_by_club.setdefault(str(row["club_id"]), dict(DEFAULT_COLORS))[str(row["key"])] = str(row["value"])

    attrs_by_player: Dict[str, Dict[str, float]] = {}
    for row in attribute_rows:
        attrs_by_player.setdefault(str(row["player_id"]), {})[str(row["key"])] = float(row["value"])

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
                attributes=dict(attrs_by_player.get(player_id, {})),
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
        )
    return clubs


def get_current_day(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT value FROM metadata WHERE key = 'current_day'").fetchone()
    if row is None:
        return 0
    return int(row["value"])


def set_current_day(conn: sqlite3.Connection, current_day: int) -> None:
    conn.execute(
        """
        INSERT INTO metadata (key, value) VALUES ('current_day', ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """,
        (str(int(current_day)),),
    )
    conn.commit()


def load_player_condition(conn: sqlite3.Connection, player_id: str) -> float | None:
    row = conn.execute(
        "SELECT current_stamina FROM player_condition WHERE player_id = ?",
        (player_id,),
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
