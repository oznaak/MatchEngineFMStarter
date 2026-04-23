from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple

from .loader import FALLBACKS, FORMATION_433, formation_slots, pick_best_xi, position_fit_level
from .models import (
    BallState,
    Club,
    DEFAULT_PLAYER_INSTRUCTIONS,
    DEFAULT_TEAM_INSTRUCTIONS,
    MatchEvent,
    MatchState,
    PlayerProfile,
    PlayerState,
    TeamState,
    current_stamina_from_fatigue,
    default_player_match_stats,
    fatigue_from_current_stamina,
)

PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0
SLICE_SECONDS = 0.18
BASE_PLAYBACK_SPEED = 0.38
MATCH_MINUTES = 90
GOAL_CELEBRATION_SECONDS = 2.8
KICKOFF_SETUP_SECONDS = 1.8
GOAL_KICK_SETUP_SECONDS = 1.6
THROW_IN_SETUP_SECONDS = 1.1
CORNER_SETUP_SECONDS = 1.3
OFFSIDE_SETUP_SECONDS = 1.0
FREE_KICK_SETUP_SECONDS = 1.4
PENALTY_SETUP_SECONDS = 1.8
HALF_REAL_SECONDS = 150.0
MATCH_REAL_SECONDS = HALF_REAL_SECONDS * 2

HOME_FORMATION_XY = {
    "GK": (8, 34),
    "LB": (23, 12),
    "CB1": (20, 27),
    "CB2": (20, 41),
    "RB": (23, 56),
    "DM": (37, 34),
    "CM": (50, 24),
    "AM": (58, 34),
    "LW": (70, 12),
    "ST": (78, 34),
    "RW": (70, 56),
}

AWAY_FORMATION_XY = {
    "GK": (97, 34),
    "LB": (82, 56),
    "CB1": (85, 41),
    "CB2": (85, 27),
    "RB": (82, 12),
    "DM": (68, 34),
    "CM": (55, 44),
    "AM": (47, 34),
    "LW": (35, 56),
    "ST": (27, 34),
    "RW": (35, 12),
}

FORMATION_LAYOUTS = {
    "4-3-3": {
        "home": HOME_FORMATION_XY,
        "away": AWAY_FORMATION_XY,
    },
    "4-2-3-1": {
        "home": {
            "GK": (8, 34), "LB": (23, 12), "CB1": (20, 27), "CB2": (20, 41), "RB": (23, 56),
            "DM1": (36, 26), "DM2": (36, 42), "AM": (56, 34), "LW": (71, 13), "RW": (71, 55), "ST": (80, 34),
        },
        "away": {
            "GK": (97, 34), "LB": (82, 56), "CB1": (85, 41), "CB2": (85, 27), "RB": (82, 12),
            "DM1": (69, 42), "DM2": (69, 26), "AM": (49, 34), "LW": (34, 55), "RW": (34, 13), "ST": (25, 34),
        },
    },
    "4-4-2": {
        "home": {
            "GK": (8, 34), "LB": (23, 12), "CB1": (20, 27), "CB2": (20, 41), "RB": (23, 56),
            "CM1": (45, 26), "CM2": (45, 42), "LW": (56, 12), "RW": (56, 56), "ST1": (76, 27), "ST2": (76, 41),
        },
        "away": {
            "GK": (97, 34), "LB": (82, 56), "CB1": (85, 41), "CB2": (85, 27), "RB": (82, 12),
            "CM1": (60, 42), "CM2": (60, 26), "LW": (49, 56), "RW": (49, 12), "ST1": (29, 41), "ST2": (29, 27),
        },
    },
    "4-1-4-1": {
        "home": {
            "GK": (8, 34), "LB": (23, 12), "CB1": (20, 27), "CB2": (20, 41), "RB": (23, 56),
            "DM": (34, 34), "CM1": (49, 22), "CM2": (49, 46), "LW": (63, 12), "RW": (63, 56), "ST": (80, 34),
        },
        "away": {
            "GK": (97, 34), "LB": (82, 56), "CB1": (85, 41), "CB2": (85, 27), "RB": (82, 12),
            "DM": (71, 34), "CM1": (56, 46), "CM2": (56, 22), "LW": (42, 56), "RW": (42, 12), "ST": (25, 34),
        },
    },
}

PASS_SPEEDS = {
    "short_ground": 28.0,
    "progressive_ground": 33.0,
    "through_ball": 36.0,
    "switch": 40.0,
    "cross": 34.0,
}

ROLE_INTENTS: Dict[str, Dict[str, float]] = {
    "GK": {"width": 0.0, "forward": 0.0, "support": 0.0, "press": 0.0},
    "LB": {"width": -1.0, "forward": 0.4, "support": 0.55, "press": 0.4},
    "CB": {"width": 0.0, "forward": 0.1, "support": 0.2, "press": 0.2},
    "RB": {"width": 1.0, "forward": 0.4, "support": 0.55, "press": 0.4},
    "DM": {"width": 0.0, "forward": 0.25, "support": 0.8, "press": 0.65},
    "CM": {"width": -0.2, "forward": 0.55, "support": 0.7, "press": 0.7},
    "AM": {"width": 0.0, "forward": 0.8, "support": 0.8, "press": 0.8},
    "LW": {"width": -1.0, "forward": 0.9, "support": 0.65, "press": 0.65},
    "RW": {"width": 1.0, "forward": 0.9, "support": 0.65, "press": 0.65},
    "ST": {"width": 0.0, "forward": 1.0, "support": 0.5, "press": 0.8},
}


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.dist(a, b)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def weighted_choice(scores: Dict[str, float], rng: random.Random) -> str:
    keys = list(scores.keys())
    values = [max(0.01, s) for s in scores.values()]
    total = sum(values)
    roll = rng.uniform(0, total)
    running = 0.0
    for key, value in zip(keys, values):
        running += value
        if roll <= running:
            return key
    return keys[-1]


