from __future__ import annotations

import argparse
import json
from pathlib import Path

import pygame

from engine.condition import advance_condition_days, apply_post_match_condition, load_condition_state, save_condition_state, save_condition_state_to_conn
from engine.db import (
    bootstrap_database,
    advance_save_one_day,
    add_save_message,
    create_save_game,
    delete_save_game,
    db_session,
    get_current_day,
    get_fixture_report,
    get_next_fixture_for_save,
    get_transfer_window_status,
    list_league_clubs,
    list_leagues,
    list_matchday_fixtures,
    list_option_choices,
    list_save_games,
    load_active_save_id,
    load_app_options,
    load_clubs_from_db,
    load_save_overview,
    load_transfer_data,
    list_player_for_transfer,
    make_transfer_offer,
    withdraw_transfer_listing,
    get_accepted_offers,
    complete_transfer,
    submit_player_negotiation,
    accept_inbound_offer,
    decline_inbound_offer,
    apply_matchday_revenue,
    get_finance_transactions,
    save_fixture_result,
    save_app_option,
    save_player_training_focus,
    save_save_club_setup,
    save_training_settings,
    set_active_save_id,
    trigger_totw_for_match_day,
    mark_message_read,
    list_club_players,
    get_club_staff,
    set_club_staff,
    get_player_scouting_pct,
    has_pending_scout_task,
    get_all_scouting_data,
    submit_scout_task,
    SCOUT_DAYS,
    SCOUT_PCT_RANGE,
    STAFF_WEEKLY_SALARIES,
    load_all_competitions,
    load_cup_bracket,
)
from engine.loader import available_formations, pick_best_xi
from engine.match_engine import MatchEngine
from engine.models import (
    DEFAULT_PLAYER_INSTRUCTIONS,
    DEFAULT_TEAM_INSTRUCTIONS,
    TEAM_INSTRUCTION_OPTIONS,
    normalize_player_instruction_value,
    normalize_team_instructions,
)
from engine.render import Renderer
from engine.db_worker import DBWorker

ROOT = Path(__file__).resolve().parent
DB_FILE = ROOT / "data" / "game.db"
SPEED_MULTIPLIERS = {
    "X1": 2.0,
    "X2": 2.5,
    "X4": 5.0,
    "X8": 10.0,
}
KEY_BINDINGS = {
    "escape": pygame.K_ESCAPE,
    "tab": pygame.K_TAB,
    "m": pygame.K_m,
    "space": pygame.K_SPACE,
    "p": pygame.K_p,
    "enter": pygame.K_RETURN,
    "s": pygame.K_s,
    "1": pygame.K_1,
    "2": pygame.K_2,
    "4": pygame.K_4,
    "8": pygame.K_8,
    "q": pygame.K_q,
    "w": pygame.K_w,
    "e": pygame.K_e,
    "r": pygame.K_r,
    "z": pygame.K_z,
    "x": pygame.K_x,
    "c": pygame.K_c,
    "v": pygame.K_v,
}


def parse_resolution(value: str) -> tuple[int, int]:
    try:
        width_text, height_text = value.lower().split("x", 1)
        width = max(960, int(width_text))
        height = max(640, int(height_text))
        return width, height
    except (ValueError, AttributeError):
        return 1560, 900


def run_match_viewer(home_id: str, away_id: str, days: int) -> int:
    with db_session(DB_FILE) as conn:
        bootstrap_database(conn)
        clubs = load_clubs_from_db(conn)
        current_day = get_current_day(conn)
    current_day = load_condition_state(DB_FILE, clubs)
    if days > 0:
        advance_condition_days(clubs, days)
        current_day += days
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
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and engine.state.is_finished:
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
                    if engine.state.is_finished:
                        running = False
                        continue
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
            selected_player_id=engine.home.xi[0].profile.id if engine.home.xi else None,
        )

    pygame.quit()
    return 0


