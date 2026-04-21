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
        pygame.draw.rect(self.screen, (34, 120, 52), pitch)
        pygame.draw.rect(self.screen, (235, 235, 235), pitch, 4)
        pygame.draw.line(self.screen, (235, 235, 235), (PITCH_MARGIN + PITCH_W // 2, PITCH_MARGIN), (PITCH_MARGIN + PITCH_W // 2, PITCH_MARGIN + PITCH_H), 3)
        pygame.draw.circle(self.screen, (235, 235, 235), (PITCH_MARGIN + PITCH_W // 2, PITCH_MARGIN + PITCH_H // 2), 72, 3)
        pygame.draw.circle(self.screen, (235, 235, 235), (PITCH_MARGIN + PITCH_W // 2, PITCH_MARGIN + PITCH_H // 2), 4)
        pygame.draw.rect(self.screen, (235, 235, 235), (PITCH_MARGIN, PITCH_MARGIN + 160, 160, 400), 3)
        pygame.draw.rect(self.screen, (235, 235, 235), (PITCH_MARGIN + PITCH_W - 160, PITCH_MARGIN + 160, 160, 400), 3)

    def _draw_players_and_ball(self, state: MatchState, alpha: float) -> None:
        for player in state.home.xi:
            x = player.prev_x + (player.x - player.prev_x) * alpha
            y = player.prev_y + (player.y - player.prev_y) * alpha
            self._draw_player(x, y, player.profile.name, (60, 140, 255), player.has_ball, player.facing_x, player.facing_y, player.render_state)
        for player in state.away.xi:
            x = player.prev_x + (player.x - player.prev_x) * alpha
            y = player.prev_y + (player.y - player.prev_y) * alpha
            self._draw_player(x, y, player.profile.name, (255, 90, 90), player.has_ball, player.facing_x, player.facing_y, player.render_state)

        bx = state.ball.prev_x + (state.ball.x - state.ball.prev_x) * alpha
        by = state.ball.prev_y + (state.ball.y - state.ball.prev_y) * alpha
        sx, sy = world_to_screen(bx, by)
        if state.ball.mode in ("travelling", "shot"):
            tail_x = int(sx - (state.ball.x - state.ball.prev_x) * 18)
            tail_y = int(sy - (state.ball.y - state.ball.prev_y) * 18)
            pygame.draw.line(self.screen, (210, 210, 210), (tail_x, tail_y), (sx, sy), 2)
        pygame.draw.circle(self.screen, (245, 245, 245), (sx, sy), 6)
        pygame.draw.circle(self.screen, (20, 20, 20), (sx, sy), 6, 1)

    def _draw_player(
        self,
        x: float,
        y: float,
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
            pygame.draw.circle(self.screen, outline, (sx, sy), 15, 2)
        pygame.draw.circle(self.screen, color, (sx, sy), 12)
        if math.hypot(facing_x, facing_y) > 0.1:
            facing_end = (int(sx + facing_x * 12), int(sy + facing_y * 12))
            pygame.draw.line(self.screen, (20, 20, 20), (sx, sy), facing_end, 3)
        if has_ball:
            pygame.draw.circle(self.screen, (255, 232, 122), (sx, sy), 15, 2)
        surname = name.split()[-1][:8]
        draw_text(self.screen, surname, sx - text_width(surname, 1) // 2, sy - 30, (255, 255, 255), scale=1)

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
