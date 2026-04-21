from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple

from .loader import FORMATION_433, pick_best_xi
from .models import BallState, Club, MatchEvent, MatchState, PlayerProfile, PlayerState, TeamState

PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0
SLICE_SECONDS = 0.18
BASE_PLAYBACK_SPEED = 0.38
MATCH_MINUTES = 90
GOAL_CELEBRATION_SECONDS = 2.8
KICKOFF_SETUP_SECONDS = 1.8
GOAL_KICK_SETUP_SECONDS = 1.6
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

PASS_SPEEDS = {
    "short_ground": 28.0,
    "progressive_ground": 33.0,
    "through_ball": 36.0,
    "switch": 40.0,
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
    def __init__(self, home_club: Club, away_club: Club, seed: int = 42) -> None:
        self.rng = random.Random(seed)
        self.playback_multiplier = 1.0
        self.home_xi_profiles, self.home_bench = pick_best_xi(home_club)
        self.away_xi_profiles, self.away_bench = pick_best_xi(away_club)
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
        self._time_accumulator = 0.0
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
        slot_counts: Dict[str, int] = {}
        formation_counts: Dict[str, int] = {}
        for formation_slot in FORMATION_433:
            formation_counts[formation_slot] = formation_counts.get(formation_slot, 0) + 1

        for idx, profile in enumerate(xi_profiles):
            slot = FORMATION_433[idx]
            slot_counts[slot] = slot_counts.get(slot, 0) + 1
            named_slot = f"{slot}{slot_counts[slot]}" if formation_counts[slot] > 1 else slot
            coords = HOME_FORMATION_XY[named_slot] if side == "home" else AWAY_FORMATION_XY[named_slot]
            pace = profile.attributes["pace"]
            speed = 2.1 + ((pace - 50.0) / 50.0) * 0.95
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
                    facing_x=facing_x,
                )
            )
        avg = round(sum(p.profile.ovr for p in xi_states) / len(xi_states), 2)
        return TeamState(club=club, side=side, xi=xi_states, bench=bench, avg_ovr=avg)

    def _kickoff(self) -> None:
        self._start_kickoff_setup("home", opening=True)
        self._derive_match_context()

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

    def teammates(self, side: str) -> List[PlayerState]:
        return self.home.xi if side == "home" else self.away.xi

    def opponents(self, side: str) -> List[PlayerState]:
        return self.away.xi if side == "home" else self.home.xi

    def update(self, dt: float) -> None:
        if self.state.is_finished:
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

        if self.state.restart_mode == "kickoff_setup":
            self._update_restart_sequence()
            return

        self.state.real_elapsed_seconds += SLICE_SECONDS
        self._update_match_clock()

        if self.state.real_elapsed_seconds >= MATCH_REAL_SECONDS:
            self.state.is_finished = True
            self.state.phase = "full_time"
            self.state.elapsed_seconds = 90 * 60
            self.state.minute = 90
            self.state.second = 0
            self.add_event("Full time")
            return

        if self.state.phase == "first_half" and self.state.real_elapsed_seconds >= HALF_REAL_SECONDS:
            self._start_second_half()
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
        if self.state.restart_mode == "kickoff_setup":
            return self.state.elapsed_seconds
        extra_real = self._time_accumulator
        if self.state.real_elapsed_seconds < HALF_REAL_SECONDS:
            display_rate = (45 * 60) / HALF_REAL_SECONDS
            return clamp(self.state.elapsed_seconds + extra_real * display_rate, 0.0, 45 * 60)
        display_rate = (45 * 60) / HALF_REAL_SECONDS
        return clamp(self.state.elapsed_seconds + extra_real * display_rate, 45 * 60, 90 * 60)

    def _start_second_half(self) -> None:
        self.add_event("Second half")
        self._start_kickoff_setup("away")
        self.state.phase = "second_half"

    def _derive_match_context(self) -> None:
        ball = self.state.ball
        x_zone = "defensive" if ball.x < PITCH_LENGTH / 3 else "middle" if ball.x < (PITCH_LENGTH * 2 / 3) else "attacking"
        if self.state.possession == "away":
            x_zone = "attacking" if x_zone == "defensive" else "defensive" if x_zone == "attacking" else "middle"
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
        return 1.0 if side == "home" else -1.0

    def _set_render_state(self, player: PlayerState, state: str, intent: Optional[str] = None) -> None:
        player.render_state = state
        player.run_intent = intent

    def _role_target(self, player: PlayerState, phase: str, ball_zone: str) -> Tuple[float, float]:
        ball_x, ball_y = self.state.ball.x, self.state.ball.y
        sign = self._side_forward_sign(player.side)
        intent = ROLE_INTENTS[player.slot]
        x_target = player.home_x
        y_target = player.home_y
        width_shift = intent["width"] * 4.0

        if player.slot == "GK":
            y_target = clamp(lerp(player.home_y, ball_y, 0.08), 24, 44)
            x_target = clamp(player.home_x + sign * (2.0 if phase == "build_up" else 0.0), 5, PITCH_LENGTH - 5)
            return x_target, y_target

        if phase == "build_up":
            if player.slot in ("CB", "LB", "RB"):
                line_push = 1.5 if player.slot == "CB" else 2.5
                x_target = player.home_x + sign * line_push
                y_target = clamp(player.home_y + (ball_y - player.home_y) * 0.20 + width_shift, 4, PITCH_WIDTH - 4)
            elif player.slot == "DM":
                x_target = ball_x - sign * 7.0
                y_target = clamp(lerp(player.home_y, ball_y, 0.25), 8, PITCH_WIDTH - 8)
            elif player.slot == "CM":
                x_target = ball_x + sign * 4.0
                y_target = clamp(ball_y - 7.0, 6, PITCH_WIDTH - 6)
            elif player.slot == "AM":
                x_target = ball_x + sign * 9.0
                y_target = clamp(ball_y + 6.0, 6, PITCH_WIDTH - 6)
            elif player.slot in ("LW", "RW"):
                same_side = (player.slot == "LW" and ball_y < PITCH_WIDTH / 2) or (player.slot == "RW" and ball_y >= PITCH_WIDTH / 2)
                x_target = player.home_x + sign * (5.0 if same_side else 1.5)
                y_target = player.home_y + (ball_y - player.home_y) * (0.25 if same_side else 0.08)
            elif player.slot == "ST":
                x_target = player.home_x + sign * 3.5
                y_target = clamp(lerp(player.home_y, ball_y, 0.18), 10, PITCH_WIDTH - 10)
        elif phase == "progression":
            if player.slot in ("CB", "LB", "RB"):
                overlap = 4.0 if player.slot in ("LB", "RB") else 2.5
                x_target = player.home_x + sign * overlap
                y_target = clamp(player.home_y + (ball_y - player.home_y) * 0.25 + width_shift, 4, PITCH_WIDTH - 4)
            elif player.slot == "DM":
                x_target = ball_x - sign * 8.0
                y_target = clamp(lerp(player.home_y, ball_y, 0.35), 7, PITCH_WIDTH - 7)
            elif player.slot == "CM":
                x_target = ball_x + sign * 5.5
                y_target = clamp(ball_y - 8.0, 6, PITCH_WIDTH - 6)
            elif player.slot == "AM":
                x_target = ball_x + sign * 10.0
                y_target = clamp(ball_y + 6.0, 6, PITCH_WIDTH - 6)
            elif player.slot in ("LW", "RW"):
                ball_on_side = (player.slot == "LW" and ball_y < PITCH_WIDTH * 0.55) or (player.slot == "RW" and ball_y > PITCH_WIDTH * 0.45)
                diag_push = 10.0 if ball_on_side else 5.5
                x_target = player.home_x + sign * diag_push
                offset = -5.0 if player.slot == "LW" else 5.0
                y_target = clamp(player.home_y + (ball_y - player.home_y) * (0.42 if ball_on_side else 0.16) + offset * 0.15, 4, PITCH_WIDTH - 4)
            elif player.slot == "ST":
                x_target = player.home_x + sign * 8.0
                y_target = clamp(lerp(player.home_y, ball_y, 0.28), 8, PITCH_WIDTH - 8)
        else:
            if player.slot in ("CB", "LB", "RB"):
                x_target = player.home_x + sign * (2.5 if player.slot == "CB" else 6.0)
                y_target = clamp(player.home_y + (ball_y - player.home_y) * 0.28 + width_shift, 4, PITCH_WIDTH - 4)
            elif player.slot == "DM":
                x_target = ball_x - sign * 5.0
                y_target = clamp(lerp(player.home_y, ball_y, 0.42), 6, PITCH_WIDTH - 6)
            elif player.slot == "CM":
                x_target = ball_x + sign * 2.0
                y_target = clamp(ball_y - 7.0, 6, PITCH_WIDTH - 6)
            elif player.slot == "AM":
                x_target = ball_x + sign * 5.0
                y_target = clamp(ball_y + 5.0, 6, PITCH_WIDTH - 6)
            elif player.slot in ("LW", "RW"):
                x_target = player.home_x + sign * 6.0
                inside = -7.0 if player.slot == "LW" else 7.0
                y_target = clamp(player.home_y + inside * 0.35 + (ball_y - player.home_y) * 0.36, 4, PITCH_WIDTH - 4)
            elif player.slot == "ST":
                x_target = player.home_x + sign * 10.0
                y_target = clamp(lerp(player.home_y, ball_y, 0.30), 8, PITCH_WIDTH - 8)

        return clamp(x_target, 2, PITCH_LENGTH - 2), clamp(y_target, 2, PITCH_WIDTH - 2)

    def _defensive_shape_target(self, player: PlayerState) -> Tuple[float, float]:
        ball_x, ball_y = self.state.ball.x, self.state.ball.y
        sign = self._side_forward_sign(player.side)
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

        if player.slot == "DM":
            x_target = ball_x - sign * 10.0
            y_target = lerp(player.home_y, ball_y, 0.22)
        elif player.slot == "ST":
            x_target = player.home_x - sign * 4.0
            y_target = lerp(player.home_y, ball_y, 0.12)

        return clamp(x_target, 2, PITCH_LENGTH - 2), clamp(y_target, 4, PITCH_WIDTH - 4)

    def _update_off_ball_targets(self) -> None:
        ball_x, ball_y = self.state.ball.x, self.state.ball.y
        reacting: List[PlayerState] = []
        if self.state.ball.mode == "loose":
            by_side = {"home": [], "away": []}
            for player in self.home.xi + self.away.xi:
                by_side[player.side].append(player)
            for side in by_side:
                reacting.extend(sorted(by_side[side], key=lambda p: distance((p.x, p.y), (ball_x, ball_y)))[:2])
        if self.state.recent_turnover_seconds > 0:
            reacting = sorted(
                self.home.xi + self.away.xi,
                key=lambda p: distance((p.x, p.y), (ball_x, ball_y)),
            )[: max(4, len(reacting))]

        for team in (self.home, self.away):
            attacking = team.side == self.state.possession
            opps = self.opponents(team.side)
            pressers = sorted(team.xi, key=lambda p: distance((p.x, p.y), (ball_x, ball_y)))
            main_presser = pressers[0]
            cover_ids = {p.profile.id for p in pressers[1:3]}
            for p in team.xi:
                if p.profile.id == self.state.ball.carrier_id:
                    continue

                if p in reacting:
                    p.target_x = clamp(lerp(p.x, ball_x, 0.28), 2, PITCH_LENGTH - 2)
                    p.target_y = clamp(lerp(p.y, ball_y, 0.28), 2, PITCH_WIDTH - 2)
                    self._set_render_state(p, "transition", "react")
                    continue

                if attacking:
                    tx, ty = self._role_target(p, self.state.phase_in_possession, self.state.ball_zone)
                    p.target_x, p.target_y = tx, ty
                    state = "support"
                    if p.profile.id == self.state.ball.target_player_id:
                        state = "receiving"
                    elif p.slot in ("LW", "RW", "ST") and abs(p.target_x - p.x) > 4:
                        state = "run"
                    self._set_render_state(p, state, self.state.phase_in_possession)
                else:
                    tx, ty = self._defensive_shape_target(p)
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
                        self._set_render_state(p, "shape", "shape")
                    p.target_x, p.target_y = clamp(tx, 2, PITCH_LENGTH - 2), clamp(ty, 2, PITCH_WIDTH - 2)

    def _move_players(self) -> None:
        for p in self.home.xi + self.away.xi:
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
            load = 0.010
            if p.render_state in ("run", "pressing", "transition", "celebrate"):
                load += 0.010
            elif p.render_state in ("carry", "receiving"):
                load += 0.005
            p.fatigue = clamp(p.fatigue + load, 0.0, 25.0)

    def _player_move_speed(self, player: PlayerState) -> float:
        if player.render_state == "celebrate":
            return 6.8
        pace = player.profile.attributes["pace"]
        stamina = player.profile.attributes["stamina"]
        fatigue_penalty = clamp(player.fatigue / max(45.0, stamina * 0.75), 0.0, 0.42)
        pace_boost = 0.90 + (pace - 50.0) / 120.0
        state_multiplier = {
            "pressing": 1.22,
            "run": 1.18,
            "transition": 1.20,
            "carry": 1.08,
            "receiving": 1.06,
            "cover": 1.04,
            "celebrate": 1.14,
            "shape": 0.97,
            "support": 1.00,
        }.get(player.render_state, 1.0)
        return max(1.8, player.base_speed * pace_boost * state_multiplier * (1.0 - fatigue_penalty))

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
        if pass_type == "through_ball":
            lead_x += move_x * 0.75 + sign * (2.0 + space * 1.6)
            lead_y += move_y * 0.55
        elif pass_type == "progressive_ground":
            lead_x += move_x * 0.35 + sign * 0.8
            lead_y += move_y * 0.25
        elif pass_type == "switch":
            lead_x += move_x * 0.18
            lead_y += move_y * 0.32
        else:
            lead_x += move_x * 0.12
            lead_y += move_y * 0.12
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
        backward_penalty = max(0.0, -progression) * 1.25
        if progression < -8.0:
            backward_penalty += 8.0
        if receiver.slot == "GK" and self._goal_distance(carrier) < 35.0:
            return -999.0
        if self._goal_distance(carrier) < 22.0 and progression < -4.0:
            return -999.0
        base = (
            carrier.profile.attributes["passing"] * 0.22
            + carrier.profile.attributes["vision"] * 0.18
            + carrier.profile.attributes["decisions"] * 0.14
            + receiver.profile.attributes["first_touch"] * 0.08
            + receiver_space * 10.0
            + body_shape * 3.0
            + forward_angle * 8.0
            + moving_into_space * 4.0
            - lane_penalty * 6.0
            - backward_penalty
            - dist * 0.12
        )
        if pass_type == "through_ball":
            if forward_angle < 0.45 or moving_into_space == 0.0 or receiver_space < 0.45:
                return -999.0
            return base + 4.5 - dist * 0.03
        if pass_type == "progressive_ground":
            return base + 2.8
        if pass_type == "switch":
            return base + (3.5 if abs(receiver.y - carrier.y) > 16 else -2.0)
        return base + 1.4 - max(0.0, dist - 18.0) * 0.10

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
            score = -(dist * 1.1) + momentum + bias + p.profile.attributes["positioning"] / 60.0
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

        if nearest_dist < 1.4 and lane_advantage > threshold:
            congestion = self._evaluate_pass_lane(self.find_player(ball.lead_player_id) or receiver, receiver, ball.pass_type)
            chance = (
                0.28
                + interceptor.profile.attributes["positioning"] / 260.0
                + interceptor.profile.attributes["tackling"] / 320.0
                + clamp(lane_advantage / 3.5, 0.0, 0.25)
                + clamp(congestion / 10.0, 0.0, 0.16)
            )
            if late_window:
                chance -= 0.08
            if self.rng.random() < clamp(chance, 0.08, 0.86):
                interceptor.x = lerp(interceptor.x, ball.x, 0.35)
                interceptor.y = lerp(interceptor.y, ball.y, 0.35)
                self._give_ball_to(interceptor, note=f"{interceptor.short_name} intercepts", action_type="interception")
                return True
        return False

    def _resolve_first_touch(self, receiver: PlayerState, nearest_opp: PlayerState) -> str:
        pressure = clamp(1.0 - distance((receiver.x, receiver.y), (nearest_opp.x, nearest_opp.y)) / 10.0, 0.0, 1.0)
        control = (
            0.44
            + (receiver.profile.attributes["first_touch"] - 50.0) / 180.0
            + (receiver.profile.attributes["composure"] - 50.0) / 260.0
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
        receiver_dist = distance((receiver.x, receiver.y), (ball.x, ball.y))
        opps = self.opponents(receiver.side)
        nearest_opp = min(opps, key=lambda p: distance((p.x, p.y), (ball.x, ball.y)))
        opp_dist = distance((nearest_opp.x, nearest_opp.y), (ball.x, ball.y))

        catchable = 1.65 if ball.pass_type == "through_ball" else 1.45
        if receiver_dist < catchable and (receiver_dist <= opp_dist + 0.55 or ball.travel_progress >= 0.9):
            outcome = self._resolve_first_touch(receiver, nearest_opp)
            if outcome == "clean":
                self._settle_ball_for_reception(receiver)
                self._give_ball_to(receiver, note=f"{receiver.short_name} receives", action_type="pass")
            elif outcome == "slowed":
                self._settle_ball_for_reception(receiver)
                self._give_ball_to(receiver, note=f"{receiver.short_name} cushions it", action_type="pass")
                receiver.control_cooldown = 0.28
                self._set_render_state(receiver, "receiving", "slow_control")
            elif outcome == "contested":
                self.state.ball.mode = "loose"
                self.state.ball.carrier_id = None
                self.state.ball.loose_owner_bias = receiver.side
                self.state.possession = receiver.side
                self.state.last_action_type = "recovery"
                self.add_event(f"{receiver.short_name} under pressure")
            else:
                sign = self._side_forward_sign(receiver.side)
                self.state.ball.mode = "loose"
                self.state.ball.carrier_id = None
                self.state.ball.x = clamp(receiver.x + sign * 1.4, 2, PITCH_LENGTH - 2)
                self.state.ball.y = clamp(receiver.y + self.rng.uniform(-1.4, 1.4), 2, PITCH_WIDTH - 2)
                self.state.ball.loose_owner_bias = nearest_opp.side if opp_dist < receiver_dist else receiver.side
                self.state.possession = self.state.ball.loose_owner_bias or receiver.side
                self.state.last_action_type = "recovery"
                self.add_event(f"Heavy touch from {receiver.short_name}")
            return True
        return False

    def _resolve_arrived_pass(self) -> None:
        receiver = self.find_player(self.state.ball.target_player_id)
        if receiver:
            opps = self.opponents(receiver.side)
            nearest_opp = min(opps, key=lambda p: distance((p.x, p.y), (receiver.x, receiver.y)))
            outcome = self._resolve_first_touch(receiver, nearest_opp)
            if outcome in ("clean", "slowed"):
                self._settle_ball_for_reception(receiver)
                self._give_ball_to(receiver, note=f"{receiver.short_name} collects", action_type="pass")
                if outcome == "slowed":
                    receiver.control_cooldown = 0.24
            else:
                self.state.ball.mode = "loose"
                self.state.ball.carrier_id = None
                self.state.ball.loose_owner_bias = receiver.side if outcome == "contested" else nearest_opp.side
        else:
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
            if shooter.side == "home":
                self.state.home_score += 1
            else:
                self.state.away_score += 1
            self.add_event(f"GOAL! {shooter.short_name} scores")
            self._start_goal_celebration(shooter)
            return
        if outcome == "save":
            self._give_ball_to(keeper, note=f"{keeper.short_name} saves", action_type="recovery")
            return
        self._start_goal_kick_setup(defending_side)

    def _start_goal_celebration(self, scorer: PlayerState) -> None:
        scoring_side = scorer.side
        self.state.celebration_timer = GOAL_CELEBRATION_SECONDS
        self.state.celebration_side = scoring_side
        self.state.celebration_scorer_id = scorer.profile.id
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
            self._execute_kickoff()
        elif self.state.restart_mode == "goal_kick_setup":
            self._execute_goal_kick()

    def _start_kickoff_setup(self, kickoff_side: str, opening: bool = False) -> None:
        self._reset_players_for_restart()
        self.state.restart_mode = "kickoff_setup"
        self.state.restart_timer = KICKOFF_SETUP_SECONDS
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

        striker = next(p for p in self.teammates(kickoff_side) if p.slot == "ST")
        support = next(p for p in self.teammates(kickoff_side) if p.slot in ("AM", "CM", "DM"))
        self._place_team_for_kickoff(kickoff_side)
        striker.x = PITCH_LENGTH / 2
        striker.y = PITCH_WIDTH / 2
        striker.target_x = striker.x
        striker.target_y = striker.y
        support.x = PITCH_LENGTH / 2 - self._side_forward_sign(kickoff_side) * 8.5
        support.y = PITCH_WIDTH / 2 + 7.5
        support.target_x = support.x
        support.target_y = support.y
        striker.prev_x = striker.x
        striker.prev_y = striker.y
        support.prev_x = support.x
        support.prev_y = support.y
        self._set_render_state(striker, "shape", "kickoff")
        self._set_render_state(support, "shape", "kickoff")
        if opening:
            self.add_event(f"{self.home.name} kick off")

    def _place_team_for_kickoff(self, kickoff_side: str) -> None:
        centre_x = PITCH_LENGTH / 2
        centre_y = PITCH_WIDTH / 2
        circle_radius = 10.2
        for side in ("home", "away"):
            for player in self.teammates(side):
                if side == kickoff_side:
                    player.x = min(player.home_x, centre_x) if side == "home" else max(player.home_x, centre_x)
                else:
                    player.x = min(player.home_x, centre_x - 0.8) if side == "home" else max(player.home_x, centre_x + 0.8)
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
                    player.x = min(player.x, centre_x - 0.8) if side == "home" else max(player.x, centre_x + 0.8)
                if side == kickoff_side:
                    player.y = player.home_y
                player.prev_x = player.x
                player.prev_y = player.y
                player.target_x = player.x
                player.target_y = player.y

    def _execute_kickoff(self) -> None:
        kickoff_side = self.state.restart_side or "home"
        striker = next(p for p in self.teammates(kickoff_side) if p.slot == "ST")
        support = next(p for p in self.teammates(kickoff_side) if p.slot in ("AM", "CM", "DM"))
        self.state.restart_mode = None
        self.state.restart_timer = 0.0
        self.state.restart_side = None
        self._give_ball_to(striker, action_type="recovery")
        self._start_pass(striker, support, "kickoff pass", "short_ground")
        self._derive_match_context()

    def _start_goal_kick_setup(self, side: str) -> None:
        self._reset_players_for_restart()
        self.state.restart_mode = "goal_kick_setup"
        self.state.restart_timer = GOAL_KICK_SETUP_SECONDS
        self.state.restart_side = side
        keeper = self._goalkeeper(side)
        spot_x = 6.0 if side == "home" else PITCH_LENGTH - 6.0
        spot_y = PITCH_WIDTH / 2
        self.state.ball.mode = "loose"
        self.state.ball.carrier_id = None
        self.state.ball.target_player_id = None
        self.state.ball.x = spot_x
        self.state.ball.y = spot_y
        self.state.ball.prev_x = self.state.ball.x
        self.state.ball.prev_y = self.state.ball.y
        self.state.ball.target_x = self.state.ball.x
        self.state.ball.target_y = self.state.ball.y
        keeper.target_x = spot_x
        keeper.target_y = spot_y
        self._set_render_state(keeper, "shape", "goal_kick")
        for teammate in self.teammates(side):
            if teammate.slot in ("CB", "LB", "RB", "DM"):
                teammate.target_x = clamp(teammate.home_x + self._side_forward_sign(side) * 2.5, 2, PITCH_LENGTH - 2)
                teammate.target_y = teammate.home_y
        for opp in self.opponents(side):
            opp.target_x = clamp(opp.home_x - self._side_forward_sign(side) * 4.0, 2, PITCH_LENGTH - 2)
            opp.target_y = opp.home_y

    def _execute_goal_kick(self) -> None:
        side = self.state.restart_side or "home"
        keeper = self._goalkeeper(side)
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
                p.fatigue = max(0.0, p.fatigue - 0.3)

    def _settle_ball_for_reception(self, receiver: PlayerState) -> None:
        ball = self.state.ball
        ball.x = clamp(lerp(ball.x, receiver.x, 0.78), 2, PITCH_LENGTH - 2)
        ball.y = clamp(lerp(ball.y, receiver.y, 0.78), 2, PITCH_WIDTH - 2)
        ball.prev_x = ball.x
        ball.prev_y = ball.y

    def _keeper_collection_point(self, keeper: PlayerState, shooter_side: str) -> Tuple[float, float]:
        step = -1.0 if shooter_side == "home" else 1.0
        x = clamp(keeper.x + step * 0.7, 2, PITCH_LENGTH - 2)
        y = clamp(keeper.y, 2, PITCH_WIDTH - 2)
        return x, y

    def _decide_shot_outcome(self, shooter: PlayerState, keeper: PlayerState) -> str:
        goal_dist = self._goal_distance(shooter)
        pressure = self._pressure_on_player(shooter)
        strength = self._team_strength(shooter.side)
        goal = (
            0.10
            + (shooter.profile.attributes["finishing"] - 50.0) / 220.0
            + (shooter.profile.attributes["composure"] - 50.0) / 260.0
            + strength * 0.04
            - pressure * 0.10
            - max(0.0, goal_dist - 18.0) / 110.0
        )
        if self._success_roll(goal):
            return "goal"
        save = 0.45 + keeper.profile.attributes["positioning"] / 260.0
        if self.rng.random() < clamp(save, 0.2, 0.95):
            return "save"
        return "off_target"

    def _team_strength(self, side: str) -> float:
        avg = self.home.avg_ovr if side == "home" else self.away.avg_ovr
        return clamp((avg - 60.0) / 30.0, 0.0, 1.25)

    def _pressure_on_player(self, player: PlayerState) -> float:
        opps = self.opponents(player.side)
        nearest = min(distance((player.x, player.y), (o.x, o.y)) for o in opps)
        return clamp(1.0 - nearest / 16.0, 0.0, 1.0)

    def _receiver_space(self, receiver: PlayerState) -> float:
        opps = self.opponents(receiver.side)
        nearest = min(distance((receiver.x, receiver.y), (o.x, o.y)) for o in opps)
        return clamp(nearest / 18.0, 0.0, 1.4)

    def _goal_distance(self, player: PlayerState) -> float:
        goal = (PITCH_LENGTH, PITCH_WIDTH / 2) if player.side == "home" else (0.0, PITCH_WIDTH / 2)
        return distance((player.x, player.y), goal)

    def _forwardness(self, side: str, x: float) -> float:
        return x if side == "home" else (PITCH_LENGTH - x)

    def _choose_pass_option(self, carrier: PlayerState, receiver: PlayerState) -> Dict[str, object]:
        pass_scores = {ptype: self._pass_type_score(carrier, receiver, ptype) for ptype in PASS_SPEEDS}
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
        pass_options = [self._choose_pass_option(carrier, teammate) for teammate in teammates]
        best_safe = max(pass_options, key=lambda opt: opt["score"])
        best_forward = max(
            pass_options,
            key=lambda opt: opt["score"] + self._forwardness(carrier.side, opt["target"].x) * 0.08,
        )
        shot_score = self._shot_score(carrier)
        dribble_score = self._dribble_score(carrier)
        short_pass_score = float(best_safe["score"]) + strength * 8.0
        forward_pass_score = float(best_forward["score"]) + strength * 6.5

        recycle_bonus = 5.0 if self._pressure_on_player(carrier) > 0.7 else 0.0
        dribble_penalty = 4.5 if self._pressure_on_player(carrier) > 0.65 else 0.0
        scores = {
            "short_pass": short_pass_score + recycle_bonus,
            "forward_pass": forward_pass_score,
            "dribble": dribble_score + strength * 3.5 - dribble_penalty,
            "shoot": shot_score + strength * 3.0,
        }
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
        return (
            attrs["finishing"] * 0.35
            + attrs["composure"] * 0.18
            + attrs["decisions"] * 0.10
            + max(0.0, 26.0 - goal_dist) * 1.0
            + angle_quality * 10.0
            - pressure * 16.0
            - max(0.0, goal_dist - 24.0) * 0.8
        )

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
        player.has_ball = True
        player.control_cooldown = 0.18
        self.state.ball.mode = "carried"
        self.state.ball.carrier_id = player.profile.id
        self.state.ball.target_player_id = None
        self.state.ball.team_in_possession = player.side
        self.state.ball.lead_player_id = player.profile.id
        self.state.ball.loose_owner_bias = player.side
        self.state.restart_mode = None
        self.state.restart_timer = 0.0
        self.state.restart_side = None
        self._register_possession_change(player.side)
        self.state.last_touch_player_id = player.profile.id
        self.state.last_action_type = action_type
        bx, by = self._ball_front_offset(player)
        self.state.ball.x = bx
        self.state.ball.y = by
        self.state.ball.target_x = bx
        self.state.ball.target_y = by
        self._set_render_state(player, "carry", action_type)
        if note:
            self.add_event(note)

    def _start_pass(self, carrier: PlayerState, receiver: PlayerState, label: str, pass_type: str) -> None:
        attrs = carrier.profile.attributes
        recv_attrs = receiver.profile.attributes
        pressure = self._pressure_on_player(carrier)
        recv_space = self._receiver_space(receiver)
        dist = distance((carrier.x, carrier.y), (receiver.x, receiver.y))
        strength = self._team_strength(carrier.side)
        lane_penalty = self._evaluate_pass_lane(carrier, receiver, pass_type)
        target_x, target_y = self._predict_receiver_target(carrier, receiver, pass_type)

        chance = (
            0.50
            + (attrs["passing"] - 50.0) / 150.0
            + (attrs["vision"] - 50.0) / 190.0
            + (recv_attrs["first_touch"] - 50.0) / 250.0
            + recv_space * 0.08
            + strength * 0.04
            - pressure * 0.17
            - lane_penalty * 0.06
            - dist / 190.0
            - carrier.fatigue / 190.0
        )
        if not self._success_roll(chance):
            direction_x = target_x - carrier.x
            direction_y = target_y - carrier.y
            mag = math.hypot(direction_x, direction_y) or 1.0
            direction_x /= mag
            direction_y /= mag
            target_x = clamp(target_x + direction_x * self.rng.uniform(-2.0, 5.5), 2, PITCH_LENGTH - 2)
            target_y = clamp(target_y + direction_y * self.rng.uniform(-2.5, 2.5) + self.rng.uniform(-2.0, 2.0), 2, PITCH_WIDTH - 2)

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
        self.state.ball.travel_time = max(0.24, travel_dist / PASS_SPEEDS[pass_type])
        self.state.ball.speed = PASS_SPEEDS[pass_type]
        self.state.ball.lead_player_id = carrier.profile.id
        self.state.last_touch_player_id = carrier.profile.id
        self.state.last_action_type = "pass"
        carrier.has_ball = False
        receiver.target_x = target_x
        receiver.target_y = target_y
        self._set_render_state(receiver, "receiving", pass_type)
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
        ball = self.state.ball
        carrier_score = (
            carrier.profile.attributes["dribbling"] * 0.35
            + carrier.profile.attributes["composure"] * 0.2
            + self.rng.uniform(0.0, 12.0)
        )
        defender_score = (
            defender.profile.attributes["tackling"] * 0.34
            + defender.profile.attributes["positioning"] * 0.24
            + self.rng.uniform(0.0, 12.0)
        )
        margin = carrier_score - defender_score
        if margin > 10.0:
            self._give_ball_to(carrier, note=f"{carrier.short_name} rides the challenge", action_type="dribble")
            carrier.control_cooldown = 0.12
            return
        ball.mode = "loose"
        ball.carrier_id = None
        ball.x = clamp((carrier.x + defender.x) / 2 + self.rng.uniform(-0.9, 0.9), 2, PITCH_LENGTH - 2)
        ball.y = clamp((carrier.y + defender.y) / 2 + self.rng.uniform(-0.9, 0.9), 2, PITCH_WIDTH - 2)
        ball.loose_owner_bias = carrier.side if margin > -6.0 else defender.side
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
            carrier.target_x = target_x
            carrier.target_y = target_y
            carrier.control_cooldown = 0.14
            self.state.last_action_type = "dribble"
            self._set_render_state(carrier, "carry", "dribble")
            self.add_event(f"{carrier.short_name} carries into space")
        else:
            self._resolve_duel(carrier, nearest)

    def _carry_ball_forward(self, carrier: PlayerState) -> None:
        lead_x, lead_y = self._open_space_target(carrier)
        carrier.target_x = lerp(carrier.x, lead_x, 0.35)
        carrier.target_y = lerp(carrier.y, lead_y, 0.22)
        bx, by = self._ball_front_offset(carrier)
        self.state.ball.x = bx
        self.state.ball.y = by
        self._set_render_state(carrier, "carry", "carry")

    def _start_shot(self, carrier: PlayerState) -> None:
        goal_x = PITCH_LENGTH if carrier.side == "home" else 0.0
        target_y = clamp(PITCH_WIDTH / 2 + self.rng.uniform(-3.5, 3.5), 8, PITCH_WIDTH - 8)
        defending_side = "away" if carrier.side == "home" else "home"
        keeper = self._goalkeeper(defending_side)
        shot_outcome = self._decide_shot_outcome(carrier, keeper)
        if shot_outcome == "save":
            goal_x, target_y = self._keeper_collection_point(keeper, carrier.side)
        elif shot_outcome == "off_target":
            goal_x = PITCH_LENGTH + 4.0 if carrier.side == "home" else -4.0
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
        if self.state.celebration_timer > 0 or self.state.restart_timer > 0:
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
