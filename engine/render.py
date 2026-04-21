from __future__ import annotations
import math
from typing import Tuple

import pygame

from .match_engine import PITCH_LENGTH, PITCH_WIDTH
from .models import MatchState

SCREEN_W = 1280
SCREEN_H = 820
PITCH_MARGIN = 40
PITCH_W = 900
PITCH_H = 720
SIDE_PANEL_X = PITCH_MARGIN + PITCH_W + 24
SIDE_PANEL_W = SCREEN_W - SIDE_PANEL_X - 24

GLYPHS = {
    'A': ["01110","10001","10001","11111","10001","10001","10001"],
    'B': ["11110","10001","10001","11110","10001","10001","11110"],
    'C': ["01110","10001","10000","10000","10000","10001","01110"],
    'D': ["11110","10001","10001","10001","10001","10001","11110"],
    'E': ["11111","10000","10000","11110","10000","10000","11111"],
    'F': ["11111","10000","10000","11110","10000","10000","10000"],
    'G': ["01110","10001","10000","10111","10001","10001","01110"],
    'H': ["10001","10001","10001","11111","10001","10001","10001"],
    'I': ["11111","00100","00100","00100","00100","00100","11111"],
    'J': ["00111","00010","00010","00010","10010","10010","01100"],
    'K': ["10001","10010","10100","11000","10100","10010","10001"],
    'L': ["10000","10000","10000","10000","10000","10000","11111"],
    'M': ["10001","11011","10101","10101","10001","10001","10001"],
    'N': ["10001","11001","10101","10011","10001","10001","10001"],
    'O': ["01110","10001","10001","10001","10001","10001","01110"],
    'P': ["11110","10001","10001","11110","10000","10000","10000"],
    'Q': ["01110","10001","10001","10001","10101","10010","01101"],
    'R': ["11110","10001","10001","11110","10100","10010","10001"],
    'S': ["01111","10000","10000","01110","00001","00001","11110"],
    'T': ["11111","00100","00100","00100","00100","00100","00100"],
    'U': ["10001","10001","10001","10001","10001","10001","01110"],
    'V': ["10001","10001","10001","10001","10001","01010","00100"],
    'W': ["10001","10001","10001","10101","10101","10101","01010"],
    'X': ["10001","10001","01010","00100","01010","10001","10001"],
    'Y': ["10001","10001","01010","00100","00100","00100","00100"],
    'Z': ["11111","00001","00010","00100","01000","10000","11111"],
    '0': ["01110","10001","10011","10101","11001","10001","01110"],
    '1': ["00100","01100","00100","00100","00100","00100","01110"],
    '2': ["01110","10001","00001","00010","00100","01000","11111"],
    '3': ["11110","00001","00001","01110","00001","00001","11110"],
    '4': ["00010","00110","01010","10010","11111","00010","00010"],
    '5': ["11111","10000","10000","11110","00001","00001","11110"],
    '6': ["01110","10000","10000","11110","10001","10001","01110"],
    '7': ["11111","00001","00010","00100","01000","01000","01000"],
    '8': ["01110","10001","10001","01110","10001","10001","01110"],
    '9': ["01110","10001","10001","01111","00001","00001","01110"],
    ':': ["00000","00100","00100","00000","00100","00100","00000"],
    '-': ["00000","00000","00000","11111","00000","00000","00000"],
    '.': ["00000","00000","00000","00000","00000","00110","00110"],
    '[': ["01110","01000","01000","01000","01000","01000","01110"],
    ']': ["01110","00010","00010","00010","00010","00010","01110"],
    '(': ["00010","00100","01000","01000","01000","00100","00010"],
    ')': ["01000","00100","00010","00010","00010","00100","01000"],
    '/': ["00001","00010","00100","01000","10000","00000","00000"],
    'X': ["10001","10001","01010","00100","01010","10001","10001"],
    ' ': ["00000","00000","00000","00000","00000","00000","00000"],
}


