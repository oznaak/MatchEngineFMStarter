# Multi-League Simulation, Cups & World Menu — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** All leagues simulate simultaneously, real promotion/relegation runs at season end, five domestic cups run with proper phases, and a World → Competitions menu exposes everything to the player.

**Architecture:** New `engine/simulation.py` handles Poisson AI match simulation and weekly AI transfers. New `engine/promotion.py` holds per-country relegation rules. New `engine/cups.py` holds cup configs and bracket seeding. `engine/db.py` grows five new tables and its daily-advance loop drives the new engines. `main.py`/`render.py` gain two new screens.

**Tech Stack:** Python 3.11, pygame 2.x, SQLite via `sqlite3`, existing `db_session` context manager.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `engine/db.py` | Modify | Schema additions, `create_save_game`, `advance_save_one_day`, `load_save_standings`, `save_fixture_result`, `complete_season_if_due`, `start_next_season_if_ready`, `delete_save_game`, new queries |
| `engine/simulation.py` | Create | Poisson AI fixture simulation, standings update, weekly AI transfers |
| `engine/promotion.py` | Create | Per-country promotion/relegation rules, `apply_promotion_relegation` |
| `engine/cups.py` | Create | Cup configs, `seed_cup_for_save`, `schedule_cup_draw`, `advance_cup_rounds` |
| `main.py` | Modify | `SCREEN_WORLD_COMPETITIONS`, `SCREEN_CUP_BRACKET` screen states, nav "WORLD" item, `_build_view`, `_handle_action` |
| `engine/render.py` | Modify | `draw_competitions_screen`, `draw_cup_bracket`, add "WORLD" to nav header |
| `tests/test_multi_league.py` | Create | Tests for new functions |

---

## Task 1: DB Schema Additions

**Files:**
- Modify: `engine/db.py` — `initialize_schema`, `_ensure_column` calls, `delete_save_game`
- Create: `tests/test_multi_league.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_multi_league.py`:

```python
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from engine.db import bootstrap_database, db_session

ROOT = Path(__file__).resolve().parents[1]
DB_TEMPLATE = ROOT / "data" / "game.db"


def prepare_test_db(db_path: Path) -> None:
    shutil.copyfile(DB_TEMPLATE, db_path)
    with db_session(db_path) as conn:
        bootstrap_database(conn)
        conn.execute("DELETE FROM fixtures")
        conn.execute("DELETE FROM saves")
        conn.execute("DELETE FROM managers")
        conn.execute("DELETE FROM metadata WHERE key IN ('active_save_id', 'current_day')")
        conn.commit()


def test_new_tables_exist():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        prepare_test_db(db_path)
        with db_session(db_path) as conn:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
            assert "competitions" in tables
            assert "cup_brackets" in tables
            assert "save_league_clubs" in tables
            assert "standings" in tables

def test_fixtures_has_new_columns():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        prepare_test_db(db_path)
        with db_session(db_path) as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(fixtures)").fetchall()}
            assert "competition_id" in cols
            assert "leg" in cols
            assert "is_neutral" in cols
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/oznaak/Documents/projects/MatchEngineFMStarter
source .venv/bin/activate
python -m pytest tests/test_multi_league.py -v
```

Expected: FAIL — tables not found.

- [ ] **Step 3: Add new tables to `initialize_schema` in `engine/db.py`**

Inside `initialize_schema`, add after the `pending_scout_tasks` table definition and before the closing `"""`):

```python
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
```

After `_backfill_player_ages(conn)` in `initialize_schema`, add:

```python
    _ensure_column(conn, "fixtures", "competition_id", "TEXT")
    _ensure_column(conn, "fixtures", "leg", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(conn, "fixtures", "is_neutral", "INTEGER NOT NULL DEFAULT 0")
```

- [ ] **Step 4: Update `delete_save_game` to clean new tables**

In `delete_save_game`, after `conn.execute("DELETE FROM save_messages WHERE save_id = ?", (int(save_id),))`, add:

```python
    conn.execute("DELETE FROM competitions WHERE save_id = ?", (int(save_id),))
    conn.execute("DELETE FROM cup_brackets WHERE save_id = ?", (int(save_id),))
    conn.execute("DELETE FROM save_league_clubs WHERE save_id = ?", (int(save_id),))
    conn.execute("DELETE FROM standings WHERE save_id = ?", (int(save_id),))
```

- [ ] **Step 5: Run test to verify it passes**

```bash
python -m pytest tests/test_multi_league.py::test_new_tables_exist tests/test_multi_league.py::test_fixtures_has_new_columns -v
```

Expected: PASS

- [ ] **Step 6: Verify existing tests still pass**

```bash
python -m pytest tests/test_match_engine.py -v --tb=short 2>&1 | tail -20
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add engine/db.py tests/test_multi_league.py
git commit -m "feat: add competitions, cup_brackets, save_league_clubs, standings tables"
```

---

## Task 2: Create `engine/simulation.py`

**Files:**
- Create: `engine/simulation.py`
- Test: `tests/test_multi_league.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_multi_league.py`:

```python
from engine.simulation import _poisson_sample, simulate_ai_fixture, _update_standings
from engine.db import create_save_game, load_save_standings


def test_poisson_sample_nonnegative():
    for lam in [0.5, 1.0, 1.35, 2.0]:
        for _ in range(20):
            assert _poisson_sample(lam) >= 0


def test_simulate_ai_fixture_marks_played():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        prepare_test_db(db_path)
        with db_session(db_path) as conn:
            save_id = create_save_game(conn, "Tester", "ENG1", "A")
            # grab any unplayed fixture that isn't club A's
            row = conn.execute(
                "SELECT id FROM fixtures WHERE save_id=? AND home_club_id != 'A' AND away_club_id != 'A' LIMIT 1",
                (save_id,)
            ).fetchone()
            if row is None:
                return  # nothing to test with current data
            fixture_id = int(row["id"])
            simulate_ai_fixture(conn, save_id, fixture_id)
            result = conn.execute(
                "SELECT played, home_goals, away_goals FROM fixtures WHERE id=?",
                (fixture_id,)
            ).fetchone()
            assert int(result["played"]) == 1
            assert result["home_goals"] is not None
            assert result["away_goals"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_multi_league.py::test_poisson_sample_nonnegative tests/test_multi_league.py::test_simulate_ai_fixture_marks_played -v
```