class ManagerGameApp:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        # Background DB worker to avoid blocking main/UI thread on commits
        self.db_worker = DBWorker(self.db_path)
        # Debounce state for squad saves
        self._squad_save_pending: bool = False
        self._squad_save_last_time: float = 0.0
        self._squad_save_delay: float = 0.6
        self._squad_save_payload: dict | None = None
        with db_session(self.db_path) as conn:
            bootstrap_database(conn)
            options = load_app_options(conn)
        width, height = parse_resolution(options.get("resolution", "1560x900"))
        fullscreen = options.get("window_mode", "windowed") == "fullscreen"
        self.renderer = Renderer(width, height, fullscreen)
        self.running = True
        self.screen = "menu"
        self.manager_name = ""
        self.selected_league_id: str | None = None
        self.selected_club_id: str | None = None
        self.error_message: str | None = None
        self.options = options
        self.option_choices: dict[str, list[dict]] = {}
        self.leagues: list[dict] = []
        self.club_choices: list[dict] = []
        self.saves: list[dict] = []
        self.selected_save_id: int | None = None
        self.active_save_id: int | None = None
        self.overview: dict | None = None
        self.overview_club_id: str | None = None
        self.overview_tab = "overview"
        self.match_engine: MatchEngine | None = None
        self.match_fixture: dict | None = None
        self.match_clubs: dict | None = None
        self.match_speed_label = "X1"
        self.match_paused = False
        self.match_condition_saved = False
        self.match_current_day = 0
        self.match_finish_timer = 0.0
        self.match_selected_player_id: str | None = None
        self.match_sub_mode = False
        self.match_sub_restore_paused = False
        self.match_sub_drag_player_id: str | None = None
        self.match_sub_drag_pos: tuple[int, int] | None = None
        self.match_sub_hover_player_id: str | None = None
        self.match_sub_draft_xi_ids: list[str] = []
        self.match_sub_draft_bench_ids: list[str] = []
        self.match_pending_substitutions: list[tuple[str, str]] = []
        self.match_pending_position_swaps: list[tuple[str, str]] = []
        self.match_sub_animation: dict | None = None
        self.match_instruction_mode: str | None = None
        self.match_instruction_restore_paused = False
        self.match_instruction_team_draft = dict(DEFAULT_TEAM_INSTRUCTIONS)
        self.match_instruction_player_draft: dict[str, dict[str, int]] = {}
        self.match_instruction_formation_draft = "4-3-3"
        self.match_pending_instruction_update: dict[str, object] | None = None
        self.match_instruction_animation: dict | None = None
        self.match_live_instruction_baseline: dict[str, dict] = {}
        self.match_instruction_slider_drag_player_id: str | None = None
        self.match_instruction_slider_drag_key: str | None = None
        self.fixture_report: dict | None = None
        self.fixture_report_selected_player_id: str | None = None
        self.modal: dict | None = None
        self.options_return_screen: str | None = None
        self.modal_paused_match = False
        self.squad_drag_player_id: str | None = None
        self.squad_drag_pos: tuple[int, int] | None = None
        self.squad_mouse_down_player_id: str | None = None
        self.squad_mouse_down_pos: tuple[int, int] | None = None
        self.squad_hover_target_id: str | None = None
        self.squad_hover_player_id: str | None = None
        self.squad_selected_player_id: str | None = None
        self.squad_slider_drag_player_id: str | None = None
        self.squad_slider_drag_key: str | None = None
        self.squad_draft_xi_ids: list[str] = []
        self.squad_draft_bench_ids: list[str] = []
        self.squad_draft_formation = "4-3-3"
        self.squad_draft_instructions = dict(DEFAULT_TEAM_INSTRUCTIONS)
        self.squad_draft_player_instructions: dict[str, dict[str, int]] = {}
        self.fixtures_page: int = 1
        self.squad_show_reserves: bool = False
        self.squad_show_unavailable: bool = False
        self.squad_pending_reserve_id: str | None = None
        self.squad_roles: dict[str, str] = {}
        self.squad_roles_selected_role: str | None = None
        self.transfer_data: dict = {}
        self.transfer_negotiate_offer_id: str | None = None
        self.overview_news_page: int = 0
        # Detail screens
        self.detail_club_id: str | None = None
        self.detail_club_data: dict | None = None
        self.detail_player_id: str | None = None
        self.detail_player_data: dict | None = None
        self.detail_selected_player_id: str | None = None
        self.detail_show_attrs: bool = False
        self.detail_nav_stack: list[tuple[str, str]] = []
        self.detail_is_user_club: bool = True
        self.detail_scouting_pct: int = 100
        self.detail_scout_pending: bool = False
        # Staff
        self.staff_data: dict[str, str] = {}
        self.competitions_data: list = []
        self.cup_bracket_data: dict = {}
        self.cup_bracket_competition_id: str = ""
        self._reload_state(apply_display=True)

    def _fixture_gameweeks(self) -> list[int]:
        if not self.overview:
            return [1]
        weeks = {
            int(fixture.get("gameweek", fixture.get("match_day", 1)) or 1)
            for fixture in self.overview.get("fixtures", [])
        }
        return sorted(week for week in weeks if week > 0) or [1]

    def _clamp_fixtures_page(self) -> None:
        weeks = self._fixture_gameweeks()
        if self.fixtures_page < weeks[0]:
            self.fixtures_page = weeks[0]
            return
        if self.fixtures_page > weeks[-1]:
            self.fixtures_page = weeks[-1]

    def _set_fixtures_page_to_current_round(self) -> None:
        if not self.overview:
            self.fixtures_page = 1
            return
        current = int(self.overview.get("current_gameweek") or 0)
        if current <= 0:
            today_fixture = self.overview.get("today_fixture")
            next_fixture = self.overview.get("next_fixture")
            fixture = today_fixture or next_fixture
            current = int((fixture or {}).get("gameweek", (fixture or {}).get("match_day", 1)) or 1)
        self.fixtures_page = current
        self._clamp_fixtures_page()

    def _reload_overview(self) -> None:
        if self.active_save_id is None:
            return
        with db_session(self.db_path) as conn:
            self.overview = load_save_overview(conn, self.active_save_id, news_page=self.overview_news_page)
            if self.overview and not self.overview_club_id:
                self.overview_club_id = self.overview["club_id"]
        if self.overview:
            self._load_squad_draft()
            self._clamp_fixtures_page()
        self._reload_transfer_data()

    def _reload_state(self, apply_display: bool = False) -> None:
        # Schema/bootstrap work is expensive and only needed once at startup.
        # Avoid re-running `bootstrap_database` here to keep UI transitions snappy.
        with db_session(self.db_path) as conn:
            self.options = load_app_options(conn)
            self.option_choices = {
                key: list_option_choices(conn, key)
                for key in (
                    "resolution",
                    "window_mode",
                    "language",
                    "bind_menu",
                    "bind_pause",
                    "bind_start",
                    "bind_speed_x1",
                    "bind_speed_x2",
                    "bind_speed_x4",
                    "bind_speed_x8",
                )
            }
            self.option_choices["display"] = self.renderer.available_displays()
            self.leagues = list_leagues(conn)
            self.saves = list_save_games(conn)
            if self.selected_save_id is not None and not any(save["id"] == self.selected_save_id for save in self.saves):
                self.selected_save_id = None
            self.active_save_id = load_active_save_id(conn)
            if self.active_save_id is not None:
                self.overview = load_save_overview(conn, self.active_save_id, news_page=self.overview_news_page)
                if self.overview and not self.overview_club_id:
                    self.overview_club_id = self.overview["club_id"]
                self.staff_data = get_club_staff(conn, self.active_save_id)
            else:
                self.overview = None
                self.staff_data = {}
        if self.overview:
            self._load_squad_draft()
            self._clamp_fixtures_page()
        self._reload_transfer_data()
        if apply_display:
            self._apply_renderer_options()

    def _apply_renderer_options(self) -> None:
        width, height = parse_resolution(self.options.get("resolution", "1560x900"))
        fullscreen = self.options.get("window_mode", "windowed") == "fullscreen"
        display_index = int(self.options.get("display", "0") or 0)
        self.renderer.set_display_mode(width, height, fullscreen, display_index)

    def _load_league_clubs(self) -> None:
        if not self.selected_league_id:
            self.club_choices = []
            return
        with db_session(self.db_path) as conn:
            self.club_choices = list_league_clubs(conn, self.selected_league_id)

    def _reload_transfer_data(self) -> None:
        if not self.active_save_id or not self.overview:
            self.transfer_data = {}
            return
        current_date = str(self.overview.get("current_date", ""))
        window_open, window_type = get_transfer_window_status(current_date) if current_date else (False, "")
        club_id = str(self.overview.get("club_id", ""))
        with db_session(self.db_path) as conn:
            data = load_transfer_data(conn, self.active_save_id, club_id)
        data["window_open"] = window_open
        data["window_type"] = window_type
        self.transfer_data = data

    def _load_save(self, save_id: int) -> None:
        with db_session(self.db_path) as conn:
            set_active_save_id(conn, save_id)
            conn.commit()
            self.overview = load_save_overview(conn, save_id, news_page=0)
        self.overview_news_page = 0
        self.active_save_id = save_id
        if self.overview:
            self.overview_club_id = self.overview["club_id"]
            self.overview_tab = "overview"
            self.screen = "overview"
        self._reload_transfer_data()

    def _create_new_save(self) -> None:
        if not self.manager_name.strip():
            self.error_message = "Manager name required."
            return
        if not self.selected_league_id or not self.selected_club_id:
            return
        with db_session(self.db_path) as conn:
            save_id = create_save_game(conn, self.manager_name, self.selected_league_id, self.selected_club_id)
            self.overview = load_save_overview(conn, save_id)
        self.active_save_id = self.overview["save_id"] if self.overview else None
        self._reload_transfer_data()
        self.overview_club_id = self.selected_club_id
        self.saves = []
        self.overview_tab = "overview"
        self.screen = "overview"

    def _save_option(self, key: str, value: str) -> None:
        # For display-changing options we need immediate reload; otherwise enqueue.
        if key in {"resolution", "window_mode", "display"}:
            with db_session(self.db_path) as conn:
                save_app_option(conn, key, value)
                conn.commit()
            self._reload_state(apply_display=True if key in {"resolution", "window_mode", "display"} else False)
            return
        # Update in-memory and enqueue save to background worker
        self.options[key] = value
        self.db_worker.enqueue(save_app_option, str(key), str(value))

    def _is_bound(self, event: pygame.event.Event, option_key: str, fallback: str) -> bool:
        value = self.options.get(option_key, fallback)
        key = KEY_BINDINGS.get(value, KEY_BINDINGS[fallback])
        if event.key == key:
            return True
        if key == pygame.K_RETURN and event.key == pygame.K_KP_ENTER:
            return True
        return False

    def _managed_match_side(self) -> str | None:
        if not self.match_fixture or not self.overview:
            return None
        managed_club_id = self.overview["club_id"]
        if self.match_fixture["home_club_id"] == managed_club_id:
            return "home"
        if self.match_fixture["away_club_id"] == managed_club_id:
            return "away"
        return None

    def _managed_match_team(self):
        if not self.match_engine:
            return None
        side = self._managed_match_side()
        if side == "home":
            return self.match_engine.home
        if side == "away":
            return self.match_engine.away
        return None

    def _managed_match_club(self):
        team = self._managed_match_team()
        return team.club if team else None

    def _managed_club_id(self) -> str | None:
        if not self.overview:
            return None
        return str(self.overview.get("club_id"))

    def _is_squad_tab(self, tab: str | None = None) -> bool:
        current = tab if tab is not None else self.overview_tab
        return str(current).startswith("squad_")

    def _load_squad_draft(self) -> None:
        if not self.overview:
            self.squad_draft_xi_ids = []
            self.squad_draft_bench_ids = []
            self.squad_draft_formation = "4-3-3"
            self.squad_draft_instructions = dict(DEFAULT_TEAM_INSTRUCTIONS)
            self.squad_draft_player_instructions = {}
            self.squad_selected_player_id = None
            return
        club_id = self._managed_club_id()
        setups = self.overview.get("club_setups", {})
        setup = setups.get(club_id or "", {})
        self.squad_draft_formation = str(setup.get("formation", "4-3-3"))
        self.squad_draft_xi_ids = list(setup.get("xi_ids", []))
        self.squad_draft_bench_ids = list(setup.get("bench_ids", []))[:9]
        self.squad_draft_instructions = normalize_team_instructions(setup.get("instructions"))
        self.squad_draft_player_instructions = {
            str(player_id): {
                key: normalize_player_instruction_value(key, value)
                for key, value in (values or {}).items()
                if key in DEFAULT_PLAYER_INSTRUCTIONS
            }
            for player_id, values in dict(setup.get("player_instructions", {})).items()
        }
        self._sanitize_squad_draft_availability()
        self._ensure_squad_selected_player()

    def _squad_player_availability(self) -> dict[str, bool]:
        if not self.overview:
            return {}
        managed_club_id = self._managed_club_id()
        return {
            str(player["id"]): bool(player.get("available", True))
            for player in self.overview.get("players_by_club", {}).get(managed_club_id, [])
        }

    def _sanitize_squad_draft_availability(self) -> None:
        if self.active_save_id is None or not self.overview:
            return
        availability = self._squad_player_availability()
        if not availability:
            return
        club_player_ids = set(availability.keys())
        # Regenerate if any XI/bench player no longer belongs to the club (sold/transferred)
        # or if any XI player is unavailable (injured/suspended).
        has_missing = any(pid not in club_player_ids for pid in self.squad_draft_xi_ids + self.squad_draft_bench_ids if pid)
        has_unavailable_xi = any(not availability.get(pid, True) for pid in self.squad_draft_xi_ids)
        if not has_missing and not has_unavailable_xi:
            return
        club_id = self._managed_club_id()
        if not club_id:
            return
        with db_session(self.db_path) as conn:
            clubs = load_clubs_from_db(conn, save_id=self.active_save_id)
        club = clubs.get(club_id)
        if not club:
            return
        xi, bench = pick_best_xi(club, formation_name=self.squad_draft_formation)
        xi_id_set = {player.id for player in xi}
        self.squad_draft_xi_ids = [player.id for player in xi]
        self.squad_draft_bench_ids = [player.id for player in bench if player.id not in xi_id_set][:9]

    def _ensure_squad_selected_player(self) -> None:
        active_ids = [player_id for player_id in self.squad_draft_xi_ids + self.squad_draft_bench_ids if player_id]
        if self.squad_selected_player_id in active_ids:
            return
        goalkeeper_id = None
        players = {}
        if self.overview:
            managed_club_id = self._managed_club_id()
            players = {
                player["id"]: player
                for player in self.overview.get("players_by_club", {}).get(managed_club_id, [])
            }
        for player_id in self.squad_draft_xi_ids:
            if players.get(player_id, {}).get("position") == "GK":
                goalkeeper_id = player_id
                break
        self.squad_selected_player_id = goalkeeper_id or (active_ids[0] if active_ids else None)

    def _persist_squad_draft(self) -> None:
        club_id = self._managed_club_id()
        if self.active_save_id is None or not club_id or not self.squad_draft_xi_ids:
            return
        # Debounce and batch frequent squad writes: schedule payload and flush
        # after a short idle period to avoid excessive DB churn while dragging.
        try:
            import time

            self._squad_save_payload = {
                "active_save_id": int(self.active_save_id),
                "club_id": str(club_id),
                "formation": str(self.squad_draft_formation),
                "xi_ids": list(self.squad_draft_xi_ids),
                "bench_ids": list(self.squad_draft_bench_ids),
                "instructions": dict(self.squad_draft_instructions),
                "player_instructions": dict(self.squad_draft_player_instructions),
            }
            self._squad_save_last_time = float(time.time())
            self._squad_save_pending = True
        except Exception:
            # Fallback: enqueue immediately if time import or other fails
            self.db_worker.enqueue(
                save_save_club_setup,
                int(self.active_save_id),
                club_id,
                self.squad_draft_formation,
                list(self.squad_draft_xi_ids),
                list(self.squad_draft_bench_ids),
                dict(self.squad_draft_instructions),
                dict(self.squad_draft_player_instructions),
            )
        # Avoid a full synchronous reload here (expensive DB reads that block the UI).
        # The in-memory draft state is already updated and the renderer reads from it,
        # so skip reloading everything to keep UI interactions snappy.
        # If a background sync / refresh is needed later, implement an async worker.

    def _change_squad_formation(self, formation: str) -> None:
        if self.active_save_id is None or not self.overview:
            return
        club_id = self._managed_club_id()
        if not club_id or formation not in available_formations():
            return
        with db_session(self.db_path) as conn:
            clubs = load_clubs_from_db(conn, save_id=self.active_save_id)
        club = clubs.get(club_id)
        if not club:
            return
        self.squad_draft_formation = formation
        # Preserve the user's existing lineup — only regenerate if no XI is set yet
        if not self.squad_draft_xi_ids:
            club.formation = formation
            club.lineup_xi = []
            club.lineup_bench = []
            xi, bench = pick_best_xi(club, formation_name=formation)
            xi_id_set = {player.id for player in xi}
            self.squad_draft_xi_ids = [player.id for player in xi]
            self.squad_draft_bench_ids = [player.id for player in bench if player.id not in xi_id_set][:9]
        self._ensure_squad_selected_player()
        self._persist_squad_draft()

    def _change_squad_instruction(self, key: str, value: str) -> None:
        if key not in TEAM_INSTRUCTION_OPTIONS:
            return
        if value not in TEAM_INSTRUCTION_OPTIONS[key]:
            return
        self.squad_draft_instructions[key] = value
        self._persist_squad_draft()

    def _step_squad_instruction(self, key: str, delta: int) -> None:
        options = TEAM_INSTRUCTION_OPTIONS.get(key, [])
        if not options:
            return
        current = str(self.squad_draft_instructions.get(key, options[0]))
        try:
            index = options.index(current)
        except ValueError:
            index = 0
        next_index = max(0, min(len(options) - 1, index + delta))
        if next_index == index:
            return
        self._change_squad_instruction(key, options[next_index])

    def _player_instruction_values(self, player_id: str | None) -> dict[str, int]:
        if not player_id:
            return dict(DEFAULT_PLAYER_INSTRUCTIONS)
        values = dict(DEFAULT_PLAYER_INSTRUCTIONS)
        values.update(self.squad_draft_player_instructions.get(player_id, {}))
        return {key: normalize_player_instruction_value(key, value) for key, value in values.items()}

    def _change_player_instruction(self, player_id: str, key: str, delta: int) -> None:
        if key not in DEFAULT_PLAYER_INSTRUCTIONS:
            return
        values = self._player_instruction_values(player_id)
        updated = normalize_player_instruction_value(key, values[key] + delta)
        if updated == values[key]:
            return
        self.squad_draft_player_instructions[player_id] = dict(values)
        self.squad_draft_player_instructions[player_id][key] = updated
        self._persist_squad_draft()

    def _set_player_instruction(self, player_id: str, key: str, value: int) -> None:
        if key not in DEFAULT_PLAYER_INSTRUCTIONS:
            return
        values = self._player_instruction_values(player_id)
        updated = normalize_player_instruction_value(key, value)
        if updated == values[key]:
            return
        self.squad_draft_player_instructions[player_id] = dict(values)
        self.squad_draft_player_instructions[player_id][key] = updated
        self._persist_squad_draft()

    def _change_training_settings(self, team_focus: str | None = None, intensity: str | None = None) -> None:
        if self.active_save_id is None or not self.overview:
            return
        club_id = self._managed_club_id()
        if not club_id:
            return
        training = dict(self.overview.get("training", {}))
        next_focus = str(team_focus or training.get("team_focus", "balanced"))
        next_intensity = str(intensity or training.get("intensity", "normal"))
        # Update in-memory overview immediately so UI reflects change,
        # then enqueue DB write to avoid blocking.
        if self.overview is not None:
            self.overview["training"] = {"team_focus": next_focus, "intensity": next_intensity}
        self.db_worker.enqueue(save_training_settings, int(self.active_save_id), str(club_id), str(next_focus), str(next_intensity))

    def _change_player_training_focus(self, player_id: str, focus: str) -> None:
        if self.active_save_id is None or not self.overview:
            return
        # Update in-memory overview/training for immediate UI feedback,
        # then enqueue DB write to avoid blocking.
        if self.overview is not None:
            player_map = self.overview.get("players_by_club", {})
            # Best-effort: record the player's focus in overview structure if present
            for club_id, players in (player_map or {}).items():
                for p in players:
                    if str(p.get("id", "")) == str(player_id):
                        p.setdefault("training_focus", focus)
        self.db_worker.enqueue(save_player_training_focus, int(self.active_save_id), str(player_id), str(focus))

    def _update_player_instruction_from_pos(self, pos: tuple[int, int]) -> None:
        player_id = self.squad_slider_drag_player_id
        key = self.squad_slider_drag_key
        if not player_id or not key:
            return
        hit = self.renderer.get_squad_slider_target(player_id, key)
        if not hit:
            return
        track = hit.get("track")
        if not isinstance(track, pygame.Rect) or track.width <= 0:
            return
        ratio = (pos[0] - track.x) / track.width
        value = round(max(0.0, min(1.0, ratio)) * 100)
        self._set_player_instruction(player_id, key, value)

    def _match_player_instruction_values(self, player_id: str | None) -> dict[str, int]:
        if not player_id:
            return dict(DEFAULT_PLAYER_INSTRUCTIONS)
        values = dict(DEFAULT_PLAYER_INSTRUCTIONS)
        values.update(self.match_instruction_player_draft.get(player_id, {}))
        return {key: normalize_player_instruction_value(key, value) for key, value in values.items()}

    def _set_match_player_instruction(self, player_id: str, key: str, value: int) -> None:
        if key not in DEFAULT_PLAYER_INSTRUCTIONS:
            return
        values = self._match_player_instruction_values(player_id)
        updated = normalize_player_instruction_value(key, value)
        if updated == values[key]:
            return
        self.match_instruction_player_draft[player_id] = dict(values)
        self.match_instruction_player_draft[player_id][key] = updated

    def _update_match_player_instruction_from_pos(self, pos: tuple[int, int]) -> None:
        player_id = self.match_instruction_slider_drag_player_id
        key = self.match_instruction_slider_drag_key
        if not player_id or not key:
            return
        hit = self.renderer.get_match_slider_target(player_id, key)
        if not hit:
            return
        track = hit.get("track")
        if not isinstance(track, pygame.Rect) or track.width <= 0:
            return
        ratio = (pos[0] - track.x) / track.width
        value = round(max(0.0, min(1.0, ratio)) * 100)
        self._set_match_player_instruction(player_id, key, value)

    def _match_has_active_popup(self) -> bool:
        return bool(self.match_sub_mode or self.match_instruction_mode)

    def _reset_match_instruction_state(self, restore_pause: bool = True) -> None:
        if restore_pause and self.match_engine and not self.match_engine.state.is_finished:
            self.match_paused = self.match_instruction_restore_paused
        self.match_instruction_mode = None
        self.match_instruction_restore_paused = False
        self.match_instruction_slider_drag_player_id = None
        self.match_instruction_slider_drag_key = None
        self.match_instruction_formation_draft = "4-3-3"

    def _restore_match_live_instructions(self) -> None:
        if not self.match_engine:
            return
        for side, baseline in self.match_live_instruction_baseline.items():
            team = self.match_engine.home if side == "home" else self.match_engine.away
            formation = str(baseline.get("formation", team.formation))
            self.match_engine.apply_formation(side, formation)
            team.club.instructions = normalize_team_instructions(baseline.get("instructions"))
            team.club.player_instructions = {
                str(player_id): {
                    key: normalize_player_instruction_value(key, value)
                    for key, value in (values or {}).items()
                    if key in DEFAULT_PLAYER_INSTRUCTIONS
                }
                for player_id, values in dict(baseline.get("player_instructions", {})).items()
            }

    def _enter_match_instruction_mode(self, mode: str) -> None:
        team = self._managed_match_team()
        if not self.match_engine or not team or mode not in {"team", "player"}:
            return
        if self.match_pending_substitutions or self.match_sub_animation or self.match_instruction_animation:
            return
        self.match_instruction_restore_paused = self.match_paused
        self.match_paused = True
        self.match_instruction_mode = mode
        self.match_instruction_slider_drag_player_id = None
        self.match_instruction_slider_drag_key = None
        self.match_instruction_team_draft = normalize_team_instructions(team.club.instructions)
        self.match_instruction_formation_draft = str(team.formation or team.club.formation or "4-3-3")
        self.match_instruction_player_draft = {
            str(player_id): {
                key: normalize_player_instruction_value(key, value)
                for key, value in (values or {}).items()
                if key in DEFAULT_PLAYER_INSTRUCTIONS
            }
            for player_id, values in dict(team.club.player_instructions).items()
        }
        active_ids = [player.profile.id for player in team.xi] + [profile.id for profile in team.bench]
        if self.match_selected_player_id not in active_ids:
            self.match_selected_player_id = active_ids[0] if active_ids else None

    def _confirm_match_instruction_changes(self) -> None:
        team = self._managed_match_team()
        if not self.match_engine or not team or not self.match_instruction_mode:
            return
        current_instructions = normalize_team_instructions(team.club.instructions)
        current_formation = str(team.formation or team.club.formation or "4-3-3")
        current_player_map = {
            str(player_id): {
                key: normalize_player_instruction_value(key, value)
                for key, value in (values or {}).items()
                if key in DEFAULT_PLAYER_INSTRUCTIONS
            }
            for player_id, values in dict(team.club.player_instructions).items()
        }
        draft_instructions = normalize_team_instructions(self.match_instruction_team_draft)
        draft_player_map = {
            str(player_id): {
                key: normalize_player_instruction_value(key, value)
                for key, value in (values or {}).items()
                if key in DEFAULT_PLAYER_INSTRUCTIONS
            }
            for player_id, values in dict(self.match_instruction_player_draft).items()
        }
        if draft_instructions != current_instructions or draft_player_map != current_player_map:
            changed = True
        else:
            changed = False
        if self.match_instruction_formation_draft != current_formation:
            changed = True
        if changed:
            self.match_pending_instruction_update = {
                "side": self._managed_match_side(),
                "formation": self.match_instruction_formation_draft,
                "instructions": draft_instructions,
                "player_instructions": draft_player_map,
            }
        self._reset_match_instruction_state(restore_pause=True)

    def _start_match_instruction_animation(self) -> None:
        update = self.match_pending_instruction_update or {}
        if not self.match_engine or not update:
            return
        side = str(update.get("side") or self._managed_match_side() or "home")
        team = self.match_engine.home if side == "home" else self.match_engine.away
        formation = str(update.get("formation") or team.formation or team.club.formation or "4-3-3")
        self.match_engine.apply_formation(side, formation)
        team.club.instructions = normalize_team_instructions(update.get("instructions"))
        team.club.player_instructions = {
            str(player_id): {
                key: normalize_player_instruction_value(key, value)
                for key, value in (values or {}).items()
                if key in DEFAULT_PLAYER_INSTRUCTIONS
            }
            for player_id, values in dict(update.get("player_instructions", {})).items()
        }
        self.match_paused = True
        self.match_instruction_animation = {
            "message": "INSTRUCTIONS CHANGED!",
            "duration": 1.5,
            "elapsed": 0.0,
        }
        self.match_pending_instruction_update = None

    def _update_match_instruction_animation(self, dt: float) -> None:
        if not self.match_instruction_animation:
            return
        self.match_instruction_animation["elapsed"] = float(self.match_instruction_animation.get("elapsed", 0.0)) + dt
        if self.match_instruction_animation["elapsed"] >= float(self.match_instruction_animation.get("duration", 1.5)):
            self.match_instruction_animation = None
            self.match_paused = False

    def _detect_ai_sub_animation(self, previous_state: dict[str, dict[str, object]]) -> None:
        if not self.match_engine or self.match_sub_mode or self.match_pending_substitutions or self.match_sub_animation:
            return
        for side in ("home", "away"):
            if side in self.match_engine.human_controlled_sides:
                continue
            team = self.match_engine.home if side == "home" else self.match_engine.away
            prior = previous_state.get(side, {})
            previous_xi = list(prior.get("xi_ids", []))
            previous_subs = int(prior.get("substitutions_used", 0))
            current_xi = [player.profile.id for player in team.xi]
            if current_xi == previous_xi or team.substitutions_used <= previous_subs:
                continue
            outgoing_ids = [player_id for player_id in previous_xi if player_id not in current_xi]
            incoming_ids = [player_id for player_id in current_xi if player_id not in previous_xi]
            if not outgoing_ids or not incoming_ids:
                continue
            pairs = list(zip(outgoing_ids, incoming_ids))
            if not pairs:
                continue
            self.match_paused = True
            self.match_sub_animation = {
                "side": side,
                "pairs": pairs,
                "duration": 1.8,
                "elapsed": 0.0,
                "applied": True,
            }
            break

    def _apply_squad_swap(self, source_id: str, target_id: str) -> None:
        if source_id == target_id:
            return
        availability = self._squad_player_availability()
        if source_id in self.squad_draft_bench_ids and target_id in self.squad_draft_xi_ids and not availability.get(source_id, True):
            return
        if target_id in self.squad_draft_bench_ids and source_id in self.squad_draft_xi_ids and not availability.get(target_id, True):
            return
        if source_id in self.squad_draft_xi_ids and target_id in self.squad_draft_bench_ids:
            xi_index = self.squad_draft_xi_ids.index(source_id)
            bench_index = self.squad_draft_bench_ids.index(target_id)
            self.squad_draft_xi_ids[xi_index], self.squad_draft_bench_ids[bench_index] = (
                self.squad_draft_bench_ids[bench_index],
                self.squad_draft_xi_ids[xi_index],
            )
        elif source_id in self.squad_draft_bench_ids and target_id in self.squad_draft_xi_ids:
            xi_index = self.squad_draft_xi_ids.index(target_id)
            bench_index = self.squad_draft_bench_ids.index(source_id)
            self.squad_draft_xi_ids[xi_index], self.squad_draft_bench_ids[bench_index] = (
                self.squad_draft_bench_ids[bench_index],
                self.squad_draft_xi_ids[xi_index],
            )
        elif source_id in self.squad_draft_xi_ids and target_id in self.squad_draft_xi_ids:
            source_index = self.squad_draft_xi_ids.index(source_id)
            target_index = self.squad_draft_xi_ids.index(target_id)
            self.squad_draft_xi_ids[source_index], self.squad_draft_xi_ids[target_index] = (
                self.squad_draft_xi_ids[target_index],
                self.squad_draft_xi_ids[source_index],
            )
        elif source_id in self.squad_draft_bench_ids and target_id in self.squad_draft_bench_ids:
            source_index = self.squad_draft_bench_ids.index(source_id)
            target_index = self.squad_draft_bench_ids.index(target_id)
            self.squad_draft_bench_ids[source_index], self.squad_draft_bench_ids[target_index] = (
                self.squad_draft_bench_ids[target_index],
                self.squad_draft_bench_ids[source_index],
            )
        else:
            return
        self._ensure_squad_selected_player()
        self._persist_squad_draft()

    def _reset_match_sub_state(self, restore_pause: bool = True) -> None:
        if restore_pause and self.match_engine and not self.match_engine.state.is_finished:
            self.match_paused = self.match_sub_restore_paused
        self.match_sub_mode = False
        self.match_sub_restore_paused = False
        self.match_sub_drag_player_id = None
        self.match_sub_drag_pos = None
        self.match_sub_hover_player_id = None
        self.match_sub_draft_xi_ids = []
        self.match_sub_draft_bench_ids = []

    def _match_has_natural_stoppage(self) -> bool:
        if not self.match_engine or self.match_engine.state.is_finished:
            return False
        state = self.match_engine.state
        return state.awaiting_start or state.restart_timer > 0.0 or state.restart_mode == "kickoff_setup"

    def _apply_pending_position_swaps(self) -> None:
        side = self._managed_match_side()
        if not self.match_engine or not side or not self.match_pending_position_swaps:
            return
        match_team = self.match_engine.home if side == "home" else self.match_engine.away
        seen: set[frozenset[str]] = set()
        for id_a, id_b in self.match_pending_position_swaps:
            pair = frozenset([id_a, id_b])
            if pair in seen:
                continue
            seen.add(pair)
            idx_a = next((i for i, p in enumerate(match_team.xi) if p.profile.id == id_a), None)
            idx_b = next((i for i, p in enumerate(match_team.xi) if p.profile.id == id_b), None)
            if idx_a is not None and idx_b is not None:
                match_team.xi[idx_a], match_team.xi[idx_b] = match_team.xi[idx_b], match_team.xi[idx_a]
                # Swap slot label and home position so the engine places them correctly
                pa = match_team.xi[idx_a]
                pb = match_team.xi[idx_b]
                pa.slot, pb.slot = pb.slot, pa.slot
                pa.home_x, pb.home_x = pb.home_x, pa.home_x
                pa.home_y, pb.home_y = pb.home_y, pa.home_y
        self.match_pending_position_swaps = []
        self.match_instruction_animation = {
            "message": "INSTRUCTIONS CHANGED!",
            "duration": 1.2,
            "elapsed": 0.0,
        }

    def _start_match_sub_animation(self) -> None:
        side = self._managed_match_side()
        if not self.match_engine or not side or not self.match_pending_substitutions:
            return
        self.match_paused = True
        self.match_sub_animation = {
            "side": side,
            "pairs": list(self.match_pending_substitutions),
            "duration": 1.8,
            "elapsed": 0.0,
            "applied": False,
        }

    def _update_match_sub_animation(self, dt: float) -> None:
        if not self.match_sub_animation or not self.match_engine:
            return
        animation = self.match_sub_animation
        animation["elapsed"] += dt
        duration = float(animation.get("duration", 1.8))
        midpoint = duration * 0.5
        if not animation.get("applied") and animation["elapsed"] >= midpoint:
            side = str(animation.get("side", "home"))
            applied = self.match_engine.apply_substitution_window(side, list(animation.get("pairs", [])))
            if applied > 0:
                active_ids = {player.profile.id for player in self.match_engine._team_state(side).xi}
                if self.match_selected_player_id and self.match_selected_player_id not in active_ids:
                    self.match_selected_player_id = next(iter(active_ids), None)
            self.match_pending_substitutions = []
            animation["applied"] = True
        if animation["elapsed"] >= duration:
            self.match_sub_animation = None
            self.match_paused = False

    def _enter_match_sub_mode(self) -> None:
        team = self._managed_match_team()
        side = self._managed_match_side()
        if not self.match_engine or not team or not side:
            return
        if self.match_pending_substitutions or self.match_sub_animation or self.match_instruction_mode or self.match_instruction_animation:
            return
        if not self.match_engine.can_make_substitution_window(side):
            return
        self.match_sub_restore_paused = self.match_paused
        self.match_paused = True
        self.match_sub_mode = True
        self.match_sub_drag_player_id = None
        self.match_sub_drag_pos = None
        self.match_sub_hover_player_id = None
        self.match_sub_draft_xi_ids = [player.profile.id for player in team.xi]
        self.match_sub_draft_bench_ids = [player.id for player in team.bench]

    def _apply_sub_draft_swap(self, source_id: str, target_id: str) -> None:
        team = self._managed_match_team()
        if not team:
            return
        if source_id == target_id:
            return
        if source_id in team.subbed_out_ids:
            return
        if target_id in team.subbed_out_ids:
            return
        if source_id in self.match_sub_draft_xi_ids and target_id in self.match_sub_draft_xi_ids:
            # Position swap between two starters — update draft only, apply on Confirm + ball stoppage
            si = self.match_sub_draft_xi_ids.index(source_id)
            ti = self.match_sub_draft_xi_ids.index(target_id)
            self.match_sub_draft_xi_ids[si], self.match_sub_draft_xi_ids[ti] = (
                self.match_sub_draft_xi_ids[ti],
                self.match_sub_draft_xi_ids[si],
            )
            return
        if source_id in self.match_sub_draft_xi_ids and target_id in self.match_sub_draft_bench_ids:
            xi_index = self.match_sub_draft_xi_ids.index(source_id)
            bench_index = self.match_sub_draft_bench_ids.index(target_id)
        elif source_id in self.match_sub_draft_bench_ids and target_id in self.match_sub_draft_xi_ids:
            xi_index = self.match_sub_draft_xi_ids.index(target_id)
            bench_index = self.match_sub_draft_bench_ids.index(source_id)
        else:
            return
        self.match_sub_draft_xi_ids[xi_index], self.match_sub_draft_bench_ids[bench_index] = (
            self.match_sub_draft_bench_ids[bench_index],
            self.match_sub_draft_xi_ids[xi_index],
        )
        remaining = 5 - team.substitutions_used
        diff_count = sum(1 for player, draft_id in zip(team.xi, self.match_sub_draft_xi_ids) if player.profile.id != draft_id)
        if diff_count > remaining:
            self.match_sub_draft_xi_ids[xi_index], self.match_sub_draft_bench_ids[bench_index] = (
                self.match_sub_draft_bench_ids[bench_index],
                self.match_sub_draft_xi_ids[xi_index],
            )

    def _confirm_match_subs(self) -> None:
        team = self._managed_match_team()
        side = self._managed_match_side()
        if not self.match_engine or not team or not side or not self.match_sub_mode:
            return
        current_xi_ids = {player.profile.id for player in team.xi}
        subs: list[tuple[str, str]] = []
        pos_swap_pairs: set[frozenset[str]] = set()
        pos_swaps: list[tuple[str, str]] = []
        for player, draft_id in zip(team.xi, self.match_sub_draft_xi_ids):
            if player.profile.id == draft_id:
                continue
            if draft_id in current_xi_ids:
                pair = frozenset([player.profile.id, draft_id])
                if pair not in pos_swap_pairs:
                    pos_swap_pairs.add(pair)
                    pos_swaps.append((player.profile.id, draft_id))
            else:
                subs.append((player.profile.id, draft_id))
        if subs:
            self.match_pending_substitutions = subs
        if pos_swaps:
            self.match_pending_position_swaps = pos_swaps
        self._reset_match_sub_state(restore_pause=True)

    def _start_next_match(self) -> None:
        if self.active_save_id is None or not self.overview:
            return
        fixture = self.overview.get("today_fixture")
        if not fixture:
            return
        # Validate XI and bench sizes before starting
        managed_id = self._managed_club_id()
        if managed_id and (fixture.get("home_club_id") == managed_id or fixture.get("away_club_id") == managed_id):
            availability = self._squad_player_availability()
            valid_xi = [pid for pid in self.squad_draft_xi_ids if pid and pid in availability]
            valid_bench = [pid for pid in self.squad_draft_bench_ids if pid and pid in availability]
            errors = []
            if len(valid_xi) < 11:
                errors.append(f"Starting XI needs 11 players ({len(valid_xi)} selected).")
            if len(valid_bench) < 9:
                errors.append(f"Bench needs 9 players ({len(valid_bench)} selected).")
            if errors:
                self.modal = {
                    "title": "SQUAD INCOMPLETE",
                    "message": " ".join(errors) + " Go to Squad/Tactics to fix your lineup.",
                    "buttons": [{"label": "GO TO TACTICS", "action": "match_preview:plan"}, {"label": "CLOSE", "action": "modal:close"}],
                }
                return
        with db_session(self.db_path) as conn:
            bootstrap_database(conn)
            clubs = load_clubs_from_db(conn, save_id=self.active_save_id)
        load_condition_state(self.db_path, clubs, save_id=self.active_save_id)
        home_id = fixture["home_club_id"]
        away_id = fixture["away_club_id"]
        if home_id not in clubs or away_id not in clubs:
            return
        managed_side = "home" if home_id == self.overview["club_id"] else "away" if away_id == self.overview["club_id"] else None
        controlled_sides = {managed_side} if managed_side else set()
        self.match_engine = MatchEngine(
            clubs[home_id],
            clubs[away_id],
            seed=hash((self.active_save_id, fixture["id"])) & 0xFFFFFFFF,
            human_controlled_sides=controlled_sides,
        )
        self.match_engine.set_speed(SPEED_MULTIPLIERS[self.match_speed_label])
        self.match_fixture = fixture
        self.match_clubs = clubs
        self.match_current_day = int(self.overview.get("current_day", 0))
        self.match_paused = False
        self.match_condition_saved = False
        self.screen = "match"
        self.match_finish_timer = 0.0
        self.match_selected_player_id = self.match_engine.home.xi[0].profile.id if self.match_engine.home.xi else None
        self._reset_match_sub_state(restore_pause=False)
        self._reset_match_instruction_state(restore_pause=False)
        self.match_pending_substitutions = []
        self.match_sub_animation = None
        self.match_pending_instruction_update = None
        self.match_instruction_animation = None
        self.match_live_instruction_baseline = {
            "home": {
                "instructions": normalize_team_instructions(self.match_engine.home.club.instructions),
                "formation": str(self.match_engine.home.formation),
                "player_instructions": {
                    str(player_id): dict(values or {})
                    for player_id, values in dict(self.match_engine.home.club.player_instructions).items()
                },
            },
            "away": {
                "instructions": normalize_team_instructions(self.match_engine.away.club.instructions),
                "formation": str(self.match_engine.away.formation),
                "player_instructions": {
                    str(player_id): dict(values or {})
                    for player_id, values in dict(self.match_engine.away.club.player_instructions).items()
                },
            },
        }

    def _advance_one_day(self) -> None:
        if self.active_save_id is None:
            return
        with db_session(self.db_path) as conn:
            managed_club_id = self._managed_club_id()
            advance_save_one_day(conn, self.active_save_id, managed_club_id)
        self._reload_overview()
        pygame.event.clear()  # discard clicks that queued during the blocking DB work

    def _advance_to_next_event(self) -> None:
        """Advance days until the user has a match today or a transfer notification appears."""
        if self.active_save_id is None:
            return
        managed_club_id = self._managed_club_id()
        prev_transfer_unread = self._count_unread_transfer_messages()
        self.renderer.draw_loading_overlay("SIMULATING...")
        for _ in range(365):
            pygame.event.pump()  # keep OS from marking the window as unresponsive
            with db_session(self.db_path) as conn:
                advance_save_one_day(conn, self.active_save_id, managed_club_id)
            self._reload_overview()
            if not self.overview:
                break
            # Stop when user has a match today
            if self.overview.get("today_fixture"):
                break
            # Stop when a new transfer notification appeared
            if self._count_unread_transfer_messages() > prev_transfer_unread:
                break
        pygame.event.clear()

    def _count_unread_transfer_messages(self) -> int:
        if not self.overview:
            return 0
        return sum(
            1 for m in self.overview.get("messages", [])
            if not m.get("is_read") and m.get("category", "") in ("transfer", "transfers", "transfer_offer", "offer")
        )

    def _finish_matchday(self) -> None:
        self._finish_matchday_with_score(None)

    def _build_match_report(self, engine: MatchEngine, fixture: dict) -> dict:
        state = engine.state
        def report_players(team, side: str) -> list[dict]:
            rows = []
            for profile in team.club.players:
                minutes = float(state.player_match_stats.get(profile.id, {}).get("minutes", 0.0))
                if minutes <= 0.01:
                    continue
                short_name = profile.name.split()[-1] if profile.name.split() else profile.name
                rows.append(
                    {
                        "id": profile.id,
                        "name": profile.name,
                        "short_name": short_name,
                        "position": profile.position,
                        "ovr": profile.ovr,
                        "side": side,
                        "minutes": minutes,
                    }
                )
            rows.sort(key=lambda player: (-float(player.get("minutes", 0.0)), player["name"]))
            return rows
        return {
            "fixture_id": int(fixture["id"]),
            "save_id": int(self.active_save_id or 0),
            "home": {
                "id": state.home.club.id,
                "name": state.home.name,
                "primary_color": state.home.club.colors.get("primary", "#D03434"),
                "secondary_color": state.home.club.colors.get("secondary", "#F5F5F5"),
                "badge": {
                    "template_id": state.home.club.badge_id,
                    "primary": state.home.club.badge_primary,
                    "secondary": state.home.club.badge_secondary,
                    "border": state.home.club.badge.get("border", "#F5F5F5"),
                },
            },
            "away": {
                "id": state.away.club.id,
                "name": state.away.name,
                "primary_color": state.away.club.colors.get("primary", "#3970D0"),
                "secondary_color": state.away.club.colors.get("secondary", "#F5F5F5"),
                "badge": {
                    "template_id": state.away.club.badge_id,
                    "primary": state.away.club.badge_primary,
                    "secondary": state.away.club.badge_secondary,
                    "border": state.away.club.badge.get("border", "#F5F5F5"),
                },
            },
            "home_score": int(state.home_score),
            "away_score": int(state.away_score),
            "team_stats": json.loads(json.dumps(state.team_match_stats)),
            "player_stats": json.loads(json.dumps(state.player_match_stats)),
            "player_goals": {key: int(value) for key, value in state.player_goals.items()},
            "player_assists": {key: int(value) for key, value in state.player_assists.items()},
            "injuries": {
                str(player_id): {
                    "days": int(float(stats.get("injury_days", 0.0) or 0.0)),
                }
                for player_id, stats in state.player_match_stats.items()
                if float(stats.get("injuries", 0.0) or 0.0) > 0.0
            },
            "players": {
                "home": report_players(state.home, "home"),
                "away": report_players(state.away, "away"),
            },
        }

    def _finish_matchday_with_score(self, score_override: tuple[int, int] | None) -> None:
        if not self.match_engine or not self.match_fixture or not self.match_clubs or self.active_save_id is None:
            return
        season_clubs = self.match_clubs
        fixture = self.match_fixture
        fixture_report = self._build_match_report(self.match_engine, fixture) if score_override is None else None
        if score_override is None:
            home_goals = self.match_engine.state.home_score
            away_goals = self.match_engine.state.away_score
        else:
            home_goals, away_goals = score_override
        with db_session(self.db_path) as conn:
            save_fixture_result(
                conn,
                fixture["id"],
                home_goals,
                away_goals,
                report=fixture_report,
            )
            if self.overview and self.active_save_id is not None:
                managed_id = str(self.overview.get("club_id", ""))
                is_home = str(fixture.get("home_club_id", "")) == managed_id
                current_date = str(self.overview.get("current_date") or "")
                standings = self.overview.get("standings", [])
                club_pos = next((int(s.get("position", 4)) for s in standings if str(s.get("club_id", "")) == managed_id), 4)
                apply_matchday_revenue(conn, self.active_save_id, is_home, current_date, club_pos)
            if fixture_report is not None and self.overview:
                managed_id = str(self.overview.get("club_id"))
                current_date = str(self.overview.get("current_date") or "")
                for player in fixture_report.get("players", {}).get("home", []) + fixture_report.get("players", {}).get("away", []):
                    player_id = str(player.get("id", ""))
                    stats = fixture_report.get("player_stats", {}).get(player_id, {})
                    if int(stats.get("red_cards", 0) or 0) <= 0:
                        continue
                    player_club = fixture_report["home"]["id"] if player.get("side") == "home" else fixture_report["away"]["id"]
                    if str(player_club) != managed_id:
                        continue
                    add_save_message(
                        conn,
                        self.active_save_id,
                        "discipline",
                        "RED CARD BAN",
                        f"{player.get('name', 'A player')} was sent off and will be unavailable through suspension.",
                        current_date,
                        "danger",
                        f"red_card:{fixture['id']}:{player_id}",
                    )
            match_day = fixture["match_day"]
            fixture_competition_id = str(fixture.get("competition_id") or "")
            same_day = list_matchday_fixtures(conn, self.active_save_id, match_day, competition_id=fixture_competition_id or None)
            for other in same_day:
                if other["id"] == fixture["id"]:
                    continue
                row = conn.execute("SELECT played FROM fixtures WHERE id = ?", (other["id"],)).fetchone()
                if row is not None and int(row["played"]) == 1:
                    continue
                engine = MatchEngine(
                    season_clubs[other["home_club_id"]],
                    season_clubs[other["away_club_id"]],
                    seed=hash((self.active_save_id, other["id"])) & 0xFFFFFFFF,
                )
                engine.set_speed(SPEED_MULTIPLIERS["X4"])
                engine.start_match_flow()
                safety = 0
                while not engine.state.is_finished and safety < 12000:
                    if engine.state.awaiting_start:
                        engine.start_match_flow()
                    engine.update(1.0 / 30.0)
                    safety += 1
                apply_post_match_condition(engine.state)
                save_fixture_result(
                    conn,
                    other["id"],
                    engine.state.home_score,
                    engine.state.away_score,
                    report=self._build_match_report(engine, other),
                )
            save_condition_state_to_conn(conn, season_clubs, self.match_current_day, save_id=self.active_save_id)
            # Simulate cross-competition AI fixtures on the same calendar date using fast
            # Poisson model (MatchEngine loop above only covers same match_day integer).
            fixture_date_str = str(fixture.get("fixture_date", ""))
            managed_id_str = str(self.overview.get("club_id", "")) if self.overview else ""
            if fixture_date_str and self.active_save_id is not None:
                from engine.simulation import simulate_all_ai_fixtures
                cross_comp_rows = conn.execute(
                    """
                    SELECT id, home_club_id, away_club_id, competition_id FROM fixtures
                    WHERE save_id=? AND played=0 AND fixture_date=?
                      AND home_club_id!=? AND away_club_id!=?
                    """,
                    (self.active_save_id, fixture_date_str, managed_id_str, managed_id_str),
                ).fetchall()
                if cross_comp_rows:
                    _sy_row = conn.execute("SELECT season_year FROM saves WHERE id=?", (self.active_save_id,)).fetchone()
                    sy = int(_sy_row["season_year"]) if _sy_row else 2025
                    simulate_all_ai_fixtures(conn, self.active_save_id, cross_comp_rows, sy)
            # Generate TOTW immediately so it appears on the next overview load
            # (uses virtual date = fixture_date + 2 to satisfy the 2-day check)
            if fixture_date_str and self.overview:
                trigger_totw_for_match_day(conn, self.active_save_id, fixture_date_str, managed_id_str or None)
            conn.commit()
        self.match_condition_saved = True
        self.match_engine = None
        self.match_fixture = None
        self.match_clubs = None
        self.match_finish_timer = 0.0
        self.match_selected_player_id = None
        self._reset_match_sub_state(restore_pause=False)
        self._reset_match_instruction_state(restore_pause=False)
        self.match_pending_substitutions = []
        self.match_pending_position_swaps = []
        self.match_sub_animation = None
        self.match_pending_instruction_update = None
        self.match_instruction_animation = None
        self.match_live_instruction_baseline = {}
        self.fixture_report = None
        self.fixture_report_selected_player_id = None
        self.screen = "overview"
        self.overview_tab = "overview"
        self._reload_state()

    def _forfeit_current_match(self) -> None:
        if not self.match_engine or not self.match_fixture or not self.overview:
            return
        managed_club_id = self.overview["club_id"]
        fixture = self.match_fixture
        if fixture["home_club_id"] == managed_club_id:
            score = (0, 3)
        else:
            score = (3, 0)
        self._finish_matchday_with_score(score)

    def _open_escape_modal(self) -> None:
        if self.modal:
            return
        if self.screen == "match" and self.match_engine and not self.match_engine.state.is_finished:
            self.match_paused = True
            self.modal_paused_match = True
        buttons = []
        if self.screen == "match" and self.match_engine and not self.match_engine.state.is_finished:
            buttons.append({"label": "FORFEIT", "action": "modal:confirm_forfeit", "fill": (206, 54, 54)})
        buttons.extend(
            [
                {"label": "OPTIONS", "action": "modal:options"},
                {"label": "MAIN MENU", "action": "modal:confirm_menu"},
                {"label": "QUIT", "action": "modal:confirm_quit", "fill": (248, 187, 32), "text_color": (24, 24, 28)},
                {"label": "CANCEL", "action": "modal:close"},
            ]
        )
        self.modal = {
            "title": "PAUSE MENU",
            "message": "CHOOSE AN ACTION",
            "buttons": buttons,
        }

    def _open_confirmation_modal(self, action: str) -> None:
        in_live_match = self.screen == "match" and self.match_engine and not self.match_engine.state.is_finished
        labels = {
            "forfeit": "FORFEIT MATCH",
            "menu": "FORFEIT + MAIN MENU" if in_live_match else "MAIN MENU",
            "quit": "FORFEIT + QUIT" if in_live_match else "QUIT",
        }
        self.modal = {
            "title": "ARE YOU SURE?",
            "message": labels[action],
            "buttons": [
                {"label": "YES", "action": f"modal:do_{action}", "fill": (206, 54, 54) if action == "forfeit" else (248, 187, 32), "text_color": (24, 24, 28) if action != "forfeit" else (245, 245, 245)},
                {"label": "NO", "action": "modal:close"},
            ],
        }

    def _navigate_to_club(self, club_id: str) -> None:
        clubs_meta = (self.overview or {}).get("clubs", [])
        club_meta = next((c for c in clubs_meta if c.get("id") == club_id), None)
        if club_meta is None:
            return
        with db_session(self.db_path) as conn:
            players = list_club_players(conn, club_id, save_id=self.active_save_id)
        club_setup = (self.overview or {}).get("club_setups", {}).get(club_id, {})
        self.detail_club_data = {
            **club_meta,
            "players": players,
            "formation": str(club_setup.get("formation", "4-3-3")),
        }
        self.detail_player_data = None
        self.detail_selected_player_id = None
        self.detail_show_attrs = False
        self.detail_nav_stack = [(self.screen, self.overview_tab)]
        self.screen = "club_detail"

    def _navigate_to_player(self, player_id: str) -> None:
        players = (self.detail_club_data or {}).get("players", [])
        player = next((p for p in players if p.get("id") == player_id), None)
        if player is None:
            return
        self.detail_player_data = player
        self.detail_show_attrs = False
        managed_club_id = (self.overview or {}).get("club_id", "")
        player_club_id = str((self.detail_club_data or {}).get("id", ""))
        self.detail_is_user_club = (player_club_id == managed_club_id)
        self.detail_scout_pending: bool = False
        if not self.detail_is_user_club and self.active_save_id:
            season_year = int((self.overview or {}).get("season_year", 0))
            with db_session(self.db_path) as conn:
                self.detail_scouting_pct = get_player_scouting_pct(conn, self.active_save_id, player_id, season_year)
                self.detail_scout_pending = has_pending_scout_task(conn, self.active_save_id, player_id)
        else:
            self.detail_scouting_pct = 100
        self.detail_nav_stack.append((self.screen, self.overview_tab))
        self.screen = "player_detail"

    def _handle_action(self, action: str | None) -> None:
        if not action:
            return
        if action == "modal:close":
            self.modal = None
            if self.modal_paused_match and self.screen == "match" and self.match_engine and not self.match_engine.state.is_finished:
                self.match_paused = False
            self.modal_paused_match = False
            return
        if action == "modal:confirm_forfeit":
            self._open_confirmation_modal("forfeit")
            return
        if action == "match_preview:plan":
            self.modal = None
            self.overview_tab = "squad_formation"
            self.overview_club_id = self._managed_club_id()
            self._load_squad_draft()
            return
        if action == "match_preview:play":
            self.modal = None
            self._start_next_match()
            return
        if action == "modal:confirm_menu":
            self._open_confirmation_modal("menu")
            return
        if action == "modal:confirm_quit":
            self._open_confirmation_modal("quit")
            return
        if action == "modal:options":
            self.modal = None
            self.options_return_screen = self.screen
            self.screen = "options"
            self._reload_state()
            return
        if action == "modal:do_forfeit":
            self.modal = None
            self.modal_paused_match = False
            self._forfeit_current_match()
            return
        if action == "modal:do_menu":
            self.modal = None
            self.modal_paused_match = False
            if self.screen == "match" and self.match_engine and not self.match_engine.state.is_finished:
                self._forfeit_current_match()
                self.screen = "menu"
                return
            self.screen = "menu"
            self.error_message = None
            return
        if action == "modal:do_quit":
            self.modal = None
            self.modal_paused_match = False
            if self.screen == "match" and self.match_engine and not self.match_engine.state.is_finished:
                self._forfeit_current_match()
            self.running = False
            return
        if action == "modal:confirm_delete_save":
            if self.selected_save_id is None:
                return
            self.modal = {
                "title": "ARE YOU SURE?",
                "message": "DELETE THIS SAVE?\nALL RELATED RECORDS WILL BE REMOVED",
                "buttons": [
                    {"label": "YES", "action": "modal:do_delete_save", "fill": (206, 54, 54)},
                    {"label": "NO", "action": "modal:close"},
                ],
            }
            return
        if action == "modal:do_delete_save":
            if self.selected_save_id is None:
                self.modal = None
                return
            with db_session(self.db_path) as conn:
                delete_save_game(conn, self.selected_save_id)
                conn.commit()
            if self.active_save_id == self.selected_save_id:
                self.active_save_id = None
                self.overview = None
                self.overview_club_id = None
            self.selected_save_id = None
            self.modal = None
            self._reload_state()
            self.screen = "load_game"
            return
        if action == "menu:quit":
            self.running = False
            return
        if action == "menu:new_game":
            self.screen = "new_game_name"
            self.error_message = None
            self.manager_name = ""
            return
        if action == "menu:load_game":
            self.selected_save_id = None
            self.screen = "load_game"
            self._reload_state()
            return
        if action == "menu:options":
            self.options_return_screen = None
            self.screen = "options"
            self._reload_state()
            return
        if action == "back:menu":
            if self.screen == "options" and self.options_return_screen:
                self.screen = self.options_return_screen
                if self.options_return_screen == "match" and self.match_engine and not self.match_engine.state.is_finished:
                    self.match_paused = False
                self.options_return_screen = None
            else:
                self.screen = "menu"
            self.error_message = None
            return
        if action == "back:new_game_name":
            self.screen = "new_game_name"
            return
        if action == "back:select_league":
            self.screen = "select_league"
            return
        if action == "new_game:continue":
            if not self.manager_name.strip():
                self.error_message = "Please enter a manager name."
            else:
                self.error_message = None
                self.screen = "select_league"
            return
        if action.startswith("league:"):
            self.selected_league_id = action.split(":", 1)[1]
            self._load_league_clubs()
            self.screen = "select_club"
            return
        if action.startswith("club:"):
            self.selected_club_id = action.split(":", 1)[1]
            self._create_new_save()
            return
        if action.startswith("option:"):
            _, key, value = action.split(":", 2)
            self._save_option(key, value)
            return
        if action.startswith("load:"):
            self._load_save(int(action.split(":", 1)[1]))
            return
        if action.startswith("match:player:"):
            player_id = action.split(":", 2)[2]
            if self.screen == "match":
                self.match_selected_player_id = player_id
            elif self.screen == "match_report":
                self.fixture_report_selected_player_id = player_id
            return
        if action == "match:subs:start":
            self._enter_match_sub_mode()
            return
        if action == "match:subs:cancel":
            self._reset_match_sub_state(restore_pause=True)
            return
        if action == "match:subs:confirm":
            self._confirm_match_subs()
            return
        if action == "match:instructions:team":
            self._enter_match_instruction_mode("team")
            return
        if action == "match:instructions:player":
            self._enter_match_instruction_mode("player")
            return
        if action == "match:instructions:cancel":
            self._reset_match_instruction_state(restore_pause=True)
            return
        if action == "match:instructions:confirm":
            self._confirm_match_instruction_changes()
            return
        if action.startswith("match:team_instruction_step:") or action.startswith("match:team:instruction_step:"):
            if action.startswith("match:team:instruction_step:"):
                _, _, _, key, delta_text = action.split(":", 4)
            else:
                _, _, key, delta_text = action.split(":", 3)
            options = TEAM_INSTRUCTION_OPTIONS.get(key, [])
            if options:
                current = str(self.match_instruction_team_draft.get(key, options[0]))
                try:
                    index = options.index(current)
                except ValueError:
                    index = 0
                next_index = max(0, min(len(options) - 1, index + int(delta_text)))
                self.match_instruction_team_draft[key] = options[next_index]
            return
        if action.startswith("match:instruction_player:select:"):
            self.match_selected_player_id = action.split(":", 3)[3]
            return
        if action.startswith("match:formation:"):
            formation = action.split(":", 2)[2]
            if formation in available_formations():
                self.match_instruction_formation_draft = formation
            return
        if action.startswith("overview:fixture:"):
            fixture_id = int(action.split(":", 2)[2])
            with db_session(self.db_path) as conn:
                report = get_fixture_report(conn, fixture_id)
                if not report:
                    # No full report — load minimal score data for the modal
                    row = conn.execute(
                        """SELECT f.home_goals, f.away_goals,
                                  hc.name AS home_name, ac.name AS away_name
                           FROM fixtures f
                           JOIN clubs hc ON hc.id = f.home_club_id
                           JOIN clubs ac ON ac.id = f.away_club_id
                           WHERE f.id=?""",
                        (fixture_id,),
                    ).fetchone()
                    if row:
                        self.modal = {
                            "type": "info",
                            "title": "FULL TIME",
                            "message": f"{row['home_name']}  {row['home_goals']} - {row['away_goals']}  {row['away_name']}",
                            "buttons": [{"label": "CLOSE", "action": "modal:close"}],
                        }
            if report:
                self.fixture_report = report
                home_players = report.get("players", {}).get("home", [])
                away_players = report.get("players", {}).get("away", [])
                self.fixture_report_selected_player_id = home_players[0]["id"] if home_players else away_players[0]["id"] if away_players else None
                self.screen = "match_report"
            return
        if action.startswith("overview_tab:"):
            tab = action.split(":", 1)[1]
            if tab in {"matches", "matches_fixtures", "matches_standings"}:
                if tab in {"matches", "matches_fixtures"}:
                    self.overview_tab = "matches_fixtures"
                    self._set_fixtures_page_to_current_round()
                else:
                    self.overview_tab = "matches_standings"
                return
            if tab in {"transfers", "transfers_market", "transfers_listings", "transfers_talks"}:
                if tab in {"transfers", "transfers_market"}:
                    self.overview_tab = "transfers_market"
                elif tab == "transfers_listings":
                    self.overview_tab = "transfers_listings"
                else:
                    self.overview_tab = "transfers_talks"
                self._reload_transfer_data()
                return
            if tab in {"club", "club_finances"}:
                self.overview_tab = "club_finances"
                return
            if tab == "club_staff":
                self.overview_tab = "club_staff"
                return
            if tab == "club_scouting":
                self.overview_tab = "club_scouting"
                return
            if tab in {"squad", "squad_formation"}:
                tab = "squad_formation"
            elif tab == "squad_players":
                self._ensure_squad_selected_player()
            if tab in {"matches", "matches_fixtures"}:
                self.overview_tab = "matches_fixtures"
                self._set_fixtures_page_to_current_round()
                return
            self.squad_drag_player_id = None
            self.squad_drag_pos = None
            self.squad_mouse_down_player_id = None
            self.squad_mouse_down_pos = None
            self.squad_hover_target_id = None
            self.squad_hover_player_id = None
            self.squad_slider_drag_player_id = None
            self.squad_slider_drag_key = None
            self.overview_tab = tab
            if self._is_squad_tab(tab):
                self.overview_club_id = self._managed_club_id()
                self._load_squad_draft()
            return
        if action.startswith("squad:formation:"):
            self._change_squad_formation(action.split(":", 2)[2])
            return
        if action.startswith("squad:instruction_step:"):
            _, _, key, delta_text = action.split(":", 3)
            self._step_squad_instruction(key, int(delta_text))
            return
        if action.startswith("squad:instruction:"):
            _, _, key, value = action.split(":", 3)
            self._change_squad_instruction(key, value)
            return
        if action.startswith("squad_roles:select:"):
            role_key = action.split(":", 2)[2]
            self.squad_roles_selected_role = role_key if self.squad_roles_selected_role != role_key else None
            return
        if action.startswith("squad_roles:assign:"):
            player_id = action.split(":", 2)[2]
            if self.squad_roles_selected_role:
                self.squad_roles[self.squad_roles_selected_role] = player_id
                self.squad_roles_selected_role = None
            return
        if action.startswith("squad_roles:clear:"):
            role_key = action.split(":", 2)[2]
            self.squad_roles.pop(role_key, None)
            return
        if action == "squad:show_bench":
            self.squad_show_reserves = False
            self.squad_show_unavailable = False
            return
        if action == "squad:toggle_reserves":
            self.squad_show_reserves = not self.squad_show_reserves
            self.squad_show_unavailable = False
            return
        if action == "squad:show_unavailable":
            self.squad_show_unavailable = True
            self.squad_show_reserves = False
            return
        if action.startswith("squad:reserve_to_bench:"):
            reserve_id = action.split(":", 2)[2]
            if reserve_id not in self.squad_draft_bench_ids:
                bench_len = len(self.squad_draft_bench_ids)
                if bench_len < 9:
                    self.squad_draft_bench_ids.append(reserve_id)
                    self._persist_squad_draft()
                else:
                    # Bench full — prompt user to choose who to drop
                    self.squad_pending_reserve_id = reserve_id
                    self.squad_show_reserves = False
                    self.squad_show_unavailable = False  # switch to bench view to pick
            return
        if action.startswith("squad:swap_with_reserve:"):
            bench_player_id = action.split(":", 2)[2]
            reserve_id = self.squad_pending_reserve_id
            if reserve_id and bench_player_id in self.squad_draft_bench_ids:
                idx = self.squad_draft_bench_ids.index(bench_player_id)
                self.squad_draft_bench_ids[idx] = reserve_id
                self.squad_pending_reserve_id = None
                self._persist_squad_draft()
            return
        if action == "squad:cancel_reserve_swap":
            self.squad_pending_reserve_id = None
            return
        if action.startswith("squad:select_player:"):
            self.squad_selected_player_id = action.split(":", 2)[2]
            return
        if action.startswith("squad:open_player:"):
            self.squad_selected_player_id = action.split(":", 2)[2]
            self.overview_tab = "squad_players"
            self.overview_club_id = self._managed_club_id() if getattr(self, "overview", None) else None
            return
        if action.startswith("squad:player_instruction:"):
            _, _, _, player_id, key, delta_text = action.split(":", 5)
            self._change_player_instruction(player_id, key, int(delta_text))
            return
        if action.startswith("training:team_focus:"):
            self._change_training_settings(team_focus=action.split(":", 2)[2])
            return
        if action.startswith("training:intensity:"):
            self._change_training_settings(intensity=action.split(":", 2)[2])
            return
        if action.startswith("training:player_focus:"):
            _, _, player_id, focus = action.split(":", 3)
            self._change_player_training_focus(player_id, focus)
            return
        if action.startswith("select_save:"):
            self.selected_save_id = int(action.split(":", 1)[1])
            return
        if action == "load_game:load_selected":
            if self.selected_save_id is not None:
                self._load_save(self.selected_save_id)
            return
        if action == "load_game:delete_selected":
            if self.selected_save_id is not None:
                self._handle_action("modal:confirm_delete_save")
            return
        if action.startswith("overview_club:"):
            self.overview_club_id = action.split(":", 1)[1]
            return
        if action == "overview:play_next_match":
            fixture = self.overview.get("today_fixture") if self.overview else None
            if not fixture:
                return
            self.modal = {
                "type": "match_preview",
                "title": "MATCH PREVIEW",
                "fixture": fixture,
                "overview": self.overview or {},
                "buttons": [
                    {"label": "PLAN STRAT", "action": "match_preview:plan", "fill": (248, 187, 32), "text_color": (24, 24, 28), "icon": "plan"},
                    {"label": "PLAY MATCH", "action": "match_preview:play", "fill": (46, 160, 67), "text_color": (245, 245, 245), "icon": "ball"},
                ],
            }
            return
        if action == "overview:advance_day":
            self._advance_one_day()
            return
        if action == "overview:advance_to_event":
            self._advance_to_next_event()
            return
        if action == "back:match_report":
            self.fixture_report = None
            self.fixture_report_selected_player_id = None
            self.screen = "overview"
            return
        if action == "fixtures:page:prev":
            self.fixtures_page = max(1, self.fixtures_page - 1)
            self._clamp_fixtures_page()
            return
        if action == "fixtures:page:next":
            self.fixtures_page = self.fixtures_page + 1
            self._clamp_fixtures_page()
            return
        if action == "fixtures:prev_gameweek":
            self.fixtures_page = max(1, self.fixtures_page - 1)
            self._clamp_fixtures_page()
            return
        if action == "fixtures:next_gameweek":
            self.fixtures_page = self.fixtures_page + 1
            self._clamp_fixtures_page()
            return
        if action == "back:fixtures":
            self.screen = "overview"
            return
        if action.startswith("news:open:"):
            try:
                msg_id = int(action.split(":", 2)[2])
            except (ValueError, IndexError):
                return
            msg = next((m for m in (self.overview or {}).get("messages", []) if m.get("id") == msg_id), None)
            if msg:
                # Mark as read in DB and update local state without full reload
                if self.active_save_id and not msg.get("is_read"):
                    # Enqueue mark as read; update UI immediately
                    self.db_worker.enqueue(mark_message_read, int(self.active_save_id), int(msg_id))
                    msg["is_read"] = True
                    if self.overview:
                        self.overview["unread_messages"] = max(0, int(self.overview.get("unread_messages", 0)) - 1)
                body_str = str(msg.get("body", ""))
                totw_data = None
                try:
                    parsed = json.loads(body_str)
                    if isinstance(parsed, dict) and parsed.get("type") == "totw":
                        totw_data = parsed
                except (ValueError, TypeError):
                    pass
                self.modal = {
                    "type": "news_detail",
                    "title": str(msg.get("title", "MESSAGE")).upper(),
                    "body": body_str,
                    "totw_data": totw_data,
                    "category": str(msg.get("category", "")),
                    "severity": str(msg.get("severity", "info")),
                    "date": str(msg.get("date_text", "")),
                    "buttons": [{"label": "CLOSE", "action": "modal:close"}],
                }
            return
        if action.startswith("news:page:"):
            try:
                page = int(action.split(":", 2)[2])
            except (ValueError, IndexError):
                return
            if not self.active_save_id or not self.overview:
                return
            total = int(self.overview.get("messages_total", 0))
            max_page = max(0, (total - 1) // 10)
            self.overview_news_page = max(0, min(page, max_page))
            self._reload_state()
            return
        if action.startswith("squad:list_player:"):
            player_id = action.split(":", 2)[2]
            if not self.active_save_id or not self.overview:
                return
            current_date = str(self.overview.get("current_date", ""))
            window_open, window_type = get_transfer_window_status(current_date) if current_date else (False, "")
            if not window_open:
                self.modal = {
                    "type": "confirm",
                    "title": "WINDOW CLOSED",
                    "message": "The transfer window is not open.\nYou can only list players during\na transfer window.",
                    "buttons": [{"label": "OK", "action": "modal:close"}],
                }
                return
            club_id = str(self.overview.get("club_id", ""))
            all_players = self.overview.get("players_by_club", {}).get(club_id, [])
            player = next((p for p in all_players if str(p.get("id", "")) == player_id), None)
            if player is None:
                return
            from engine.db import _compute_asking_price
            ovr = int(player.get("ovr", 70))
            market_price = _compute_asking_price(ovr)
            def _fmtp(v: int) -> str:
                return f"£{v // 1_000_000}M" if v >= 1_000_000 else f"£{v // 1_000}K"
            low_price = max(500_000, round(market_price * 0.70 / 500_000) * 500_000)
            high_price = round(market_price * 1.50 / 500_000) * 500_000
            self.modal = {
                "type": "confirm",
                "title": "LIST ON MARKET",
                "message": f"{str(player.get('name', '')).upper()}\nMARKET VALUE: {_fmtp(market_price)}\nSET YOUR ASKING PRICE:",
                "buttons": [
                    {"label": f"{_fmtp(low_price)} (QUICK SALE)", "action": f"squad:confirm_list:{player_id}:{low_price}"},
                    {"label": f"{_fmtp(market_price)} (MARKET)", "action": f"squad:confirm_list:{player_id}:{market_price}", "fill": (46, 160, 67), "text_color": (245, 245, 245)},
                    {"label": f"{_fmtp(high_price)} (PREMIUM)", "action": f"squad:confirm_list:{player_id}:{high_price}"},
                    {"label": "CANCEL", "action": "modal:close"},
                ],
            }
            return
        if action.startswith("squad:confirm_list:"):
            parts = action.split(":", 3)
            if len(parts) < 4:
                return
            player_id, price_str = parts[2], parts[3]
            try:
                custom_price = int(price_str)
            except ValueError:
                return
            if not self.active_save_id or not self.overview:
                return
            current_date = str(self.overview.get("current_date", ""))
            _, window_type = get_transfer_window_status(current_date) if current_date else (False, "")
            season_year = int(self.overview.get("season_year", 0))
            club_id = str(self.overview.get("club_id", ""))
            with db_session(self.db_path) as conn:
                list_player_for_transfer(conn, self.active_save_id, player_id, club_id, current_date, season_year, window_type, custom_price=custom_price)
                conn.commit()
            self._reload_transfer_data()
            self.modal = None
            return
        if action.startswith("transfers:make_offer:"):
            player_id = action.split(":", 2)[2]
            if not self.active_save_id or not self.overview:
                return
            listing = next((l for l in self.transfer_data.get("market", []) if str(l.get("player_id", "")) == player_id), None)
            if not listing:
                return
            asking = int(listing.get("asking_price", 0))
            player_name = str(listing.get("player_name", "PLAYER")).upper()
            low = max(500_000, round(asking * 0.60 / 500_000) * 500_000)
            mid_low = max(500_000, round(asking * 0.80 / 500_000) * 500_000)
            high = round(asking * 1.10 / 500_000) * 500_000
            def _fmt(v: int) -> str:
                return f"£{v // 1_000_000}M" if v >= 1_000_000 else f"£{v // 1_000}K"
            self.modal = {
                "type": "confirm",
                "title": "MAKE OFFER",
                "message": f"{player_name}\nASKING: {_fmt(asking)}\nSELECT OFFER AMOUNT:",
                "buttons": [
                    {"label": f"{_fmt(low)} (LOW)", "action": f"transfers:confirm_offer:{player_id}:{low}"},
                    {"label": f"{_fmt(mid_low)} (BELOW)", "action": f"transfers:confirm_offer:{player_id}:{mid_low}"},
                    {"label": f"{_fmt(asking)} (ASKING)", "action": f"transfers:confirm_offer:{player_id}:{asking}", "fill": (46, 160, 67), "text_color": (245, 245, 245)},
                    {"label": f"{_fmt(high)} (ABOVE)", "action": f"transfers:confirm_offer:{player_id}:{high}"},
                    {"label": "CANCEL", "action": "modal:close"},
                ],
            }
            return
        if action.startswith("transfers:confirm_offer:"):
            parts = action.split(":", 3)
            if len(parts) < 4:
                return
            player_id, amount_str = parts[2], parts[3]
            try:
                amount = int(amount_str)
            except ValueError:
                return
            if not self.active_save_id or not self.overview:
                return
            # Finance check
            finances = self.overview.get("finances", {})
            budget = int(finances.get("transfer_budget", 0))
            balance = int(finances.get("balance", 0))
            affordable = min(budget, balance)
            if amount > affordable:
                def _fmt(v: int) -> str:
                    return f"£{v // 1_000_000}M" if v >= 1_000_000 else f"£{v // 1_000}K"
                self.modal = {
                    "type": "confirm",
                    "title": "INSUFFICIENT FUNDS",
                    "message": f"OFFER: {_fmt(amount)}\nTRANSFER BUDGET: {_fmt(budget)}\nBALANCE: {_fmt(balance)}\n\nYou cannot afford this offer.",
                    "buttons": [{"label": "OK", "action": "modal:close"}],
                }
                return
            current_date = str(self.overview.get("current_date", ""))
            window_open, window_type = get_transfer_window_status(current_date) if current_date else (False, "")
            if not window_open:
                self.modal = {
                    "type": "confirm",
                    "title": "WINDOW CLOSED",
                    "message": "The transfer window is not open.",
                    "buttons": [{"label": "OK", "action": "modal:close"}],
                }
                return
            season_year = int(self.overview.get("season_year", 0))
            listing = next((l for l in self.transfer_data.get("market", []) if str(l.get("player_id", "")) == player_id), None)
            w_type = str((listing or {}).get("window_type", window_type))
            s_year = int((listing or {}).get("season_year", season_year))
            with db_session(self.db_path) as conn:
                result = make_transfer_offer(conn, self.active_save_id, player_id, amount, w_type, s_year, current_date)
                conn.commit()
            self._reload_transfer_data()
            if result.get("ok"):
                self.modal = {
                    "type": "confirm",
                    "title": "OFFER SUBMITTED",
                    "message": "Offer sent to club board.\nYou will receive a response within 2-4 days.",
                    "buttons": [{"label": "OK", "action": "modal:close"}],
                }
            else:
                err = str(result.get("error", "unknown"))
                err_msg = {
                    "max_offers_reached": "You have already made the maximum number of offers for this player this window.",
                    "not_listed": "This player is no longer available for transfer.",
                }.get(err, f"Could not submit offer: {err}")
                self.modal = {
                    "type": "confirm",
                    "title": "OFFER FAILED",
                    "message": err_msg,
                    "buttons": [{"label": "OK", "action": "modal:close"}],
                }
            return
        if action.startswith("transfers:withdraw:"):
            listing_id_str = action.split(":", 2)[2]
            try:
                listing_id = int(listing_id_str)
            except ValueError:
                return
            if not self.active_save_id:
                return
            if not self.active_save_id:
                return
            with db_session(self.db_path) as conn:
                withdraw_transfer_listing(conn, self.active_save_id, listing_id)
                conn.commit()
            self._reload_transfer_data()
            return
        if action.startswith("transfers:accept_inbound:"):
            offer_id_str = action.split(":", 2)[2]
            try:
                offer_id_int = int(offer_id_str)
            except ValueError:
                return
            if not self.active_save_id or not self.overview:
                return
            club_id = str(self.overview.get("club_id", ""))
            current_date = str(self.overview.get("current_date", ""))
            with db_session(self.db_path) as conn:
                result = accept_inbound_offer(conn, self.active_save_id, offer_id_int, current_date, club_id)
                conn.commit()
            self._reload_state()
            if result.get("ok"):
                amt = int(result.get("amount", 0))
                def _fmtm(v: int) -> str:
                    return f"£{v // 1_000_000}M" if v >= 1_000_000 else f"£{v // 1_000}K"
                self.modal = {
                    "type": "confirm",
                    "title": "PLAYER SOLD",
                    "message": f"{str(result.get('player_name', '')).upper()} has been sold for {_fmtm(amt)}.\nFunds added to your transfer budget.",
                    "buttons": [{"label": "OK", "action": "modal:close"}],
                }
            return
        if action.startswith("transfers:decline_inbound:"):
            offer_id_str = action.split(":", 2)[2]
            try:
                offer_id_int = int(offer_id_str)
            except ValueError:
                return
            if not self.active_save_id:
                return
            with db_session(self.db_path) as conn:
                decline_inbound_offer(conn, self.active_save_id, offer_id_int)
                conn.commit()
            self._reload_transfer_data()
            return
        if action.startswith("transfers:negotiate:"):
            offer_id = action.split(":", 2)[2]
            self.transfer_negotiate_offer_id = offer_id
            if not self.active_save_id or not self.overview:
                return
            with db_session(self.db_path) as conn:
                offers = get_accepted_offers(conn, self.active_save_id)
            offer = next((o for o in offers if str(o.get("id", "")) == offer_id), None)
            if not offer:
                return
            ovr = int(offer.get("ovr", 75))
            market_rate = max(1_000, ovr * 600)
            player_name = str(offer.get("player_name", "PLAYER")).upper()[:20]
            def _fw(v: int) -> str:
                return f"£{v:,}/WK"
            low_w = max(500, round(market_rate * 0.80 / 500) * 500)
            high_w = round(market_rate * 1.30 / 500) * 500
            top_w = round(market_rate * 1.80 / 500) * 500
            self.modal = {
                "type": "confirm",
                "title": "PLAYER NEGOTIATION",
                "message": f"{player_name}\nMARKET RATE: {_fw(market_rate)}\n\nCHOOSE CONTRACT TERMS (3 YEARS):\nPlayer will respond within 2-3 days.",
                "buttons": [
                    {"label": f"{_fw(low_w)} — BELOW MARKET", "action": f"transfers:submit_negotiation:{offer_id}:{low_w}:3"},
                    {"label": f"{_fw(market_rate)} — MARKET RATE", "action": f"transfers:submit_negotiation:{offer_id}:{market_rate}:3", "fill": (46, 160, 67), "text_color": (245, 245, 245)},
                    {"label": f"{_fw(high_w)} — ABOVE MARKET", "action": f"transfers:submit_negotiation:{offer_id}:{high_w}:3"},
                    {"label": f"{_fw(top_w)} — TOP WAGES", "action": f"transfers:submit_negotiation:{offer_id}:{top_w}:3"},
                    {"label": "CANCEL", "action": "modal:close"},
                ],
            }
            return
        if action.startswith("transfers:submit_negotiation:"):
            parts = action.split(":", 4)
            if len(parts) < 5:
                return
            offer_id_str, wage_str, years_str = parts[2], parts[3], parts[4]
            try:
                offer_id_int = int(offer_id_str)
                wage = int(wage_str)
                years = int(years_str)
            except ValueError:
                return
            if not self.active_save_id or not self.overview:
                return
            current_date = str(self.overview.get("current_date", ""))
            with db_session(self.db_path) as conn:
                result = submit_player_negotiation(conn, self.active_save_id, offer_id_int, wage, years, current_date)
                conn.commit()
            self._reload_transfer_data()
            resp_date = str(result.get("player_response_date", ""))
            self.modal = {
                "type": "confirm",
                "title": "TERMS SUBMITTED",
                "message": f"Contract terms sent to player.\nYou will receive a response by {resp_date}.\n\nCheck Transfer Talks for updates.",
                "buttons": [{"label": "OK", "action": "modal:close"}],
            }
            return
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
            self.screen = "overview"
            self.overview_tab = "matches_standings"
            return
        if action == "back:world_competitions":
            if self.active_save_id:
                with db_session(self.db_path) as conn:
                    self.competitions_data = load_all_competitions(conn, self.active_save_id)
            self.screen = "world_competitions"
            return
        if action.startswith("goto:club:"):
            self._navigate_to_club(action[len("goto:club:"):])
            return
        if action.startswith("goto:player:"):
            self._navigate_to_player(action[len("goto:player:"):])
            return
        if action == "back":
            if self.detail_nav_stack:
                prev_screen, prev_tab = self.detail_nav_stack.pop()
            else:
                prev_screen, prev_tab = "overview", "matches_standings"
            self.screen = prev_screen
            self.overview_tab = prev_tab
            self.detail_player_data = None
            if prev_screen != "club_detail":
                self.detail_club_data = None
                self.detail_nav_stack.clear()
            return
        if action == "player_detail:toggle_attrs":
            self.detail_show_attrs = not self.detail_show_attrs
            return
        if action == "scout:request":
            player = self.detail_player_data or {}
            player_id = str(player.get("id", ""))
            player_name = str(player.get("name", "PLAYER")).upper()
            if not player_id or not self.active_save_id:
                return
            scout_quality = self.staff_data.get("scout", "")
            if not scout_quality:
                self.modal = {
                    "title": "NO SCOUT",
                    "message": "You have no scout on staff.\nHire a scout from the Club > Staff menu.",
                    "buttons": [{"label": "OK", "action": "modal:close"}],
                }
                return
            self.modal = {
                "title": "SEND SCOUT?",
                "message": f"Send your {scout_quality.upper()} scout\nto watch {player_name}?\nReport in {SCOUT_DAYS[scout_quality]} days.",
                "buttons": [
                    {"label": "YES, SEND SCOUT", "action": f"scout:confirm:{player_id}", "fill": (46, 160, 67)},
                    {"label": "CANCEL", "action": "modal:close"},
                ],
            }
            return
        if action.startswith("scout:confirm:"):
            player_id = action[len("scout:confirm:"):]
            if not self.active_save_id or not self.overview:
                return
            scout_quality = self.staff_data.get("scout", "")
            if not scout_quality or not player_id:
                return
            current_date = str(self.overview.get("current_date", ""))
            player = self.detail_player_data or {}
            player_name = str(player.get("name", "PLAYER"))
            from datetime import date as _date, timedelta as _td
            days = SCOUT_DAYS.get(scout_quality, 10)
            due_date = (_date.fromisoformat(current_date) + _td(days=days)).isoformat()
            pct_min, pct_max = SCOUT_PCT_RANGE.get(scout_quality, (15, 25))
            with db_session(self.db_path) as conn:
                # Enqueue scout task write; update UI immediately.
                self.db_worker.enqueue(
                    submit_scout_task,
                    int(self.active_save_id),
                    player_id,
                    player_name,
                    due_date,
                    scout_quality,
                    pct_min,
                    pct_max,
                )
            self.detail_scout_pending = True
            self.modal = {
                "title": "SCOUT DISPATCHED",
                "message": f"Scout sent to watch {player_name.upper()}.\nExpect a report in {days} days.",
                "buttons": [{"label": "OK", "action": "modal:close"}],
            }
            return
        if action.startswith("staff:hire:"):
            parts = action.split(":")
            if len(parts) < 4:
                return
            staff_type, quality = parts[2], parts[3]
            salary = STAFF_WEEKLY_SALARIES.get(staff_type, {}).get(quality, 0)
            self.modal = {
                "title": f"HIRE {quality.upper()} {staff_type.upper().replace('_', ' ')}?",
                "message": f"Weekly salary: £{salary:,}\nThis replaces any existing staff\nof this type.",
                "buttons": [
                    {"label": "HIRE", "action": f"staff:confirm:{staff_type}:{quality}", "fill": (46, 160, 67)},
                    {"label": "CANCEL", "action": "modal:close"},
                ],
            }
            return
        if action.startswith("staff:confirm:"):
            parts = action.split(":")
            if len(parts) < 4:
                return
            staff_type, quality = parts[2], parts[3]
            if not self.active_save_id:
                return
            # Update in-memory staff data for immediate UI feedback,
            # enqueue DB write to avoid blocking.
            if self.staff_data is None:
                self.staff_data = {}
            try:
                self.staff_data[staff_type] = quality
            except Exception:
                pass
            self.db_worker.enqueue(set_club_staff, int(self.active_save_id), str(staff_type), str(quality))
            self.modal = None
            return
        if action.startswith("scouting:player:"):
            player_id = action[len("scouting:player:"):]
            if not player_id or not self.overview:
                return
            clubs = (self.overview or {}).get("clubs", [])
            target_club = None
            target_player = None
            for c in clubs:
                club_id = str(c.get("id", ""))
                with db_session(self.db_path) as conn:
                    players = list_club_players(conn, club_id, save_id=self.active_save_id)
                p = next((pl for pl in players if str(pl.get("id", "")) == player_id), None)
                if p:
                    target_club = c
                    target_player = players
                    break
            if not target_club:
                return
            club_setup = (self.overview or {}).get("club_setups", {}).get(str(target_club.get("id", "")), {})
            self.detail_club_data = {
                **target_club,
                "players": target_player,
                "formation": str(club_setup.get("formation", "4-3-3")),
            }
            self.detail_nav_stack = [(self.screen, self.overview_tab)]
            self._navigate_to_player(player_id)
            return

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        if self.modal:
            if self._is_bound(event, "bind_menu", "escape"):
                self.modal = None
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                buttons = self.modal.get("buttons", [])
                if buttons:
                    self._handle_action(buttons[0].get("action"))
            return
        if self.screen == "match":
            if not self.match_engine:
                return
            if self._is_bound(event, "bind_menu", "escape"):
                if self.match_sub_mode:
                    self._reset_match_sub_state(restore_pause=True)
                    return
                if self.match_instruction_mode:
                    self._reset_match_instruction_state(restore_pause=True)
                    return
                self._open_escape_modal()
                return
            if self.match_engine.state.is_finished:
                if self._is_bound(event, "bind_start", "enter"):
                    self._finish_matchday()
                return
            if self.match_engine.state.awaiting_start and self._is_bound(event, "bind_start", "enter"):
                if self.match_engine.start_match_flow():
                    self.match_paused = False
                return
            if self.match_sub_mode:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._confirm_match_subs()
                return
            if self.match_instruction_mode:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._confirm_match_instruction_changes()
                return
            if self._is_bound(event, "bind_pause", "space"):
                if not self.match_engine.state.awaiting_start and not self.match_engine.state.is_finished:
                    self.match_paused = not self.match_paused
                return
            if self._is_bound(event, "bind_speed_x1", "1"):
                self.match_speed_label = "X1"
                self.match_engine.set_speed(SPEED_MULTIPLIERS[self.match_speed_label])
                return
            if self._is_bound(event, "bind_speed_x2", "2"):
                self.match_speed_label = "X2"
                self.match_engine.set_speed(SPEED_MULTIPLIERS[self.match_speed_label])
                return
            if self._is_bound(event, "bind_speed_x4", "4"):
                self.match_speed_label = "X4"
                self.match_engine.set_speed(SPEED_MULTIPLIERS[self.match_speed_label])
                return
            if self._is_bound(event, "bind_speed_x8", "8"):
                self.match_speed_label = "X8"
                self.match_engine.set_speed(SPEED_MULTIPLIERS[self.match_speed_label])
                return
        if self.screen == "match_report":
            if self._is_bound(event, "bind_menu", "escape"):
                self._handle_action("back:match_report")
            return
        if self.screen in ("club_detail", "player_detail"):
            if self._is_bound(event, "bind_menu", "escape"):
                self._handle_action("back")
            return
        if self.screen == "overview" and not self.modal and event.key == pygame.K_SPACE:
            if self.overview and self.overview.get("today_fixture"):
                self._handle_action("overview:play_next_match")
            elif self.overview:
                self._handle_action("overview:advance_day")
            return
        if self.screen != "new_game_name":
            if self.screen == "options" and self._is_bound(event, "bind_menu", "escape"):
                self._handle_action("back:menu")
                return
            if self._is_bound(event, "bind_menu", "escape") and self.screen != "menu":
                self._open_escape_modal()
            return
        if self._is_bound(event, "bind_menu", "escape"):
            self._open_escape_modal()
            return
        if event.key == pygame.K_BACKSPACE:
            self.manager_name = self.manager_name[:-1]
            return
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._handle_action("new_game:continue")
            return
        if event.unicode and event.unicode.isprintable() and len(self.manager_name) < 24:
            self.manager_name += event.unicode

    def _build_view(self) -> dict:
        footer_text = "New saves, leagues, fixtures, standings, and options are all DB-backed."
        if self.screen == "menu":
            count = len(self.saves)
            if count:
                footer_text = f"{count} save{'s' if count != 1 else ''} available in database."
            return {"screen": "menu", "footer_text": footer_text}
        if self.screen == "new_game_name":
            return {"screen": "new_game_name", "manager_name": self.manager_name, "error": self.error_message}
        if self.screen == "select_league":
            return {"screen": "select_league", "leagues": self.leagues}
        if self.screen == "select_club":
            return {"screen": "select_club", "clubs": self.club_choices}
        if self.screen == "options":
            return {"screen": "options", "options": self.options, "choices": self.option_choices}
        if self.screen == "load_game":
            return {"screen": "load_game", "saves": self.saves, "selected_save_id": self.selected_save_id}
        if self.screen == "match_report":
            return {
                "screen": "match_report",
                "report": self.fixture_report or {},
                "selected_player_id": self.fixture_report_selected_player_id,
            }
        if self.screen == "overview":
            overview = self.overview or {}
            club_id = overview.get("club_id", "")
            listed_ids: list[str] = [str(l.get("player_id", "")) for l in self.transfer_data.get("user_listings", [])]
            finance_transactions: list[dict] = []
            scouting_entries: list[dict] = []
            if self.active_save_id and self.overview_tab == "club_finances":
                with db_session(self.db_path) as conn:
                    finance_transactions = get_finance_transactions(conn, self.active_save_id)
            if self.active_save_id and self.overview_tab == "club_scouting":
                season_year = int(overview.get("season_year", 0))
                clubs_meta = overview.get("clubs", [])
                with db_session(self.db_path) as conn:
                    scouting_entries = get_all_scouting_data(conn, self.active_save_id, season_year)
                    # Build player→club lookup for enrichment
                    player_club_map: dict[str, dict] = {}
                    player_info_map: dict[str, dict] = {}
                    for c in clubs_meta:
                        cid = str(c.get("id", ""))
                        cplayers = list_club_players(conn, cid, save_id=self.active_save_id)
                        for p in cplayers:
                            pid = str(p.get("id", ""))
                            player_club_map[pid] = c
                            player_info_map[pid] = p
                for entry in scouting_entries:
                    pid = str(entry.get("player_id", ""))
                    p = player_info_map.get(pid)
                    c = player_club_map.get(pid)
                    if p:
                        entry["player_name"] = str(p.get("name", entry.get("player_name", pid)))
                        entry["ovr"] = int(p.get("ovr", 0))
                        entry["age"] = int(p.get("age", 0))
                        entry["pos"] = str(p.get("position", ""))
                        entry["player_data"] = p
                    if c:
                        entry["club_name"] = str(c.get("name", ""))
                        entry["club_badge"] = c.get("badge")
                        entry["club_primary"] = str(c.get("primary_color", "#2E3A6A"))
                        entry["club_secondary"] = str(c.get("secondary_color", "#F5F5F5"))
            return {
                "screen": "overview",
                "overview": overview,
                "selected_club_id": self.overview_club_id,
                "overview_tab": self.overview_tab,
                "fixtures_page": self.fixtures_page,
                "selected_gameweek": self.fixtures_page,
                "transfer_data": self.transfer_data,
                "transfer_listed_ids": listed_ids,
                "finance_transactions": finance_transactions,
                "scouting_entries": scouting_entries,
                "news_page": self.overview_news_page,
                "staff_data": self.staff_data,
                "squad_draft": {
                    "formation": self.squad_draft_formation,
                    "xi_ids": self.squad_draft_xi_ids,
                    "bench_ids": self.squad_draft_bench_ids,
                    "instructions": self.squad_draft_instructions,
                    "player_instructions": self.squad_draft_player_instructions,
                    "drag_player_id": self.squad_drag_player_id,
                    "drag_pos": self.squad_drag_pos,
                    "hover_target_id": self.squad_hover_target_id,
                    "hover_player_id": self.squad_hover_player_id,
                    "selected_player_id": self.squad_selected_player_id,
                    "show_reserves": self.squad_show_reserves,
                    "show_unavailable": self.squad_show_unavailable,
                    "pending_reserve_id": self.squad_pending_reserve_id,
                    "roles": self.squad_roles,
                    "roles_selected_role": self.squad_roles_selected_role,
                },
            }
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
        if self.screen == "club_detail":
            return {
                "screen": "club_detail",
                "club": self.detail_club_data or {},
                "players": (self.detail_club_data or {}).get("players", []),
                "standings": (self.overview or {}).get("standings", []),
                "fixtures": (self.overview or {}).get("fixtures", []),
                "clubs_meta": (self.overview or {}).get("clubs", []),
                "selected_player_id": self.detail_selected_player_id,
                "show_attrs": self.detail_show_attrs,
            }
        if self.screen == "player_detail":
            return {
                "screen": "player_detail",
                "player": self.detail_player_data or {},
                "club": self.detail_club_data or {},
                "show_attrs": self.detail_show_attrs,
                "is_user_club": self.detail_is_user_club,
                "scouting_pct": self.detail_scouting_pct,
                "scout_pending": self.detail_scout_pending,
                "has_scout": "scout" in self.staff_data,
                "staff_data": self.staff_data,
            }
        return {"screen": "menu", "footer_text": footer_text}

    def run(self) -> int:
        while self.running:
            dt = self.renderer.tick()
            # Flush debounced squad save if pending and delay elapsed
            try:
                import time

                if self._squad_save_pending and (time.time() - float(self._squad_save_last_time) >= float(self._squad_save_delay)):
                    payload = self._squad_save_payload or {}
                    # Enqueue actual DB write
                    self.db_worker.enqueue(
                        save_save_club_setup,
                        int(payload.get("active_save_id", self.active_save_id or 0)),
                        str(payload.get("club_id", "")),
                        str(payload.get("formation", "4-3-3")),
                        list(payload.get("xi_ids", [])),
                        list(payload.get("bench_ids", [])),
                        dict(payload.get("instructions", {})),
                        dict(payload.get("player_instructions", {})),
                    )
                    self._squad_save_pending = False
                    self._squad_save_payload = None
            except Exception:
                pass
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_keydown(event)
                elif event.type == pygame.MOUSEMOTION:
                    if self.screen == "match" and self.match_sub_mode and self.match_sub_drag_player_id:
                        self.match_sub_drag_pos = event.pos
                        hit = self.renderer.handle_sub_row_hit(event.pos)
                        if hit:
                            target_id = str(hit["player_id"])
                            dragging_from_xi = self.match_sub_drag_player_id in self.match_sub_draft_xi_ids
                            hovering_valid_target = (
                                target_id != self.match_sub_drag_player_id
                                and not bool(hit.get("unavailable"))
                                and (
                                    (dragging_from_xi and target_id in self.match_sub_draft_bench_ids)
                                    or (dragging_from_xi and target_id in self.match_sub_draft_xi_ids)
                                    or ((not dragging_from_xi) and target_id in self.match_sub_draft_xi_ids)
                                )
                            )
                            self.match_sub_hover_player_id = target_id if hovering_valid_target else None
                        else:
                            self.match_sub_hover_player_id = None
                    elif self.screen == "match" and self.match_instruction_mode == "player":
                        if self.match_instruction_slider_drag_player_id and self.match_instruction_slider_drag_key:
                            self._update_match_player_instruction_from_pos(event.pos)
                    elif self.screen == "overview" and self.overview_tab == "squad_formation":
                        if self.squad_slider_drag_player_id and self.squad_slider_drag_key:
                            self._update_player_instruction_from_pos(event.pos)
                        hit = self.renderer.handle_squad_hit(event.pos)
                        hover_player_id = str(hit["player_id"]) if hit else None
                        self.squad_hover_player_id = hover_player_id
                        if self.squad_slider_drag_player_id and self.squad_slider_drag_key:
                            self.squad_drag_player_id = None
                            self.squad_drag_pos = None
                            self.squad_hover_target_id = None
                        elif self.squad_drag_player_id:
                            self.squad_drag_pos = event.pos
                            self.squad_hover_target_id = hover_player_id if hover_player_id != self.squad_drag_player_id else None
                        elif self.squad_mouse_down_player_id and self.squad_mouse_down_pos:
                            dx = event.pos[0] - self.squad_mouse_down_pos[0]
                            dy = event.pos[1] - self.squad_mouse_down_pos[1]
                            if (dx * dx + dy * dy) >= 49:
                                self.squad_drag_player_id = self.squad_mouse_down_player_id
                                self.squad_drag_pos = event.pos
                                self.squad_hover_target_id = hover_player_id if hover_player_id != self.squad_drag_player_id else None
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.modal:
                        action = self.renderer.handle_ui_click(event.pos)
                        if action:
                            self._handle_action(action)
                        elif self.modal.get("type") == "news_detail":
                            self.modal = None
                        continue
                    if self.screen == "match" and self.match_engine:
                        if self.match_sub_mode:
                            action = self.renderer.handle_ui_click(event.pos)
                            if action:
                                self._handle_action(action)
                                continue
                            hit = self.renderer.handle_sub_row_hit(event.pos)
                            if hit and not bool(hit.get("unavailable")):
                                self.match_sub_drag_player_id = str(hit["player_id"])
                                self.match_sub_drag_pos = event.pos
                                self.match_sub_hover_player_id = None
                            continue
                        if self.match_instruction_mode:
                            action = self.renderer.handle_ui_click(event.pos)
                            if action:
                                self._handle_action(action)
                                continue
                            if self.match_instruction_mode == "player":
                                slider_hit = self.renderer.handle_match_slider_hit(event.pos)
                                if slider_hit:
                                    self.match_instruction_slider_drag_player_id = str(slider_hit["player_id"])
                                    self.match_instruction_slider_drag_key = str(slider_hit["key"])
                                    self.match_selected_player_id = self.match_instruction_slider_drag_player_id
                                    self._update_match_player_instruction_from_pos(event.pos)
                            continue
                        action = self.renderer.handle_ui_click(event.pos)
                        if action:
                            self._handle_action(action)
                            continue
                        action = self.renderer.handle_click(event.pos)
                        if action == "start":
                            if self.match_engine.state.is_finished:
                                self._finish_matchday()
                                continue
                            if self.match_engine.start_match_flow():
                                self.match_paused = False
                        elif action and action.startswith("speed:"):
                            self.match_speed_label = action.split(":", 1)[1]
                            self.match_engine.set_speed(SPEED_MULTIPLIERS[self.match_speed_label])
                    else:
                        action = self.renderer.handle_ui_click(event.pos)
                        self._handle_action(action)
                        if not action and self.screen == "overview" and self.overview_tab == "squad_formation":
                            slider_hit = self.renderer.handle_squad_slider_hit(event.pos)
                            if slider_hit:
                                self.squad_slider_drag_player_id = str(slider_hit["player_id"])
                                self.squad_slider_drag_key = str(slider_hit["key"])
                                self.squad_selected_player_id = self.squad_slider_drag_player_id
                                self._update_player_instruction_from_pos(event.pos)
                            else:
                                hit = self.renderer.handle_squad_hit(event.pos)
                                if not hit:
                                    continue
                                self.squad_selected_player_id = str(hit["player_id"])
                                self.squad_mouse_down_player_id = str(hit["player_id"])
                                self.squad_mouse_down_pos = event.pos
                                self.squad_hover_target_id = None
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if self.screen == "match" and self.match_sub_mode and self.match_sub_drag_player_id:
                        hit = self.renderer.handle_sub_row_hit(event.pos)
                        if hit and not bool(hit.get("unavailable")):
                            self._apply_sub_draft_swap(self.match_sub_drag_player_id, str(hit["player_id"]))
                        self.match_sub_drag_player_id = None
                        self.match_sub_drag_pos = None
                        self.match_sub_hover_player_id = None
                    elif self.screen == "match" and self.match_instruction_mode == "player":
                        if self.match_instruction_slider_drag_player_id and self.match_instruction_slider_drag_key:
                            self._update_match_player_instruction_from_pos(event.pos)
                        self.match_instruction_slider_drag_player_id = None
                        self.match_instruction_slider_drag_key = None
                    elif self.screen == "overview" and self.overview_tab == "squad_formation":
                        hit = self.renderer.handle_squad_hit(event.pos)
                        if self.squad_slider_drag_player_id and self.squad_slider_drag_key:
                            self._update_player_instruction_from_pos(event.pos)
                        elif self.squad_drag_player_id:
                            if hit:
                                self._apply_squad_swap(self.squad_drag_player_id, str(hit["player_id"]))
                        elif self.squad_mouse_down_player_id:
                            if hit and str(hit["player_id"]) == self.squad_mouse_down_player_id:
                                self.squad_selected_player_id = self.squad_mouse_down_player_id
                        self.squad_drag_player_id = None
                        self.squad_drag_pos = None
                        self.squad_mouse_down_player_id = None
                        self.squad_mouse_down_pos = None
                        self.squad_hover_target_id = None
                        self.squad_slider_drag_player_id = None
                        self.squad_slider_drag_key = None
            if self.screen == "match" and self.match_engine:
                if self.match_pending_instruction_update and not self.match_instruction_animation and not self.match_paused and self._match_has_natural_stoppage():
                    self._start_match_instruction_animation()
                if self.match_pending_substitutions and not self.match_sub_animation and not self.match_paused and self._match_has_natural_stoppage():
                    self._start_match_sub_animation()
                if self.match_pending_position_swaps and not self.match_instruction_animation and not self.match_sub_animation and not self.match_paused and self._match_has_natural_stoppage():
                    self._apply_pending_position_swaps()
                if self.match_sub_animation:
                    self._update_match_sub_animation(dt)
                if self.match_instruction_animation:
                    self._update_match_instruction_animation(dt)
                if not self.match_paused:
                    previous_ai_state = {
                        "home": {
                            "xi_ids": [player.profile.id for player in self.match_engine.home.xi],
                            "substitutions_used": self.match_engine.home.substitutions_used,
                        },
                        "away": {
                            "xi_ids": [player.profile.id for player in self.match_engine.away.xi],
                            "substitutions_used": self.match_engine.away.substitutions_used,
                        },
                    }
                    self.match_engine.update(dt)
                    self._detect_ai_sub_animation(previous_ai_state)
                if self.match_engine.state.is_finished and not self.match_condition_saved:
                    self._restore_match_live_instructions()
                    apply_post_match_condition(self.match_engine.state)
                    self.match_condition_saved = True
                fixture_label = f"{self.match_engine.state.home.name} vs {self.match_engine.state.away.name}"
                self.renderer.draw(
                    self.match_engine.state,
                    fixture_label,
                    self.match_paused,
                    alpha=self.match_engine.slice_progress(),
                    speed_label=self.match_speed_label,
                    clock_seconds=self.match_engine.display_clock_seconds(),
                    commentary_colors=self._managed_club_colors(),
                    selected_player_id=self.match_selected_player_id,
                    managed_side=self._managed_match_side(),
                    subs_mode=self.match_sub_mode,
                    draft_xi_ids=self.match_sub_draft_xi_ids if self.match_sub_mode else None,
                    draft_bench_ids=self.match_sub_draft_bench_ids if self.match_sub_mode else None,
                    drag_player_id=self.match_sub_drag_player_id,
                    drag_pos=self.match_sub_drag_pos,
                    hover_player_id=self.match_sub_hover_player_id,
                    sub_animation=self.match_sub_animation,
                    instruction_mode=self.match_instruction_mode,
                    live_formation=(self.match_instruction_formation_draft if self.match_instruction_mode else str(self._managed_match_team().formation) if self._managed_match_team() else "4-3-3"),
                    live_team_instructions=(dict(self.match_instruction_team_draft) if self.match_instruction_mode else normalize_team_instructions((self._managed_match_club().instructions if self._managed_match_club() else None))),
                    live_player_instructions=(dict(self.match_instruction_player_draft) if self.match_instruction_mode else dict(self._managed_match_club().player_instructions) if self._managed_match_club() else {}),
                    selected_player_id_for_instructions=self.match_selected_player_id,
                    instruction_animation=self.match_instruction_animation,
                    instructions_pending=bool(self.match_pending_instruction_update),
                    subs_pending=bool(self.match_pending_substitutions) or bool(self.match_pending_position_swaps),
                    present=not self.modal,
                )
                if self.modal:
                    self.renderer.draw_modal(self.modal)
                    pygame.display.flip()
                continue
            if self.screen == "match_report" and self.fixture_report:
                self.renderer.draw_match_report_view(
                    self.fixture_report,
                    self.fixture_report_selected_player_id,
                    present=not self.modal,
                )
                if self.modal:
                    self.renderer.draw_modal(self.modal)
                    pygame.display.flip()
                continue
            self.renderer.draw_app_view(self._build_view(), present=not self.modal)
            if self.modal:
                self.renderer.draw_modal(self.modal)
                pygame.display.flip()
        pygame.quit()
        # Ensure any queued DB writes are flushed before exit.
        try:
            self.db_worker.stop(wait=True)
        except Exception:
            pass
        return 0

    def _managed_club_colors(self) -> tuple[tuple[int, int, int], tuple[int, int, int]] | None:
        if not self.overview or not self.match_clubs:
            return None
        managed_club = self.match_clubs.get(self.overview["club_id"])
        if not managed_club:
            return None
        return (
            Renderer.hex_to_rgb_static(managed_club.colors.get("primary", "#F8BB20"), (248, 187, 32)),
            Renderer.hex_to_rgb_static(managed_club.colors.get("secondary", "#1C1C1C"), (28, 28, 28)),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Touchline Stories desktop prototype")
    parser.add_argument("clubs", nargs="*", help="Optional legacy match viewer club ids: HOME AWAY")
    parser.add_argument("--days", type=int, default=0, help="Advance squad recovery by this many days before kickoff")
    args = parser.parse_args()

    if len(args.clubs) == 2:
        home_id = args.clubs[0].strip().upper()
        away_id = args.clubs[1].strip().upper()
        if home_id == away_id:
            print("Home and away clubs must be different.")
            return 1
        return run_match_viewer(home_id, away_id, args.days)
    if args.clubs:
        print("Usage: python main.py HOME AWAY  or  python main.py")
        return 1
    app = ManagerGameApp(DB_FILE)
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
