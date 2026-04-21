from __future__ import annotations
import sys
from pathlib import Path

import pygame

from engine.loader import load_league
from engine.match_engine import MatchEngine
from engine.render import Renderer

ROOT = Path(__file__).resolve().parent
LEAGUE_FILE = ROOT / "data" / "league.json"
SPEED_MULTIPLIERS = {
    "X1": 2.0,
    "X2": 2.5,
    "X4": 5.0,
}


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python main.py A D")
        return 1

    home_id = sys.argv[1].strip().upper()
    away_id = sys.argv[2].strip().upper()
    if home_id == away_id:
        print("Home and away clubs must be different.")
        return 1

    clubs = load_league(LEAGUE_FILE)
    if home_id not in clubs or away_id not in clubs:
        print(f"Unknown club id. Available: {', '.join(sorted(clubs.keys()))}")
        return 1

    renderer = Renderer()
    paused = False
    speed_label = "X1"

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