Expected: FAIL — `engine.simulation` not found.

- [ ] **Step 3: Create `engine/simulation.py`**

```python
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
    candidate = conn.execute(
        """
        SELECT id FROM players
        WHERE club_id NOT IN ({})
        ORDER BY RANDOM() LIMIT 1
        """.format(",".join("?" * len(league_club_ids))),
        list(league_club_ids),
    ).fetchone()
    if candidate:
        conn.execute(
            "UPDATE players SET club_id=? WHERE id=?",
            (club_id, str(candidate["id"])),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_multi_league.py::test_poisson_sample_nonnegative tests/test_multi_league.py::test_simulate_ai_fixture_marks_played -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/simulation.py tests/test_multi_league.py
git commit -m "feat: add Poisson AI fixture simulation engine"
```

---

## Task 3: Seed `save_league_clubs` + All-League Fixtures on Save Creation

**Files:**
- Modify: `engine/db.py` — `_seed_fixtures_for_save`, `create_save_game`
- Test: `tests/test_multi_league.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_multi_league.py`:

```python
def test_save_league_clubs_seeded_on_create():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        prepare_test_db(db_path)
        with db_session(db_path) as conn:
            save_id = create_save_game(conn, "Tester", "ENG1", "A")
            rows = conn.execute(
                "SELECT * FROM save_league_clubs WHERE save_id=?", (save_id,)
            ).fetchall()
            assert len(rows) > 0

def test_all_league_fixtures_seeded():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        prepare_test_db(db_path)
        with db_session(db_path) as conn:
            save_id = create_save_game(conn, "Tester", "ENG1", "A")
            league_ids = [r["id"] for r in conn.execute("SELECT id FROM leagues").fetchall()]
            assert len(league_ids) > 1  # multiple leagues present
            for lid in league_ids:
                comp_id_prefix = f"{lid}_"
                count = conn.execute(
                    "SELECT COUNT(*) AS c FROM fixtures WHERE save_id=? AND competition_id LIKE ?",
                    (save_id, comp_id_prefix + "%")
                ).fetchone()
                # each league should have fixtures (if it has clubs)
                clubs_in_league = conn.execute(
                    "SELECT COUNT(*) AS c FROM league_clubs WHERE league_id=?", (lid,)
                ).fetchone()
                if int(clubs_in_league["c"]) >= 2:
                    assert int(count["c"]) > 0, f"No fixtures for league {lid}"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_multi_league.py::test_save_league_clubs_seeded_on_create tests/test_multi_league.py::test_all_league_fixtures_seeded -v
```

Expected: FAIL

- [ ] **Step 3: Add `_seed_save_league_clubs` to `engine/db.py`**

Add this function before `_seed_fixtures_for_save`:

```python
def _seed_save_league_clubs(conn: sqlite3.Connection, save_id: int, season_year: int) -> None:
    rows = conn.execute("SELECT league_id, club_id FROM league_clubs").fetchall()
    conn.executemany(
        """
        INSERT OR IGNORE INTO save_league_clubs (save_id, league_id, club_id, season)
        VALUES (?, ?, ?, ?)
        """,
        [(save_id, str(r["league_id"]), str(r["club_id"]), season_year) for r in rows],
    )
```

- [ ] **Step 4: Modify `_seed_fixtures_for_save` to accept `competition_id`**

Replace the existing `_seed_fixtures_for_save` function with:

```python
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
```

- [ ] **Step 5: Modify `create_save_game` to seed all leagues**

In `create_save_game`, replace the single `_seed_fixtures_for_save(conn, save_id, league_id, season_year)` call with:

```python
    _seed_save_league_clubs(conn, save_id, season_year)
    all_leagues = conn.execute("SELECT id FROM leagues").fetchall()
    for league_row in all_leagues:
        lid = str(league_row["id"])
        _seed_fixtures_for_save(conn, save_id, lid, season_year)
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
python -m pytest tests/test_multi_league.py::test_save_league_clubs_seeded_on_create tests/test_multi_league.py::test_all_league_fixtures_seeded -v
```

Expected: PASS

- [ ] **Step 7: Verify existing tests still pass**

```bash
python -m pytest tests/test_match_engine.py -v --tb=short 2>&1 | tail -20
```