def draw_text(surface: pygame.Surface, text: str, x: int, y: int, color: Tuple[int, int, int], scale: int = 2) -> None:
    cx = x
    for ch in text.upper():
        glyph = GLYPHS.get(ch, GLYPHS[' '])
        for row_idx, row in enumerate(glyph):
            for col_idx, bit in enumerate(row):
                if bit == '1':
                    pygame.draw.rect(surface, color, (cx + col_idx * scale, y + row_idx * scale, scale, scale))
        cx += 6 * scale


def text_width(text: str, scale: int = 2) -> int:
    return len(text) * 6 * scale


def world_to_screen(x: float, y: float) -> Tuple[int, int]:
    sx = int(PITCH_MARGIN + (x / PITCH_LENGTH) * PITCH_W)
    sy = int(PITCH_MARGIN + (y / PITCH_WIDTH) * PITCH_H)
    return sx, sy


def pitch_length_to_px(length: float) -> int:
    return int((length / PITCH_LENGTH) * PITCH_W)


def pitch_width_to_px(width: float) -> int:
    return int((width / PITCH_WIDTH) * PITCH_H)


class Renderer:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("FM-Style Match Engine Prototype")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()

    def tick(self) -> float:
        return self.clock.tick(60) / 1000.0

    def draw(
        self,
        state: MatchState,
        fixture_label: str,
        paused: bool,
        alpha: float = 1.0,
        speed_label: str = "x1",
        clock_seconds: float | None = None,
    ) -> None:
        self.screen.fill((20, 20, 24))
        self._draw_pitch()
        self._draw_players_and_ball(state, alpha)
        self._draw_scoreboard(state, fixture_label, paused, speed_label, clock_seconds)
        self._draw_events(state)
        self._draw_goal_banner(state)
        pygame.display.flip()

    def _draw_pitch(self) -> None:
        pitch = pygame.Rect(PITCH_MARGIN, PITCH_MARGIN, PITCH_W, PITCH_H)
        stripe_h = PITCH_H // 7
        for idx in range(7):
            color = (112, 146, 67) if idx % 2 == 0 else (104, 139, 60)
            band = pygame.Rect(PITCH_MARGIN, PITCH_MARGIN + idx * stripe_h, PITCH_W, stripe_h + 2)
            pygame.draw.rect(self.screen, color, band)
        pygame.draw.rect(self.screen, (235, 235, 235), pitch, 4)
        pygame.draw.line(self.screen, (235, 235, 235), (PITCH_MARGIN + PITCH_W // 2, PITCH_MARGIN), (PITCH_MARGIN + PITCH_W // 2, PITCH_MARGIN + PITCH_H), 3)
        pygame.draw.circle(self.screen, (235, 235, 235), (PITCH_MARGIN + PITCH_W // 2, PITCH_MARGIN + PITCH_H // 2), 72, 3)
        pygame.draw.circle(self.screen, (235, 235, 235), (PITCH_MARGIN + PITCH_W // 2, PITCH_MARGIN + PITCH_H // 2), 5)

        penalty_depth = pitch_length_to_px(16.5)
        six_yard_depth = pitch_length_to_px(5.5)
        goal_width = pitch_width_to_px(7.32)
        six_yard_width = pitch_width_to_px(18.32)
        penalty_width = pitch_width_to_px(40.32)
        top_penalty_y = PITCH_MARGIN + (PITCH_H - penalty_width) // 2
        top_six_yard_y = PITCH_MARGIN + (PITCH_H - six_yard_width) // 2
        goal_y = PITCH_MARGIN + (PITCH_H - goal_width) // 2

        left_penalty = pygame.Rect(PITCH_MARGIN, top_penalty_y, penalty_depth, penalty_width)
        right_penalty = pygame.Rect(PITCH_MARGIN + PITCH_W - penalty_depth, top_penalty_y, penalty_depth, penalty_width)
        left_six_yard = pygame.Rect(PITCH_MARGIN, top_six_yard_y, six_yard_depth, six_yard_width)
        right_six_yard = pygame.Rect(PITCH_MARGIN + PITCH_W - six_yard_depth, top_six_yard_y, six_yard_depth, six_yard_width)
        pygame.draw.rect(self.screen, (235, 235, 235), left_penalty, 3)
        pygame.draw.rect(self.screen, (235, 235, 235), right_penalty, 3)
        pygame.draw.rect(self.screen, (235, 235, 235), left_six_yard, 3)
        pygame.draw.rect(self.screen, (235, 235, 235), right_six_yard, 3)

        left_goal = pygame.Rect(PITCH_MARGIN - pitch_length_to_px(2.2), goal_y, pitch_length_to_px(2.2), goal_width)
        right_goal = pygame.Rect(PITCH_MARGIN + PITCH_W, goal_y, pitch_length_to_px(2.2), goal_width)
        pygame.draw.rect(self.screen, (235, 235, 235), left_goal, 3)
        pygame.draw.rect(self.screen, (235, 235, 235), right_goal, 3)

        arc_radius = pitch_length_to_px(9.15)
        penalty_spot_offset = pitch_length_to_px(11.0)
        centre_y = PITCH_MARGIN + PITCH_H // 2
        pygame.draw.arc(
            self.screen,
            (235, 235, 235),
            (PITCH_MARGIN + penalty_spot_offset - arc_radius, centre_y - arc_radius, arc_radius * 2, arc_radius * 2),
            math.radians(308),
            math.radians(52),
            3,
        )
        pygame.draw.arc(
            self.screen,
            (235, 235, 235),
            (PITCH_MARGIN + PITCH_W - penalty_spot_offset - arc_radius, centre_y - arc_radius, arc_radius * 2, arc_radius * 2),
            math.radians(128),
            math.radians(232),
            3,
        )

        corner_r = 38
        pygame.draw.arc(self.screen, (235, 235, 235), (PITCH_MARGIN, PITCH_MARGIN, corner_r * 2, corner_r * 2), math.pi, math.pi * 1.5, 3)
        pygame.draw.arc(self.screen, (235, 235, 235), (PITCH_MARGIN + PITCH_W - corner_r * 2, PITCH_MARGIN, corner_r * 2, corner_r * 2), math.pi * 1.5, math.pi * 2, 3)
        pygame.draw.arc(self.screen, (235, 235, 235), (PITCH_MARGIN, PITCH_MARGIN + PITCH_H - corner_r * 2, corner_r * 2, corner_r * 2), math.pi / 2, math.pi, 3)
        pygame.draw.arc(self.screen, (235, 235, 235), (PITCH_MARGIN + PITCH_W - corner_r * 2, PITCH_MARGIN + PITCH_H - corner_r * 2, corner_r * 2, corner_r * 2), 0, math.pi / 2, 3)

    def _draw_players_and_ball(self, state: MatchState, alpha: float) -> None:
        for player in state.home.xi:
            x = player.prev_x + (player.x - player.prev_x) * alpha
            y = player.prev_y + (player.y - player.prev_y) * alpha
            self._draw_player(x, y, player.profile.id, player.profile.name, (50, 95, 230), player.has_ball, player.facing_x, player.facing_y, player.render_state)
        for player in state.away.xi:
            x = player.prev_x + (player.x - player.prev_x) * alpha
            y = player.prev_y + (player.y - player.prev_y) * alpha
            self._draw_player(x, y, player.profile.id, player.profile.name, (225, 88, 88), player.has_ball, player.facing_x, player.facing_y, player.render_state)

        bx = state.ball.prev_x + (state.ball.x - state.ball.prev_x) * alpha
        by = state.ball.prev_y + (state.ball.y - state.ball.prev_y) * alpha
        sx, sy = world_to_screen(bx, by)
        pygame.draw.circle(self.screen, (245, 245, 245), (sx, sy), 6)
        pygame.draw.circle(self.screen, (20, 20, 20), (sx, sy), 6, 1)

    def _draw_player(
        self,
        x: float,
        y: float,
        player_id: str,
        name: str,
        color: Tuple[int, int, int],
        has_ball: bool,
        facing_x: float,
        facing_y: float,
        render_state: str,
    ) -> None:
        sx, sy = world_to_screen(x, y)
        outline = {
            "receiving": (255, 232, 122),
            "pressing": (255, 170, 90),
            "cover": (180, 235, 255),
            "carry": (120, 255, 160),
            "shooting": (255, 120, 120),
            "run": (220, 220, 220),
            "transition": (255, 205, 145),
            "celebrate": (255, 236, 90),
        }.get(render_state)

        if outline:
            pygame.draw.circle(self.screen, outline, (sx, sy), 20, 2)
        pygame.draw.circle(self.screen, (245, 245, 245), (sx, sy), 18)
        pygame.draw.circle(self.screen, color, (sx, sy), 15)
        if math.hypot(facing_x, facing_y) > 0.1:
            start = (int(sx + facing_x * 18), int(sy + facing_y * 18))
            end = (int(sx + facing_x * 28), int(sy + facing_y * 28))
            pygame.draw.line(self.screen, (255, 255, 255), start, end, 2)
        if has_ball:
            pygame.draw.circle(self.screen, (255, 232, 122), (sx, sy), 22, 2)
        shirt_number = "".join(ch for ch in player_id if ch.isdigit())[-2:] or "0"
        draw_text(self.screen, shirt_number, sx - text_width(shirt_number, 1) // 2, sy - 5, (255, 255, 255), scale=1)
        label = name[:12]
        draw_text(self.screen, label, sx - text_width(label, 1) // 2, sy + 24, (18, 18, 18), scale=1)

    def _draw_scoreboard(
        self,
        state: MatchState,
        fixture_label: str,
        paused: bool,
        speed_label: str,
        clock_seconds: float | None,
    ) -> None:
        panel = pygame.Rect(0, 0, SCREEN_W, 34)
        pygame.draw.rect(self.screen, (12, 12, 16), panel)
        score = f"{state.home.name} {state.home_score} - {state.away_score} {state.away.name}"
        draw_text(self.screen, score, 30, SCREEN_H - 70, (255, 255, 255), scale=3)
        shown_seconds = state.elapsed_seconds if clock_seconds is None else clock_seconds
        minute = min(90, int(shown_seconds // 60))
        second = int(shown_seconds % 60)
        minute_text = f"{minute:02d}:{second:02d}"
        draw_text(self.screen, minute_text, SCREEN_W - 220, SCREEN_H - 70, (255, 232, 122), scale=3)
        draw_text(self.screen, speed_label, SCREEN_W - 90, SCREEN_H - 70, (255, 255, 255), scale=3)
        top = fixture_label + (" [PAUSED]" if paused else "")
        draw_text(self.screen, top, 20, 8, (255, 255, 255), scale=2)

    def _draw_events(self, state: MatchState) -> None:
        x = SIDE_PANEL_X + 12
        y = 60
        panel = pygame.Rect(SIDE_PANEL_X, y - 14, SIDE_PANEL_W, 260)
        pygame.draw.rect(self.screen, (12, 12, 16), panel)
        draw_text(self.screen, "Commentary", x, y, (255, 255, 255), scale=2)
        line_y = y + 30
        for event in state.events[:8]:
            line = f"{event.minute:02d}:{event.second:02d}  {event.text[:18]}"
            draw_text(self.screen, line, x, line_y, (220, 220, 220), scale=1)
            line_y += 22

    def _draw_goal_banner(self, state: MatchState) -> None:
        if not state.goal_banner_text:
            return
        banner_w = 420
        banner_h = 56
        x = PITCH_MARGIN + (PITCH_W - banner_w) // 2
        y = 54
        panel = pygame.Rect(x, y, banner_w, banner_h)
        pygame.draw.rect(self.screen, (24, 24, 28), panel)
        pygame.draw.rect(self.screen, (255, 220, 90), panel, 3)
        draw_text(self.screen, state.goal_banner_text, x + 18, y + 18, (255, 240, 120), scale=2)