class MatchEngine:
    def __init__(
        self,
        home_club: Club,
        away_club: Club,
        seed: int = 42,
        human_controlled_sides: set[str] | None = None,
    ) -> None:
        self.rng = random.Random(seed)
        self.playback_multiplier = 1.0
        self.human_controlled_sides = set(human_controlled_sides or set())
        self.home_xi_profiles, self.home_bench = pick_best_xi(home_club, formation_name=home_club.formation)
        self.away_xi_profiles, self.away_bench = pick_best_xi(away_club, formation_name=away_club.formation)
        self.home = self._make_team_state(home_club, "home", self.home_xi_profiles, self.home_bench)
        self.away = self._make_team_state(away_club, "away", self.away_xi_profiles, self.away_bench)
        self.state = MatchState(
            home=self.home,
            away=self.away,
            ball=BallState(
                x=PITCH_LENGTH / 2,
                y=PITCH_WIDTH / 2,
                target_x=PITCH_LENGTH / 2,
                target_y=PITCH_WIDTH / 2,
            ),
            possession="home",
        )
        self.state.referee_strictness = self.rng.uniform(46.0, 54.0)
        self._time_accumulator = 0.0
        self._init_match_stats()
        self._kickoff()

    def set_speed(self, multiplier: float) -> None:
        self.playback_multiplier = max(0.25, multiplier)

    def slice_progress(self) -> float:
        return clamp(self._time_accumulator / SLICE_SECONDS, 0.0, 1.0)

    def _make_team_state(
        self,
        club: Club,
        side: str,
        xi_profiles: List[PlayerProfile],
        bench: List[PlayerProfile],
    ) -> TeamState:
        xi_states: List[PlayerState] = []
        formation_name = str(club.formation or "4-3-3")
        formation_slots_list = formation_slots(formation_name)
        slot_counts: Dict[str, int] = {}
        formation_counts: Dict[str, int] = {}
        for formation_slot in formation_slots_list:
            formation_counts[formation_slot] = formation_counts.get(formation_slot, 0) + 1
        layout = FORMATION_LAYOUTS.get(formation_name, FORMATION_LAYOUTS["4-3-3"])[side]

        for idx, profile in enumerate(xi_profiles):
            slot = formation_slots_list[idx]
            slot_counts[slot] = slot_counts.get(slot, 0) + 1
            named_slot = f"{slot}{slot_counts[slot]}" if formation_counts[slot] > 1 else slot
            coords = layout[named_slot]
            pace = profile.attributes["pace"]
            acceleration = profile.attributes.get("acceleration", pace)
            speed_rating = pace * 0.65 + acceleration * 0.35
            speed = 2.35 + ((speed_rating - 50.0) / 50.0) * 1.08
            facing_x = 1.0 if side == "home" else -1.0
            xi_states.append(
                PlayerState(
                    profile=profile,
                    side=side,
                    slot=slot,
                    x=coords[0],
                    y=coords[1],
                    home_x=coords[0],
                    home_y=coords[1],
                    target_x=coords[0],
                    target_y=coords[1],
                    speed=speed,
                    base_speed=speed,
                    fatigue=fatigue_from_current_stamina(profile.current_stamina),
                    facing_x=facing_x,
                )
            )
        avg = round(sum(p.profile.ovr for p in xi_states) / len(xi_states), 2)
        return TeamState(club=club, side=side, xi=xi_states, bench=bench, avg_ovr=avg, formation=formation_name)

    def _make_player_state_from_profile(
        self,
        profile: PlayerProfile,
        side: str,
        slot: str,
        x: float,
        y: float,
    ) -> PlayerState:
        pace = profile.attributes["pace"]
        acceleration = profile.attributes.get("acceleration", pace)
        speed_rating = pace * 0.65 + acceleration * 0.35
        speed = 2.35 + ((speed_rating - 50.0) / 50.0) * 1.08
        facing_x = 1.0 if side == "home" else -1.0
        return PlayerState(
            profile=profile,
            side=side,
            slot=slot,
            x=x,
            y=y,
            home_x=x,
            home_y=y,
            target_x=x,
            target_y=y,
            speed=speed,
            base_speed=speed,
            fatigue=fatigue_from_current_stamina(profile.current_stamina),
            facing_x=facing_x,
        )

    def _kickoff(self) -> None:
        self.state.phase = "pre_match"
        self.state.awaiting_start = True
        self._setup_pre_match_presentation()
        self.add_event(f"{self.home.name} vs {self.away.name}")
        self._derive_match_context()

    def _init_match_stats(self) -> None:
        for profile in self.home.club.players + self.away.club.players:
            self.state.player_match_stats[profile.id] = default_player_match_stats()

    def _team_match_stats(self, side: str) -> Dict[str, float]:
        return self.state.team_match_stats["home" if side == "home" else "away"]

    def _player_match_stats(self, player_or_id: PlayerState | str) -> Dict[str, float]:
        player_id = player_or_id.profile.id if isinstance(player_or_id, PlayerState) else player_or_id
        if player_id not in self.state.player_match_stats:
            self.state.player_match_stats[player_id] = default_player_match_stats()
        return self.state.player_match_stats[player_id]

    def _record_live_stats_slice(self, display_seconds_delta: float) -> None:
        self._team_match_stats(self.state.possession)["possession_seconds"] += SLICE_SECONDS
        minutes_delta = max(0.0, display_seconds_delta) / 60.0
        for player in self.home.xi + self.away.xi:
            if player.red_card:
                continue
            self._player_match_stats(player)["minutes"] += minutes_delta

    def _record_pass_attempt(self, passer: PlayerState) -> None:
        self._team_match_stats(passer.side)["passes_attempted"] += 1.0
        self._player_match_stats(passer)["passes_attempted"] += 1.0

    def _record_completed_pass(self, passer: Optional[PlayerState]) -> None:
        if not passer:
            return
        self._team_match_stats(passer.side)["passes_completed"] += 1.0
        stats = self._player_match_stats(passer)
        stats["passes_completed"] += 1.0
        if passer.slot == "GK" and self._last_pass_was_long_ball(passer):
            stats["long_balls_completed"] += 1.0

    def _record_shot(self, shooter: PlayerState, on_target: bool) -> None:
        team_stats = self._team_match_stats(shooter.side)
        player_stats = self._player_match_stats(shooter)
        if on_target:
            team_stats["shots_on_target"] += 1.0
            player_stats["shots_on_target"] += 1.0
        else:
            team_stats["shots_off_target"] += 1.0
            player_stats["shots_off_target"] += 1.0

    def _record_goal(self, scorer: PlayerState) -> None:
        self._player_match_stats(scorer)["goals"] += 1.0

    def _record_assist(self, assister: PlayerState) -> None:
        self._player_match_stats(assister)["assists"] += 1.0

    def _record_goalkeeper_goal_conceded(self, keeper: PlayerState) -> None:
        self._player_match_stats(keeper)["goalkeeper_goals_conceded"] += 1.0

    def _record_goalkeeper_save(self, keeper: PlayerState) -> None:
        self._player_match_stats(keeper)["goalkeeper_saves"] += 1.0

    def _record_goalkeeper_high_claim(self, keeper: PlayerState) -> None:
        self._player_match_stats(keeper)["goalkeeper_high_claims"] += 1.0

    def _record_ball_recovery(self, player: PlayerState) -> None:
        self._player_match_stats(player)["ball_recoveries"] += 1.0

    def _last_pass_was_long_ball(self, player: PlayerState) -> bool:
        ball = self.state.ball
        if ball.lead_player_id != player.profile.id:
            return False
        if ball.pass_type in ("switch", "cross"):
            return True
        return distance((ball.start_x, ball.start_y), (ball.target_x, ball.target_y)) >= 30.0

    def start_match_flow(self) -> bool:
        if not self.state.awaiting_start or self.state.is_finished:
            return False
        self.state.awaiting_start = False
        if self.state.phase == "pre_match":
            self.state.phase = "first_half"
            self.add_event(f"{self.home.name} kick off")
            self._start_kickoff_setup("home", opening=True, immediate=False)
            return True
        if self.state.phase == "halftime":
            self.state.phase = "second_half"
            self.add_event("Second half")
            self._start_kickoff_setup("away", immediate=False)
            return True
        return False

    def add_event(self, text: str) -> None:
        self.state.events.insert(0, MatchEvent(self.state.minute, self.state.second, text))
        self.state.events = self.state.events[:10]

    def find_player(self, player_id: Optional[str]) -> Optional[PlayerState]:
        if not player_id:
            return None
        for p in self.home.xi + self.away.xi:
            if p.profile.id == player_id:
                return p
        return None

    def can_make_substitution_window(self, side: str) -> bool:
        team = self._team_state(side)
        return team.substitutions_used < 5 and team.substitution_windows_used < 3 and not self.state.is_finished

    def _player_live_rating(self, player: PlayerState) -> float:
        stats = self._player_match_stats(player)
        rating = 6.5
        rating += stats.get("goals", 0.0) * 0.8
        rating += stats.get("assists", 0.0) * 0.5
        rating += stats.get("passes_completed", 0.0) * 0.008
        rating += stats.get("tackles", 0.0) * 0.06
        rating += stats.get("interceptions", 0.0) * 0.06
        rating += stats.get("goalkeeper_saves", 0.0) * 0.16
        rating -= stats.get("goalkeeper_goals_conceded", 0.0) * 0.28
        rating -= stats.get("yellow_cards", 0.0) * 0.18
        rating -= stats.get("red_cards", 0.0) * 1.0
        live_stamina = current_stamina_from_fatigue(player.fatigue)
        stamina_penalty = max(0.0, 45.0 - live_stamina) / 40.0
        return rating - stamina_penalty

    def _bench_sub_score(self, profile: PlayerProfile, slot: str, stamina_override: float | None = None) -> float:
        fit = position_fit_level(profile.position, slot)
        fit_bonus = 20.0 if fit == 2 else 10.0 if fit == 1 else -18.0
        stamina_bonus = (profile.current_stamina if stamina_override is None else stamina_override) * 0.12
        role_bonus = 0.0
        if slot == "GK" and profile.position == "GK":
            role_bonus += 12.0
        if slot in ("LW", "RW") and profile.attributes.get("pace", 50.0) >= 70.0:
            role_bonus += 4.0
        if slot in ("DM", "CM") and profile.attributes.get("passing", 50.0) >= 70.0:
            role_bonus += 4.0
        if slot in ("CB", "LB", "RB", "DM") and profile.attributes.get("tackling", 50.0) >= 70.0:
            role_bonus += 4.0
        return profile.ovr + fit_bonus + stamina_bonus + role_bonus

    def _corner_taker_score(self, player: PlayerState) -> float:
        attrs = player.profile.attributes
        return (
            attrs.get("corners", attrs.get("crossing", attrs["passing"])) * 0.34
            + attrs.get("crossing", attrs["passing"]) * 0.26
            + attrs.get("technique", attrs["passing"]) * 0.18
            + attrs["decisions"] * 0.12
            + attrs["composure"] * 0.10
        )

    def _free_kick_taker_score(self, player: PlayerState) -> float:
        attrs = player.profile.attributes
        return (
            attrs.get("free_kick_taking", attrs["passing"]) * 0.36
            + attrs.get("technique", attrs["passing"]) * 0.22
            + attrs.get("long_shots", attrs["finishing"]) * 0.12
            + attrs["decisions"] * 0.12
            + attrs["composure"] * 0.10
            + attrs["passing"] * 0.08
        )

    def _penalty_taker_score(self, player: PlayerState) -> float:
        attrs = player.profile.attributes
        return (
            attrs.get("penalty_taking", attrs["finishing"]) * 0.42
            + attrs["finishing"] * 0.22
            + attrs["composure"] * 0.18
            + attrs["decisions"] * 0.10
            + attrs.get("technique", attrs["finishing"]) * 0.08
        )

    def _keeper_save_score(self, keeper: PlayerState) -> float:
        attrs = keeper.profile.attributes
        return (
            attrs.get("reflexes", attrs["positioning"]) * 0.34
            + attrs.get("one_on_ones", attrs["positioning"]) * 0.20
            + attrs.get("handling", attrs["positioning"]) * 0.18
            + attrs["positioning"] * 0.12
            + attrs.get("agility", attrs.get("acceleration", attrs["pace"])) * 0.10
            + attrs.get("jumping_reach", attrs.get("strength", attrs["positioning"])) * 0.06
        )

    def _aerial_target_score(self, player: PlayerState) -> float:
        attrs = player.profile.attributes
        return (
            attrs.get("heading", attrs["positioning"]) * 0.28
            + attrs.get("jumping_reach", attrs.get("strength", attrs["positioning"])) * 0.24
            + attrs.get("strength", attrs["positioning"]) * 0.18
            + attrs["positioning"] * 0.12
            + attrs.get("off_ball", attrs["positioning"]) * 0.10
            + attrs.get("bravery", attrs["composure"]) * 0.08
        )

    def _ai_substitution_targets(self, side: str) -> tuple[int, int]:
        team = self._team_state(side)
        margin = (self.state.home_score - self.state.away_score) if side == "home" else (self.state.away_score - self.state.home_score)
        xi_stamina = [
            current_stamina_from_fatigue(player.fatigue)
            for player in team.xi
            if not player.red_card and player.slot != "GK"
        ]
        avg_stamina = sum(xi_stamina) / len(xi_stamina) if xi_stamina else 100.0

        desired_total = 0
        if self.state.phase == "halftime" or self.state.minute >= 62:
            desired_total = 1
        if self.state.minute >= 74:
            desired_total = 2
        if self.state.minute >= 84:
            desired_total = 3
        if self.state.minute >= 88 and (margin < 0 or avg_stamina < 62.0):
            desired_total = 4

        if margin <= -2:
            desired_total += 1
        elif margin >= 2 and self.state.minute >= 78:
            desired_total = max(desired_total, 3)

        if avg_stamina < 66.0:
            desired_total += 1
        desired_total = min(desired_total, 5)

        batch_size = 1
        if desired_total - team.substitutions_used >= 2 and self.state.minute >= 70:
            batch_size = 2
        if desired_total - team.substitutions_used >= 3 and self.state.minute >= 84:
            batch_size = 3
        return desired_total, batch_size

    def choose_ai_substitutions(self, side: str) -> List[Tuple[str, str]]:
        team = self._team_state(side)
        if side in self.human_controlled_sides or not self.can_make_substitution_window(side):
            return []
        if (self.state.minute < 55 and self.state.phase != "halftime") or team.last_ai_sub_minute >= self.state.minute - 10:
            return []

        desired_total, desired_batch = self._ai_substitution_targets(side)
        if team.substitutions_used >= desired_total and self.state.minute < 88:
            return []

        candidates: list[tuple[float, str, str]] = []
        reserve_candidates: list[tuple[float, str, str]] = []
        for player in team.xi:
            if player.slot == "GK":
                continue
            fit = position_fit_level(player.profile.position, player.slot)
            live_stamina = current_stamina_from_fatigue(player.fatigue)
            fatigue_score = max(0.0, 64.0 - live_stamina) * 0.26
            rating_penalty = max(0.0, 6.4 - self._player_live_rating(player)) * 7.0
            card_penalty = player.yellow_cards * 2.5
            fit_penalty = 4.0 if fit == 1 else 10.0 if fit == 0 else 0.0
            replace_score = fatigue_score + rating_penalty + card_penalty + fit_penalty
            management_need = max(0, desired_total - team.substitutions_used)
            if self.state.minute < 70 and replace_score < (2.0 if management_need > 0 else 3.5):
                continue
            best_bench = None
            best_gain = -999.0
            for bench_player in team.bench:
                if bench_player.id in team.subbed_out_ids:
                    continue
                bench_fit = position_fit_level(bench_player.position, player.slot)
                if bench_fit <= 0:
                    continue
                raw_gain = self._bench_sub_score(bench_player, player.slot) - self._bench_sub_score(
                    player.profile,
                    player.slot,
                    stamina_override=current_stamina_from_fatigue(player.fatigue),
                )
                freshness_gain = max(0.0, bench_player.current_stamina - live_stamina) * 0.34
                fit_gain = 3.0 if bench_fit > fit else 0.0
                late_urgency = max(0.0, 55.0 - live_stamina) * 0.08
                gain = raw_gain + freshness_gain + fit_gain + late_urgency
                if gain > best_gain:
                    best_gain = gain
                    best_bench = bench_player
            if best_bench is None:
                continue
            management_bonus = management_need * (2.2 if self.state.minute < 75 else 3.0)
            total_score = replace_score + best_gain + management_bonus
            threshold = 5.0 if self.state.minute < 75 else 2.5
            if management_need > 0:
                threshold -= 1.8 if self.state.minute < 75 else 1.2
            if self.state.minute >= 84 and team.substitutions_used < 2:
                threshold = min(threshold, 1.0)
            reserve_candidates.append((total_score, player.profile.id, best_bench.id))
            if total_score >= threshold:
                candidates.append((total_score, player.profile.id, best_bench.id))

        candidates.sort(reverse=True)
        reserve_candidates.sort(reverse=True)
        remaining = min(desired_batch if desired_total > team.substitutions_used else 1, 5 - team.substitutions_used)
        chosen: list[Tuple[str, str]] = []
        used_out: set[str] = set()
        used_in: set[str] = set()
        for _, outgoing_id, incoming_id in candidates:
            if outgoing_id in used_out or incoming_id in used_in:
                continue
            chosen.append((outgoing_id, incoming_id))
            used_out.add(outgoing_id)
            used_in.add(incoming_id)
            if len(chosen) >= remaining:
                break
        if self.state.minute >= 82 and team.substitutions_used + len(chosen) < 2:
            for score, outgoing_id, incoming_id in reserve_candidates:
                if outgoing_id in used_out or incoming_id in used_in:
                    continue
                chosen.append((outgoing_id, incoming_id))
                used_out.add(outgoing_id)
                used_in.add(incoming_id)
                if team.substitutions_used + len(chosen) >= 2 or len(chosen) >= remaining:
                    break
        return chosen

    def _maybe_apply_ai_substitutions(self) -> None:
        if self.state.is_finished:
            return
        for side in ("home", "away"):
            team = self._team_state(side)
            pairs = self.choose_ai_substitutions(side)
            if not pairs:
                continue
            applied = self.apply_substitution_window(side, pairs)
            if applied > 0:
                team.last_ai_sub_minute = self.state.minute

    def make_substitution(self, side: str, outgoing_id: str, incoming_id: str) -> bool:
        team = self._team_state(side)
        if team.substitutions_used >= 5 or self.state.is_finished:
            return False
        outgoing_index = next((idx for idx, player in enumerate(team.xi) if player.profile.id == outgoing_id), None)
        incoming_index = next((idx for idx, profile in enumerate(team.bench) if profile.id == incoming_id), None)
        if outgoing_index is None or incoming_index is None or incoming_id in team.subbed_out_ids:
            return False

        outgoing = team.xi[outgoing_index]
        incoming_profile = team.bench[incoming_index]
        outgoing.profile.current_stamina = current_stamina_from_fatigue(outgoing.fatigue)
        incoming = self._make_player_state_from_profile(
            incoming_profile,
            side,
            outgoing.slot,
            outgoing.x,
            outgoing.y,
        )
        incoming.prev_x = outgoing.prev_x
        incoming.prev_y = outgoing.prev_y
        incoming.target_x = outgoing.target_x
        incoming.target_y = outgoing.target_y
        incoming.render_state = outgoing.render_state
        incoming.run_intent = outgoing.run_intent
        incoming.run_commit_timer = outgoing.run_commit_timer
        incoming.commit_target_x = outgoing.commit_target_x
        incoming.commit_target_y = outgoing.commit_target_y
        incoming.control_cooldown = outgoing.control_cooldown
        incoming.vx = outgoing.vx
        incoming.vy = outgoing.vy
        incoming.facing_x = outgoing.facing_x
        incoming.facing_y = outgoing.facing_y
        incoming.action_time = outgoing.action_time
        incoming.state = outgoing.state

        if outgoing.has_ball or self.state.ball.carrier_id == outgoing.profile.id:
            outgoing.has_ball = False
            incoming.has_ball = True
            self.state.ball.carrier_id = incoming.profile.id
            self.state.ball.x = incoming.x
            self.state.ball.y = incoming.y
            self.state.ball.target_x = incoming.x
            self.state.ball.target_y = incoming.y
        if self.state.ball.target_player_id == outgoing.profile.id:
            self.state.ball.target_player_id = incoming.profile.id
        if self.state.ball.lead_player_id == outgoing.profile.id:
            self.state.ball.lead_player_id = incoming.profile.id
        if self.state.last_touch_player_id == outgoing.profile.id:
            self.state.last_touch_player_id = incoming.profile.id
        if self.state.assist_candidate_id == outgoing.profile.id:
            self.state.assist_candidate_id = None
        if self.state.restart_taker_id == outgoing.profile.id:
            self.state.restart_taker_id = incoming.profile.id
        if self.state.fouled_player_id == outgoing.profile.id:
            self.state.fouled_player_id = incoming.profile.id

        team.xi[outgoing_index] = incoming
        team.bench[incoming_index] = outgoing.profile
        team.avg_ovr = round(sum(player.profile.ovr for player in team.xi) / len(team.xi), 2)
        team.subbed_out_ids.add(outgoing.profile.id)
        team.substitutions_used += 1
        self.add_event(f"Substitution: {incoming.short_name} for {outgoing.short_name}")
        return True

    def apply_substitution_window(self, side: str, substitutions: List[Tuple[str, str]]) -> int:
        team = self._team_state(side)
        if not substitutions or not self.can_make_substitution_window(side):
            return 0
        remaining = 5 - team.substitutions_used
        approved = substitutions[: max(0, remaining)]
        completed = 0
        for outgoing_id, incoming_id in approved:
            if self.make_substitution(side, outgoing_id, incoming_id):
                completed += 1
        if completed > 0:
            team.substitution_windows_used += 1
        return completed

    def teammates(self, side: str) -> List[PlayerState]:
        team = self.home.xi if side == "home" else self.away.xi
        return [p for p in team if not p.red_card]

    def opponents(self, side: str) -> List[PlayerState]:
        team = self.away.xi if side == "home" else self.home.xi
        return [p for p in team if not p.red_card]

    def update(self, dt: float) -> None:
        if self.state.is_finished or self.state.awaiting_start:
            return
        self._time_accumulator += dt * BASE_PLAYBACK_SPEED * self.playback_multiplier
        while self._time_accumulator >= SLICE_SECONDS:
            self._time_accumulator -= SLICE_SECONDS
            self._step()

    def _snapshot_positions(self) -> None:
        for p in self.home.xi + self.away.xi:
            p.prev_x = p.x
            p.prev_y = p.y
        self.state.ball.prev_x = self.state.ball.x
        self.state.ball.prev_y = self.state.ball.y

    def _step(self) -> None:
        self._snapshot_positions()
        self.state.recent_turnover_seconds = max(0.0, self.state.recent_turnover_seconds - SLICE_SECONDS)
        was_first_half = self.state.real_elapsed_seconds < HALF_REAL_SECONDS

        if self.state.restart_mode == "kickoff_setup":
            self._update_restart_sequence()
            return

        previous_display_seconds = self.state.elapsed_seconds
        self.state.real_elapsed_seconds += SLICE_SECONDS
        self._update_match_clock()
        self._record_live_stats_slice(self.state.elapsed_seconds - previous_display_seconds)
        if self.state.minute >= 82 and (self.home.substitutions_used < 2 or self.away.substitutions_used < 2):
            self._maybe_apply_ai_substitutions()
        if self.state.celebration_timer > 0 or self.state.restart_timer > 0:
            self._maybe_apply_ai_substitutions()

        if was_first_half and self.state.real_elapsed_seconds >= HALF_REAL_SECONDS:
            self._start_halftime_break()
            return

        if self.state.real_elapsed_seconds >= MATCH_REAL_SECONDS:
            self.state.is_finished = True
            self.state.phase = "full_time"
            self.state.elapsed_seconds = 90 * 60
            self.state.minute = 90
            self.state.second = 0
            self.add_event("Full time")
            return

        if self.state.celebration_timer > 0:
            self._update_goal_celebration()
            return
        if self.state.restart_timer > 0:
            self._update_restart_sequence()
            return

        self._derive_match_context()
        self._update_off_ball_targets()
        self._move_players()
        self._update_ball_motion()
        self._update_render_states()

        carrier = self.find_player(self.state.ball.carrier_id) if self.state.ball.mode == "carried" else None
        if carrier is None:
            return

        if carrier.control_cooldown > 0:
            carrier.control_cooldown = max(0.0, carrier.control_cooldown - SLICE_SECONDS)
            self._carry_ball_forward(carrier)
            return

        action = self._choose_action(carrier)
        self._resolve_action(carrier, action)

    def _update_match_clock(self) -> None:
        if self.state.real_elapsed_seconds < HALF_REAL_SECONDS:
            display_seconds = (self.state.real_elapsed_seconds / HALF_REAL_SECONDS) * (45 * 60)
            self.state.phase = "first_half"
        else:
            second_half_real = self.state.real_elapsed_seconds - HALF_REAL_SECONDS
            display_seconds = (45 * 60) + (second_half_real / HALF_REAL_SECONDS) * (45 * 60)
            self.state.phase = "second_half"
        display_seconds = clamp(display_seconds, 0.0, 90 * 60)
        self.state.elapsed_seconds = display_seconds
        self.state.minute = min(90, int(display_seconds // 60))
        self.state.second = int(display_seconds % 60)

    def display_clock_seconds(self) -> float:
        if self.state.restart_mode == "kickoff_setup" or self.state.awaiting_start:
            return self.state.elapsed_seconds
        extra_real = self._time_accumulator
        if self.state.real_elapsed_seconds < HALF_REAL_SECONDS:
            display_rate = (45 * 60) / HALF_REAL_SECONDS
            return clamp(self.state.elapsed_seconds + extra_real * display_rate, 0.0, 45 * 60)
        display_rate = (45 * 60) / HALF_REAL_SECONDS
        return clamp(self.state.elapsed_seconds + extra_real * display_rate, 45 * 60, 90 * 60)

    def _start_halftime_break(self) -> None:
        self.state.elapsed_seconds = 45 * 60
        self.state.minute = 45
        self.state.second = 0
        self.state.phase = "halftime"
        self.state.awaiting_start = True
        for player in self.home.xi + self.away.xi:
            player.fatigue = max(0.0, player.fatigue - 0.7)
        self._maybe_apply_ai_substitutions()
        self.add_event("Half time")
        self._switch_team_sides()
        self._prepare_kickoff_positions("away")

    def _derive_match_context(self) -> None:
        ball = self.state.ball
        forward_ball_x = self._forwardness(self.state.possession, ball.x)
        x_zone = "defensive" if forward_ball_x < PITCH_LENGTH / 3 else "middle" if forward_ball_x < (PITCH_LENGTH * 2 / 3) else "attacking"
        if ball.y < PITCH_WIDTH * 0.22 or ball.y > PITCH_WIDTH * 0.78:
            y_zone = "wide"
        elif ball.y < PITCH_WIDTH * 0.38 or ball.y > PITCH_WIDTH * 0.62:
            y_zone = "halfspace"
        else:
            y_zone = "central"
        self.state.ball_zone = f"{x_zone}_{y_zone}"

        if self.state.recent_turnover_seconds > 0:
            self.state.phase_in_possession = "transition"
            self.state.phase_out_of_possession = "recovery"
            return

        if x_zone == "defensive":
            self.state.phase_in_possession = "build_up"
            self.state.phase_out_of_possession = "high_press"
        elif x_zone == "middle":
            self.state.phase_in_possession = "progression"
            self.state.phase_out_of_possession = "mid_block"
        else:
            self.state.phase_in_possession = "final_third"
            self.state.phase_out_of_possession = "mid_block"

    def _side_forward_sign(self, side: str) -> float:
        if self.state.phase in ("second_half", "halftime"):
            return -1.0 if side == "home" else 1.0
        return 1.0 if side == "home" else -1.0

    def _attacking_goal_x(self, side: str) -> float:
        return PITCH_LENGTH if self._side_forward_sign(side) > 0 else 0.0

    def _defending_goal_x(self, side: str) -> float:
        return 0.0 if self._side_forward_sign(side) > 0 else PITCH_LENGTH

    def _goal_line_defending_side(self, x: float) -> str:
        if x <= 0.0:
            return "home" if self._defending_goal_x("home") == 0.0 else "away"
        return "home" if self._defending_goal_x("home") == PITCH_LENGTH else "away"

    def _team_state(self, side: str) -> TeamState:
        return self.home if side == "home" else self.away

    def _instruction_value(self, side: str, key: str) -> str:
        if key not in DEFAULT_TEAM_INSTRUCTIONS:
            return ""
        return str(self._team_state(side).club.instructions.get(key, DEFAULT_TEAM_INSTRUCTIONS[key]))

    def _player_instruction_value(self, player: PlayerState, key: str) -> int:
        values = self._team_state(player.side).club.player_instructions.get(player.profile.id, {})
        try:
            return max(0, min(100, int(values.get(key, DEFAULT_PLAYER_INSTRUCTIONS[key]))))
        except (TypeError, ValueError):
            return DEFAULT_PLAYER_INSTRUCTIONS[key]

    def _player_pressure_bias(self, player: PlayerState) -> float:
        return (self._player_instruction_value(player, "pressure") - 50.0) / 50.0

    def _player_mindset_bias(self, player: PlayerState) -> float:
        return (self._player_instruction_value(player, "mindset") - 50.0) / 50.0

    def _instruction_tactic_delta(self, side: str, key: str) -> float:
        if key == "directness":
            return {
                "shorter": -18.0,
                "long_balls": 22.0,
                "possession": -6.0,
                "quick_play": 10.0,
            }.get(self._instruction_value(side, "passing"), 0.0) + {
                "possession": -8.0,
                "quick_play": 8.0,
            }.get(self._instruction_value(side, "gameplan"), 0.0)
        if key == "width":
            return {
                "narrow": -22.0,
                "wide": 22.0,
            }.get(self._instruction_value(side, "width"), 0.0)
        if key == "tempo":
            return {
                "lower": -20.0,
                "higher": 20.0,
            }.get(self._instruction_value(side, "tempo"), 0.0)
        if key == "counter":
            return {
                "possession": -14.0,
                "quick_play": 18.0,
            }.get(self._instruction_value(side, "gameplan"), 0.0)
        if key == "crossing":
            return {
                "possession": -16.0,
                "direct": 16.0,
            }.get(self._instruction_value(side, "set_pieces"), 0.0)
        if key == "pressing":
            return {
                "park_the_bus": -14.0,
                "defending": -6.0,
                "attacking": 6.0,
                "all_out_attack": 14.0,
            }.get(self._instruction_value(side, "playstyle"), 0.0)
        return 0.0

    def _tactic_value(self, side: str, key: str, default: float = 50.0) -> float:
        base = float(self._team_state(side).club.tactics.get(key, default))
        return clamp(base + self._instruction_tactic_delta(side, key), 0.0, 100.0)

    def _playstyle_attack_modifier(self, side: str) -> float:
        return {
            "park_the_bus": -0.18,
            "defending": -0.08,
            "balanced": 0.0,
            "attacking": 0.08,
            "all_out_attack": 0.18,
        }.get(self._instruction_value(side, "playstyle"), 0.0)

    def _playstyle_defence_modifier(self, side: str) -> float:
        return {
            "park_the_bus": 0.18,
            "defending": 0.08,
            "balanced": 0.0,
            "attacking": -0.08,
            "all_out_attack": -0.18,
        }.get(self._instruction_value(side, "playstyle"), 0.0)

    def _is_time_wasting(self, side: str) -> bool:
        margin = (self.state.home_score - self.state.away_score) if side == "home" else (self.state.away_score - self.state.home_score)
        mode = self._instruction_value(side, "time_management")
        if mode == "ball_out":
            return False
        if mode == "often":
            return margin >= 2
        return margin >= 4

    def _set_render_state(self, player: PlayerState, state: str, intent: Optional[str] = None) -> None:
        player.render_state = state
        player.run_intent = intent

    def _clear_run_commitment(self, player: PlayerState) -> None:
        player.run_commit_timer = 0.0
        player.commit_target_x = None
        player.commit_target_y = None

    def _start_run_commitment(
        self,
        player: PlayerState,
        tx: float,
        ty: float,
        state: str,
        intent: Optional[str],
        duration: float,
    ) -> None:
        player.run_commit_timer = duration
        player.commit_target_x = tx
        player.commit_target_y = ty
        player.target_x = tx
        player.target_y = ty
        self._set_render_state(player, state, intent)

    def _run_commit_duration(self, player: PlayerState, state: str, intent: Optional[str]) -> float:
        off_ball = player.profile.attributes.get("off_ball", player.profile.attributes["positioning"])
        acceleration = player.profile.attributes.get("acceleration", player.profile.attributes["pace"])
        base = {
            "run": 1.10,
            "recover": 0.95,
            "receiving": 0.85,
        }.get(state, 0.0)
        if base <= 0.0:
            return 0.0
        if intent in ("cross", "through_ball", "kickoff_recover"):
            base += 0.18
        if player.slot in ("LW", "RW", "ST"):
            base += 0.14
        elif player.slot in ("CM", "AM"):
            base += 0.08
        base += max(0.0, off_ball - 70.0) / 90.0
        base += max(0.0, acceleration - 70.0) / 180.0
        return clamp(base, 0.72, 1.75)

    def _maybe_apply_run_commitment(
        self,
        player: PlayerState,
        tx: float,
        ty: float,
        state: str,
        intent: Optional[str],
    ) -> Tuple[float, float, str, Optional[str]]:
        if player.profile.id == self.state.ball.target_player_id and state != "receiving":
            self._clear_run_commitment(player)
            return tx, ty, state, intent

        if player.run_commit_timer > 0 and player.commit_target_x is not None and player.commit_target_y is not None:
            if state in ("run", "recover", "receiving") and distance((player.x, player.y), (self.state.ball.x, self.state.ball.y)) > 7.0:
                held_x = lerp(player.commit_target_x, tx, 0.10)
                held_y = lerp(player.commit_target_y, ty, 0.10)
                player.commit_target_x = held_x
                player.commit_target_y = held_y
                held_state = player.render_state if player.render_state in ("run", "recover", "receiving") else state
                held_intent = player.run_intent or intent
                return held_x, held_y, held_state, held_intent
            self._clear_run_commitment(player)

        duration = self._run_commit_duration(player, state, intent)
        if duration > 0.0 and distance((player.x, player.y), (tx, ty)) > 3.0:
            self._start_run_commitment(player, tx, ty, state, intent, duration)
            return tx, ty, state, intent

        self._clear_run_commitment(player)
        return tx, ty, state, intent

    def _role_target(self, player: PlayerState, phase: str, ball_zone: str) -> Tuple[float, float]:
        ball_x, ball_y = self.state.ball.x, self.state.ball.y
        sign = self._side_forward_sign(player.side)
        intent = ROLE_INTENTS[player.slot]
        x_target = player.home_x
        y_target = player.home_y
        width_tactic = (self._tactic_value(player.side, "width") - 50.0) / 50.0
        width_shift = intent["width"] * (4.0 + width_tactic * 2.0)
        defensive_line_push = (self._tactic_value(player.side, "defensive_line") - 50.0) / 50.0

        if player.slot == "GK":
            y_target = clamp(lerp(player.home_y, ball_y, 0.08), 24, 44)
            x_target = clamp(player.home_x + sign * (2.0 if phase == "build_up" else 0.0), 5, PITCH_LENGTH - 5)
            return x_target, y_target

        if phase == "build_up":
            if player.slot in ("CB", "LB", "RB"):
                line_push = (1.5 if player.slot == "CB" else 2.5) + defensive_line_push * 1.2
                x_target = player.home_x + sign * line_push
                y_target = clamp(player.home_y + (ball_y - player.home_y) * 0.20 + width_shift, 4, PITCH_WIDTH - 4)
            elif player.slot == "DM":
                x_target = ball_x - sign * 7.0
                y_target = clamp(lerp(player.home_y, ball_y, 0.25), 8, PITCH_WIDTH - 8)
            elif player.slot == "CM":
                x_target = ball_x + sign * 2.5
                side_offset = -7.5 if player.home_y < PITCH_WIDTH / 2 else 7.5
                y_target = clamp(ball_y + side_offset, 6, PITCH_WIDTH - 6)
            elif player.slot == "AM":
                x_target = ball_x + sign * 6.5
                y_target = clamp(lerp(player.home_y, ball_y, 0.22), 8, PITCH_WIDTH - 8)
            elif player.slot in ("LW", "RW"):
                same_side = (player.slot == "LW" and ball_y < PITCH_WIDTH / 2) or (player.slot == "RW" and ball_y >= PITCH_WIDTH / 2)
                x_target = player.home_x + sign * (3.5 if same_side else 1.0)
                y_target = clamp(player.home_y + (ball_y - player.home_y) * (0.12 if same_side else 0.04), 3, PITCH_WIDTH - 3)
            elif player.slot == "ST":
                x_target = player.home_x + sign * 2.0
                y_target = clamp(lerp(player.home_y, ball_y, 0.10), 10, PITCH_WIDTH - 10)
        elif phase == "progression":
            if player.slot in ("CB", "LB", "RB"):
                overlap = (4.0 if player.slot in ("LB", "RB") else 2.5) + defensive_line_push * 1.8
                x_target = player.home_x + sign * overlap
                y_target = clamp(player.home_y + (ball_y - player.home_y) * 0.25 + width_shift, 4, PITCH_WIDTH - 4)
            elif player.slot == "DM":
                x_target = ball_x - sign * 8.0
                y_target = clamp(lerp(player.home_y, ball_y, 0.35), 7, PITCH_WIDTH - 7)
            elif player.slot == "CM":
                x_target = ball_x + sign * 3.8
                side_offset = -8.0 if player.home_y < PITCH_WIDTH / 2 else 8.0
                y_target = clamp(ball_y + side_offset, 6, PITCH_WIDTH - 6)
            elif player.slot == "AM":
                x_target = ball_x + sign * 7.2
                y_target = clamp(lerp(player.home_y, ball_y, 0.24), 7, PITCH_WIDTH - 7)
            elif player.slot in ("LW", "RW"):
                ball_on_side = (player.slot == "LW" and ball_y < PITCH_WIDTH * 0.55) or (player.slot == "RW" and ball_y > PITCH_WIDTH * 0.45)
                diag_push = 8.0 if ball_on_side else 4.2
                x_target = player.home_x + sign * diag_push
                offset = -5.0 if player.slot == "LW" else 5.0
                y_target = clamp(player.home_y + (ball_y - player.home_y) * (0.24 if ball_on_side else 0.08) + offset * 0.10, 3, PITCH_WIDTH - 3)
            elif player.slot == "ST":
                x_target = player.home_x + sign * 5.5
                y_target = clamp(lerp(player.home_y, ball_y, 0.18), 9, PITCH_WIDTH - 9)
        else:
            if player.slot in ("CB", "LB", "RB"):
                base_push = (8.0 if player.slot == "CB" else 13.0) + defensive_line_push * 3.0
                x_target = max(player.home_x + sign * base_push, ball_x - sign * 26.0) if sign > 0 else min(player.home_x + sign * base_push, ball_x - sign * 26.0)
                y_target = clamp(player.home_y + (ball_y - player.home_y) * 0.28 + width_shift, 4, PITCH_WIDTH - 4)
            elif player.slot == "DM":
                x_target = ball_x - sign * 10.0
                y_target = clamp(lerp(player.home_y, ball_y, 0.42), 6, PITCH_WIDTH - 6)
            elif player.slot == "CM":
                x_target = ball_x + sign * 4.0
                y_target = clamp(ball_y - 7.0, 6, PITCH_WIDTH - 6)
            elif player.slot == "AM":
                x_target = ball_x + sign * 7.0
                y_target = clamp(ball_y + 5.0, 6, PITCH_WIDTH - 6)
            elif player.slot in ("LW", "RW"):
                x_target = player.home_x + sign * 10.0
                inside = -7.0 if player.slot == "LW" else 7.0
                y_target = clamp(player.home_y + inside * 0.22 + (ball_y - player.home_y) * 0.24, 3, PITCH_WIDTH - 3)
            elif player.slot == "ST":
                x_target = player.home_x + sign * 12.0
                y_target = clamp(lerp(player.home_y, ball_y, 0.30), 8, PITCH_WIDTH - 8)

        return clamp(x_target, 2, PITCH_LENGTH - 2), clamp(y_target, 2, PITCH_WIDTH - 2)

    def _defensive_shape_target(self, player: PlayerState) -> Tuple[float, float]:
        ball_x, ball_y = self.state.ball.x, self.state.ball.y
        sign = self._side_forward_sign(player.side)
        pressure_bias = self._player_pressure_bias(player)
        mindset_bias = self._player_mindset_bias(player)
        if player.slot == "GK":
            defend_goal_x = self._defending_goal_x(player.side)
            base_x = 8.0 if defend_goal_x == 0.0 else PITCH_LENGTH - 8.0
            aggressive_step = clamp((distance((ball_x, ball_y), (defend_goal_x, PITCH_WIDTH / 2)) - 10.0) / 26.0, 0.0, 1.0)
            x_target = lerp(base_x, defend_goal_x + sign * 4.0, 1.0 - aggressive_step)
            y_target = clamp(lerp(player.home_y, ball_y, 0.10), 24, 44)
            return clamp(x_target, 4, PITCH_LENGTH - 4), y_target
        if self.state.phase_out_of_possession == "recovery":
            retreat = -sign * 3.5
            pull = 0.12
        elif self.state.phase_out_of_possession == "high_press":
            retreat = sign * 1.5
            pull = 0.24
        else:
            retreat = -sign * 1.0
            pull = 0.18

        x_target = player.home_x + retreat
        y_target = lerp(player.home_y, ball_y, pull)
        x_target += sign * pressure_bias * 1.6
        x_target += sign * (-mindset_bias) * 1.8

        if player.slot == "DM":
            x_target = ball_x - sign * 10.0
            y_target = lerp(player.home_y, ball_y, 0.22)
        elif player.slot == "ST":
            x_target = player.home_x - sign * 4.0
            y_target = lerp(player.home_y, ball_y, 0.12)

        return clamp(x_target, 2, PITCH_LENGTH - 2), clamp(y_target, 4, PITCH_WIDTH - 4)

    def _setup_pre_match_presentation(self) -> None:
        self._reset_players_for_restart()
        self.state.restart_mode = None
        self.state.restart_timer = 0.0
        self.state.restart_side = None
        self.state.ball.mode = "loose"
        self.state.ball.carrier_id = None
        self.state.ball.target_player_id = None
        self.state.ball.x = PITCH_LENGTH / 2
        self.state.ball.y = PITCH_WIDTH / 2
        self.state.ball.prev_x = self.state.ball.x
        self.state.ball.prev_y = self.state.ball.y
        self.state.ball.target_x = self.state.ball.x
        self.state.ball.target_y = self.state.ball.y

        for side in ("home", "away"):
            team = self.teammates(side)
            team.sort(key=lambda p: p.home_y)
            start_x = 10.5 if side == "home" else PITCH_LENGTH - 10.5
            end_x = (PITCH_LENGTH / 2) - 4.5 if side == "home" else (PITCH_LENGTH / 2) + 4.5
            line_y = 11.5
            if len(team) == 1:
                xs = [(start_x + end_x) / 2.0]
            else:
                xs = [lerp(start_x, end_x, idx / (len(team) - 1)) for idx in range(len(team))]
            for idx, (player, x) in enumerate(zip(team, xs)):
                player.x = x
                player.y = line_y + (2.8 if idx % 2 else 0.0)
                player.prev_x = x
                player.prev_y = player.y
                player.target_x = x
                player.target_y = player.y
                player.facing_x = 0.0
                player.facing_y = 1.0
                self._set_render_state(player, "shape", "lineup")

    def _switch_team_sides(self) -> None:
        for player in self.home.xi + self.away.xi:
            player.home_x = PITCH_LENGTH - player.home_x
            player.x = PITCH_LENGTH - player.x
            player.prev_x = PITCH_LENGTH - player.prev_x
            player.target_x = PITCH_LENGTH - player.target_x
            if player.commit_target_x is not None:
                player.commit_target_x = PITCH_LENGTH - player.commit_target_x
            player.facing_x *= -1.0

    def _prepare_kickoff_positions(self, kickoff_side: str, opening: bool = False) -> None:
        self._reset_players_for_restart()
        self.state.restart_mode = None
        self.state.restart_timer = 0.0
        self.state.restart_side = kickoff_side
        self.state.ball.mode = "loose"
        self.state.ball.carrier_id = None
        self.state.ball.target_player_id = None
        self.state.ball.x = PITCH_LENGTH / 2
        self.state.ball.y = PITCH_WIDTH / 2
        self.state.ball.prev_x = self.state.ball.x
        self.state.ball.prev_y = self.state.ball.y
        self.state.ball.target_x = self.state.ball.x
        self.state.ball.target_y = self.state.ball.y
        desired = self._kickoff_layout(kickoff_side)
        for player in self.home.xi + self.away.xi:
            x, y = desired[player.profile.id]
            player.x = x
            player.y = y
            player.prev_x = x
            player.prev_y = y
            player.target_x = x
            player.target_y = y
            self._set_render_state(player, "shape", "kickoff")

    def _update_off_ball_targets(self) -> None:
        ball_x, ball_y = self.state.ball.x, self.state.ball.y
        reacting: List[PlayerState] = []
        reacting_ids: set[str] = set()
        if self.state.ball.mode == "loose":
            by_side = {"home": [], "away": []}
            for player in self.home.xi + self.away.xi:
                if player.red_card:
                    continue
                by_side[player.side].append(player)
            for side in by_side:
                chasers = [
                    p for p in sorted(by_side[side], key=lambda p: distance((p.x, p.y), (ball_x, ball_y)))
                    if p.slot != "GK" or distance((ball_x, ball_y), (self._defending_goal_x(side), PITCH_WIDTH / 2)) < 10.0
                ]
                reacting.extend(chasers[:2])
                reacting_ids.update(p.profile.id for p in chasers[:2])
        if self.state.recent_turnover_seconds > 0:
            for side in ("home", "away"):
                chasers = [
                    p for p in sorted(self.teammates(side), key=lambda p: distance((p.x, p.y), (ball_x, ball_y)))
                    if p.slot != "GK"
                ][:2]
                for chaser in chasers:
                    if chaser.profile.id not in reacting_ids:
                        reacting.append(chaser)
                        reacting_ids.add(chaser.profile.id)

        for team in (self.home, self.away):
            attacking = team.side == self.state.possession
            opps = self.opponents(team.side)
            active_players = [p for p in team.xi if not p.red_card]
            if not active_players:
                continue
            pressers = sorted(active_players, key=lambda p: distance((p.x, p.y), (ball_x, ball_y)))
            main_presser = pressers[0]
            cover_ids = {p.profile.id for p in pressers[1:3]}
            for p in active_players:
                if p.profile.id == self.state.ball.carrier_id:
                    continue

                if p in reacting:
                    self._clear_run_commitment(p)
                    p.target_x = clamp(lerp(p.x, ball_x, 0.28), 2, PITCH_LENGTH - 2)
                    p.target_y = clamp(lerp(p.y, ball_y, 0.28), 2, PITCH_WIDTH - 2)
                    self._set_render_state(p, "transition", "react")
                    continue

                if attacking:
                    tx, ty = self._role_target(p, self.state.phase_in_possession, self.state.ball_zone)
                    tx, ty = self._dynamic_attack_target(p, tx, ty)
                    tx, ty = self._return_to_role_target(p, tx, ty)
                    state = "support"
                    intent = self.state.phase_in_possession
                    if p.profile.id == self.state.ball.target_player_id:
                        state = "receiving"
                        intent = self.state.ball.pass_type
                    elif distance((p.x, p.y), (p.home_x, p.home_y)) > 10.0 and distance((p.x, p.y), (ball_x, ball_y)) > 9.0:
                        state = "recover"
                    elif p.slot in ("LW", "RW", "ST", "AM", "CM") and abs(tx - p.x) > 3:
                        state = "run"
                    tx, ty, state, intent = self._maybe_apply_run_commitment(p, tx, ty, state, intent)
                    p.target_x, p.target_y = tx, ty
                    self._set_render_state(p, state, intent)
                else:
                    tx, ty = self._defensive_shape_target(p)
                    tx, ty = self._return_to_role_target(p, tx, ty)
                    self._clear_run_commitment(p)
                    if p.profile.id == main_presser.profile.id and p.profile.id != self.state.ball.carrier_id:
                        tx = lerp(p.x, ball_x, 0.48)
                        ty = lerp(p.y, ball_y, 0.48)
                        self._set_render_state(p, "pressing", "press")
                    elif p.profile.id in cover_ids:
                        if opps:
                            dangerous = sorted(opps, key=lambda opp: self._forwardness(opp.side, opp.x), reverse=True)[0]
                            tx = lerp(p.x, dangerous.x, 0.25)
                            ty = lerp(p.y, dangerous.y, 0.25)
                        self._set_render_state(p, "cover", "cover")
                    else:
                        state = "recover" if distance((p.x, p.y), (p.home_x, p.home_y)) > 10.0 and distance((p.x, p.y), (ball_x, ball_y)) > 9.0 else "shape"
                        self._set_render_state(p, state, "shape")
                    p.target_x, p.target_y = clamp(tx, 2, PITCH_LENGTH - 2), clamp(ty, 2, PITCH_WIDTH - 2)

    def _dynamic_attack_target(self, player: PlayerState, tx: float, ty: float) -> Tuple[float, float]:
        if player.slot == "GK":
            return tx, ty
        sign = self._side_forward_sign(player.side)
        ball_x, ball_y = self.state.ball.x, self.state.ball.y
        phase = self.state.phase_in_possession
        space = self._receiver_space(player)
        off_ball = player.profile.attributes.get("off_ball", player.profile.attributes["positioning"])
        run_bias = max(0.0, off_ball - 68.0) / 18.0
        width_tactic = (self._tactic_value(player.side, "width") - 50.0) / 50.0
        dist_to_ball = distance((player.x, player.y), (ball_x, ball_y))
        mindset_bias = self._player_mindset_bias(player)

        if phase == "build_up":
            if player.slot in ("CM", "AM"):
                tx += sign * (1.6 + space * 1.2)
            elif player.slot in ("LW", "RW", "ST"):
                tx += sign * (2.8 + space * 1.4)
        elif phase == "progression":
            if player.slot in ("CB", "LB", "RB"):
                tx += sign * (2.2 + space * 1.0)
            if player.slot == "CM":
                tx += sign * (3.4 + space * 2.0)
                ty += -2.0 if player.home_y < PITCH_WIDTH / 2 else 2.0
            elif player.slot == "AM":
                tx += sign * (4.5 + space * 2.4)
                ty += 2.5 if player.home_y >= PITCH_WIDTH / 2 else -2.5
            elif player.slot in ("LW", "RW"):
                tx += sign * (5.8 + space * 2.4 + run_bias * 1.0)
                ty += (-2.8 if player.slot == "LW" else 2.8) * (1.0 + width_tactic * 0.35)
            elif player.slot == "ST":
                tx += sign * (6.4 + space * 2.8 + run_bias * 0.9)
                ty += (-3.5 if ball_y < PITCH_WIDTH / 2 else 3.5) * 0.6
        else:
            if player.slot in ("CB", "LB", "RB"):
                tx += sign * (3.5 + space * 1.2)
            if player.slot == "CM":
                tx += sign * (2.8 + space * 1.6)
            elif player.slot == "AM":
                tx += sign * (4.2 + space * 2.0)
            elif player.slot in ("LW", "RW"):
                tx += sign * (4.8 + space * 2.2 + run_bias * 1.0)
                ty += (-2.0 if player.slot == "LW" else 2.0) * (1.0 + width_tactic * 0.28)
            elif player.slot == "ST":
                tx += sign * (5.4 + space * 2.4 + run_bias * 0.8)

        if dist_to_ball > 12.0 and player.slot in ("CM", "AM", "LW", "RW", "ST"):
            tx += sign * 1.6
        if player.slot in ("LB", "RB", "DM", "CM", "AM", "LW", "RW", "ST"):
            tx += sign * mindset_bias * (2.8 if player.slot in ("AM", "LW", "RW", "ST") else 1.8)
        elif player.slot in ("CB", "GK"):
            tx += sign * mindset_bias * 0.8

        tx, ty = clamp(tx, 2, PITCH_LENGTH - 2), clamp(ty, 2, PITCH_WIDTH - 2)
        return self._apply_onside_target_limit(player, tx, ty)

    def _return_to_role_target(self, player: PlayerState, tx: float, ty: float) -> Tuple[float, float]:
        ball_x, ball_y = self.state.ball.x, self.state.ball.y
        role_gap = distance((player.x, player.y), (player.home_x, player.home_y))
        ball_gap = distance((player.x, player.y), (ball_x, ball_y))
        target_gap = distance((player.x, player.y), (tx, ty))
        if role_gap < 8.0 or ball_gap < 9.0 or target_gap < 4.0:
            return tx, ty

        recover_blend = clamp((role_gap - 8.0) / 18.0, 0.0, 0.7)
        recover_x = lerp(tx, player.home_x, recover_blend * 0.55)
        recover_y = lerp(ty, player.home_y, recover_blend * 0.70)
        return clamp(recover_x, 2, PITCH_LENGTH - 2), clamp(recover_y, 2, PITCH_WIDTH - 2)

    def _offside_line(self, attacking_side: str) -> float:
        defenders = sorted(self.opponents(attacking_side), key=lambda p: p.x)
        if len(defenders) < 2:
            return PITCH_LENGTH if self._side_forward_sign(attacking_side) > 0 else 0.0
        if self._side_forward_sign(attacking_side) > 0:
            return defenders[-2].x
        return defenders[1].x

    def _is_position_offside(self, side: str, x: float, passer_x: float) -> bool:
        forward = self._forwardness(side, x)
        passer_forward = self._forwardness(side, passer_x)
        line_forward = self._forwardness(side, self._offside_line(side))
        if forward <= (PITCH_LENGTH / 2):
            return False
        if forward <= passer_forward + 0.35:
            return False
        return forward > line_forward + 0.2

    def _is_player_offside(self, player: PlayerState, passer_x: float) -> bool:
        return self._is_position_offside(player.side, player.x, passer_x)

    def _offside_depth(self, side: str, x: float) -> float:
        return self._forwardness(side, x) - self._forwardness(side, self._offside_line(side))

    def _offside_margin(self, side: str, x: float, passer_x: float) -> float:
        forward = self._forwardness(side, x)
        passer_forward = self._forwardness(side, passer_x)
        line_forward = self._forwardness(side, self._offside_line(side))
        if forward <= (PITCH_LENGTH / 2):
            return -999.0
        return forward - max(line_forward + 0.2, passer_forward + 0.35)

    def _event_frequency_boost(self, kind: str) -> float:
        elapsed_ratio = clamp(self.state.elapsed_seconds / (MATCH_MINUTES * 60.0), 0.0, 1.0)
        targets = {
            "throw_in": 16.0,
            "corner": 9.0,
            "offside": 4.0,
            "foul": 16.0,
            "yellow": 3.0,
        }
        currents = {
            "throw_in": float(self.state.throw_ins_count),
            "corner": float(self.state.corners_count),
            "offside": float(self.state.offsides_count),
            "foul": float(self.state.fouls_count_home + self.state.fouls_count_away),
            "yellow": float(self.state.yellow_cards_home + self.state.yellow_cards_away),
        }
        target = targets.get(kind, 0.0)
        current = currents.get(kind, 0.0)
        if target <= 0.0:
            return 0.0
        if kind == "throw_in":
            width_bias = (
                (self._tactic_value("home", "width") - 50.0) / 50.0
                + (self._tactic_value("away", "width") - 50.0) / 50.0
            ) * 0.5
            target *= 1.0 + max(0.0, width_bias) * 0.18
        expected = target * elapsed_ratio
        deficit = expected - current
        return clamp(deficit / max(1.0, target * 0.18), 0.0, 3.0)

    def _is_in_penalty_area(self, side: str, x: float, y: float) -> bool:
        defend_x = self._defending_goal_x(side)
        if defend_x == 0.0:
            return x <= 16.5 and 13.84 <= y <= (PITCH_WIDTH - 13.84)
        return x >= (PITCH_LENGTH - 16.5) and 13.84 <= y <= (PITCH_WIDTH - 13.84)

    def _discipline_intensity(self, side: str) -> float:
        pressing = (self._tactic_value(side, "pressing") - 50.0) / 50.0
        tempo = (self._tactic_value(side, "tempo") - 50.0) / 50.0
        directness = (self._tactic_value(side, "directness") - 50.0) / 50.0
        return clamp(1.0 + pressing * 0.16 + max(0.0, tempo) * 0.06 + max(0.0, directness) * 0.04, 0.84, 1.18)

    def _card_event(self, offender: PlayerState, color: str) -> None:
        if color == "yellow":
            offender.yellow_cards += 1
            if offender.side == "home":
                self.state.yellow_cards_home += 1
            else:
                self.state.yellow_cards_away += 1
            self._team_match_stats(offender.side)["yellow_cards"] += 1.0
            self._player_match_stats(offender)["yellow_cards"] += 1.0
            self.add_event(f"Yellow card for {offender.short_name}")
            if offender.yellow_cards >= 2:
                self._card_event(offender, "red")
            return
        if offender.red_card:
            return
        offender.red_card = True
        offender.has_ball = False
        offender.target_x = -10.0
        offender.target_y = -10.0
        offender.x = -10.0
        offender.y = -10.0
        offender.prev_x = -10.0
        offender.prev_y = -10.0
        self._set_render_state(offender, "shape", "sent_off")
        if offender.side == "home":
            self.state.red_cards_home += 1
        else:
            self.state.red_cards_away += 1
        self._team_match_stats(offender.side)["red_cards"] += 1.0
        self._player_match_stats(offender)["red_cards"] += 1.0
        self.add_event(f"Red card for {offender.short_name}")

    def _foul_card_color(self, offender: PlayerState, foul_spot: Tuple[float, float], attacking_side: str, severity: float) -> Optional[str]:
        strictness = (self.state.referee_strictness - 50.0) / 50.0
        attack_forward = self._forwardness(attacking_side, foul_spot[0])
        central_gap = abs(foul_spot[1] - PITCH_WIDTH / 2)
        dogso = attack_forward > 88.0 and central_gap < 10.0
        pressure_bias = self._player_pressure_bias(offender)
        yellow = (
            severity * 0.78
            + max(0.0, strictness) * 0.08
            + (0.08 if attack_forward > 78.0 else 0.0)
            + (0.06 if offender.fouls_committed >= 3 else 0.0)
            + (0.04 if offender.yellow_cards >= 1 else 0.0)
            + (self._discipline_intensity(offender.side) - 1.0) * 0.12
            + pressure_bias * 0.10
        )
        if dogso and severity > 0.84:
            return "red"
        if yellow > 0.66:
            return "yellow"
        return None

    def _start_direct_free_kick_setup(self, attacking_side: str, x: float, y: float, taker: PlayerState, fouled: Optional[PlayerState] = None) -> None:
        self._prepare_players_for_restart_motion()
        self.state.restart_mode = "direct_free_kick_setup"
        self.state.restart_timer = FREE_KICK_SETUP_SECONDS
        self.state.restart_side = attacking_side
        self.state.restart_taker_id = taker.profile.id
        self.state.fouled_player_id = fouled.profile.id if fouled else None
        x = clamp(x, 4.0, PITCH_LENGTH - 4.0)
        y = clamp(y, 4.0, PITCH_WIDTH - 4.0)
        self._reset_ball_for_restart(x, y)
        taker.target_x = x
        taker.target_y = y
        self._set_render_state(taker, "restart", "free_kick")
        sign = self._side_forward_sign(attacking_side)
        dangerous = self._forwardness(attacking_side, x) > 74.0 and abs(y - PITCH_WIDTH / 2) < 15.0
        for teammate in self.teammates(attacking_side):
            if teammate.profile.id == taker.profile.id:
                continue
            if dangerous and teammate.slot in ("ST", "AM", "CB", "CM"):
                teammate.target_x = clamp(x + sign * (8.0 + (3.0 if teammate.slot == "ST" else 0.0)), 2.0, PITCH_LENGTH - 2.0)
                teammate.target_y = clamp(y + ((teammate.home_y - PITCH_WIDTH / 2) * 0.35), 6.0, PITCH_WIDTH - 6.0)
                self._set_render_state(teammate, "restart", "free_kick_attack")
            else:
                teammate.target_x = clamp(lerp(teammate.home_x, x, 0.10), 2, PITCH_LENGTH - 2)
                teammate.target_y = teammate.home_y
                self._set_render_state(teammate, "restart", "free_kick_shape")
        wall_x = x + sign * 9.15
        defenders = sorted(self.opponents(attacking_side), key=lambda p: p.slot == "GK")
        for idx, defender in enumerate(defenders):
            if defender.slot == "GK":
                defender.target_x = clamp(self._defending_goal_x(defender.side) + self._side_forward_sign(defender.side) * 2.5, 2, PITCH_LENGTH - 2)
                defender.target_y = PITCH_WIDTH / 2
            elif dangerous and idx < 4:
                defender.target_x = clamp(wall_x, 2, PITCH_LENGTH - 2)
                defender.target_y = clamp(y + (-2.4 + idx * 1.6), 8.0, PITCH_WIDTH - 8.0)
            else:
                defender.target_x = clamp(lerp(defender.home_x, x, 0.12), 2, PITCH_LENGTH - 2)
                defender.target_y = defender.home_y
            self._set_render_state(defender, "restart", "free_kick_defend")
        self.add_event(f"Free kick to {self._team_state(attacking_side).name}")

    def _execute_direct_free_kick(self) -> None:
        side = self.state.restart_side or "home"
        set_piece_mode = self._instruction_value(side, "set_pieces")
        taker = self.find_player(self.state.restart_taker_id) or min(self.teammates(side), key=lambda p: distance((p.x, p.y), (self.state.ball.x, self.state.ball.y)))
        forwardness = self._forwardness(side, self.state.ball.x)
        central_gap = abs(self.state.ball.y - PITCH_WIDTH / 2)
        dangerous = forwardness > 74.0 and central_gap < 15.0
        advanced = forwardness > 60.0
        own_half = forwardness < 45.0
        wide = central_gap > 13.0
        self.state.restart_mode = None
        self.state.restart_timer = 0.0
        self.state.restart_side = None
        self.state.restart_taker_id = None
        self.state.fouled_player_id = None
        self._give_ball_to(taker, note="Free kick", action_type="recovery")
        direct_quality = self._free_kick_taker_score(taker)
        direct_shot_bias = clamp((direct_quality - 60.0) / 35.0, 0.0, 1.0)
        if dangerous and set_piece_mode == "direct" and self.rng.random() < clamp(0.36 + direct_shot_bias * 0.34, 0.24, 0.74):
            self._start_shot(taker)
            return
        if dangerous and set_piece_mode != "possession" and self.rng.random() < clamp(0.22 + direct_shot_bias * 0.28, 0.12, 0.58):
            self._start_shot(taker)
            return
        if advanced:
            if set_piece_mode == "possession":
                receivers = [
                    p for p in self.teammates(side)
                    if p.profile.id != taker.profile.id and p.slot in ("DM", "CM", "AM", "LB", "RB")
                ]
                if not receivers:
                    receivers = [p for p in self.teammates(side) if p.profile.id != taker.profile.id]
                receiver = max(
                    receivers,
                    key=lambda p: p.profile.attributes["first_touch"] + p.profile.attributes["passing"] + self._receiver_space(p) * 16.0,
                )
                pass_type = "short_ground"
                label = "free kick short"
            elif wide or set_piece_mode == "direct" or self.rng.random() < 0.72:
                receivers = [
                    p for p in self.teammates(side)
                    if p.profile.id != taker.profile.id and p.slot in ("ST", "AM", "CM", "LW", "RW", "CB")
                ]
                if not receivers:
                    receivers = [p for p in self.teammates(side) if p.profile.id != taker.profile.id]
                receiver = max(
                    receivers,
                    key=lambda p: (
                        self._forwardness(side, p.x) * 0.5
                        + p.profile.attributes["positioning"]
                        + p.profile.attributes.get("off_ball", p.profile.attributes["positioning"]) * 0.35
                        + self._receiver_space(p) * 18.0
                    ),
                )
                pass_type = "cross"
                label = "free kick cross"
            else:
                receivers = [
                    p for p in self.teammates(side)
                    if p.profile.id != taker.profile.id and p.slot in ("AM", "CM", "LW", "RW", "ST")
                ]
                if not receivers:
                    receivers = [p for p in self.teammates(side) if p.profile.id != taker.profile.id]
                receiver = max(
                    receivers,
                    key=lambda p: p.profile.attributes["first_touch"] + p.profile.attributes["passing"] + self._receiver_space(p) * 16.0,
                )
                pass_type = "progressive_ground"
                label = "free kick"
        elif own_half:
            if set_piece_mode == "direct" and self.rng.random() < 0.6:
                receivers = [
                    p for p in self.teammates(side)
                    if p.profile.id != taker.profile.id and p.slot in ("ST", "LW", "RW", "AM", "CM")
                ]
                if not receivers:
                    receivers = [p for p in self.teammates(side) if p.profile.id != taker.profile.id]
                receiver = max(
                    receivers,
                    key=lambda p: self._forwardness(side, p.x) + p.profile.attributes.get("off_ball", p.profile.attributes["positioning"]) * 0.4,
                )
                pass_type = "cross"
                label = "free kick long"
            elif self.rng.random() < 0.78:
                receivers = [
                    p for p in self.teammates(side)
                    if p.profile.id != taker.profile.id and p.slot in ("DM", "CM", "CB", "LB", "RB")
                ]
                if not receivers:
                    receivers = [p for p in self.teammates(side) if p.profile.id != taker.profile.id]
                receiver = max(
                    receivers,
                    key=lambda p: p.profile.attributes["first_touch"] + p.profile.attributes["passing"] + self._receiver_space(p) * 12.0,
                )
                pass_type = "short_ground"
                label = "free kick"
            else:
                receivers = [
                    p for p in self.teammates(side)
                    if p.profile.id != taker.profile.id and p.slot in ("ST", "LW", "RW", "AM", "CM")
                ]
                if not receivers:
                    receivers = [p for p in self.teammates(side) if p.profile.id != taker.profile.id]
                receiver = max(
                    receivers,
                    key=lambda p: self._forwardness(side, p.x) + p.profile.attributes.get("off_ball", p.profile.attributes["positioning"]) * 0.4,
                )
                pass_type = "cross"
                label = "free kick long"
        else:
            receivers = [
                p for p in self.teammates(side)
                if p.profile.id != taker.profile.id and p.slot in ("CM", "AM", "DM", "LW", "RW", "ST")
            ]
            if not receivers:
                receivers = [p for p in self.teammates(side) if p.profile.id != taker.profile.id]
            receiver = max(
                receivers,
                key=lambda p: p.profile.attributes["positioning"] + self._receiver_space(p) * 16.0,
            )
            pass_type = "progressive_ground"
            label = "free kick"
        self._start_pass(taker, receiver, label, pass_type)

    def _start_penalty_setup(self, attacking_side: str, taker: PlayerState) -> None:
        self._prepare_players_for_restart_motion()
        self.state.restart_mode = "penalty_setup"
        self.state.restart_timer = PENALTY_SETUP_SECONDS
        self.state.restart_side = attacking_side
        self.state.restart_taker_id = taker.profile.id
        spot_x = 11.0 if self._attacking_goal_x(attacking_side) == 0.0 else PITCH_LENGTH - 11.0
        spot_y = PITCH_WIDTH / 2
        self._reset_ball_for_restart(spot_x, spot_y)
        for player in self.home.xi + self.away.xi:
            if player.red_card:
                continue
            if player.profile.id == taker.profile.id:
                player.target_x = spot_x
                player.target_y = spot_y
                self._set_render_state(player, "restart", "penalty")
            elif player.slot == "GK" and player.side != attacking_side:
                player.target_x = self._defending_goal_x(player.side) + self._side_forward_sign(player.side) * 0.8
                player.target_y = PITCH_WIDTH / 2
                self._set_render_state(player, "restart", "penalty_keeper")
            else:
                arc_x = spot_x - self._side_forward_sign(attacking_side) * 9.5
                player.target_x = clamp(arc_x + ((player.home_y - PITCH_WIDTH / 2) * 0.05), 2, PITCH_LENGTH - 2)
                player.target_y = clamp(player.home_y, 8.0, PITCH_WIDTH - 8.0)
                self._set_render_state(player, "restart", "penalty_wait")
        self.add_event(f"Penalty to {self._team_state(attacking_side).name}")

    def _execute_penalty(self) -> None:
        side = self.state.restart_side or "home"
        taker = self.find_player(self.state.restart_taker_id) or max(self.teammates(side), key=self._penalty_taker_score)
        keeper = self._goalkeeper("away" if side == "home" else "home")
        self.state.assist_candidate_id = None
        self.state.restart_mode = None
        self.state.restart_timer = 0.0
        self.state.restart_side = None
        self.state.restart_taker_id = None
        taker_score = self._penalty_taker_score(taker)
        keeper_score = self._keeper_save_score(keeper)
        chance = 0.58 + (taker_score - keeper_score) / 260.0
        if self.rng.random() < clamp(chance, 0.42, 0.86):
            self._record_shot(taker, True)
            self.state.player_goals[taker.profile.id] = self.state.player_goals.get(taker.profile.id, 0) + 1
            self._record_goal(taker)
            if side == "home":
                self.state.home_score += 1
            else:
                self.state.away_score += 1
            self.add_event(f"GOAL! {taker.short_name} scores the penalty")
            self._start_goal_celebration(taker)
            return
        if self.rng.random() < 0.72:
            self._record_shot(taker, True)
            self._record_goalkeeper_save(keeper)
            self._give_ball_to(keeper, note=f"{keeper.short_name} saves the penalty", action_type="recovery")
            return
        self._record_shot(taker, False)
        self._start_goal_kick_setup("away" if side == "home" else "home", shot_out_position=(self._attacking_goal_x(side) + self._side_forward_sign(side) * 2.0, PITCH_WIDTH / 2))

    def _commit_foul(self, offender: PlayerState, fouled: PlayerState, foul_spot: Tuple[float, float], severity: float) -> bool:
        attacking_side = fouled.side
        defending_side = offender.side
        offender.fouls_committed += 1
        fouled.fouls_suffered += 1
        if attacking_side == "home":
            self.state.fouls_count_home += 1
        else:
            self.state.fouls_count_away += 1
        self._team_match_stats(offender.side)["fouls"] += 1.0
        self._player_match_stats(offender)["fouls_committed"] += 1.0
        self._player_match_stats(fouled)["fouls_suffered"] += 1.0
        card = self._foul_card_color(offender, foul_spot, attacking_side, severity)
        if card:
            self._card_event(offender, card)
        self.add_event(f"Foul by {offender.short_name}")
        taker_pool = [p for p in self.teammates(attacking_side) if not p.red_card]
        taker = fouled if not fouled.red_card else max(taker_pool, key=self._free_kick_taker_score)
        if self._is_in_penalty_area(defending_side, foul_spot[0], foul_spot[1]) and attacking_side != defending_side:
            taker = max(taker_pool, key=self._penalty_taker_score)
            self._start_penalty_setup(attacking_side, taker)
            return True
        self._start_direct_free_kick_setup(attacking_side, foul_spot[0], foul_spot[1], taker, fouled)
        return True

    def _should_flag_offside(self, carrier: PlayerState, receiver: PlayerState, pass_type: str, check_x: float) -> bool:
        sign = self._side_forward_sign(carrier.side)
        if (check_x - carrier.x) * sign <= 0:
            return False
        margin = self._offside_margin(receiver.side, check_x, carrier.x)
        if margin > 0.0:
            return True
        if pass_type not in ("through_ball", "progressive_ground"):
            return False
        if receiver.slot not in ("ST", "LW", "RW"):
            return False
        if margin < (-0.8 if pass_type == "through_ball" else -0.35):
            return False

        boost = self._event_frequency_boost("offside")
        defenders = [p for p in self.opponents(receiver.side) if p.slot in ("CB", "LB", "RB", "DM")]
        if defenders:
            line_discipline = sum(
                p.profile.attributes["positioning"] + p.profile.attributes.get("anticipation", p.profile.attributes["positioning"])
                for p in defenders
            ) / (len(defenders) * 2.0)
        else:
            line_discipline = 65.0
        trap = self._tactic_value("away" if receiver.side == "home" else "home", "offside_trap", 50.0)
        attacker_timing = (
            receiver.profile.attributes.get("off_ball", receiver.profile.attributes["positioning"])
            + receiver.profile.attributes.get("anticipation", receiver.profile.attributes["positioning"])
            + receiver.profile.attributes["decisions"]
        ) / 3.0
        passer_release = (
            carrier.profile.attributes["vision"]
            + carrier.profile.attributes["decisions"]
            + carrier.profile.attributes["passing"]
        ) / 3.0
        chance = (
            0.08
            + boost * 0.22
            + clamp((line_discipline - attacker_timing) / 180.0, -0.10, 0.12)
            + clamp((trap - 50.0) / 220.0, -0.05, 0.08)
            + clamp((68.0 - passer_release) / 200.0, -0.04, 0.06)
            + clamp((margin + 0.8) / 6.0, 0.0, 0.10)
        )
        return self.rng.random() < clamp(chance, 0.04, 0.50)

    def _apply_onside_target_limit(self, player: PlayerState, tx: float, ty: float) -> Tuple[float, float]:
        if player.side != self.state.possession or player.slot in ("GK", "CB", "LB", "RB", "DM"):
            return tx, ty
        sign = self._side_forward_sign(player.side)
        allowance = -1.0
        if player.slot in ("LW", "RW", "ST"):
            if self.state.phase_in_possession in ("final_third", "transition"):
                allowance = 0.0
            elif self.state.phase_in_possession == "progression":
                allowance = -0.1
        elif player.slot == "AM" and self.state.phase_in_possession in ("final_third", "transition"):
            allowance = -0.6
        line = self._offside_line(player.side) + sign * allowance
        if sign > 0:
            tx = min(tx, max(PITCH_LENGTH / 2 + 0.5, line))
        else:
            tx = max(tx, min(PITCH_LENGTH / 2 - 0.5, line))
        return clamp(tx, 2, PITCH_LENGTH - 2), ty

    def _call_offside(self, offender: PlayerState) -> None:
        defending_side = "away" if offender.side == "home" else "home"
        defenders = self.teammates(defending_side)
        spot_x = offender.x
        spot_y = offender.y
        taker = min(
            defenders,
            key=lambda p: distance((p.x, p.y), (spot_x, spot_y)) + (0.8 if p.slot == "GK" else 0.0),
        )
        self._start_offside_restart(defending_side, taker, spot_x, spot_y, offender.short_name)

    def _move_players(self) -> None:
        for p in self.home.xi + self.away.xi:
            if p.red_card:
                p.x = -10.0
                p.y = -10.0
                p.prev_x = -10.0
                p.prev_y = -10.0
                p.target_x = -10.0
                p.target_y = -10.0
                p.vx = 0.0
                p.vy = 0.0
                continue
            p.run_commit_timer = max(0.0, p.run_commit_timer - SLICE_SECONDS)
            if p.run_commit_timer <= 0.0 and p.commit_target_x is not None and p.commit_target_y is not None:
                p.commit_target_x = None
                p.commit_target_y = None
            dx = p.target_x - p.x
            dy = p.target_y - p.y
            d = math.hypot(dx, dy)
            if d < 0.01:
                p.vx = 0.0
                p.vy = 0.0
                continue
            step = min(self._player_move_speed(p) * SLICE_SECONDS, d)
            old_x, old_y = p.x, p.y
            p.x += dx / d * step
            p.y += dy / d * step
            p.vx = (p.x - old_x) / SLICE_SECONDS
            p.vy = (p.y - old_y) / SLICE_SECONDS
            move_mag = math.hypot(p.vx, p.vy)
            if move_mag > 0.05:
                p.facing_x = p.vx / move_mag
                p.facing_y = p.vy / move_mag
            p.fatigue = clamp(p.fatigue + self._fatigue_load_for_player(p), 0.0, 25.0)

    def _fatigue_load_for_player(self, player: PlayerState) -> float:
        role_factor = {
            "GK": 0.26,
            "CB": 0.62,
            "LB": 0.88,
            "RB": 0.88,
            "DM": 0.72,
            "CM": 0.82,
            "AM": 0.88,
            "LW": 0.95,
            "RW": 0.95,
            "ST": 0.86,
        }.get(player.slot, 0.8)
        state_factor = {
            "shape": 0.54,
            "support": 0.66,
            "cover": 0.62,
            "receiving": 0.84,
            "carry": 0.96,
            "run": 1.06,
            "recover": 1.10,
            "pressing": 1.14,
            "transition": 1.08,
            "restart": 0.72,
            "celebrate": 0.92,
        }.get(player.render_state, 0.78)
        stamina = player.profile.attributes["stamina"]
        stamina_factor = clamp(1.1 - (stamina - 50.0) / 180.0, 0.72, 1.12)
        width_bias = max(0.0, (self._tactic_value(player.side, "width") - 50.0) / 50.0)
        pressing_bias = max(0.0, (self._tactic_value(player.side, "pressing") - 50.0) / 50.0)
        tempo_bias = max(0.0, (self._tactic_value(player.side, "tempo") - 50.0) / 50.0)
        tempo_mode = self._instruction_value(player.side, "tempo")

        load = 0.0054 * role_factor * state_factor * stamina_factor
        if player.slot in ("LB", "RB", "LW", "RW"):
            load *= 1.0 + width_bias * 0.28
        elif player.slot in ("CB", "DM", "GK"):
            load *= 1.0 - width_bias * 0.06

        if player.slot != "GK":
            load *= 1.0 + pressing_bias * (0.18 if player.slot in ("LW", "RW", "ST", "AM", "CM") else 0.12)
            load *= 1.0 + tempo_bias * (0.14 if player.slot in ("CM", "AM", "LW", "RW", "ST") else 0.08)
        if tempo_mode == "lower":
            load *= 0.9
        elif tempo_mode == "higher":
            load *= 1.1

        if player.has_ball:
            load *= 1.28
        elif self.state.ball.target_player_id == player.profile.id:
            load *= 1.16

        ball_dist = distance((player.x, player.y), (self.state.ball.x, self.state.ball.y))
        if ball_dist < 8.0:
            load *= 1.2
        elif ball_dist < 16.0:
            load *= 1.1
        elif player.render_state == "shape":
            load *= 0.92

        if self.state.last_touch_player_id == player.profile.id:
            load *= 1.12

        return clamp(load, 0.0007, 0.013)

    def _player_move_speed(self, player: PlayerState) -> float:
        if player.render_state == "celebrate":
            return 6.8
        pace = player.profile.attributes["pace"]
        acceleration = player.profile.attributes.get("acceleration", pace)
        stamina = player.profile.attributes["stamina"]
        fatigue_penalty = clamp(player.fatigue / max(45.0, stamina * 0.75), 0.0, 0.42)
        pace_boost = 0.96 + (pace - 50.0) / 112.0
        acceleration_boost = 0.96 + (acceleration - 50.0) / 120.0
        state_multiplier = {
            "pressing": 1.28,
            "recover": 1.38,
            "run": 1.24,
            "transition": 1.26,
            "carry": 1.13,
            "receiving": 1.10,
            "cover": 1.08,
            "celebrate": 1.14,
            "restart": 1.92,
            "shape": 1.01,
            "support": 1.05,
        }.get(player.render_state, 1.0)
        burst_multiplier = acceleration_boost if player.render_state in ("pressing", "recover", "run", "transition", "receiving") else 1.0
        return max(2.1, player.base_speed * pace_boost * burst_multiplier * state_multiplier * (1.0 - fatigue_penalty))

    def _ball_front_offset(self, carrier: PlayerState) -> Tuple[float, float]:
        mag = math.hypot(carrier.facing_x, carrier.facing_y)
        if mag < 0.01:
            return carrier.x, carrier.y
        offset = 0.75 if carrier.render_state in ("carry", "shooting") else 0.45
        return carrier.x + carrier.facing_x * offset, carrier.y + carrier.facing_y * offset

    def _predict_receiver_target(self, carrier: PlayerState, receiver: PlayerState, pass_type: str) -> Tuple[float, float]:
        sign = self._side_forward_sign(carrier.side)
        lead_x = receiver.x
        lead_y = receiver.y
        move_x = receiver.target_x - receiver.x
        move_y = receiver.target_y - receiver.y
        space = self._receiver_space(receiver)
        off_ball = receiver.profile.attributes.get("off_ball", receiver.profile.attributes["positioning"])
        run_quality = max(0.0, off_ball - 60.0) / 30.0
        if pass_type == "through_ball":
            lead_x += move_x * 0.75 + sign * (2.0 + space * 1.6 + run_quality * 0.9)
            lead_y += move_y * 0.55
        elif pass_type == "cross":
            lead_x += move_x * 0.24 + sign * (1.8 + space * 1.0 + run_quality * 0.4)
            lead_y += (PITCH_WIDTH / 2 - receiver.y) * 0.12 + move_y * 0.18
            attacking_goal_x = self._attacking_goal_x(carrier.side)
            min_depth = 6.5
            if abs(attacking_goal_x - lead_x) < min_depth:
                lead_x = attacking_goal_x - sign * min_depth
        elif pass_type == "progressive_ground":
            lead_x += move_x * 0.35 + sign * 0.8
            lead_y += move_y * 0.25
        elif pass_type == "switch":
            lead_x += move_x * 0.18
            lead_y += move_y * 0.32
        else:
            lead_x += move_x * 0.12
            lead_y += move_y * 0.12
        lead_x = clamp(lead_x, 2, PITCH_LENGTH - 2)
        lead_y = clamp(lead_y, 2, PITCH_WIDTH - 2)
        pass_speed = PASS_SPEEDS.get(pass_type, PASS_SPEEDS["short_ground"])
        travel_dist = distance((carrier.x, carrier.y), (lead_x, lead_y))
        travel_time = max(0.24, travel_dist / pass_speed)
        reachable = self._player_move_speed(receiver) * travel_time * 0.92 + 0.9
        target_dist = distance((receiver.x, receiver.y), (lead_x, lead_y))
        if target_dist > reachable:
            blend = reachable / max(0.01, target_dist)
            lead_x = lerp(receiver.x, lead_x, blend)
            lead_y = lerp(receiver.y, lead_y, blend)
        return clamp(lead_x, 2, PITCH_LENGTH - 2), clamp(lead_y, 2, PITCH_WIDTH - 2)

    def _evaluate_pass_lane(self, passer: PlayerState, receiver: PlayerState, pass_type: str) -> float:
        samples = 5 if pass_type == "through_ball" else 4
        lane_penalty = 0.0
        segment = distance((passer.x, passer.y), (receiver.x, receiver.y))
        if segment < 0.01:
            return 0.0
        opps = self.opponents(passer.side)
        for idx in range(1, samples + 1):
            t = idx / (samples + 1)
            sx = lerp(passer.x, receiver.x, t)
            sy = lerp(passer.y, receiver.y, t)
            nearest = min(distance((sx, sy), (opp.x, opp.y)) for opp in opps)
            lane_penalty += clamp((5.2 - nearest) / 5.2, 0.0, 1.0)
        angle = abs(receiver.y - passer.y) / max(1.0, segment)
        return lane_penalty + angle * (0.4 if pass_type == "switch" else 0.18)

    def _pass_forward_angle(self, carrier: PlayerState, receiver: PlayerState) -> float:
        sign = self._side_forward_sign(carrier.side)
        dx = (receiver.x - carrier.x) * sign
        dy = abs(receiver.y - carrier.y)
        if dx <= 0:
            return -0.2
        return dx / max(1.0, dx + dy)

    def _pass_type_score(self, carrier: PlayerState, receiver: PlayerState, pass_type: str) -> float:
        dist = distance((carrier.x, carrier.y), (receiver.x, receiver.y))
        forward_angle = self._pass_forward_angle(carrier, receiver)
        progression = self._forwardness(carrier.side, receiver.x) - self._forwardness(carrier.side, carrier.x)
        lane_penalty = self._evaluate_pass_lane(carrier, receiver, pass_type)
        receiver_space = self._receiver_space(receiver)
        moving_into_space = 1.0 if (receiver.target_x - receiver.x) * self._side_forward_sign(receiver.side) > 0.5 else 0.0
        body_shape = clamp(receiver.facing_x * self._side_forward_sign(receiver.side), -1.0, 1.0)
        phase = self.state.phase_in_possession
        attrs = carrier.profile.attributes
        recv_attrs = receiver.profile.attributes
        passing_attr = attrs["passing"]
        if pass_type == "short_ground":
            passing_attr = attrs.get("short_passing", passing_attr)
        elif pass_type in ("switch", "through_ball", "cross"):
            passing_attr = attrs.get("long_passing", passing_attr)
        if pass_type == "cross":
            passing_attr = attrs.get("crossing", passing_attr)
        backward_penalty = max(0.0, -progression) * 1.25
        if progression < -8.0:
            backward_penalty += 8.0
        if receiver.slot == "GK" and self._goal_distance(carrier) < 35.0:
            return -999.0
        if self._goal_distance(carrier) < 22.0 and progression < -4.0:
            return -999.0

        link_bonus = 0.0
        if phase in ("build_up", "progression"):
            if receiver.slot in ("DM", "CM", "AM"):
                link_bonus += 4.5
            if carrier.slot in ("CB", "LB", "RB", "DM") and receiver.slot in ("DM", "CM", "AM"):
                link_bonus += 4.0
            if carrier.slot in ("LW", "RW", "ST") and receiver.slot in ("CM", "AM", "DM"):
                link_bonus += 3.6
            if carrier.slot in ("CM", "AM", "DM") and receiver.slot in ("LW", "RW"):
                same_side = (receiver.slot == "LW" and carrier.y < PITCH_WIDTH / 2) or (receiver.slot == "RW" and carrier.y >= PITCH_WIDTH / 2)
                link_bonus += 3.5 if same_side else 1.6
            if carrier.slot in ("LW", "RW") and receiver.slot in ("ST", "LW", "RW"):
                link_bonus -= 3.4
            if carrier.slot == "ST" and receiver.slot in ("LW", "RW", "ST"):
                link_bonus -= 4.4
        if phase == "final_third":
            if carrier.slot == "ST" and receiver.slot == "AM":
                link_bonus += 12.0
            if carrier.slot == "ST" and receiver.slot in ("LW", "RW", "ST"):
                link_bonus -= 13.0
            if carrier.slot in ("LW", "RW") and receiver.slot in ("CM", "AM"):
                link_bonus += 2.5
            if carrier.slot in ("CM", "AM") and receiver.slot in ("LW", "RW"):
                link_bonus += 2.9
            if carrier.slot in ("LW", "RW") and receiver.slot == "ST":
                link_bonus += 2.2

        base = (
            passing_attr * 0.22
            + attrs["vision"] * 0.18
            + attrs["decisions"] * 0.14
            + attrs.get("technique", attrs["passing"]) * 0.08
            + recv_attrs["first_touch"] * 0.08
            + recv_attrs.get("off_ball", recv_attrs["positioning"]) * 0.05
            + recv_attrs.get("technique", recv_attrs["first_touch"]) * 0.03
            + receiver_space * 10.0
            + body_shape * 3.0
            + forward_angle * 8.0
            + moving_into_space * 4.0
            + link_bonus
            - lane_penalty * 6.0
            - backward_penalty
            - dist * 0.12
        )
        if pass_type == "through_ball":
            if forward_angle < 0.45 or moving_into_space == 0.0 or receiver_space < 0.45:
                return -999.0
            offside_depth = self._offside_depth(receiver.side, receiver.x)
            if offside_depth > 2.0:
                return -999.0
            if self._is_player_offside(receiver, carrier.x):
                return base - 12.0 - offside_depth * 3.5
            return base + 4.5 - dist * 0.03
        if pass_type == "cross":
            if not self._is_cross_situation(carrier, receiver):
                return -999.0
            offside_depth = self._offside_depth(receiver.side, receiver.x)
            if offside_depth > 2.0:
                return -999.0
            if self._is_player_offside(receiver, carrier.x):
                return base - 10.0 - offside_depth * 3.0
            target_box_bonus = max(0.0, self._forwardness(receiver.side, receiver.x) - 74.0) * 1.2
            central_bonus = max(0.0, 16.0 - abs(receiver.y - PITCH_WIDTH / 2)) * 1.1
            aerial_bonus = (
                recv_attrs.get("heading", recv_attrs["positioning"]) * 0.08
                + recv_attrs.get("jumping_reach", recv_attrs.get("strength", recv_attrs["positioning"])) * 0.06
                + recv_attrs.get("strength", recv_attrs["positioning"]) * 0.04
                + recv_attrs["positioning"] * 0.04
            )
            return base + 10.0 + target_box_bonus + central_bonus + aerial_bonus - abs(progression) * 0.04
        if progression > 0.8 and self._is_player_offside(receiver, carrier.x):
            offside_depth = self._offside_depth(receiver.side, receiver.x)
            if offside_depth > 1.8:
                return -999.0
            return base - 11.0 - offside_depth * 3.2
        if pass_type == "progressive_ground":
            if phase == "final_third" and carrier.slot == "ST" and receiver.slot in ("LW", "RW", "ST"):
                return base - 6.5
            return base + 2.8
        if phase == "final_third" and carrier.slot == "ST" and receiver.slot in ("LW", "RW", "ST"):
            return base - 10.0 - max(0.0, 18.0 - dist) * 0.25
        if pass_type == "switch":
            return base + (3.5 if abs(receiver.y - carrier.y) > 16 else -2.0)
        return base + 1.4 - max(0.0, dist - 18.0) * 0.10

    def _is_cross_situation(self, carrier: PlayerState, receiver: PlayerState) -> bool:
        if carrier.slot not in ("LW", "RW", "LB", "RB"):
            return False
        if receiver.slot not in ("ST", "AM", "CM", "LW", "RW"):
            return False
        carrier_forward = self._forwardness(carrier.side, carrier.x)
        receiver_forward = self._forwardness(receiver.side, receiver.x)
        wide_zone = carrier.y < 14.0 or carrier.y > (PITCH_WIDTH - 14.0)
        if carrier_forward < 74.0 or not wide_zone:
            return False
        if receiver_forward < 70.0:
            return False
        if abs(receiver.y - PITCH_WIDTH / 2) > 18.0 and receiver.slot not in ("LW", "RW"):
            return False
        return True

    def _update_ball_motion(self) -> None:
        ball = self.state.ball
        if ball.mode == "carried":
            carrier = self.find_player(ball.carrier_id)
            if carrier:
                bx, by = self._ball_front_offset(carrier)
                ball.x = bx
                ball.y = by
                ball.target_x = bx
                ball.target_y = by
                if self._ball_is_out_of_bounds(ball.x, ball.y):
                    self._handle_ball_out(carrier.side, ball.x, ball.y)
            return

        if ball.mode in ("travelling", "shot"):
            if ball.travel_time <= 0:
                ball.travel_progress = 1.0
            else:
                ball.travel_progress = clamp(ball.travel_progress + (SLICE_SECONDS / ball.travel_time), 0.0, 1.0)

            t = ball.travel_progress
            ball.x = lerp(ball.start_x, ball.target_x, t)
            ball.y = lerp(ball.start_y, ball.target_y, t)

            if ball.mode == "travelling":
                if self._ball_is_out_of_bounds(ball.x, ball.y):
                    self._handle_ball_out(self._ball_last_touch_side(), ball.x, ball.y)
                    return
                if self._check_for_interception():
                    return
                if self._check_for_reception():
                    return
                if ball.travel_progress >= 1.0:
                    self._resolve_arrived_pass()
                    return
            elif ball.mode == "shot" and ball.travel_progress >= 1.0:
                self._resolve_arrived_shot()
                return

        if ball.mode == "loose":
            if self._ball_is_out_of_bounds(ball.x, ball.y):
                self._handle_ball_out(self._ball_last_touch_side(), ball.x, ball.y)
                return
            winner = self._loose_ball_favorite()
            if winner and distance((winner.x, winner.y), (ball.x, ball.y)) < 2.1:
                self._give_ball_to(winner, action_type="recovery")

    def _nearest_player_to_ball(self) -> PlayerState:
        players = self.home.xi + self.away.xi
        players.sort(key=lambda p: distance((p.x, p.y), (self.state.ball.x, self.state.ball.y)))
        return players[0]

    def _loose_ball_favorite(self) -> Optional[PlayerState]:
        ball = self.state.ball
        favorite = None
        best_score = -999.0
        for p in self.home.xi + self.away.xi:
            dist = distance((p.x, p.y), (ball.x, ball.y))
            momentum = self._side_forward_sign(p.side) * p.vx * 0.18
            bias = 0.8 if ball.loose_owner_bias == p.side else 0.0
            anticipation = p.profile.attributes.get("anticipation", p.profile.attributes["positioning"])
            acceleration = p.profile.attributes.get("acceleration", p.profile.attributes["pace"])
            score = -(dist * 1.1) + momentum + bias + anticipation / 60.0 + acceleration / 210.0
            if score > best_score:
                best_score = score
                favorite = p
        return favorite

    def _nearest_interceptor(self) -> Optional[PlayerState]:
        ball = self.state.ball
        receiver = self.find_player(ball.target_player_id)
        if not receiver:
            return None
        best: Optional[PlayerState] = None
        best_score = 999.0
        start = (ball.start_x, ball.start_y)
        end = (ball.target_x, ball.target_y)
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        line_len_sq = dx * dx + dy * dy
        if line_len_sq <= 0.01:
            return None
        for opp in self.opponents(ball.intended_side):
            t = ((opp.x - start[0]) * dx + (opp.y - start[1]) * dy) / line_len_sq
            if t < max(0.08, ball.travel_progress - 0.08) or t > min(0.98, ball.travel_progress + 0.22):
                continue
            proj_x = start[0] + dx * t
            proj_y = start[1] + dy * t
            lane_dist = distance((opp.x, opp.y), (proj_x, proj_y))
            ball_dist = distance((proj_x, proj_y), (ball.x, ball.y))
            score = lane_dist + ball_dist * 0.28
            if score < best_score:
                best_score = score
                best = opp
        return best

    def _check_for_interception(self) -> bool:
        ball = self.state.ball
        receiver = self.find_player(ball.target_player_id)
        interceptor = self._nearest_interceptor()
        if not receiver or interceptor is None:
            return False

        nearest_dist = distance((interceptor.x, interceptor.y), (ball.x, ball.y))
        receiver_dist = distance((receiver.x, receiver.y), (ball.x, ball.y))
        lane_advantage = receiver_dist - nearest_dist
        late_window = ball.travel_progress > 0.82
        threshold = 0.7 if late_window else 1.0

        if nearest_dist < 1.6 and lane_advantage > (threshold - 0.1):
            congestion = self._evaluate_pass_lane(self.find_player(ball.lead_player_id) or receiver, receiver, ball.pass_type)
            chance = (
                0.31
                + interceptor.profile.attributes["positioning"] / 260.0
                + interceptor.profile.attributes.get("anticipation", interceptor.profile.attributes["positioning"]) / 420.0
                + interceptor.profile.attributes["tackling"] / 320.0
                + clamp(lane_advantage / 3.5, 0.0, 0.25)
                + clamp(congestion / 10.0, 0.0, 0.16)
            )
            if late_window:
                chance -= 0.08
            if self.rng.random() < clamp(chance, 0.08, 0.86):
                attacking_goal_x = self._attacking_goal_x(ball.intended_side)
                near_goal_line = abs(ball.x - attacking_goal_x) < 4.2
                in_cross_box = ball.pass_type == "cross" and near_goal_line and 10.0 < ball.y < (PITCH_WIDTH - 10.0)
                if in_cross_box and self.rng.random() < 0.48:
                    if self.rng.random() < clamp(0.55 + self._event_frequency_boost("corner") * 0.18, 0.40, 0.88):
                        out_x = attacking_goal_x + self._side_forward_sign(ball.intended_side) * 1.2
                        out_y = clamp(ball.y + self.rng.uniform(-2.4, 2.4), 2.0, PITCH_WIDTH - 2.0)
                        self.state.last_touch_player_id = interceptor.profile.id
                        self.state.ball.x = out_x
                        self.state.ball.y = out_y
                        self._handle_ball_out(interceptor.side, out_x, out_y)
                        return True
                interceptor.x = lerp(interceptor.x, ball.x, 0.35)
                interceptor.y = lerp(interceptor.y, ball.y, 0.35)
                self._player_match_stats(interceptor)["interceptions"] += 1.0
                if interceptor.slot != "GK" and self._defending_goal_distance(interceptor) < 24.0:
                    self._player_match_stats(interceptor)["clearances"] += 1.0
                self._give_ball_to(interceptor, note=f"{interceptor.short_name} intercepts", action_type="interception")
                return True
        return False

    def _resolve_first_touch(self, receiver: PlayerState, nearest_opp: PlayerState) -> str:
        pressure = clamp(1.0 - distance((receiver.x, receiver.y), (nearest_opp.x, nearest_opp.y)) / 10.0, 0.0, 1.0)
        attrs = receiver.profile.attributes
        control = (
            0.44
            + (attrs["first_touch"] - 50.0) / 180.0
            + (attrs.get("technique", attrs["first_touch"]) - 50.0) / 220.0
            + (attrs["composure"] - 50.0) / 260.0
            + (attrs.get("balance", attrs["composure"]) - 50.0) / 260.0
            + self._receiver_space(receiver) * 0.05
            - pressure * 0.22
        )
        clean = clamp(control, 0.12, 0.82)
        slowed = clamp(0.30 + control * 0.35 - pressure * 0.08, 0.08, 0.50)
        contested = clamp(0.16 + pressure * 0.22 - control * 0.08, 0.04, 0.34)
        roll = self.rng.random()
        if roll < clean:
            return "clean"
        if roll < clean + slowed:
            return "slowed"
        if roll < clean + slowed + contested:
            return "contested"
        return "heavy"

    def _check_for_reception(self) -> bool:
        ball = self.state.ball
        receiver = self.find_player(ball.target_player_id)
        if not receiver:
            return False
        if ball.offside_flag:
            self._call_offside(receiver)
            return True
        receiver_dist = distance((receiver.x, receiver.y), (ball.x, ball.y))
        opps = self.opponents(receiver.side)
        nearest_opp = min(opps, key=lambda p: distance((p.x, p.y), (ball.x, ball.y)))
        opp_dist = distance((nearest_opp.x, nearest_opp.y), (ball.x, ball.y))

        catchable = 1.65 if ball.pass_type == "through_ball" else 1.45
        if receiver_dist < catchable and (receiver_dist <= opp_dist + 0.55 or ball.travel_progress >= 0.9):
            if ball.pass_type == "cross":
                attacking_goal_x = self._attacking_goal_x(receiver.side)
                if (
                    nearest_opp.slot != "GK"
                    and abs(ball.x - attacking_goal_x) < 6.0
                    and opp_dist < min(receiver_dist + 0.35, 2.2)
                    and self.rng.random() < clamp(0.28 + self._event_frequency_boost("corner") * 0.18, 0.18, 0.72)
                ):
                    out_x = attacking_goal_x + self._side_forward_sign(receiver.side) * 1.2
                    out_y = clamp(ball.y + self.rng.uniform(-2.5, 2.5), 2.0, PITCH_WIDTH - 2.0)
                    self.state.last_touch_player_id = nearest_opp.profile.id
                    self._handle_ball_out(nearest_opp.side, out_x, out_y)
                    return True
            outcome = self._resolve_first_touch(receiver, nearest_opp)
            if outcome == "clean":
                self._record_completed_pass(self.find_player(ball.lead_player_id))
                self._settle_ball_for_reception(receiver)
                if receiver.slot == "GK" and ball.pass_type == "cross":
                    self._record_goalkeeper_high_claim(receiver)
                self._give_ball_to(receiver, note=f"{receiver.short_name} receives", action_type="pass")
                receiver.control_cooldown = max(receiver.control_cooldown, 0.33)
            elif outcome == "slowed":
                self._record_completed_pass(self.find_player(ball.lead_player_id))
                self._settle_ball_for_reception(receiver)
                if receiver.slot == "GK" and ball.pass_type == "cross":
                    self._record_goalkeeper_high_claim(receiver)
                self._give_ball_to(receiver, note=f"{receiver.short_name} cushions it", action_type="pass")
                receiver.control_cooldown = 0.41
                self._set_render_state(receiver, "receiving", "slow_control")
            elif outcome == "contested":
                self.state.ball.mode = "loose"
                self.state.ball.carrier_id = None
                self.state.ball.loose_owner_bias = receiver.side
                self.state.possession = receiver.side
                self.state.last_action_type = "recovery"
                self.add_event(f"{receiver.short_name} under pressure")
            else:
                if (
                    ball.pass_type in ("cross", "progressive_ground", "switch")
                    and (receiver.y < 8.5 or receiver.y > (PITCH_WIDTH - 8.5))
                    and self.rng.random() < clamp(0.42 + self._event_frequency_boost("throw_in") * 0.20, 0.28, 0.88)
                ):
                    out_y = -0.8 if receiver.y < (PITCH_WIDTH / 2) else (PITCH_WIDTH + 0.8)
                    out_x = clamp(receiver.x + self._side_forward_sign(receiver.side) * 0.8, 1.0, PITCH_LENGTH - 1.0)
                    self.state.last_touch_player_id = receiver.profile.id
                    self._handle_ball_out(receiver.side, out_x, out_y)
                    return True
                sign = self._side_forward_sign(receiver.side)
                self.state.ball.mode = "loose"
                self.state.ball.carrier_id = None
                self.state.ball.x = clamp(receiver.x + sign * 1.4, -2.5, PITCH_LENGTH + 2.5)
                self.state.ball.y = clamp(receiver.y + self.rng.uniform(-1.4, 1.4), -2.5, PITCH_WIDTH + 2.5)
                self.state.ball.loose_owner_bias = nearest_opp.side if opp_dist < receiver_dist else receiver.side
                self.state.possession = self.state.ball.loose_owner_bias or receiver.side
                self.state.last_action_type = "recovery"
                self.add_event(f"Heavy touch from {receiver.short_name}")
            return True
        return False

    def _resolve_arrived_pass(self) -> None:
        receiver = self.find_player(self.state.ball.target_player_id)
        passer = self.find_player(self.state.ball.lead_player_id)
        if receiver:
            if self.state.ball.offside_flag:
                self._call_offside(receiver)
                return
            if self.state.ball.pass_type == "cross":
                nearest_def = min(self.opponents(receiver.side), key=lambda p: distance((p.x, p.y), (self.state.ball.x, self.state.ball.y)))
                attacking_goal_x = self._attacking_goal_x(receiver.side)
                if (
                    nearest_def.slot != "GK"
                    and abs(self.state.ball.x - attacking_goal_x) < 5.4
                    and distance((nearest_def.x, nearest_def.y), (self.state.ball.x, self.state.ball.y)) < 2.6
                    and self.rng.random() < clamp(0.42 + self._event_frequency_boost("corner") * 0.18, 0.28, 0.86)
                ):
                    out_x = attacking_goal_x + self._side_forward_sign(receiver.side) * 1.2
                    out_y = clamp(self.state.ball.y + self.rng.uniform(-2.5, 2.5), 2.0, PITCH_WIDTH - 2.0)
                    self.state.last_touch_player_id = nearest_def.profile.id
                    self._handle_ball_out(nearest_def.side, out_x, out_y)
                    return
            if distance((receiver.x, receiver.y), (self.state.ball.x, self.state.ball.y)) > 1.9:
                self.state.ball.mode = "loose"
                self.state.ball.carrier_id = None
                self.state.ball.loose_owner_bias = receiver.side
                receiver.target_x = self.state.ball.x
                receiver.target_y = self.state.ball.y
                self._start_run_commitment(receiver, self.state.ball.x, self.state.ball.y, "receiving", self.state.ball.pass_type, 0.45)
                return
            opps = self.opponents(receiver.side)
            nearest_opp = min(opps, key=lambda p: distance((p.x, p.y), (receiver.x, receiver.y)))
            outcome = self._resolve_first_touch(receiver, nearest_opp)
            if outcome in ("clean", "slowed"):
                if passer and passer.side == receiver.side:
                    self.state.assist_candidate_id = passer.profile.id
                self._record_completed_pass(passer)
                self._settle_ball_for_reception(receiver)
                if receiver.slot == "GK" and self.state.ball.pass_type == "cross":
                    self._record_goalkeeper_high_claim(receiver)
                self._give_ball_to(receiver, note=f"{receiver.short_name} collects", action_type="pass")
                if outcome == "slowed":
                    receiver.control_cooldown = 0.40
                else:
                    receiver.control_cooldown = max(receiver.control_cooldown, 0.34)
            else:
                self.state.assist_candidate_id = None
                self.state.ball.mode = "loose"
                self.state.ball.carrier_id = None
                self.state.ball.loose_owner_bias = receiver.side if outcome == "contested" else nearest_opp.side
        else:
            self.state.assist_candidate_id = None
            self.state.ball.mode = "loose"
            self.state.ball.carrier_id = None

    def _resolve_arrived_shot(self) -> None:
        shooter = self.find_player(self.state.last_touch_player_id)
        if not shooter:
            self.state.ball.mode = "loose"
            self.state.ball.carrier_id = None
            return

        defending_side = "away" if shooter.side == "home" else "home"
        keeper = self._goalkeeper(defending_side)
        outcome = self.state.ball.shot_outcome or self._decide_shot_outcome(shooter, keeper)
        self.state.ball.shot_outcome = None
        if outcome == "goal":
            self.state.player_goals[shooter.profile.id] = self.state.player_goals.get(shooter.profile.id, 0) + 1
            self._record_goal(shooter)
            self._record_goalkeeper_goal_conceded(keeper)
            assister_id = self.state.assist_candidate_id
            if assister_id and assister_id != shooter.profile.id:
                assister = self.find_player(assister_id)
                if assister and assister.side == shooter.side:
                    self.state.player_assists[assister_id] = self.state.player_assists.get(assister_id, 0) + 1
                    self._record_assist(assister)
            if shooter.side == "home":
                self.state.home_score += 1
            else:
                self.state.away_score += 1
            self.add_event(f"GOAL! {shooter.short_name} scores")
            self._start_goal_celebration(shooter)
            return
        self.state.assist_candidate_id = None
        if outcome == "save":
            self._record_goalkeeper_save(keeper)
            self._give_ball_to(keeper, note=f"{keeper.short_name} saves", action_type="recovery")
            return
        if outcome == "save_out":
            self._record_goalkeeper_save(keeper)
            out_x = self._attacking_goal_x(shooter.side) + self._side_forward_sign(shooter.side) * 1.2
            out_y = clamp(self.state.ball.target_y + self.rng.uniform(-2.0, 2.0), 2.0, PITCH_WIDTH - 2.0)
            self.state.last_touch_player_id = keeper.profile.id
            self._handle_ball_out(keeper.side, out_x, out_y)
            return
        defenders = [p for p in self.teammates(defending_side) if p.slot != "GK"]
        nearest_defender = min(defenders, key=lambda p: distance((p.x, p.y), (shooter.x, shooter.y)))
        attack_sign = self._side_forward_sign(shooter.side)
        if (
            self._goal_distance(shooter) < 24.0
            and self._pressure_on_player(shooter) > 0.32
            and distance((nearest_defender.x, nearest_defender.y), (shooter.x, shooter.y)) < 8.0
            and (nearest_defender.x - shooter.x) * attack_sign > -1.5
            and self.rng.random() < clamp(0.34 + self._event_frequency_boost("corner") * 0.18, 0.22, 0.76)
        ):
            out_x = self._attacking_goal_x(shooter.side) + self._side_forward_sign(shooter.side) * 1.2
            out_y = clamp(self.state.ball.target_y, 2.0, PITCH_WIDTH - 2.0)
            self.state.last_touch_player_id = nearest_defender.profile.id
            self._handle_ball_out(nearest_defender.side, out_x, out_y)
            return
        self._start_goal_kick_setup(defending_side, shot_out_position=(self.state.ball.target_x, self.state.ball.target_y))

    def _start_goal_celebration(self, scorer: PlayerState) -> None:
        scoring_side = scorer.side
        self.state.celebration_timer = GOAL_CELEBRATION_SECONDS
        self.state.celebration_side = scoring_side
        self.state.celebration_scorer_id = scorer.profile.id
        self.state.assist_candidate_id = None
        self.state.pending_kickoff_side = "away" if scoring_side == "home" else "home"
        self.state.goal_banner_text = (
            f"GOAL {self.state.minute:02d}:{self.state.second:02d}  {scorer.short_name}"
        )
        self.state.ball.mode = "loose"
        self.state.ball.carrier_id = None
        self.state.ball.target_player_id = None
        self.state.ball.x = PITCH_LENGTH / 2
        self.state.ball.y = PITCH_WIDTH / 2
        self.state.ball.target_x = self.state.ball.x
        self.state.ball.target_y = self.state.ball.y
        self.state.ball.prev_x = self.state.ball.x
        self.state.ball.prev_y = self.state.ball.y
        corner_x = PITCH_LENGTH - 7.0 if scoring_side == "home" else 7.0
        corner_y = 8.0
        for player in self.home.xi + self.away.xi:
            player.has_ball = False
            player.control_cooldown = 0.0
            if player.side == scoring_side:
                spread_x = self.rng.uniform(-4.0, 2.0)
                spread_y = self.rng.uniform(-2.0, 5.0)
                player.target_x = clamp(corner_x + spread_x, 2, PITCH_LENGTH - 2)
                player.target_y = clamp(corner_y + spread_y, 2, PITCH_WIDTH - 2)
                self._set_render_state(player, "celebrate", "goal")
            else:
                player.target_x = lerp(player.x, player.home_x, 0.55)
                player.target_y = lerp(player.y, player.home_y, 0.55)
                self._set_render_state(player, "shape", "reset")
        scorer.target_x = clamp(corner_x, 2, PITCH_LENGTH - 2)
        scorer.target_y = clamp(corner_y + 1.0, 2, PITCH_WIDTH - 2)
        self._set_render_state(scorer, "celebrate", "scorer")

    def _update_goal_celebration(self) -> None:
        self.state.celebration_timer = max(0.0, self.state.celebration_timer - SLICE_SECONDS)
        self._move_players()
        self._update_render_states()
        if self.state.celebration_timer <= 0:
            kickoff_side = self.state.pending_kickoff_side or "home"
            self._start_kickoff_setup(kickoff_side)

    def _update_restart_sequence(self) -> None:
        self.state.restart_timer = max(0.0, self.state.restart_timer - SLICE_SECONDS)
        self._move_players()
        if self.state.restart_timer > 0:
            return
        if self.state.restart_mode == "kickoff_setup":
            self._snap_players_to_targets()
            self._execute_kickoff()
        elif self.state.restart_mode == "goal_kick_setup":
            self._snap_players_to_targets()
            self._execute_goal_kick()
        elif self.state.restart_mode == "throw_in_setup":
            self._snap_players_to_targets()
            self._execute_throw_in()
        elif self.state.restart_mode == "corner_setup":
            self._snap_players_to_targets()
            self._execute_corner()
        elif self.state.restart_mode == "offside_restart_setup":
            self._snap_players_to_targets()
            self._execute_offside_restart()
        elif self.state.restart_mode == "direct_free_kick_setup":
            self._snap_players_to_targets()
            self._execute_direct_free_kick()
        elif self.state.restart_mode == "penalty_setup":
            self._snap_players_to_targets()
            self._execute_penalty()

    def _start_kickoff_setup(self, kickoff_side: str, opening: bool = False, immediate: bool = False) -> None:
        if immediate:
            self._prepare_kickoff_positions(kickoff_side, opening=opening)
        else:
            self._prepare_kickoff_transition(kickoff_side, opening=opening)
        if immediate:
            self._execute_kickoff()
            return
        self.state.restart_mode = "kickoff_setup"
        self.state.restart_timer = KICKOFF_SETUP_SECONDS

    def _pick_restart_player(self, side: str, preferred_slots: Tuple[str, ...], exclude_id: Optional[str] = None) -> PlayerState:
        players = [p for p in self.teammates(side) if not p.red_card and p.profile.id != exclude_id]
        for slot in preferred_slots:
            for player in players:
                if player.slot == slot:
                    return player
        if players:
            return players[0]
        return next(p for p in self.teammates(side) if p.profile.id != exclude_id)

    def _kickoff_layout(self, kickoff_side: str) -> Dict[str, Tuple[float, float]]:
        snapshot = {
            p.profile.id: (p.x, p.y, p.prev_x, p.prev_y, p.target_x, p.target_y)
            for p in self.home.xi + self.away.xi
        }
        self._place_team_for_kickoff(kickoff_side)
        striker = self._pick_restart_player(kickoff_side, ("ST", "AM", "CM", "LW", "RW"))
        support = self._pick_restart_player(kickoff_side, ("AM", "CM", "DM", "LW", "RW"), exclude_id=striker.profile.id)
        striker.x = PITCH_LENGTH / 2
        striker.y = PITCH_WIDTH / 2
        support.x = PITCH_LENGTH / 2 - self._side_forward_sign(kickoff_side) * 8.5
        support.y = PITCH_WIDTH / 2 + 7.5
        self._resolve_kickoff_overlaps(kickoff_side, striker.profile.id)
        layout = {p.profile.id: (p.x, p.y) for p in self.home.xi + self.away.xi}
        for p in self.home.xi + self.away.xi:
            x, y, prev_x, prev_y, target_x, target_y = snapshot[p.profile.id]
            p.x = x
            p.y = y
            p.prev_x = prev_x
            p.prev_y = prev_y
            p.target_x = target_x
            p.target_y = target_y
        return layout

    def _prepare_kickoff_transition(self, kickoff_side: str, opening: bool = False) -> None:
        self._prepare_players_for_restart_motion()
        self.state.restart_side = kickoff_side
        self.state.ball.mode = "loose"
        self.state.ball.carrier_id = None
        self.state.ball.target_player_id = None
        self.state.ball.x = PITCH_LENGTH / 2
        self.state.ball.y = PITCH_WIDTH / 2
        self.state.ball.prev_x = self.state.ball.x
        self.state.ball.prev_y = self.state.ball.y
        self.state.ball.target_x = self.state.ball.x
        self.state.ball.target_y = self.state.ball.y

        desired = self._kickoff_layout(kickoff_side)
        for player in self.home.xi + self.away.xi:
            player.target_x, player.target_y = desired[player.profile.id]
            self._set_render_state(player, "restart", "kickoff_walk")
        if opening:
            self.add_event(f"{self.home.name} kick off")

    def _place_team_for_kickoff(self, kickoff_side: str) -> None:
        centre_x = PITCH_LENGTH / 2
        centre_y = PITCH_WIDTH / 2
        circle_radius = 10.2
        for side in ("home", "away"):
            for player in self.teammates(side):
                own_right = self._side_forward_sign(player.side) < 0
                if side == kickoff_side:
                    player.x = max(player.home_x, centre_x) if own_right else min(player.home_x, centre_x)
                else:
                    player.x = max(player.home_x, centre_x + 0.8) if own_right else min(player.home_x, centre_x - 0.8)
                    dx = player.x - centre_x
                    dy = player.home_y - centre_y
                    dist = math.hypot(dx, dy)
                    if dist < circle_radius:
                        if dist < 0.01:
                            dy = -circle_radius
                            dist = circle_radius
                        scale = circle_radius / dist
                        player.x = centre_x + dx * scale
                        player.y = centre_y + dy * scale
                    else:
                        player.y = player.home_y
                    player.x = max(player.x, centre_x + 0.8) if own_right else min(player.x, centre_x - 0.8)
                if side == kickoff_side:
                    player.y = player.home_y
                player.prev_x = player.x
                player.prev_y = player.y
                player.target_x = player.x
                player.target_y = player.y

    def _resolve_kickoff_overlaps(self, kickoff_side: str, kicker_id: str) -> None:
        centre_x = PITCH_LENGTH / 2
        centre_y = PITCH_WIDTH / 2
        protected_radius = 5.0
        opposition_circle_radius = 10.2
        players = self.home.xi + self.away.xi

        for player in players:
            if player.profile.id == kicker_id:
                continue
            own_right = self._side_forward_sign(player.side) < 0
            dist_to_centre = distance((player.x, player.y), (centre_x, centre_y))
            if dist_to_centre < protected_radius:
                dx = player.x - centre_x
                dy = player.y - centre_y
                if abs(dx) < 0.01 and abs(dy) < 0.01:
                    dx = 1.0 if own_right else -1.0
                    dy = 0.6 if player.side == kickoff_side else -0.6
                mag = math.hypot(dx, dy) or 1.0
                player.x = clamp(centre_x + dx / mag * protected_radius, 2, PITCH_LENGTH - 2)
                player.y = clamp(centre_y + dy / mag * protected_radius, 2, PITCH_WIDTH - 2)
                if player.side != kickoff_side:
                    player.x = max(player.x, centre_x + 0.8) if own_right else min(player.x, centre_x - 0.8)
                else:
                    player.x = max(player.x, centre_x) if own_right else min(player.x, centre_x)

        for _ in range(3):
            moved = False
            for idx, player in enumerate(players):
                for other in players[idx + 1:]:
                    if distance((player.x, player.y), (other.x, other.y)) >= 1.55:
                        continue
                    dx = other.x - player.x
                    dy = other.y - player.y
                    if abs(dx) < 0.01 and abs(dy) < 0.01:
                        dx = 0.9 if other.side == "away" else -0.9
                        dy = 0.7 if other.slot in ("CM", "AM", "DM") else -0.7
                    mag = math.hypot(dx, dy) or 1.0
                    push_x = dx / mag * 1.0
                    push_y = dy / mag * 1.0
                    player.x = clamp(player.x - push_x, 2, PITCH_LENGTH - 2)
                    player.y = clamp(player.y - push_y, 2, PITCH_WIDTH - 2)
                    other.x = clamp(other.x + push_x, 2, PITCH_LENGTH - 2)
                    other.y = clamp(other.y + push_y, 2, PITCH_WIDTH - 2)
                    if player.profile.id != kicker_id:
                        player.x = max(player.x, centre_x) if self._side_forward_sign(player.side) < 0 else min(player.x, centre_x)
                    if other.profile.id != kicker_id:
                        other.x = max(other.x, centre_x) if self._side_forward_sign(other.side) < 0 else min(other.x, centre_x)
                    moved = True
            if not moved:
                break

        for player in players:
            if player.side == kickoff_side or player.profile.id == kicker_id:
                continue
            own_right = self._side_forward_sign(player.side) < 0
            dx = player.x - centre_x
            dy = player.y - centre_y
            dist = math.hypot(dx, dy)
            if dist < opposition_circle_radius:
                if dist < 0.01:
                    dx = 1.0 if own_right else -1.0
                    dy = 0.0
                    dist = 1.0
                scale = opposition_circle_radius / dist
                player.x = clamp(centre_x + dx * scale, 2, PITCH_LENGTH - 2)
                player.y = clamp(centre_y + dy * scale, 2, PITCH_WIDTH - 2)
                player.x = max(player.x, centre_x + 0.8) if own_right else min(player.x, centre_x - 0.8)

        for player in players:
            player.prev_x = player.x
            player.prev_y = player.y
            player.target_x = player.x
            player.target_y = player.y

    def _snap_players_to_targets(self) -> None:
        for player in self.home.xi + self.away.xi:
            player.x = player.target_x
            player.y = player.target_y
            player.prev_x = player.x
            player.prev_y = player.y

    def _execute_kickoff(self) -> None:
        kickoff_side = self.state.restart_side or "home"
        striker = self._pick_restart_player(kickoff_side, ("ST", "AM", "CM", "LW", "RW"))
        support = self._pick_restart_player(kickoff_side, ("AM", "CM", "DM", "LW", "RW"), exclude_id=striker.profile.id)
        self.state.restart_mode = None
        self.state.restart_timer = 0.0
        self.state.restart_side = None
        self._give_ball_to(striker, action_type="recovery")
        self._start_pass(striker, support, "kickoff pass", "short_ground")
        self._start_run_commitment(striker, striker.home_x, striker.home_y, "recover", "kickoff_recover", self._run_commit_duration(striker, "recover", "kickoff_recover"))
        self._derive_match_context()

    def _start_goal_kick_setup(self, side: str, shot_out_position: Optional[Tuple[float, float]] = None) -> None:
        self._prepare_players_for_restart_motion()
        self.state.restart_mode = "goal_kick_setup"
        self.state.restart_timer = GOAL_KICK_SETUP_SECONDS
        self.state.restart_side = side
        keeper = self._goalkeeper(side)
        defend_goal_x = self._defending_goal_x(side)
        spot_x = 6.0 if defend_goal_x == 0.0 else PITCH_LENGTH - 6.0
        spot_y = PITCH_WIDTH / 2
        self.state.ball.mode = "loose"
        self.state.ball.carrier_id = None
        self.state.ball.target_player_id = None
        if shot_out_position is not None:
            self.state.ball.x, self.state.ball.y = shot_out_position
        else:
            self.state.ball.x = spot_x
            self.state.ball.y = spot_y
        self.state.ball.prev_x = self.state.ball.x
        self.state.ball.prev_y = self.state.ball.y
        self.state.ball.target_x = self.state.ball.x
        self.state.ball.target_y = self.state.ball.y
        keeper.target_x = spot_x
        keeper.target_y = spot_y
        self._set_render_state(keeper, "restart", "goal_kick")
        for teammate in self.teammates(side):
            if teammate.slot in ("CB", "LB", "RB", "DM"):
                teammate.target_x = clamp(teammate.home_x + self._side_forward_sign(side) * 2.5, 2, PITCH_LENGTH - 2)
                teammate.target_y = teammate.home_y
                self._set_render_state(teammate, "restart", "goal_kick_shape")
        for opp in self.opponents(side):
            opp.target_x = clamp(opp.home_x - self._side_forward_sign(side) * 4.0, 2, PITCH_LENGTH - 2)
            opp.target_y = opp.home_y
            self._set_render_state(opp, "restart", "goal_kick_press")

    def _execute_goal_kick(self) -> None:
        side = self.state.restart_side or "home"
        keeper = self._goalkeeper(side)
        self.state.ball.x = keeper.x
        self.state.ball.y = keeper.y
        self.state.ball.prev_x = keeper.x
        self.state.ball.prev_y = keeper.y
        self.state.ball.target_x = keeper.x
        self.state.ball.target_y = keeper.y
        target = max(
            [p for p in self.teammates(side) if p.slot in ("DM", "CB", "LB", "RB") and p.profile.id != keeper.profile.id],
            key=lambda p: self._receiver_space(p) + p.profile.attributes["first_touch"] / 30.0,
        )
        self.state.restart_mode = None
        self.state.restart_timer = 0.0
        self.state.restart_side = None
        self._give_ball_to(keeper, note="Goal kick", action_type="recovery")
        self._start_pass(keeper, target, "goal kick", "short_ground")
        self._derive_match_context()

    def _reset_players_for_restart(self) -> None:
        self.state.recent_turnover_seconds = 0.0
        self.state.celebration_timer = 0.0
        self.state.celebration_side = None
        self.state.celebration_scorer_id = None
        self.state.pending_kickoff_side = None
        self.state.goal_banner_text = None
        self.state.restart_taker_id = None
        self.state.fouled_player_id = None
        self.state.ball.pass_type = "short_ground"
        self.state.ball.shot_outcome = None
        for team in (self.home, self.away):
            for p in team.xi:
                p.x = p.home_x
                p.y = p.home_y
                p.prev_x = p.x
                p.prev_y = p.y
                p.target_x = p.home_x
                p.target_y = p.home_y
                p.has_ball = False
                p.control_cooldown = 0.0
                p.vx = 0.0
                p.vy = 0.0
                p.render_state = "shape"
                p.run_intent = None
                p.run_commit_timer = 0.0
                p.commit_target_x = None
                p.commit_target_y = None

    def _prepare_players_for_restart_motion(self) -> None:
        self.state.recent_turnover_seconds = 0.0
        self.state.celebration_timer = 0.0
        self.state.celebration_side = None
        self.state.celebration_scorer_id = None
        self.state.pending_kickoff_side = None
        self.state.goal_banner_text = None
        self.state.restart_taker_id = None
        self.state.fouled_player_id = None
        self.state.ball.pass_type = "short_ground"
        self.state.ball.shot_outcome = None
        for team in (self.home, self.away):
            for p in team.xi:
                p.has_ball = False
                p.control_cooldown = 0.0
                p.vx = 0.0
                p.vy = 0.0
                p.render_state = "shape"
                p.run_intent = None
                p.run_commit_timer = 0.0
                p.commit_target_x = None
                p.commit_target_y = None

    def _reset_ball_for_restart(self, x: float, y: float) -> None:
        self.state.ball.mode = "loose"
        self.state.ball.carrier_id = None
        self.state.ball.target_player_id = None
        self.state.ball.offside_flag = False
        self.state.ball.x = x
        self.state.ball.y = y
        self.state.ball.prev_x = x
        self.state.ball.prev_y = y
        self.state.ball.target_x = x
        self.state.ball.target_y = y

    def _restart_taker_candidates(self, side: str) -> List[PlayerState]:
        return [p for p in self.teammates(side) if p.slot != "GK"] or self.teammates(side)

    def _pick_restart_receiver(self, side: str, taker: PlayerState, allowed_slots: Tuple[str, ...]) -> PlayerState:
        options = [p for p in self.teammates(side) if p.profile.id != taker.profile.id and p.slot in allowed_slots]
        if not options:
            options = [p for p in self.teammates(side) if p.profile.id != taker.profile.id]
        return max(
            options,
            key=lambda p: self._receiver_space(p) + p.profile.attributes["first_touch"] / 25.0,
        )

    def _start_offside_restart(self, defending_side: str, taker: PlayerState, x: float, y: float, offender_name: str) -> None:
        self._prepare_players_for_restart_motion()
        self.state.restart_mode = "offside_restart_setup"
        self.state.restart_timer = OFFSIDE_SETUP_SECONDS
        self.state.restart_side = defending_side
        self.state.offsides_count += 1
        self._team_match_stats("away" if defending_side == "home" else "home")["offsides"] += 1.0
        x = clamp(x, 5.0, PITCH_LENGTH - 5.0)
        y = clamp(y, 5.0, PITCH_WIDTH - 5.0)
        self._reset_ball_for_restart(x, y)
        taker.target_x = x
        taker.target_y = y
        self._set_render_state(taker, "restart", "offside")
        sign = self._side_forward_sign(defending_side)
        for teammate in self.teammates(defending_side):
            if teammate.profile.id == taker.profile.id:
                continue
            teammate.target_x = clamp(teammate.home_x + sign * 2.0, 2, PITCH_LENGTH - 2)
            teammate.target_y = teammate.home_y
            self._set_render_state(teammate, "restart", "offside_shape")
        for opp in self.opponents(defending_side):
            opp.target_x = clamp(opp.home_x - sign * 3.5, 2, PITCH_LENGTH - 2)
            opp.target_y = opp.home_y
            self._set_render_state(opp, "restart", "offside_retreat")
        self.add_event(f"Offside against {offender_name}")

    def _execute_offside_restart(self) -> None:
        side = self.state.restart_side or "home"
        spot = (self.state.ball.x, self.state.ball.y)
        taker = min(self.teammates(side), key=lambda p: distance((p.x, p.y), spot))
        receiver = self._pick_restart_receiver(side, taker, ("DM", "CB", "LB", "RB", "CM"))
        self.state.restart_mode = None
        self.state.restart_timer = 0.0
        self.state.restart_side = None
        self._give_ball_to(taker, note="Offside free kick", action_type="recovery")
        self._start_pass(taker, receiver, "offside restart", "short_ground")

    def _start_throw_in_setup(self, side: str, x: float, y: float) -> None:
        self._prepare_players_for_restart_motion()
        self.state.restart_mode = "throw_in_setup"
        self.state.restart_timer = THROW_IN_SETUP_SECONDS
        self.state.restart_side = side
        self.state.throw_ins_count += 1
        y = 1.0 if y < PITCH_WIDTH / 2 else PITCH_WIDTH - 1.0
        x = clamp(x, 3.0, PITCH_LENGTH - 3.0)
        self._reset_ball_for_restart(x, y)
        taker = max(
            self._restart_taker_candidates(side),
            key=lambda p: p.profile.attributes.get("long_throws", p.profile.attributes["passing"]) - distance((p.x, p.y), (x, y)) * 0.45,
        )
        taker.target_x = x
        taker.target_y = y
        self._set_render_state(taker, "restart", "throw_in")
        sign = self._side_forward_sign(side)
        close_options = sorted(
            [p for p in self.teammates(side) if p.profile.id != taker.profile.id and p.slot != "GK"],
            key=lambda p: (
                p.slot not in ("LB", "RB", "CM", "DM", "LW", "RW"),
                distance((p.home_x, p.home_y), (x, y)),
            ),
        )[:3]
        close_ids = {p.profile.id for p in close_options}
        for teammate in self.teammates(side):
            if teammate.profile.id == taker.profile.id:
                continue
            if teammate.profile.id in close_ids:
                lane_bias = -4.0 if teammate.home_y < PITCH_WIDTH / 2 else 4.0
                depth_bias = 5.0 + abs(teammate.home_x - x) * 0.08
                teammate.target_x = clamp(x + sign * depth_bias, 2, PITCH_LENGTH - 2)
                teammate.target_y = clamp(y + lane_bias, 3.0, PITCH_WIDTH - 3.0)
                self._set_render_state(teammate, "restart", "throw_in_option")
            elif teammate.slot == "GK":
                teammate.target_x = teammate.home_x
                teammate.target_y = teammate.home_y
                self._set_render_state(teammate, "restart", "throw_in_reset")
            else:
                teammate.target_x = clamp(lerp(teammate.home_x, x, 0.12), 2, PITCH_LENGTH - 2)
                teammate.target_y = clamp(lerp(teammate.home_y, y, 0.08), 3.0, PITCH_WIDTH - 3.0)
                self._set_render_state(teammate, "restart", "throw_in_shape")
        for opp in self.opponents(side):
            opp.target_x = clamp(opp.home_x - sign * 2.5, 2, PITCH_LENGTH - 2)
            opp.target_y = clamp(lerp(opp.home_y, y, 0.15), 2, PITCH_WIDTH - 2)
            self._set_render_state(opp, "restart", "throw_in_mark")
        self.add_event(f"{self._team_state(side).name} throw in")

    def _execute_throw_in(self) -> None:
        side = self.state.restart_side or "home"
        spot = (self.state.ball.x, self.state.ball.y)
        taker = min(self.teammates(side), key=lambda p: distance((p.x, p.y), spot))
        set_piece_mode = self._instruction_value(side, "set_pieces")
        if set_piece_mode == "direct":
            receiver = self._pick_restart_receiver(side, taker, ("ST", "LW", "RW", "AM", "CM"))
            pass_type = "progressive_ground"
        else:
            receiver = self._pick_restart_receiver(side, taker, ("CM", "AM", "DM", "LW", "RW", "ST", "LB", "RB"))
            pass_type = "short_ground"
        self.state.restart_mode = None
        self.state.restart_timer = 0.0
        self.state.restart_side = None
        self._give_ball_to(taker, note="Throw in", action_type="recovery")
        self._start_pass(taker, receiver, "throw in", pass_type)

    def _start_corner_setup(self, attacking_side: str, x: float, y: float) -> None:
        self._prepare_players_for_restart_motion()
        self.state.restart_mode = "corner_setup"
        self.state.restart_timer = CORNER_SETUP_SECONDS
        self.state.restart_side = attacking_side
        self.state.corners_count += 1
        self._team_match_stats(attacking_side)["corners"] += 1.0
        x = 0.5 if self._attacking_goal_x(attacking_side) == 0.0 else PITCH_LENGTH - 0.5
        y = 0.5 if y < PITCH_WIDTH / 2 else PITCH_WIDTH - 0.5
        self._reset_ball_for_restart(x, y)
        wide_candidates = [p for p in self._restart_taker_candidates(attacking_side) if p.slot in ("LW", "RW", "LB", "RB", "AM")]
        taker_pool = wide_candidates or self._restart_taker_candidates(attacking_side)
        taker = max(
            taker_pool,
            key=lambda p: self._corner_taker_score(p) - distance((p.x, p.y), (x, y)) * 0.55,
        )
        taker.target_x = x
        taker.target_y = y
        self._set_render_state(taker, "restart", "corner")
        attack_sign = self._side_forward_sign(attacking_side)
        corner_from_top = y < PITCH_WIDTH / 2
        box_x = self._attacking_goal_x(attacking_side) - attack_sign * 8.0
        attackers = [p for p in self.teammates(attacking_side) if p.profile.id != taker.profile.id and p.slot != "GK"]
        stay_back_slots = {"LB", "RB", "DM"}
        stay_back = [p for p in attackers if p.slot in stay_back_slots]
        attack_group = [p for p in attackers if p.profile.id not in {p2.profile.id for p2 in stay_back}]
        priority_y = [PITCH_WIDTH / 2 - 6.0, PITCH_WIDTH / 2, PITCH_WIDTH / 2 + 6.0, PITCH_WIDTH / 2 - 11.0, PITCH_WIDTH / 2 + 11.0]
        priority_x = [box_x - attack_sign * 1.5, box_x, box_x + attack_sign * 1.5, box_x - attack_sign * 4.0, box_x - attack_sign * 6.0]
        ordered = sorted(attack_group, key=lambda p: (p.slot not in ("ST", "AM", "CB"), -p.profile.attributes["positioning"]))
        for idx, teammate in enumerate(ordered):
            tx = clamp(priority_x[min(idx, len(priority_x) - 1)], 2, PITCH_LENGTH - 2)
            ty = clamp(priority_y[min(idx, len(priority_y) - 1)] + (-2.0 if corner_from_top else 2.0) * (0.4 if idx > 2 else 0.0), 4.0, PITCH_WIDTH - 4.0)
            teammate.target_x = tx
            teammate.target_y = ty
            self._set_render_state(teammate, "restart", "corner_attack")
        safety_x = box_x - attack_sign * 22.0
        safety_y = PITCH_WIDTH / 2
        for idx, teammate in enumerate(sorted(stay_back, key=lambda p: p.home_y)):
            teammate.target_x = clamp(safety_x - attack_sign * (idx * 4.0), 8.0, PITCH_LENGTH - 8.0)
            teammate.target_y = clamp(safety_y + (-8.0 + idx * 8.0), 8.0, PITCH_WIDTH - 8.0)
            self._set_render_state(teammate, "restart", "corner_cover")
        atk_gk = self._goalkeeper(attacking_side)
        atk_gk.target_x = clamp(self._defending_goal_x(attacking_side) + self._side_forward_sign(attacking_side) * 3.5, 4.0, PITCH_LENGTH - 4.0)
        atk_gk.target_y = PITCH_WIDTH / 2
        self._set_render_state(atk_gk, "restart", "corner_reset")
        defenders = self.opponents(attacking_side)
        for idx, defender in enumerate(sorted(defenders, key=lambda p: p.slot == "GK")):
            if defender.slot == "GK":
                defender.target_x = clamp(self._defending_goal_x(defender.side) + self._side_forward_sign(defender.side) * 2.5, 2, PITCH_LENGTH - 2)
                defender.target_y = PITCH_WIDTH / 2
            else:
                defender.target_x = clamp(box_x - attack_sign * (2.0 + (idx % 3) * 1.5), 2, PITCH_LENGTH - 2)
                defender.target_y = clamp((PITCH_WIDTH / 2) + (-7.0 + idx * 3.2), 4, PITCH_WIDTH - 4)
            self._set_render_state(defender, "restart", "corner_defend")
        self.add_event(f"{self._team_state(attacking_side).name} corner")

    def _execute_corner(self) -> None:
        side = self.state.restart_side or "home"
        set_piece_mode = self._instruction_value(side, "set_pieces")
        taker = min(self.teammates(side), key=lambda p: distance((p.x, p.y), (self.state.ball.x, self.state.ball.y)))
        short_pool = [
            p for p in self.teammates(side)
            if p.profile.id != taker.profile.id and p.slot in ("LW", "RW", "LB", "RB", "AM")
            and distance((p.x, p.y), (self.state.ball.x, self.state.ball.y)) < 18.0
        ]
        target_pool = [p for p in self.teammates(side) if p.profile.id != taker.profile.id and p.slot in ("ST", "AM", "CB", "CM")]
        if not target_pool:
            target_pool = [p for p in self.teammates(side) if p.profile.id != taker.profile.id and p.slot != "GK"]
        receiver = max(target_pool, key=lambda p: self._aerial_target_score(p) + self._receiver_space(p) * 18.0)
        short_chance = 0.18 + max(0.0, (self._tactic_value(side, "crossing") - 55.0) / -220.0)
        if set_piece_mode == "possession":
            short_chance += 0.35
        elif set_piece_mode == "direct":
            short_chance -= 0.10
        use_short = bool(short_pool) and self.rng.random() < clamp(short_chance, 0.08, 0.62)
        if use_short:
            receiver = max(
                short_pool,
                key=lambda p: p.profile.attributes["first_touch"] + p.profile.attributes["passing"] + self._receiver_space(p) * 18.0,
            )
        self.state.restart_mode = None
        self.state.restart_timer = 0.0
        self.state.restart_side = None
        self._give_ball_to(taker, note="Corner", action_type="recovery")
        if use_short:
            self._start_pass(taker, receiver, "short corner", "short_ground")
        else:
            self._start_pass(taker, receiver, "corner", "cross")

    def _ball_last_touch_side(self) -> Optional[str]:
        player = self.find_player(self.state.last_touch_player_id)
        return player.side if player else None

    def _ball_is_out_of_bounds(self, x: float, y: float) -> bool:
        return x < 0.0 or x > PITCH_LENGTH or y < 0.0 or y > PITCH_WIDTH

    def _handle_ball_out(self, last_touch_side: Optional[str], x: float, y: float) -> None:
        if last_touch_side is None:
            last_touch_side = self.state.possession
        self.state.ball.mode = "loose"
        self.state.ball.carrier_id = None
        self.state.ball.target_player_id = None
        if y < 0.0 or y > PITCH_WIDTH:
            restart_side = "away" if last_touch_side == "home" else "home"
            self._start_throw_in_setup(restart_side, clamp(x, 1.0, PITCH_LENGTH - 1.0), y)
            return
        if x < 0.0 or x > PITCH_LENGTH:
            defending_side = self._goal_line_defending_side(x)
            if last_touch_side == defending_side:
                attacking_side = "away" if defending_side == "home" else "home"
                self._start_corner_setup(attacking_side, x, clamp(y, 1.0, PITCH_WIDTH - 1.0))
            else:
                self._start_goal_kick_setup(defending_side, shot_out_position=(x, clamp(y, 1.0, PITCH_WIDTH - 1.0)))

    def _snap_players_to_targets(self) -> None:
        for player in self.home.xi + self.away.xi:
            player.x = player.target_x
            player.y = player.target_y
            player.prev_x = player.x
            player.prev_y = player.y

    def _prepare_kickoff_transition(self, kickoff_side: str, opening: bool = False) -> None:
        self._prepare_players_for_restart_motion()
        self.state.restart_side = kickoff_side
        self.state.ball.mode = "loose"
        self.state.ball.carrier_id = None
        self.state.ball.target_player_id = None
        self.state.ball.x = PITCH_LENGTH / 2
        self.state.ball.y = PITCH_WIDTH / 2
        self.state.ball.prev_x = self.state.ball.x
        self.state.ball.prev_y = self.state.ball.y
        self.state.ball.target_x = self.state.ball.x
        self.state.ball.target_y = self.state.ball.y

        desired = self._kickoff_layout(kickoff_side)
        for player in self.home.xi + self.away.xi:
            tx, ty = desired[player.profile.id]
            player.target_x = tx
            player.target_y = ty
            self._set_render_state(player, "restart", "kickoff_walk")
        if opening:
            self.add_event(f"{self.home.name} kick off")

    def _settle_ball_for_reception(self, receiver: PlayerState) -> None:
        ball = self.state.ball
        ball.x = clamp(lerp(ball.x, receiver.x, 0.78), 2, PITCH_LENGTH - 2)
        ball.y = clamp(lerp(ball.y, receiver.y, 0.78), 2, PITCH_WIDTH - 2)
        ball.prev_x = ball.x
        ball.prev_y = ball.y

    def _keeper_collection_point(self, keeper: PlayerState, shooter_side: str) -> Tuple[float, float]:
        step = -self._side_forward_sign(shooter_side)
        x = clamp(keeper.x + step * 0.7, 2, PITCH_LENGTH - 2)
        y = clamp(keeper.y, 2, PITCH_WIDTH - 2)
        return x, y

    def _decide_shot_outcome(self, shooter: PlayerState, keeper: PlayerState) -> str:
        goal_dist = self._goal_distance(shooter)
        pressure = self._pressure_on_player(shooter)
        strength = self._team_strength(shooter.side)
        shooter_attrs = shooter.profile.attributes
        keeper_attrs = keeper.profile.attributes
        long_shot_factor = max(0.0, min(1.0, (goal_dist - 18.0) / 12.0))
        goal = (
            0.045
            + ((shooter_attrs["finishing"] * (1.0 - long_shot_factor) + shooter_attrs.get("long_shots", shooter_attrs["finishing"]) * long_shot_factor) - 50.0) / 255.0
            + (shooter_attrs["composure"] - 50.0) / 300.0
            + (shooter_attrs.get("technique", shooter_attrs["finishing"]) - 50.0) / 340.0
            + strength * 0.02
            - pressure * 0.14
            - max(0.0, goal_dist - 18.0) / 82.0
        )
        if self._success_roll(goal):
            return "goal"
        save = 0.46 + self._keeper_save_score(keeper) / 205.0
        save_roll = self.rng.random()
        if save_roll < clamp(save, 0.2, 0.95):
            parry = (
                0.14
                + pressure * 0.10
                + max(0.0, 22.0 - goal_dist) / 120.0
                - keeper_attrs.get("handling", keeper_attrs["positioning"]) / 420.0
                + self._event_frequency_boost("corner") * 0.10
            )
            if save_roll < clamp(parry, 0.06, 0.40):
                return "save_out"
            return "save"
        return "off_target"

    def _team_strength(self, side: str) -> float:
        avg = self.home.avg_ovr if side == "home" else self.away.avg_ovr
        tempo_boost = {
            "lower": -0.03,
            "balanced": 0.0,
            "higher": 0.04,
        }.get(self._instruction_value(side, "tempo"), 0.0)
        return clamp((avg - 60.0) / 30.0 + self._playstyle_attack_modifier(side) + tempo_boost, 0.0, 1.25)

    def _pressure_on_player(self, player: PlayerState) -> float:
        opps = self.opponents(player.side)
        nearest_opp = min(opps, key=lambda o: distance((player.x, player.y), (o.x, o.y)))
        nearest = distance((player.x, player.y), (nearest_opp.x, nearest_opp.y))
        defending_side = "away" if player.side == "home" else "home"
        intensity = 1.0 + self._playstyle_defence_modifier(defending_side) * 0.85 + self._player_pressure_bias(nearest_opp) * 0.38
        intensity += max(0.0, -self._player_mindset_bias(nearest_opp)) * 0.16
        return clamp((1.0 - nearest / 16.0) * intensity, 0.0, 1.0)

    def _receiver_space(self, receiver: PlayerState) -> float:
        opps = self.opponents(receiver.side)
        nearest_opp = min(opps, key=lambda o: distance((receiver.x, receiver.y), (o.x, o.y)))
        nearest = distance((receiver.x, receiver.y), (nearest_opp.x, nearest_opp.y))
        defending_side = "away" if receiver.side == "home" else "home"
        squeeze = 1.0 - self._playstyle_defence_modifier(defending_side) * 0.55 - self._player_pressure_bias(nearest_opp) * 0.20
        squeeze -= max(0.0, -self._player_mindset_bias(nearest_opp)) * 0.10
        return clamp((nearest / 18.0) * squeeze, 0.0, 1.4)

    def _goal_distance(self, player: PlayerState) -> float:
        goal = (self._attacking_goal_x(player.side), PITCH_WIDTH / 2)
        return distance((player.x, player.y), goal)

    def _defending_goal_distance(self, player: PlayerState) -> float:
        goal = (self._defending_goal_x(player.side), PITCH_WIDTH / 2)
        return distance((player.x, player.y), goal)

    def _forwardness(self, side: str, x: float) -> float:
        return x if self._side_forward_sign(side) > 0 else (PITCH_LENGTH - x)

    def _choose_pass_option(self, carrier: PlayerState, receiver: PlayerState) -> Dict[str, object]:
        pass_scores = {ptype: self._pass_type_score(carrier, receiver, ptype) for ptype in PASS_SPEEDS}
        phase = self.state.phase_in_possession
        directness = (self._tactic_value(carrier.side, "directness") - 50.0) / 50.0
        crossing_bias = (self._tactic_value(carrier.side, "crossing") - 50.0) / 50.0
        width_bias = (self._tactic_value(carrier.side, "width") - 50.0) / 50.0
        side_lane = abs(receiver.y - PITCH_WIDTH / 2) / (PITCH_WIDTH / 2)
        pass_scores["short_ground"] -= max(0.0, directness) * 2.2
        pass_scores["progressive_ground"] += directness * 1.8
        pass_scores["switch"] += directness * 1.0
        pass_scores["cross"] += crossing_bias * 3.8
        pass_scores["cross"] += width_bias * side_lane * 2.4
        pass_scores["switch"] += width_bias * side_lane * 1.3
        pass_scores["short_ground"] += (-width_bias) * (1.0 - side_lane) * 2.2
        pass_scores["progressive_ground"] += (-width_bias) * (1.0 - side_lane) * 1.0
        if phase == "build_up":
            pass_scores["short_ground"] += 9.0
            pass_scores["progressive_ground"] -= 4.0
            pass_scores["switch"] -= 1.5
            pass_scores["cross"] = -999.0
        elif phase == "progression":
            pass_scores["short_ground"] += 3.0
            pass_scores["progressive_ground"] += 1.0
            pass_scores["switch"] -= 0.5
        pass_type = max(pass_scores, key=pass_scores.get)
        return {
            "type": "pass",
            "target": receiver,
            "label": pass_type.replace("_", " "),
            "pass_type": pass_type,
            "score": pass_scores[pass_type],
        }

    def _choose_action(self, carrier: PlayerState) -> Dict[str, object]:
        teammates = [p for p in self.teammates(carrier.side) if p.profile.id != carrier.profile.id]
        strength = self._team_strength(carrier.side)
        tempo = (self._tactic_value(carrier.side, "tempo") - 50.0) / 50.0
        counter = (self._tactic_value(carrier.side, "counter") - 50.0) / 50.0
        directness = (self._tactic_value(carrier.side, "directness") - 50.0) / 50.0
        mindset_bias = self._player_mindset_bias(carrier)
        gameplan = self._instruction_value(carrier.side, "gameplan")
        time_wasting = self._is_time_wasting(carrier.side)
        pass_options = [self._choose_pass_option(carrier, teammate) for teammate in teammates]
        best_safe = max(pass_options, key=lambda opt: opt["score"])
        best_forward = max(
            pass_options,
            key=lambda opt: opt["score"] + self._forwardness(carrier.side, opt["target"].x) * 0.08,
        )
        shot_score = self._shot_score(carrier)
        dribble_score = self._dribble_score(carrier)
        pressure = self._pressure_on_player(carrier)
        goal_dist = self._goal_distance(carrier)
        short_pass_score = float(best_safe["score"]) + strength * 6.8
        forward_pass_score = float(best_forward["score"]) + strength * 5.8
        if str(best_forward.get("pass_type")) == "cross":
            forward_pass_score += 7.5 if carrier.slot in ("LW", "RW", "LB", "RB") else 3.0

        phase = self.state.phase_in_possession
        recycle_bonus = 5.0 if pressure > 0.7 else 0.0
        dribble_penalty = 4.5 if pressure > 0.68 else 0.0
        carry_bias = 0.0
        if pressure < 0.42:
            carry_bias += 4.4
        if goal_dist > 22.0:
            carry_bias += 2.4
        if self.state.phase_in_possession in ("progression", "transition"):
            carry_bias += 2.0
        short_pass_score += 0.9
        forward_pass_score += directness * 4.2
        short_pass_score -= max(0.0, directness) * 1.5
        short_pass_score -= max(0.0, mindset_bias) * 1.6
        short_pass_score += max(0.0, -mindset_bias) * 2.2
        forward_pass_score += mindset_bias * 3.2
        carry_bias += mindset_bias * 2.1
        shot_score += mindset_bias * 4.0
        if self.state.phase_in_possession == "transition":
            forward_pass_score += max(0.0, counter) * 3.5
            carry_bias += max(0.0, counter) * 2.0
        if gameplan == "possession":
            short_pass_score += 2.4
            forward_pass_score -= 1.0
            carry_bias -= 0.6
        elif gameplan == "quick_play":
            short_pass_score -= 0.8
            forward_pass_score += 1.8
            carry_bias += 0.7
        if tempo < 0.0:
            short_pass_score += abs(tempo) * 3.0
            forward_pass_score -= abs(tempo) * 1.5
            carry_bias -= abs(tempo) * 1.4
        else:
            forward_pass_score += tempo * 1.8
            carry_bias += tempo * 1.0
        if phase == "build_up":
            short_pass_score += 15.0
            forward_pass_score -= 1.4
            carry_bias -= 3.2
        elif phase == "progression":
            short_pass_score += 7.8
            forward_pass_score += 1.4
            carry_bias -= 1.2
        elif phase == "final_third":
            short_pass_score += 0.6
            forward_pass_score += 2.1
            carry_bias += 1.4
        if time_wasting:
            short_pass_score += 4.2
            forward_pass_score -= 2.4
            carry_bias -= 2.0
            shot_score -= 3.0
        scores = {
            "short_pass": short_pass_score + recycle_bonus,
            "forward_pass": forward_pass_score,
            "dribble": dribble_score + strength * 3.5 + carry_bias - dribble_penalty,
        }
        if self._should_attempt_shot(carrier):
            scores["shoot"] = shot_score + strength * 1.8 - 1.6
        chosen = weighted_choice(scores, self.rng)
        if chosen == "short_pass":
            return best_safe
        if chosen == "forward_pass":
            return best_forward
        if chosen == "dribble":
            return {"type": "dribble"}
        return {"type": "shoot"}

    def _dribble_score(self, carrier: PlayerState) -> float:
        attrs = carrier.profile.attributes
        pressure = self._pressure_on_player(carrier)
        goal_dist = self._goal_distance(carrier)
        open_x, open_y = self._open_space_target(carrier)
        open_space = distance((carrier.x, carrier.y), (open_x, open_y))
        return (
            attrs["dribbling"] * 0.31
            + attrs.get("technique", attrs["dribbling"]) * 0.14
            + attrs.get("agility", attrs.get("acceleration", attrs["pace"])) * 0.12
            + attrs["pace"] * 0.22
            + attrs["decisions"] * 0.18
            + max(0.0, 34.0 - goal_dist) * 0.34
            + open_space * 1.8
            - pressure * 21.0
        )

    def _shot_score(self, carrier: PlayerState) -> float:
        attrs = carrier.profile.attributes
        pressure = self._pressure_on_player(carrier)
        goal_dist = self._goal_distance(carrier)
        angle_quality = 1.0 - abs(carrier.y - PITCH_WIDTH / 2) / (PITCH_WIDTH / 2)
        forwardness = self._forwardness(carrier.side, carrier.x)
        long_shot_factor = max(0.0, min(1.0, (goal_dist - 18.0) / 12.0))
        return (
            (attrs["finishing"] * (0.35 - long_shot_factor * 0.10))
            + attrs.get("long_shots", attrs["finishing"]) * long_shot_factor * 0.22
            + attrs["composure"] * 0.18
            + attrs.get("technique", attrs["finishing"]) * 0.10
            + attrs["first_touch"] * 0.05
            + attrs["decisions"] * 0.10
            + max(0.0, 26.0 - goal_dist) * 1.0
            + angle_quality * 10.0
            + max(0.0, forwardness - 63.0) * 0.45
            - pressure * 16.0
            - max(0.0, goal_dist - 24.0) * 0.8
            - max(0.0, 58.0 - forwardness) * 1.2
        )

    def _should_attempt_shot(self, carrier: PlayerState) -> bool:
        goal_dist = self._goal_distance(carrier)
        pressure = self._pressure_on_player(carrier)
        angle_quality = 1.0 - abs(carrier.y - PITCH_WIDTH / 2) / (PITCH_WIDTH / 2)
        forwardness = self._forwardness(carrier.side, carrier.x)
        decisions = carrier.profile.attributes["decisions"]
        finishing = carrier.profile.attributes["finishing"]
        long_shots = carrier.profile.attributes.get("long_shots", finishing)

        if forwardness < (PITCH_LENGTH / 2) - 1.0:
            return False
        if goal_dist > 34.0:
            return False
        if goal_dist > 29.0 and (pressure > 0.24 or angle_quality < 0.76):
            return False
        if goal_dist > 25.0 and angle_quality < 0.58:
            return False
        if goal_dist > 28.0 and long_shots < 72.0 and decisions < 68.0:
            return False
        if goal_dist > 26.0 and decisions < 66.0 and finishing < 70.0 and long_shots < 74.0:
            return False
        return True

    def _resolve_action(self, carrier: PlayerState, action: Dict[str, object]) -> None:
        if action["type"] == "pass":
            self._start_pass(carrier, action["target"], str(action["label"]), str(action["pass_type"]))
        elif action["type"] == "dribble":
            self._resolve_dribble(carrier)
        elif action["type"] == "shoot":
            self._start_shot(carrier)

    def _success_roll(self, chance: float) -> bool:
        return self.rng.random() <= clamp(chance, 0.03, 0.97)

    def _register_possession_change(self, new_side: str) -> None:
        if self.state.possession != new_side:
            self.state.recent_turnover_seconds = 2.0
        self.state.possession = new_side

    def _give_ball_to(self, player: PlayerState, note: Optional[str] = None, action_type: str = "recovery") -> None:
        for p in self.home.xi + self.away.xi:
            p.has_ball = False
            if p.profile.id != player.profile.id:
                self._clear_run_commitment(p)
        player.has_ball = True
        self._clear_run_commitment(player)
        player.control_cooldown = {
            "pass": 0.32,
            "dribble": 0.22,
            "recovery": 0.21,
            "interception": 0.23,
            "shot": 0.18,
        }.get(action_type, 0.24)
        self.state.ball.mode = "carried"
        self.state.ball.carrier_id = player.profile.id
        self.state.ball.target_player_id = None
        self.state.ball.team_in_possession = player.side
        self.state.ball.lead_player_id = player.profile.id
        self.state.ball.loose_owner_bias = player.side
        self.state.ball.offside_flag = False
        self.state.restart_mode = None
        self.state.restart_timer = 0.0
        self.state.restart_side = None
        self.state.restart_taker_id = None
        self.state.fouled_player_id = None
        if action_type != "pass":
            self.state.assist_candidate_id = None
        self._register_possession_change(player.side)
        self.state.last_touch_player_id = player.profile.id
        self.state.last_action_type = action_type
        bx, by = self._ball_front_offset(player)
        self.state.ball.x = bx
        self.state.ball.y = by
        self.state.ball.target_x = bx
        self.state.ball.target_y = by
        self._set_render_state(player, "carry", action_type)
        if action_type in ("recovery", "interception"):
            self._record_ball_recovery(player)
        if note:
            self.add_event(note)

    def _start_pass(self, carrier: PlayerState, receiver: PlayerState, label: str, pass_type: str) -> None:
        attrs = carrier.profile.attributes
        recv_attrs = receiver.profile.attributes
        self._record_pass_attempt(carrier)
        if carrier.slot == "GK" and (pass_type in ("switch", "cross") or distance((carrier.x, carrier.y), (receiver.x, receiver.y)) >= 30.0):
            self._player_match_stats(carrier)["long_balls_attempted"] += 1.0
        pressure = self._pressure_on_player(carrier)
        recv_space = self._receiver_space(receiver)
        dist = distance((carrier.x, carrier.y), (receiver.x, receiver.y))
        strength = self._team_strength(carrier.side)
        lane_penalty = self._evaluate_pass_lane(carrier, receiver, pass_type)
        target_x, target_y = self._predict_receiver_target(carrier, receiver, pass_type)

        chance = (
            0.515
            + (attrs["passing"] - 50.0) / 150.0
            + (attrs["vision"] - 50.0) / 190.0
            + (recv_attrs["first_touch"] - 50.0) / 250.0
            + recv_space * 0.09
            + strength * 0.04
            - pressure * 0.16
            - lane_penalty * 0.058
            - dist / 198.0
            - carrier.fatigue / 190.0
        )
        if not self._success_roll(chance):
            direction_x = target_x - carrier.x
            direction_y = target_y - carrier.y
            mag = math.hypot(direction_x, direction_y) or 1.0
            direction_x /= mag
            direction_y /= mag
            target_x = clamp(target_x + direction_x * self.rng.uniform(-2.0, 5.5), -4.0, PITCH_LENGTH + 4.0)
            target_y = clamp(target_y + direction_y * self.rng.uniform(-2.5, 2.5) + self.rng.uniform(-2.0, 2.0), -4.0, PITCH_WIDTH + 4.0)
            wide_carrier = carrier.y < 9.5 or carrier.y > (PITCH_WIDTH - 9.5)
            final_third = self._forwardness(carrier.side, carrier.x) > 73.0
            nearest_touchline = -1.8 if carrier.y < (PITCH_WIDTH / 2) else (PITCH_WIDTH + 1.8)
            if pass_type == "cross":
                if wide_carrier and self.rng.random() < 0.80:
                    if label != "corner":
                        target_y = nearest_touchline
                elif final_third and self.rng.random() < 0.58:
                    target_x = self._attacking_goal_x(carrier.side) + self._side_forward_sign(carrier.side) * self.rng.uniform(1.4, 4.8)
            elif wide_carrier and self.rng.random() < 0.46:
                target_y = nearest_touchline
            elif pressure > 0.62 and carrier.slot in ("LB", "RB", "CB") and self.rng.random() < 0.16:
                target_y = nearest_touchline if abs(carrier.y - PITCH_WIDTH / 2) > 12.0 else target_y
            if max(0.0, (self._tactic_value(carrier.side, "width") - 50.0) / 50.0) > 0.2 and self.rng.random() < 0.14:
                target_y = nearest_touchline

        travel_dist = distance((carrier.x, carrier.y), (target_x, target_y))
        self.state.ball.mode = "travelling"
        self.state.ball.carrier_id = None
        self.state.ball.target_player_id = receiver.profile.id
        self.state.ball.team_in_possession = carrier.side
        self.state.ball.intended_side = carrier.side
        self.state.ball.start_x = carrier.x
        self.state.ball.start_y = carrier.y
        self.state.ball.x = carrier.x
        self.state.ball.y = carrier.y
        self.state.ball.target_x = target_x
        self.state.ball.target_y = target_y
        self.state.ball.travel_progress = 0.0
        self.state.ball.pass_type = pass_type
        sign = self._side_forward_sign(carrier.side)
        projected_x = receiver.x
        if (receiver.target_x - receiver.x) * sign > 0.6:
            if pass_type == "through_ball":
                projected_x = lerp(receiver.x, receiver.target_x, 0.42)
            elif (
                pass_type == "progressive_ground"
                and receiver.slot in ("ST", "LW", "RW")
                and self.state.phase_in_possession in ("progression", "final_third")
            ):
                projected_x = lerp(receiver.x, receiver.target_x, 0.26)
        check_x = projected_x if pass_type in ("through_ball", "progressive_ground") else receiver.x
        self.state.ball.offside_flag = self._should_flag_offside(carrier, receiver, pass_type, check_x)
        self.state.ball.travel_time = max(0.24, travel_dist / PASS_SPEEDS[pass_type])
        self.state.ball.speed = PASS_SPEEDS[pass_type]
        self.state.ball.lead_player_id = carrier.profile.id
        self.state.last_touch_player_id = carrier.profile.id
        self.state.last_action_type = "pass"
        carrier.has_ball = False
        receiver.target_x = target_x
        receiver.target_y = target_y
        self._start_run_commitment(receiver, target_x, target_y, "receiving", pass_type, self._run_commit_duration(receiver, "receiving", pass_type))
        self.add_event(f"{carrier.short_name} plays a {label}")

    def _open_space_target(self, carrier: PlayerState) -> Tuple[float, float]:
        sign = self._side_forward_sign(carrier.side)
        best_score = -999.0
        best_target = (carrier.x + sign * 2.0, carrier.y)
        for angle in (-40, -18, 0, 18, 40):
            radians = math.radians(angle)
            dx = sign * math.cos(radians)
            dy = math.sin(radians)
            tx = clamp(carrier.x + dx * 4.2, 2, PITCH_LENGTH - 2)
            ty = clamp(carrier.y + dy * 3.6, 2, PITCH_WIDTH - 2)
            nearest = min(distance((tx, ty), (opp.x, opp.y)) for opp in self.opponents(carrier.side))
            forward = (tx - carrier.x) * sign
            score = nearest * 1.2 + forward * 1.5 - abs(ty - carrier.y) * 0.18
            if score > best_score:
                best_score = score
                best_target = (tx, ty)
        return best_target

    def _resolve_duel(self, carrier: PlayerState, defender: PlayerState) -> None:
        self._player_match_stats(carrier)["duels_total"] += 1.0
        self._player_match_stats(defender)["duels_total"] += 1.0
        ball = self.state.ball
        carrier_score = (
            carrier.profile.attributes["dribbling"] * 0.35
            + carrier.profile.attributes["composure"] * 0.2
            + carrier.profile.attributes.get("technique", carrier.profile.attributes["dribbling"]) * 0.14
            + carrier.profile.attributes.get("agility", carrier.profile.attributes.get("acceleration", carrier.profile.attributes["pace"])) * 0.12
            + carrier.profile.attributes.get("acceleration", carrier.profile.attributes["pace"]) * 0.14
            + self.rng.uniform(0.0, 12.0)
        )
        defender_score = (
            defender.profile.attributes["tackling"] * 0.34
            + defender.profile.attributes["positioning"] * 0.24
            + defender.profile.attributes.get("marking", defender.profile.attributes["positioning"]) * 0.16
            + defender.profile.attributes.get("strength", defender.profile.attributes["positioning"]) * 0.12
            + defender.profile.attributes.get("anticipation", defender.profile.attributes["positioning"]) * 0.12
            + self.rng.uniform(0.0, 12.0)
        )
        if defender.yellow_cards >= 1:
            defender_score -= 2.0
        pressure_bias = self._player_pressure_bias(defender)
        mindset_bias = self._player_mindset_bias(defender)
        defender_score += pressure_bias * 4.0
        defender_score += max(0.0, -mindset_bias) * 3.6
        margin = carrier_score - defender_score
        pressure = self._pressure_on_player(carrier)
        near_touchline = carrier.y < 6.8 or carrier.y > (PITCH_WIDTH - 6.8)
        discipline_intensity = self._discipline_intensity(defender.side)
        foul_chance = (
            0.028
            + (defender.profile.attributes.get("aggression", 60.0) - 50.0) / 260.0
            + defender.profile.attributes["tackling"] / 700.0
            - defender.profile.attributes["decisions"] / 760.0
            + defender.fatigue / 340.0
            + pressure * 0.08
            + self._event_frequency_boost("foul") * 0.025
            + pressure_bias * 0.08
            + max(0.0, -mindset_bias) * 0.03
        )
        foul_chance *= discipline_intensity
        if near_touchline:
            foul_chance -= 0.08
        if defender.yellow_cards >= 1:
            foul_chance -= 0.04
        foul_spot = ((carrier.x + defender.x) / 2, (carrier.y + defender.y) / 2)
        severity = clamp(
            0.12
            + max(0.0, -margin) / 34.0
            + pressure * 0.16
            + defender.profile.attributes.get("aggression", 60.0) / 320.0
            + defender.fatigue / 360.0
            + pressure_bias * 0.10
            + (discipline_intensity - 1.0) * 0.18,
            0.08,
            0.92,
        )
        touchline_spill_chance = clamp(
            0.34
            + self._event_frequency_boost("throw_in") * 0.18
            + max(0.0, -margin) / 95.0
            + pressure * 0.08
            - severity * 0.16,
            0.0,
            0.88,
        )
        if near_touchline and severity < 0.72 and self.rng.random() < touchline_spill_chance:
            out_y = -0.8 if carrier.y < (PITCH_WIDTH / 2) else (PITCH_WIDTH + 0.8)
            out_x = clamp((carrier.x + defender.x) / 2, 1.0, PITCH_LENGTH - 1.0)
            self.state.last_touch_player_id = defender.profile.id
            self._handle_ball_out(defender.side, out_x, out_y)
            return
        if self.rng.random() < clamp(foul_chance + max(0.0, -margin) / 110.0, 0.015, 0.24):
            self._commit_foul(defender, carrier, foul_spot, severity)
            return
        if margin > 10.0:
            self._player_match_stats(carrier)["duels_won"] += 1.0
            self._player_match_stats(carrier)["dribbles_completed"] += 1.0
            self._give_ball_to(carrier, note=f"{carrier.short_name} rides the challenge", action_type="dribble")
            carrier.control_cooldown = 0.22
            return
        ball.mode = "loose"
        ball.carrier_id = None
        if near_touchline and self.rng.random() < clamp(0.52 + self._event_frequency_boost("throw_in") * 0.20, 0.36, 0.90):
            out_y = -0.8 if carrier.y < (PITCH_WIDTH / 2) else (PITCH_WIDTH + 0.8)
            out_x = clamp((carrier.x + defender.x) / 2, 1.0, PITCH_LENGTH - 1.0)
            self.state.last_touch_player_id = defender.profile.id
            self._handle_ball_out(defender.side, out_x, out_y)
            return
        ball.x = clamp((carrier.x + defender.x) / 2 + self.rng.uniform(-0.9, 0.9), -2.5, PITCH_LENGTH + 2.5)
        ball.y = clamp((carrier.y + defender.y) / 2 + self.rng.uniform(-0.9, 0.9), -2.5, PITCH_WIDTH + 2.5)
        ball.loose_owner_bias = carrier.side if margin > -6.0 else defender.side
        self._player_match_stats(defender)["duels_won"] += 1.0
        self._player_match_stats(defender)["tackles"] += 1.0
        if defender.slot != "GK" and self._defending_goal_distance(defender) < 24.0:
            self._player_match_stats(defender)["clearances"] += 1.0
        self.state.last_touch_player_id = defender.profile.id
        self.state.last_action_type = "recovery"
        self.add_event(f"{defender.short_name} gets a touch")

    def _resolve_dribble(self, carrier: PlayerState) -> None:
        attrs = carrier.profile.attributes
        nearest = min(self.opponents(carrier.side), key=lambda p: distance((p.x, p.y), (carrier.x, carrier.y)))
        pressure = self._pressure_on_player(carrier)
        strength = self._team_strength(carrier.side)
        target_x, target_y = self._open_space_target(carrier)
        chance = (
            0.38
            + (attrs["dribbling"] - 50.0) / 155.0
            + (attrs["pace"] - 50.0) / 185.0
            + (attrs["composure"] - 50.0) / 250.0
            + strength * 0.04
            - pressure * 0.18
            - nearest.profile.attributes["tackling"] / 310.0
            - nearest.profile.attributes["positioning"] / 360.0
        )
        if self._success_roll(chance):
            self._player_match_stats(carrier)["dribbles_completed"] += 1.0
            carrier.target_x = target_x
            carrier.target_y = target_y
            carrier.control_cooldown = 0.26
            self.state.last_action_type = "dribble"
            self._set_render_state(carrier, "carry", "dribble")
            self.add_event(f"{carrier.short_name} carries into space")
        else:
            self._resolve_duel(carrier, nearest)

    def _carry_ball_forward(self, carrier: PlayerState) -> None:
        lead_x, lead_y = self._open_space_target(carrier)
        sign = self._side_forward_sign(carrier.side)
        carrier.target_x = clamp(lerp(carrier.x, lead_x, 0.58) + sign * 0.8, 2, PITCH_LENGTH - 2)
        carrier.target_y = clamp(lerp(carrier.y, lead_y, 0.34), 2, PITCH_WIDTH - 2)
        bx, by = self._ball_front_offset(carrier)
        self.state.ball.x = bx
        self.state.ball.y = by
        self._set_render_state(carrier, "carry", "carry")

    def _start_shot(self, carrier: PlayerState) -> None:
        goal_x = self._attacking_goal_x(carrier.side)
        target_y = clamp(PITCH_WIDTH / 2 + self.rng.uniform(-3.5, 3.5), 8, PITCH_WIDTH - 8)
        defending_side = "away" if carrier.side == "home" else "home"
        keeper = self._goalkeeper(defending_side)
        shot_outcome = self._decide_shot_outcome(carrier, keeper)
        self._record_shot(carrier, shot_outcome in ("goal", "save", "save_out"))
        if shot_outcome == "save":
            goal_x, target_y = self._keeper_collection_point(keeper, carrier.side)
        elif shot_outcome == "off_target":
            goal_x = self._attacking_goal_x(carrier.side) + self._side_forward_sign(carrier.side) * 4.0
            target_y = clamp(target_y + self.rng.uniform(-4.0, 4.0), 5, PITCH_WIDTH - 5)

        self.state.ball.mode = "shot"
        self.state.ball.carrier_id = None
        self.state.ball.target_player_id = None
        self.state.ball.team_in_possession = carrier.side
        self.state.ball.intended_side = carrier.side
        self.state.ball.start_x = carrier.x
        self.state.ball.start_y = carrier.y
        self.state.ball.x = carrier.x
        self.state.ball.y = carrier.y
        self.state.ball.target_x = goal_x
        self.state.ball.target_y = target_y
        self.state.ball.travel_progress = 0.0
        self.state.ball.travel_time = max(0.25, distance((carrier.x, carrier.y), (goal_x, target_y)) / 55.0)
        self.state.ball.speed = 55.0
        self.state.ball.shot_outcome = shot_outcome
        self.state.last_touch_player_id = carrier.profile.id
        self.state.last_action_type = "shot"
        carrier.has_ball = False
        self._set_render_state(carrier, "shooting", "shot")
        self.add_event(f"{carrier.short_name} shoots")

    def _goalkeeper(self, side: str) -> PlayerState:
        return next(p for p in self.teammates(side) if p.slot == "GK")

    def _update_render_states(self) -> None:
        if self.state.awaiting_start or self.state.celebration_timer > 0 or self.state.restart_timer > 0:
            return
        if self.state.ball.mode == "travelling":
            receiver = self.find_player(self.state.ball.target_player_id)
            if receiver:
                self._set_render_state(receiver, "receiving", self.state.ball.pass_type)
        carrier = self.find_player(self.state.ball.carrier_id)
        if carrier:
            if self.state.last_action_type == "shot":
                self._set_render_state(carrier, "shooting", "shot")
            else:
                self._set_render_state(carrier, "carry", self.state.last_action_type)