Expected: all pass (standings might have slight differences; if `load_save_standings` still works, we're good).

- [ ] **Step 8: Commit**

```bash
git add engine/db.py tests/test_multi_league.py
git commit -m "feat: seed all leagues and save_league_clubs on save creation"
```

---

## Task 4: Fix `load_save_standings` with `competition_id` Filter

**Files:**
- Modify: `engine/db.py` — `load_save_standings`, `save_fixture_result`
- Test: `tests/test_multi_league.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_multi_league.py`:

```python
from engine.db import save_fixture_result


def test_standings_filtered_by_competition():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        prepare_test_db(db_path)
        with db_session(db_path) as conn:
            save_id = create_save_game(conn, "Tester", "ENG1", "A")
            season_row = conn.execute("SELECT season_year FROM saves WHERE id=?", (save_id,)).fetchone()
            season = int(season_row["season_year"])
            comp_id = f"ENG1_{season}"
            # Simulate one AI fixture from ENG1
            row = conn.execute(
                "SELECT id FROM fixtures WHERE save_id=? AND competition_id=? LIMIT 1",
                (save_id, comp_id)
            ).fetchone()
            if row is None:
                return
            from engine.simulation import simulate_ai_fixture
            simulate_ai_fixture(conn, save_id, int(row["id"]))
            conn.commit()
            standings = load_save_standings(conn, save_id, competition_id=comp_id)
            assert len(standings) > 0
            total_played = sum(r["played"] for r in standings)
            assert total_played == 2  # one match = 1 played per team = 2 total
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_multi_league.py::test_standings_filtered_by_competition -v
```

Expected: FAIL — `load_save_standings` doesn't accept `competition_id`.

- [ ] **Step 3: Modify `load_save_standings` in `engine/db.py`**

Replace the full `load_save_standings` function with:

```python
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
          AND (competition_id = ? OR (competition_id IS NULL AND ? LIKE '%ENG1%'))
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
          AND (competition_id = ? OR (competition_id IS NULL AND ? LIKE '%ENG1%'))
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
```

- [ ] **Step 4: Update `save_fixture_result` to also update standings**

In `engine/db.py`, add this import at the top of the file (after existing imports):

```python
# deferred import to avoid circular — see simulate_ai_fixture
```

In `save_fixture_result`, after the `UPDATE fixtures` execute block and before the closing, add:

```python
    # Update pre-aggregated standings table for the competition
    if fixture_meta is not None:
        fid_row = conn.execute(
            "SELECT competition_id FROM fixtures WHERE id=?", (int(fixture_id),)
        ).fetchone()
        comp_id = str(fid_row["competition_id"] or "") if fid_row else ""
        if comp_id:
            save_id_val = fixture_meta[0]
            season_row = conn.execute(
                "SELECT season_year FROM saves WHERE id=?", (save_id_val,)
            ).fetchone()
            season = int(season_row["season_year"]) if season_row else 2025
            from .simulation import _update_standings
            _update_standings(
                conn, save_id_val, comp_id, season,
                str(fixture_meta[1]), str(fixture_meta[2]),
                int(home_goals), int(away_goals),
            )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/test_multi_league.py::test_standings_filtered_by_competition -v
python -m pytest tests/test_match_engine.py -v --tb=short 2>&1 | tail -20
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add engine/db.py tests/test_multi_league.py
git commit -m "feat: filter standings by competition_id, update standings on user match result"
```

---

## Task 5: Overhaul `advance_save_one_day` to Simulate All Leagues

**Files:**
- Modify: `engine/db.py` — `advance_save_one_day`
- Test: `tests/test_multi_league.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_multi_league.py`:

```python
from engine.db import advance_save_one_day, set_save_current_day


def test_ai_fixtures_simulated_on_advance():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        prepare_test_db(db_path)
        with db_session(db_path) as conn:
            save_id = create_save_game(conn, "Tester", "ENG1", "A")
            # advance enough days to get past first match day (day 38+ from season start)
            for _ in range(45):
                advance_save_one_day(conn, save_id, "A")
            conn.commit()
            # check that some non-A fixtures got simulated
            played_count = conn.execute(
                """
                SELECT COUNT(*) AS c FROM fixtures
                WHERE save_id=? AND played=1
                  AND home_club_id != 'A' AND away_club_id != 'A'
                """,
                (save_id,)
            ).fetchone()
            assert int(played_count["c"]) > 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_multi_league.py::test_ai_fixtures_simulated_on_advance -v
```

Expected: FAIL — AI fixtures not simulated.

- [ ] **Step 3: Modify `advance_save_one_day` in `engine/db.py`**

Replace the body of `advance_save_one_day` with:

```python
def advance_save_one_day(conn: sqlite3.Connection, save_id: int, managed_club_id: str | None) -> dict:
    if start_next_season_if_ready(conn, save_id):
        conn.commit()
        row = conn.execute(
            "SELECT current_day, saves.current_date AS current_date, season_year FROM saves WHERE id = ?",
            (int(save_id),),
        ).fetchone()
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

    # Simulate all non-user fixtures scheduled for today
    from .simulation import simulate_ai_fixture, simulate_ai_transfers
    ai_fixture_rows = conn.execute(
        """
        SELECT id FROM fixtures
        WHERE save_id = ? AND played = 0 AND fixture_date = ?
          AND home_club_id != ? AND away_club_id != ?
        """,
        (save_id, current_date_str, str(managed_club_id or ""), str(managed_club_id or "")),
    ).fetchall()
    for f_row in ai_fixture_rows:
        simulate_ai_fixture(conn, save_id, int(f_row["id"]))

    # Weekly AI transfers (every 7 days)
    if next_day % 7 == 0:
        simulate_ai_transfers(conn, save_id)

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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_multi_league.py::test_ai_fixtures_simulated_on_advance -v
python -m pytest tests/test_match_engine.py -v --tb=short 2>&1 | tail -20
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add engine/db.py tests/test_multi_league.py
git commit -m "feat: simulate all AI league fixtures daily in advance_save_one_day"
```

---

## Task 6: Create `engine/promotion.py` — Promotion & Relegation

**Files:**
- Create: `engine/promotion.py`
- Modify: `engine/db.py` — `complete_season_if_due`, `start_next_season_if_ready`
- Test: `tests/test_multi_league.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_multi_league.py`:

```python
from engine.promotion import get_promotion_relegation_plan, RELEGATION_RULES


def test_relegation_rules_defined_for_all_leagues():
    for league_pair in [("ENG1", "ENG2"), ("ESP1", "ESP2"), ("FRA1", "FRA2"), ("GER1", "GER2"), ("PRT1", "PRT2")]:
        top, bottom = league_pair
        assert top in RELEGATION_RULES or bottom in RELEGATION_RULES


def test_promotion_relegation_plan_england():
    # Build fake standings: 20 clubs, ordered by position
    standings_eng1 = [{"club_id": f"E1_{i:02d}", "position": i} for i in range(1, 21)]
    standings_eng2 = [{"club_id": f"E2_{i:02d}", "position": i} for i in range(1, 25)]
    plan = get_promotion_relegation_plan("ENG1", "ENG2", standings_eng1, standings_eng2)
    relegated = [m for m in plan if m["action"] == "relegate"]
    promoted_auto = [m for m in plan if m["action"] == "promote_auto"]
    assert len(relegated) == 3
    assert len(promoted_auto) == 2
    assert all(m["club_id"] in {s["club_id"] for s in standings_eng1} for m in relegated)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_multi_league.py::test_relegation_rules_defined_for_all_leagues tests/test_multi_league.py::test_promotion_relegation_plan_england -v
```

Expected: FAIL — `engine.promotion` not found.

- [ ] **Step 3: Create `engine/promotion.py`**

```python
from __future__ import annotations

import sqlite3
from typing import List, Dict

# Each entry: (auto_relegated, playoff_relegated_spots, auto_promoted, playoff_promoted_spots)
RELEGATION_RULES: Dict[str, tuple[int, int, int, int]] = {
    "ENG1": (3, 0, 0, 0),   # 3 relegated; ENG2 handles the 2 auto + 4 playoff
    "ENG2": (0, 0, 2, 4),   # top 2 auto-promoted; 3rd-6th playoff
    "ESP1": (3, 0, 0, 0),
    "ESP2": (0, 0, 2, 4),
    "FRA1": (1, 2, 0, 0),   # 18th direct, 16th-17th playoff vs FRA2 3rd-4th
    "FRA2": (0, 0, 2, 0),
    "GER1": (2, 1, 0, 0),   # bottom 2 direct, 16th playoff vs GER2 3rd
    "GER2": (0, 0, 2, 0),
    "PRT1": (2, 2, 0, 0),   # bottom 2 direct, 15th-16th playoff
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

    # Direct relegation: bottom N clubs of top league
    for club in top_sorted[-auto_rel:]:
        plan.append({"club_id": club["club_id"], "action": "relegate",
                     "from_league": top_league_id, "to_league": bottom_league_id})

    # Playoff relegation (e.g. FRA1: positions 16-17)
    if playoff_rel > 0:
        playoff_zone_start = -(auto_rel + playoff_rel)
        playoff_zone_end = -auto_rel
        for club in top_sorted[playoff_zone_start:playoff_zone_end]:
            plan.append({"club_id": club["club_id"], "action": "relegate_playoff",
                         "from_league": top_league_id, "to_league": bottom_league_id})

    # Direct promotion: top N clubs of bottom league
    for club in bot_sorted[:auto_prom]:
        plan.append({"club_id": club["club_id"], "action": "promote_auto",
                     "from_league": bottom_league_id, "to_league": top_league_id})

    # Playoff promotion: next N clubs of bottom league
    if playoff_prom > 0:
        for club in bot_sorted[auto_prom:auto_prom + playoff_prom]:
            plan.append({"club_id": club["club_id"], "action": "promote_playoff",
                         "from_league": bottom_league_id, "to_league": top_league_id})

    return plan


def apply_promotion_relegation(conn: sqlite3.Connection, save_id: int, season_year: int) -> None:
    from .db import load_save_standings

    for top_id, bot_id in TIER_PAIRS:
        top_comp = f"{top_id}_{season_year}"
        bot_comp = f"{bot_id}_{season_year}"
        top_standings = load_save_standings(conn, save_id, competition_id=top_comp)
        bot_standings = load_save_standings(conn, save_id, competition_id=bot_comp)
        if not top_standings or not bot_standings:
            continue
        plan = get_promotion_relegation_plan(top_id, bot_id, top_standings, bot_standings)
        next_season = season_year + 1
        for move in plan:
            club_id = move["club_id"]
            action = move["action"]
            from_league = move["from_league"]
            to_league = move["to_league"]
            # Direct moves: update save_league_clubs for next season
            if action in ("relegate", "promote_auto"):
                conn.execute(
                    "DELETE FROM save_league_clubs WHERE save_id=? AND league_id=? AND club_id=? AND season=?",
                    (save_id, from_league, club_id, next_season),
                )
                conn.execute(
                    """
                    INSERT OR IGNORE INTO save_league_clubs (save_id, league_id, club_id, season)
                    VALUES (?, ?, ?, ?)
                    """,
                    (save_id, to_league, club_id, next_season),
                )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_multi_league.py::test_relegation_rules_defined_for_all_leagues tests/test_multi_league.py::test_promotion_relegation_plan_england -v
```

Expected: PASS

- [ ] **Step 5: Hook `apply_promotion_relegation` into `complete_season_if_due`**

In `engine/db.py`, in `complete_season_if_due`, add before `conn.execute("UPDATE saves SET season_completed = 1 ...")`:

```python
    from .promotion import apply_promotion_relegation
    apply_promotion_relegation(conn, save_id, int(save_row["season_year"]))
```

Also generalize the champion message to use the actual league name instead of hardcoded "England Division I":

Replace:
```python
    body = (
        f"{champion['club_name']} win England Division I with {champion['points']} points, "
        ...
    )
```

With:
```python
    league_name_row = conn.execute(
        "SELECT l.name FROM saves s JOIN leagues l ON l.id = s.league_id WHERE s.id = ?",
        (int(save_id),)
    ).fetchone()
    league_display = str(league_name_row["name"]) if league_name_row else "the League"
    body = (
        f"{champion['club_name']} win {league_display} with {champion['points']} points, "
        f"{champion['wins']} wins and a {champion['goal_difference']:+d} goal difference."
    )
```

- [ ] **Step 6: Run all tests**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add engine/promotion.py engine/db.py tests/test_multi_league.py
git commit -m "feat: promotion/relegation rules and apply at season end"
```

---

## Task 7: Create `engine/cups.py` — Domestic Cup Configs & Seeding

**Files:**
- Create: `engine/cups.py`
- Modify: `engine/db.py` — `create_save_game`, `advance_save_one_day`, `start_next_season_if_ready`
- Test: `tests/test_multi_league.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_multi_league.py`:

```python
from engine.cups import seed_cup_for_save, advance_cup_rounds, CUP_CONFIGS


def test_cup_configs_defined():
    expected = {"FA_CUP", "TACA_PT", "COPA_REY", "COUPE_FR", "DFB_POKAL"}
    assert expected == set(CUP_CONFIGS.keys())


def test_fa_cup_seeded_on_save_create():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        prepare_test_db(db_path)
        with db_session(db_path) as conn:
            save_id = create_save_game(conn, "Tester", "ENG1", "A")
            season_row = conn.execute("SELECT season_year FROM saves WHERE id=?", (save_id,)).fetchone()
            season = int(season_row["season_year"])
            comp_id = f"FA_CUP_{season}"
            comp = conn.execute(
                "SELECT * FROM competitions WHERE save_id=? AND id=?", (save_id, comp_id)
            ).fetchone()
            assert comp is not None, "FA Cup competition not created"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_multi_league.py::test_cup_configs_defined tests/test_multi_league.py::test_fa_cup_seeded_on_save_create -v
```

Expected: FAIL

- [ ] **Step 3: Create `engine/cups.py`**

```python
from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta
from typing import Dict, List

# month is 1-indexed; day is the day within that month the round is scheduled
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
        """
        INSERT OR IGNORE INTO competitions (id, name, country, type, season, save_id)
        VALUES (?, ?, ?, 'cup', ?, ?)
        """,
        (comp_id, cfg["name"], cfg["country"], season_year, save_id),
    )
    # Collect clubs from all participating leagues
    all_clubs: List[str] = []
    for league_id in cfg["leagues"]:
        rows = conn.execute(
            """
            SELECT club_id FROM save_league_clubs
            WHERE save_id=? AND league_id=? AND season=?
            ORDER BY club_id
            """,
            (save_id, league_id, season_year),
        ).fetchall()
        if not rows:
            rows = conn.execute(
                "SELECT club_id FROM league_clubs WHERE league_id=? ORDER BY display_order, club_id",
                (league_id,),
            ).fetchall()
        all_clubs.extend(str(r["club_id"]) for r in rows)

    random.shuffle(all_clubs)
    first_round = cfg["rounds"][0]
    round_name = first_round["name"]
    round_date = _round_date(season_year, first_round["month"], first_round["day"])
    is_neutral = int(first_round.get("neutral", False))
    legs = int(first_round.get("legs", 1))

    # Pair clubs into bracket slots
    pairs = [(all_clubs[i], all_clubs[i + 1]) for i in range(0, len(all_clubs) - 1, 2)]
    for slot, (club_a, club_b) in enumerate(pairs):
        conn.execute(
            """
            INSERT INTO cup_brackets
                (save_id, competition_id, round, slot, club_a, club_b)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (save_id, comp_id, round_name, slot, club_a, club_b),
        )
        conn.execute(
            """
            INSERT INTO fixtures
                (save_id, match_day, fixture_date, home_club_id, away_club_id, competition_id, leg, is_neutral)
            VALUES (?, 0, ?, ?, ?, ?, 1, ?)
            """,
            (save_id, round_date.isoformat(), club_a, club_b, comp_id, is_neutral),
        )
        if legs == 2:
            leg2_date = round_date + timedelta(days=14)
            conn.execute(
                """
                INSERT INTO fixtures
                    (save_id, match_day, fixture_date, home_club_id, away_club_id, competition_id, leg, is_neutral)
                VALUES (?, 0, ?, ?, ?, ?, 2, ?)
                """,
                (save_id, leg2_date.isoformat(), club_b, club_a, comp_id, 0),
            )


def advance_cup_rounds(conn: sqlite3.Connection, save_id: int, current_date_str: str) -> None:
    current_date = date.fromisoformat(current_date_str)
    season_row = conn.execute("SELECT season_year FROM saves WHERE id=?", (save_id,)).fetchone()
    if season_row is None:
        return
    season_year = int(season_row["season_year"])

    for cup_key, cfg in CUP_CONFIGS.items():
        comp_id = f"{cup_key}_{season_year}"
        rounds = cfg["rounds"]
        for r_idx, round_cfg in enumerate(rounds[:-1]):
            next_round_cfg = rounds[r_idx + 1]
            round_name = round_cfg["name"]
            next_round_name = next_round_cfg["name"]

            # Check if this round's fixtures are all played and next round has no bracket yet
            played = conn.execute(
                """
                SELECT COUNT(*) AS c FROM fixtures
                WHERE save_id=? AND competition_id=? AND played=1
                  AND id IN (
                    SELECT f2.id FROM fixtures f2
                    JOIN cup_brackets cb ON cb.save_id=f2.save_id
                      AND cb.competition_id=f2.competition_id
                      AND (cb.club_a=f2.home_club_id OR cb.club_b=f2.home_club_id)
                    WHERE cb.round=? AND f2.competition_id=?
                  )
                """,
                (save_id, comp_id, round_name, comp_id),
            ).fetchone()
            unplayed = conn.execute(
                """
                SELECT COUNT(*) AS c FROM fixtures
                WHERE save_id=? AND competition_id=? AND played=0
                  AND id IN (
                    SELECT f2.id FROM fixtures f2
                    JOIN cup_brackets cb ON cb.save_id=f2.save_id
                      AND cb.competition_id=f2.competition_id
                      AND (cb.club_a=f2.home_club_id OR cb.club_b=f2.home_club_id)
                    WHERE cb.round=? AND f2.competition_id=?
                  )
                """,
                (save_id, comp_id, round_name, comp_id),
            ).fetchone()
            next_exists = conn.execute(
                "SELECT COUNT(*) AS c FROM cup_brackets WHERE save_id=? AND competition_id=? AND round=?",
                (save_id, comp_id, next_round_name),
            ).fetchone()
            if (int(played["c"]) > 0 and int(unplayed["c"]) == 0 and int(next_exists["c"]) == 0):
                _seed_next_cup_round(conn, save_id, comp_id, round_name, next_round_cfg, season_year)


def _seed_next_cup_round(
    conn: sqlite3.Connection,
    save_id: int,
    comp_id: str,
    completed_round: str,
    next_round_cfg: Dict,
    season_year: int,
) -> None:
    winners: List[str] = []
    brackets = conn.execute(
        "SELECT slot, club_a, club_b, winner FROM cup_brackets WHERE save_id=? AND competition_id=? AND round=? ORDER BY slot",
        (save_id, comp_id, completed_round),
    ).fetchall()
    for b in brackets:
        winner = str(b["winner"] or "")
        if not winner:
            # Determine winner from fixture result
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
                winner = str(fx["home_club_id"]) if hg > ag else str(fx["away_club_id"])
                conn.execute(
                    "UPDATE cup_brackets SET winner=? WHERE save_id=? AND competition_id=? AND round=? AND slot=?",
                    (winner, save_id, comp_id, completed_round, int(b["slot"])),
                )
        if winner:
            winners.append(winner)

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
            """
            INSERT INTO fixtures
                (save_id, match_day, fixture_date, home_club_id, away_club_id, competition_id, leg, is_neutral)
            VALUES (?, 0, ?, ?, ?, ?, 1, ?)
            """,
            (save_id, next_date.isoformat(), club_a, club_b, comp_id, is_neutral),
        )
        if legs == 2:
            leg2_date = next_date + timedelta(days=14)
            conn.execute(
                """
                INSERT INTO fixtures
                    (save_id, match_day, fixture_date, home_club_id, away_club_id, competition_id, leg, is_neutral)
                VALUES (?, 0, ?, ?, ?, ?, 2, ?)
                """,
                (save_id, leg2_date.isoformat(), club_b, club_a, comp_id, 0),
            )
```

- [ ] **Step 4: Integrate cup seeding into `create_save_game` in `engine/db.py`**

In `create_save_game`, after the `_seed_fixtures_for_save` loop, add:

```python
    from .cups import seed_cup_for_save, CUP_CONFIGS
    for cup_key in CUP_CONFIGS:
        seed_cup_for_save(conn, save_id, cup_key, season_year)
```

- [ ] **Step 5: Integrate `advance_cup_rounds` into `advance_save_one_day`**

In `advance_save_one_day`, after the `simulate_ai_transfers` weekly block, add:

```python
    from .cups import advance_cup_rounds
    advance_cup_rounds(conn, save_id, current_date_str)
```

- [ ] **Step 6: Integrate cup seeding into `start_next_season_if_ready`**

In `start_next_season_if_ready`, after `_seed_fixtures_for_save(conn, save_id, str(row["league_id"]), next_year)`, replace it with:

```python
    all_leagues = conn.execute("SELECT id FROM leagues").fetchall()
    for league_row in all_leagues:
        _seed_fixtures_for_save(conn, save_id, str(league_row["id"]), next_year)
    from .cups import seed_cup_for_save, CUP_CONFIGS
    for cup_key in CUP_CONFIGS:
        seed_cup_for_save(conn, save_id, cup_key, next_year)
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
python -m pytest tests/test_multi_league.py::test_cup_configs_defined tests/test_multi_league.py::test_fa_cup_seeded_on_save_create -v
python -m pytest tests/test_match_engine.py -v --tb=short 2>&1 | tail -20
```

Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add engine/cups.py engine/db.py tests/test_multi_league.py
git commit -m "feat: domestic cup seeding, bracket generation, and round advancement"
```

---

## Task 8: New DB Queries for World/Competitions Menu

**Files:**
- Modify: `engine/db.py` — add `load_all_competitions`, `load_cup_bracket`
- Test: `tests/test_multi_league.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_multi_league.py`:

```python
from engine.db import load_all_competitions, load_cup_bracket


def test_load_all_competitions_returns_list():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        prepare_test_db(db_path)
        with db_session(db_path) as conn:
            save_id = create_save_game(conn, "Tester", "ENG1", "A")
            comps = load_all_competitions(conn, save_id)
            assert isinstance(comps, list)
            types = {c["type"] for c in comps}
            assert "league" in types
            assert "cup" in types


def test_load_cup_bracket_returns_rounds():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        prepare_test_db(db_path)
        with db_session(db_path) as conn:
            save_id = create_save_game(conn, "Tester", "ENG1", "A")
            season_row = conn.execute("SELECT season_year FROM saves WHERE id=?", (save_id,)).fetchone()
            season = int(season_row["season_year"])
            bracket = load_cup_bracket(conn, save_id, f"FA_CUP_{season}")
            assert isinstance(bracket, dict)
            assert len(bracket) > 0  # has at least one round
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_multi_league.py::test_load_all_competitions_returns_list tests/test_multi_league.py::test_load_cup_bracket_returns_rounds -v
```

Expected: FAIL

- [ ] **Step 3: Add functions to `engine/db.py`**

Add after `load_save_standings`:

```python
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

    # Also add league competitions that may not have a competitions row yet
    league_rows = conn.execute("SELECT id, name FROM leagues ORDER BY id").fetchall()
    existing_ids = {str(r["id"]) for r in comp_rows}
    result = []
    for row in comp_rows:
        comp_id = str(row["id"])
        comp_type = str(row["type"])
        entry = {
            "id": comp_id,
            "name": str(row["name"]),
            "country": str(row["country"]),
            "type": comp_type,
            "season": int(row["season"]),
        }
        if comp_type == "cup":
            # Current round: first round with unplayed bracket fixtures
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
            # Last 4 results
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

    # Add league entries for leagues with fixtures but no competitions row
    for lg in league_rows:
        lid = str(lg["id"])
        comp_id = f"{lid}_{season_year}"
        if comp_id in existing_ids:
            continue
        fix_count = conn.execute(
            "SELECT COUNT(*) AS c FROM fixtures WHERE save_id=? AND competition_id=?",
            (save_id, comp_id),
        ).fetchone()
        if fix_count and int(fix_count["c"]) > 0:
            played = conn.execute(
                "SELECT COUNT(*) AS c FROM fixtures WHERE save_id=? AND competition_id=? AND played=1",
                (save_id, comp_id),
            ).fetchone()
            total = int(fix_count["c"])
            played_count = int(played["c"]) if played else 0
            result.append({
                "id": comp_id,
                "name": str(lg["name"]),
                "country": lid[:3],
                "type": "league",
                "season": season_year,
                "matchday_played": played_count,
                "matchday_total": total,
            })

    # Enrich leagues with top 3 standings
    for entry in result:
        if entry["type"] != "league":
            continue
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_multi_league.py::test_load_all_competitions_returns_list tests/test_multi_league.py::test_load_cup_bracket_returns_rounds -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/db.py tests/test_multi_league.py
git commit -m "feat: add load_all_competitions and load_cup_bracket DB queries"
```

---

## Task 9: World/Competitions Screen — `main.py`

**Files:**
- Modify: `main.py` — new screen constants, `_build_view`, `_handle_action`
- Test: manual (UI screens aren't unit-testable)

- [ ] **Step 1: Add screen constants at the top of `main.py`**

After the existing screen-related imports/state setup, add (at the class attribute or module level where other screen names are defined — search for `"menu"` as the first screen string):

In `main.py`, find the `__init__` method where `self.screen = "menu"` is set (around line 201). Before or around that area, the screen names are just strings. We don't need constants — we'll just use the string values. Add two new instance variables in `__init__` after `self.screen = "menu"`:

```python
        self.competitions_data: list = []
        self.cup_bracket_data: dict = {}
        self.cup_bracket_competition_id: str = ""
```

- [ ] **Step 2: Add `load_all_competitions` and `load_cup_bracket` to the imports in `main.py`**

In `main.py`, find the `from engine.db import (` block and add:

```python
    load_all_competitions,
    load_cup_bracket,
```

- [ ] **Step 3: Add `world_competitions` case to `_build_view`**

In `_build_view`, add before the final `return` (which builds the overview view or at the end of the chain of `if self.screen ==` blocks):

```python
        if self.screen == "world_competitions":
            return {
                "screen": "world_competitions",
                "competitions": self.competitions_data,
            }
        if self.screen == "cup_bracket":
            return {
                "screen": "cup_bracket",
                "competition_id": self.cup_bracket_competition_id,
                "bracket": self.cup_bracket_data,
            }
```

- [ ] **Step 4: Add action handlers in `_handle_action`**

In `_handle_action`, add after the existing `if action == "modal:options":` block:

```python
        if action == "nav:world_competitions":
            if self.active_save_id:
                with db_session(self.db_path) as conn:
                    self.competitions_data = load_all_competitions(conn, self.active_save_id)
            self.screen = "world_competitions"
            return
        if action.startswith("open_cup_bracket:"):
            comp_id = action.split(":", 1)[1]
            if self.active_save_id:
                with db_session(self.db_path) as conn:
                    self.cup_bracket_data = load_cup_bracket(conn, self.active_save_id, comp_id)
            self.cup_bracket_competition_id = comp_id
            self.screen = "cup_bracket"
            return
        if action.startswith("open_league_standings:"):
            comp_id = action.split(":", 1)[1]
            self.screen = "overview"
            self.overview_tab = "matches_standings"
            return
        if action == "back:world_competitions":
            self.screen = "world_competitions"
            if self.active_save_id:
                with db_session(self.db_path) as conn:
                    self.competitions_data = load_all_competitions(conn, self.active_save_id)
            return
```

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: add world_competitions and cup_bracket screen state to main.py"
```

---

## Task 10: World/Competitions Render — `engine/render.py`

**Files:**
- Modify: `engine/render.py` — add "WORLD" nav item in `_draw_overview_header`, add `draw_competitions_screen`, `draw_cup_bracket`, wire `draw_app_view`

- [ ] **Step 1: Add "WORLD" to nav in `_draw_overview_header`**

In `engine/render.py`, find the `nav_items` list (around line 2321):

```python
        nav_items = [
            ("OVERVIEW", "overview"),
            ("SQUAD", "squad"),
            ("MATCHES", "matches"),
            ("TRANSFERS", "transfers"),
            ("CLUB", "club"),
            ("CAREER", "career"),
        ]
```

Replace with:

```python
        nav_items = [
            ("OVERVIEW", "overview"),
            ("SQUAD", "squad"),
            ("MATCHES", "matches"),
            ("TRANSFERS", "transfers"),
            ("CLUB", "club"),
            ("CAREER", "career"),
            ("WORLD", "world"),
        ]
```

Also add the "world" active check in the active tab logic. Find:

```python
            or (tab_key == "club" and overview_tab.startswith("club_"))
```

And add after it:

```python
            or (tab_key == "world" and overview_tab in ("world_competitions", "cup_bracket"))
```

Add the action for "world" tab in the action assignment block. Find the `elif tab_key == "club":` block and add after:

```python
            elif tab_key == "world":
                action = "nav:world_competitions"
```

- [ ] **Step 2: Add `draw_competitions_screen` to `engine/render.py`**

Add this method to the `Renderer` class (before `draw_app_view`):

```python
    def draw_competitions_screen(self, view: dict) -> None:
        self.screen.fill((18, 20, 26))
        competitions = list(view.get("competitions", []))
        leagues = [c for c in competitions if c.get("type") == "league"]
        cups = [c for c in competitions if c.get("type") == "cup"]

        # Header
        header_rect = pygame.Rect(0, 0, SCREEN_W, 48)
        pygame.draw.rect(self.screen, (12, 12, 16), header_rect)
        draw_text(self.screen, "WORLD  /  COMPETITIONS", 24, 14, (220, 220, 224), scale=2)

        # Back button
        back_rect = pygame.Rect(SCREEN_W - 110, 12, 90, 26)
        pygame.draw.rect(self.screen, (40, 44, 56), back_rect, border_radius=3)
        draw_text(self.screen, "BACK", back_rect.x + 28, back_rect.y + 7, (180, 184, 192), scale=1)
        self._register_ui("back", back_rect)

        panel_top = 60
        panel_h = SCREEN_H - panel_top - 8
        left_w = SCREEN_W // 2 - 4
        right_w = SCREEN_W - left_w - 8

        # Left panel: Leagues
        left_rect = pygame.Rect(4, panel_top, left_w, panel_h)
        pygame.draw.rect(self.screen, (24, 26, 34), left_rect, border_radius=4)
        draw_text(self.screen, "LEAGUES", left_rect.x + 12, left_rect.y + 10, (248, 187, 32), scale=1)

        card_y = left_rect.y + 30
        for comp in leagues:
            card_h = 72
            if card_y + card_h > left_rect.bottom - 4:
                break
            card_rect = pygame.Rect(left_rect.x + 6, card_y, left_rect.w - 12, card_h)
            pygame.draw.rect(self.screen, (32, 36, 46), card_rect, border_radius=3)
            draw_text(self.screen, str(comp.get("name", "")).upper(), card_rect.x + 10, card_rect.y + 8, (220, 220, 224), scale=1)
            draw_text(self.screen, str(comp.get("country", "")), card_rect.x + 10, card_rect.y + 22, (130, 134, 142), scale=1)
            top3 = comp.get("top3", [])
            for i, entry in enumerate(top3):
                row_y = card_rect.y + 38 + i * 10
                draw_text(self.screen, f"{i+1}. {entry['name']}", card_rect.x + 10, row_y, (180, 184, 192), scale=1)
                pts_str = f"{entry['points']}pts"
                draw_text(self.screen, pts_str, card_rect.right - text_width(pts_str, 1) - 10, row_y, (140, 144, 152), scale=1)
            comp_id = str(comp.get("id", ""))
            self._register_ui(f"open_league_standings:{comp_id}", card_rect)
            card_y += card_h + 4

        # Right panel: Cups
        right_rect = pygame.Rect(left_w + 8, panel_top, right_w, panel_h)
        pygame.draw.rect(self.screen, (24, 26, 34), right_rect, border_radius=4)
        draw_text(self.screen, "DOMESTIC CUPS", right_rect.x + 12, right_rect.y + 10, (248, 187, 32), scale=1)

        card_y = right_rect.y + 30
        for comp in cups:
            card_h = 90
            if card_y + card_h > right_rect.bottom - 4:
                break
            card_rect = pygame.Rect(right_rect.x + 6, card_y, right_rect.w - 12, card_h)
            pygame.draw.rect(self.screen, (32, 36, 46), card_rect, border_radius=3)
            draw_text(self.screen, str(comp.get("name", "")).upper(), card_rect.x + 10, card_rect.y + 8, (220, 220, 224), scale=1)
            draw_text(self.screen, f"Round: {comp.get('current_round', '?')}", card_rect.x + 10, card_rect.y + 22, (130, 134, 142), scale=1)
            recent = comp.get("recent_results", [])
            for i, res in enumerate(recent[:4]):
                row_y = card_rect.y + 38 + i * 12
                score_str = f"{res['home_name'][:12]} {res['home_goals']}-{res['away_goals']} {res['away_name'][:12]}"
                draw_text(self.screen, score_str, card_rect.x + 10, row_y, (160, 164, 172), scale=1)
            comp_id = str(comp.get("id", ""))
            self._register_ui(f"open_cup_bracket:{comp_id}", card_rect)
            card_y += card_h + 4
```

- [ ] **Step 3: Add `draw_cup_bracket` to `engine/render.py`**

```python
    def draw_cup_bracket(self, view: dict) -> None:
        self.screen.fill((18, 20, 26))
        bracket = dict(view.get("bracket", {}))
        comp_id = str(view.get("competition_id", ""))

        header_rect = pygame.Rect(0, 0, SCREEN_W, 48)
        pygame.draw.rect(self.screen, (12, 12, 16), header_rect)
        draw_text(self.screen, f"CUP BRACKET  /  {comp_id}", 24, 14, (220, 220, 224), scale=2)

        back_rect = pygame.Rect(SCREEN_W - 110, 12, 90, 26)
        pygame.draw.rect(self.screen, (40, 44, 56), back_rect, border_radius=3)
        draw_text(self.screen, "BACK", back_rect.x + 28, back_rect.y + 7, (180, 184, 192), scale=1)
        self._register_ui("back:world_competitions", back_rect)

        if not bracket:
            draw_text(self.screen, "NO BRACKET DATA", SCREEN_W // 2 - 60, SCREEN_H // 2, (130, 134, 142), scale=2)
            return

        rounds = list(bracket.keys())
        col_w = max(180, SCREEN_W // max(len(rounds), 1))
        top = 68

        for col_idx, rnd in enumerate(rounds):
            col_x = col_idx * col_w + 8
            draw_text(self.screen, rnd, col_x + 4, top, (248, 187, 32), scale=1)
            matchups = bracket[rnd]
            row_h = max(40, (SCREEN_H - top - 20) // max(len(matchups), 1))
            for m_idx, match in enumerate(matchups):
                cell_y = top + 18 + m_idx * row_h
                cell_rect = pygame.Rect(col_x, cell_y, col_w - 8, row_h - 4)
                winner = str(match.get("winner", ""))
                bg = (28, 30, 38) if not winner else (22, 40, 28)
                pygame.draw.rect(self.screen, bg, cell_rect, border_radius=2)
                name_a = str(match.get("name_a", "TBD"))[:16]
                name_b = str(match.get("name_b", "TBD"))[:16]
                s1a = match.get("score_a_leg1")
                s1b = match.get("score_b_leg1")
                score_str = f"{s1a}-{s1b}" if s1a is not None else "vs"
                draw_text(self.screen, name_a, cell_rect.x + 4, cell_rect.y + 4, (210, 214, 222), scale=1)
                draw_text(self.screen, name_b, cell_rect.x + 4, cell_rect.y + 18, (210, 214, 222), scale=1)
                score_x = cell_rect.right - text_width(score_str, 1) - 4
                draw_text(self.screen, score_str, score_x, cell_rect.y + 10, (180, 220, 160) if winner else (160, 164, 172), scale=1)
```

- [ ] **Step 4: Wire new screens in `draw_app_view`**

In `draw_app_view`, find where it dispatches to screen-specific draw methods. Add before the final `pygame.display.flip()` or similar:

```python
        if screen == "world_competitions":
            self.draw_competitions_screen(view)
            if present:
                pygame.display.flip()
            return
        if screen == "cup_bracket":
            self.draw_cup_bracket(view)
            if present:
                pygame.display.flip()
            return
```

Find the `draw_app_view` method body and look for where it checks `screen = view.get("screen", "")` — add the two new screen cases alongside the existing ones.

- [ ] **Step 5: Run the game and navigate to World → Competitions**

```bash
cd /home/oznaak/Documents/projects/MatchEngineFMStarter
source .venv/bin/activate
python main.py A D
```

Steps to test:
1. Start or load a save
2. Click "WORLD" in the nav bar
3. Verify the Competitions screen shows league cards on the left and cup cards on the right
4. Click a cup card → verify bracket screen appears
5. Click "BACK" → verify return to competitions screen

- [ ] **Step 6: Run all tests**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add engine/render.py main.py
git commit -m "feat: World/Competitions screen with league overview and cup bracket drill-down"
```

---

## Self-Review Checklist

After completing all tasks, verify:

- [ ] `save_league_clubs` seeded for all leagues on save creation
- [ ] All league fixtures tagged with `competition_id`
- [ ] `load_save_standings` works with and without `competition_id` parameter
- [ ] AI fixtures simulated daily in `advance_save_one_day`
- [ ] Standings table updated on both AI and user match results
- [ ] Promotion/relegation applied at season end
- [ ] All 5 cups seeded with correct clubs and bracket slots
- [ ] Cup rounds advance automatically when all previous-round fixtures are played
- [ ] `load_all_competitions` returns both leagues and cups with enriched metadata
- [ ] World/Competitions screen renders without crash
- [ ] Cup bracket screen renders without crash with back navigation
- [ ] All existing `test_match_engine.py` tests still pass
