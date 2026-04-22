from __future__ import annotations
import argparse
import sys
from pathlib import Path

import pygame

from engine.db import bootstrap_database, db_session, get_current_day, load_clubs_from_db
from engine.condition import advance_condition_days, apply_post_match_condition, load_condition_state, save_condition_state
from engine.match_engine import MatchEngine
from engine.render import Renderer

ROOT = Path(__file__).resolve().parent
LEAGUE_FILE = ROOT / "data" / "league.json"
DB_FILE = ROOT / "data" / "game.db"
SPEED_MULTIPLIERS = {
    "X1": 2.0,
    "X2": 2.5,
    "X4": 5.0,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="FM-style match viewer")
    parser.add_argument("home_id")
    parser.add_argument("away_id")
    parser.add_argument("--days", type=int, default=0, help="Advance squad recovery by this many days before kickoff")
    args = parser.parse_args()

    home_id = args.home_id.strip().upper()
    away_id = args.away_id.strip().upper()
    if home_id == away_id:
        print("Home and away clubs must be different.")
        return 1

    with db_session(DB_FILE) as conn:
        bootstrap_database(conn, LEAGUE_FILE)
        clubs = load_clubs_from_db(conn)
        current_day = get_current_day(conn)
    current_day = load_condition_state(DB_FILE, clubs)
    if args.days > 0:
        advance_condition_days(clubs, args.days)
        current_day += args.days
        save_condition_state(DB_FILE, clubs, current_day)
    if home_id not in clubs or away_id not in clubs:
        print(f"Unknown club id. Available: {', '.join(sorted(clubs.keys()))}")
        return 1

    renderer = Renderer()
    paused = False
    speed_label = "X1"
    match_condition_saved = False

    def build_engine() -> MatchEngine:
        seed = hash((home_id, away_id)) & 0xFFFFFFFF
        engine = MatchEngine(clubs[home_id], clubs[away_id], seed=seed)
        engine.set_speed(SPEED_MULTIPLIERS[speed_label])
        return engine

    engine = build_engine()
    fixture_label = f"{clubs[home_id].name} vs {clubs[away_id].name}"

    running = True
    while running:
        dt = renderer.tick()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    if not engine.state.awaiting_start and not engine.state.is_finished:
                        paused = not paused
                elif event.key == pygame.K_r:
                    engine = build_engine()
                    paused = False
                    match_condition_saved = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                action = renderer.handle_click(event.pos)
                if action == "start":
                    if engine.start_match_flow():
                        paused = False
                elif action and action.startswith("speed:"):
                    speed_label = action.split(":", 1)[1]
                    engine.set_speed(SPEED_MULTIPLIERS[speed_label])

        if not paused:
            engine.update(dt)
        if engine.state.is_finished and not match_condition_saved:
            apply_post_match_condition(engine.state)
            save_condition_state(DB_FILE, clubs, current_day)
            match_condition_saved = True

        renderer.draw(
            engine.state,
            fixture_label,
            paused,
            alpha=engine.slice_progress(),
            speed_label=speed_label,
            clock_seconds=engine.display_clock_seconds(),
        )

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
