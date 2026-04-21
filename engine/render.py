from __future__ import annotations
import math
from typing import Tuple

import pygame

from .match_engine import PITCH_LENGTH, PITCH_WIDTH
from .models import MatchState

SCREEN_W = 1280
SCREEN_H = 820
TOP_BAR_H = 40
BOTTOM_TICKER_H = 44
VIEWPORT_Y = TOP_BAR_H
VIEWPORT_H = SCREEN_H - TOP_BAR_H - BOTTOM_TICKER_H
PITCH_PANEL = pygame.Rect(0, VIEWPORT_Y, SCREEN_W, VIEWPORT_H)
VIEWPORT_PAD_X = 28
PITCH_X = 62
PITCH_Y = VIEWPORT_Y
PITCH_W = 1138
PITCH_H = 737
SPEED_OPTIONS = ("X1", "X2", "X4")
PLAYER_OUTLINE_RADIUS = 16
PLAYER_OUTER_RADIUS = 14
PLAYER_INNER_RADIUS = 11
PLAYER_HAS_BALL_RADIUS = 18

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


def compact_team_name(name: str) -> str:
    if len(name) <= 10:
        return name
    words = name.split()
    if len(words) >= 2:
        compact = f"{words[0][0]} {words[-1]}"
        if len(compact) <= 10:
            return compact
    return name[:10]


def world_to_screen(x: float, y: float) -> Tuple[int, int]:
    sx = int(PITCH_X + (x / PITCH_LENGTH) * PITCH_W)
    sy = int(PITCH_Y + (y / PITCH_WIDTH) * PITCH_H)
    return sx, sy


def pitch_length_to_px(length: float) -> int:
    return int((length / PITCH_LENGTH) * PITCH_W)


def pitch_width_to_px(width: float) -> int:
    return int((width / PITCH_WIDTH) * PITCH_H)


def arc_points(center: Tuple[int, int], radius: int, start_deg: float, end_deg: float, steps: int = 18) -> list[Tuple[int, int]]:
    points: list[Tuple[int, int]] = []
    for idx in range(steps + 1):
        t = idx / steps
        angle = math.radians(start_deg + (end_deg - start_deg) * t)
        x = int(center[0] + math.cos(angle) * radius)
        y = int(center[1] + math.sin(angle) * radius)
        points.append((x, y))
    return points


class Renderer:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("FM-Style Match Engine Prototype")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        self.speed_menu_open = False
        self.speed_rect = pygame.Rect(0, 0, 0, 0)
        self.start_rect = pygame.Rect(0, 0, 0, 0)
        self.speed_option_rects: dict[str, pygame.Rect] = {}

    def tick(self) -> float:
        return self.clock.tick(60) / 1000.0

    def handle_click(self, pos: Tuple[int, int]) -> str | None:
        if self.start_rect.collidepoint(pos):
            return "start"
        if self.speed_rect.collidepoint(pos):
            self.speed_menu_open = not self.speed_menu_open
            return None
        if self.speed_menu_open:
            for label, rect in self.speed_option_rects.items():
                if rect.collidepoint(pos):
                    self.speed_menu_open = False
                    return f"speed:{label}"
            self.speed_menu_open = False
        return None

    def draw(
        self,
        state: MatchState,
        fixture_label: str,
        paused: bool,
        alpha: float = 1.0,
        speed_label: str = "x1",
        clock_seconds: float | None = None,
    ) -> None:
        self.screen.fill((18, 18, 22))
        self._layout_pitch()
        pygame.draw.rect(self.screen, (108, 142, 63), PITCH_PANEL)
        self._draw_pitch()
        self._draw_players_and_ball(state, alpha)
        self._draw_pitch_overlay(state, fixture_label)
        self._draw_scoreboard(state, fixture_label, paused, speed_label, clock_seconds)
        self._draw_events(state)
        self._draw_goal_banner(state)
        pygame.display.flip()

    def _layout_pitch(self) -> None:
        global PITCH_X, PITCH_Y, PITCH_W, PITCH_H

        max_height = VIEWPORT_H
        max_width = SCREEN_W - VIEWPORT_PAD_X * 2 - 2 * 28
        pitch_ratio = PITCH_LENGTH / PITCH_WIDTH

        pitch_h = max_height
        pitch_w = int(pitch_h * pitch_ratio)
        if pitch_w > max_width:
            pitch_w = max_width
            pitch_h = int(pitch_w / pitch_ratio)

        goal_depth = int((2.2 / PITCH_LENGTH) * pitch_w)
        total_width = pitch_w + goal_depth * 2
        pitch_x = max(VIEWPORT_PAD_X + goal_depth, (SCREEN_W - total_width) // 2 + goal_depth)
        pitch_y = VIEWPORT_Y

        PITCH_X = pitch_x
        PITCH_Y = pitch_y
        PITCH_W = pitch_w
        PITCH_H = pitch_h

    def _draw_pitch(self) -> None:
        pitch = pygame.Rect(PITCH_X, PITCH_Y, PITCH_W, PITCH_H)
        stripe_h = PITCH_H // 7
        for idx in range(7):
            color = (112, 146, 67) if idx % 2 == 0 else (104, 139, 60)
            band = pygame.Rect(PITCH_X, PITCH_Y + idx * stripe_h, PITCH_W, stripe_h + 2)
            pygame.draw.rect(self.screen, color, band)
        pygame.draw.rect(self.screen, (235, 235, 235), pitch, 4)
        pygame.draw.line(self.screen, (235, 235, 235), (PITCH_X + PITCH_W // 2, PITCH_Y), (PITCH_X + PITCH_W // 2, PITCH_Y + PITCH_H), 3)
        centre_circle_radius = pitch_length_to_px(9.15)
        pygame.draw.circle(self.screen, (235, 235, 235), (PITCH_X + PITCH_W // 2, PITCH_Y + PITCH_H // 2), centre_circle_radius, 3)
        pygame.draw.circle(self.screen, (235, 235, 235), (PITCH_X + PITCH_W // 2, PITCH_Y + PITCH_H // 2), 5)

        penalty_depth = pitch_length_to_px(16.5)
        six_yard_depth = pitch_length_to_px(5.5)
        goal_width = pitch_width_to_px(7.32)
        six_yard_width = pitch_width_to_px(18.32)
        penalty_width = pitch_width_to_px(40.32)
        top_penalty_y = PITCH_Y + (PITCH_H - penalty_width) // 2
        top_six_yard_y = PITCH_Y + (PITCH_H - six_yard_width) // 2
        goal_y = PITCH_Y + (PITCH_H - goal_width) // 2

        left_penalty = pygame.Rect(PITCH_X, top_penalty_y, penalty_depth, penalty_width)
        right_penalty = pygame.Rect(PITCH_X + PITCH_W - penalty_depth, top_penalty_y, penalty_depth, penalty_width)
        left_six_yard = pygame.Rect(PITCH_X, top_six_yard_y, six_yard_depth, six_yard_width)
        right_six_yard = pygame.Rect(PITCH_X + PITCH_W - six_yard_depth, top_six_yard_y, six_yard_depth, six_yard_width)
        pygame.draw.rect(self.screen, (235, 235, 235), left_penalty, 3)
        pygame.draw.rect(self.screen, (235, 235, 235), right_penalty, 3)
        pygame.draw.rect(self.screen, (235, 235, 235), left_six_yard, 3)
        pygame.draw.rect(self.screen, (235, 235, 235), right_six_yard, 3)

        left_goal = pygame.Rect(PITCH_X - pitch_length_to_px(2.2), goal_y, pitch_length_to_px(2.2), goal_width)
        right_goal = pygame.Rect(PITCH_X + PITCH_W, goal_y, pitch_length_to_px(2.2), goal_width)
        pygame.draw.rect(self.screen, (235, 235, 235), left_goal, 3)
        pygame.draw.rect(self.screen, (235, 235, 235), right_goal, 3)

        arc_radius = pitch_length_to_px(9.15)
        penalty_spot_offset = pitch_length_to_px(11.0)
        centre_y = PITCH_Y + PITCH_H // 2
        pygame.draw.arc(
            self.screen,
            (235, 235, 235),
            (PITCH_X + penalty_spot_offset - arc_radius, centre_y - arc_radius, arc_radius * 2, arc_radius * 2),
            math.radians(308),
            math.radians(52),
            3,
        )
        pygame.draw.arc(
            self.screen,
            (235, 235, 235),
            (PITCH_X + PITCH_W - penalty_spot_offset - arc_radius, centre_y - arc_radius, arc_radius * 2, arc_radius * 2),
            math.radians(128),
            math.radians(232),
            3,
        )

        corner_r = max(20, pitch_width_to_px(1.25))
        corner_inset = 2
        pygame.draw.lines(self.screen, (235, 235, 235), False, arc_points((PITCH_X + corner_inset, PITCH_Y + corner_inset), corner_r, 0, 90), 3)
        pygame.draw.lines(self.screen, (235, 235, 235), False, arc_points((PITCH_X + PITCH_W - corner_inset, PITCH_Y + corner_inset), corner_r, 90, 180), 3)
        pygame.draw.lines(self.screen, (235, 235, 235), False, arc_points((PITCH_X + corner_inset, PITCH_Y + PITCH_H - corner_inset), corner_r, -90, 0), 3)
        pygame.draw.lines(self.screen, (235, 235, 235), False, arc_points((PITCH_X + PITCH_W - corner_inset, PITCH_Y + PITCH_H - corner_inset), corner_r, 180, 270), 3)

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
            pygame.draw.circle(self.screen, outline, (sx, sy), PLAYER_OUTLINE_RADIUS, 2)
        pygame.draw.circle(self.screen, (245, 245, 245), (sx, sy), PLAYER_OUTER_RADIUS)
        pygame.draw.circle(self.screen, color, (sx, sy), PLAYER_INNER_RADIUS)
        if math.hypot(facing_x, facing_y) > 0.1:
            start = (int(sx + facing_x * 16), int(sy + facing_y * 16))
            end = (int(sx + facing_x * 25), int(sy + facing_y * 25))
            pygame.draw.line(self.screen, (255, 255, 255), start, end, 2)
        if has_ball:
            pygame.draw.circle(self.screen, (255, 232, 122), (sx, sy), PLAYER_HAS_BALL_RADIUS, 2)
        shirt_number = "".join(ch for ch in player_id if ch.isdigit())[-2:] or "0"
        draw_text(self.screen, shirt_number, sx - text_width(shirt_number, 1) // 2, sy - 5, (255, 255, 255), scale=1)
        label = (name.split()[-1] if name.split() else name)[:12]
        draw_text(self.screen, label, sx - text_width(label, 1) // 2, sy + 22, (18, 18, 18), scale=1)

    def _draw_pitch_overlay(self, state: MatchState, fixture_label: str) -> None:
        if state.phase == "pre_match" and state.awaiting_start:
            home_name = state.home.name
            away_name = state.away.name
            mid = "VS"
            subtitle = "CLICK START"
            title_y = PITCH_Y + PITCH_H // 2 - 58
            draw_text(self.screen, home_name, PITCH_X + (PITCH_W - text_width(home_name, 3)) // 2, title_y, (245, 245, 245), scale=3)
            draw_text(self.screen, mid, PITCH_X + (PITCH_W - text_width(mid, 3)) // 2, title_y + 28, (245, 245, 245), scale=3)
            draw_text(self.screen, away_name, PITCH_X + (PITCH_W - text_width(away_name, 3)) // 2, title_y + 56, (245, 245, 245), scale=3)
            draw_text(
                self.screen,
                subtitle,
                PITCH_X + (PITCH_W - text_width(subtitle, 2)) // 2,
                title_y + 95,
                (248, 187, 32),
                scale=2,
            )
        elif state.phase == "halftime" and state.awaiting_start:
            title = "HALF TIME"
            subtitle = fixture_label[:32]
            title_x = PITCH_X + (PITCH_W - text_width(title, 3)) // 2
            title_y = PITCH_Y + PITCH_H // 2 - 34
            draw_text(self.screen, title, title_x, title_y, (245, 245, 245), scale=3)
            draw_text(
                self.screen,
                subtitle,
                PITCH_X + (PITCH_W - text_width(subtitle, 2)) // 2,
                title_y + 38,
                (248, 187, 32),
                scale=2,
            )

    def _draw_scoreboard(
        self,
        state: MatchState,
        fixture_label: str,
        paused: bool,
        speed_label: str,
        clock_seconds: float | None,
    ) -> None:
        panel = pygame.Rect(0, 0, SCREEN_W, TOP_BAR_H)
        pygame.draw.rect(self.screen, (10, 10, 12), panel)
        shown_seconds = state.elapsed_seconds if clock_seconds is None else clock_seconds
        minute = min(90, int(shown_seconds // 60))
        second = int(shown_seconds % 60)
        minute_text = f"{minute:02d}:{second:02d}"
        self._draw_top_bar(state, minute_text, paused, speed_label)

    def _draw_events(self, state: MatchState) -> None:
        panel = pygame.Rect(0, SCREEN_H - BOTTOM_TICKER_H, SCREEN_W, BOTTOM_TICKER_H)
        pygame.draw.rect(self.screen, (12, 12, 14), panel)
        left_pad = 14
        right_pad = 14
        icon_box = pygame.Rect(left_pad, SCREEN_H - BOTTOM_TICKER_H + 6, 54, BOTTOM_TICKER_H - 12)
        right_icon_box = pygame.Rect(SCREEN_W - right_pad - 54, SCREEN_H - BOTTOM_TICKER_H + 6, 54, BOTTOM_TICKER_H - 12)
        pygame.draw.rect(self.screen, (8, 8, 10), icon_box)
        pygame.draw.rect(self.screen, (8, 8, 10), right_icon_box)
        draw_text(self.screen, "S", icon_box.x + 20, icon_box.y + 8, (240, 240, 240), scale=2)
        draw_text(self.screen, "S", right_icon_box.x + 20, right_icon_box.y + 8, (240, 240, 240), scale=2)

        ticker_x = icon_box.right + 14
        ticker_w = right_icon_box.x - ticker_x - 14
        ticker = pygame.Rect(ticker_x, SCREEN_H - BOTTOM_TICKER_H + 4, ticker_w, BOTTOM_TICKER_H - 8)
        pygame.draw.rect(self.screen, (248, 187, 32), ticker)
        latest = state.events[0] if state.events else None
        ticker_text = "Kick off"
        if latest:
            ticker_text = latest.text[:48]
        draw_text(
            self.screen,
            ticker_text,
            ticker.x + max(16, (ticker.width - text_width(ticker_text, 2)) // 2),
            ticker.y + 11,
            (28, 28, 28),
            scale=2,
        )

    def _draw_goal_banner(self, state: MatchState) -> None:
        if not state.goal_banner_text:
            return
        banner_w = 420
        banner_h = 56
        x = PITCH_X + (PITCH_W - banner_w) // 2
        y = TOP_BAR_H + 12
        panel = pygame.Rect(x, y, banner_w, banner_h)
        pygame.draw.rect(self.screen, (24, 24, 28), panel)
        pygame.draw.rect(self.screen, (255, 220, 90), panel, 3)
        draw_text(self.screen, state.goal_banner_text, x + 18, y + 18, (255, 240, 120), scale=2)

    def _draw_top_bar(self, state: MatchState, minute_text: str, paused: bool, speed_label: str) -> None:
        menu_box = pygame.Rect(0, 0, 62, TOP_BAR_H)
        time_box = pygame.Rect(menu_box.right, 0, 96, TOP_BAR_H)
        home_box = pygame.Rect(time_box.right, 0, 138, TOP_BAR_H)
        score_box = pygame.Rect(home_box.right, 0, 116, TOP_BAR_H)
        away_box = pygame.Rect(score_box.right, 0, 138, TOP_BAR_H)
        pause_box = pygame.Rect(SCREEN_W - 172, 0, 172, TOP_BAR_H)

        pygame.draw.rect(self.screen, (10, 10, 12), menu_box)
        pygame.draw.rect(self.screen, (10, 10, 12), time_box)
        pygame.draw.rect(self.screen, (243, 183, 41), home_box)
        pygame.draw.rect(self.screen, (10, 10, 12), score_box)
        pygame.draw.rect(self.screen, (44, 58, 104), away_box)
        pygame.draw.rect(self.screen, (120, 108, 242), pause_box)

        draw_text(self.screen, "=", 24, 11, (245, 245, 245), scale=2)
        draw_text(self.screen, minute_text, time_box.x + 18, 11, (245, 245, 245), scale=2)

        home_name = compact_team_name(state.home.name)
        away_name = compact_team_name(state.away.name)
        draw_text(self.screen, home_name, home_box.x + 16, 11, (40, 30, 14), scale=2)
        draw_text(self.screen, away_name, away_box.x + 16, 11, (236, 207, 97), scale=2)

        home_score = str(state.home_score)
        away_score = str(state.away_score)
        score_y = 11
        draw_text(self.screen, home_score, score_box.x + 28, score_y, (250, 250, 250), scale=2)
        draw_text(self.screen, away_score, score_box.x + 74, score_y, (250, 250, 250), scale=2)

        indicator_y = TOP_BAR_H // 2
        indicator_start = SCREEN_W // 2 + 80
        for idx in range(6):
            color = (245, 245, 245) if idx == 0 else (110, 110, 114)
            pygame.draw.circle(self.screen, color, (indicator_start + idx * 24, indicator_y), 3)

        speed_w = 84
        speed_h = 28
        speed_x = pause_box.x - 102
        speed_y = 6
        self.speed_rect = pygame.Rect(speed_x, speed_y, speed_w, speed_h)
        pygame.draw.rect(self.screen, (14, 14, 16), self.speed_rect)
        pygame.draw.rect(self.screen, (78, 78, 84), self.speed_rect, 1)
        draw_text(self.screen, speed_label, speed_x + 16, 11, (245, 245, 245), scale=2)
        draw_text(self.screen, "V" if self.speed_menu_open else "/", speed_x + 56, 11, (190, 190, 196), scale=1)
        if state.awaiting_start:
            status_text = "START"
            status_color = (255, 250, 215)
        elif paused:
            status_text = "PAUSE"
            status_color = (245, 245, 245)
        else:
            status_text = "LIVE"
            status_color = (230, 245, 255)
        draw_text(self.screen, status_text, pause_box.x + 42, 11, status_color, scale=2)
        self.start_rect = pause_box
        self._draw_speed_menu(speed_label)

    def _draw_speed_menu(self, current_label: str) -> None:
        self.speed_option_rects = {}
        if not self.speed_menu_open:
            return

        menu_w = self.speed_rect.width
        option_h = 28
        menu_h = option_h * len(SPEED_OPTIONS)
        menu_rect = pygame.Rect(self.speed_rect.x, self.speed_rect.bottom + 4, menu_w, menu_h)
        pygame.draw.rect(self.screen, (14, 14, 16), menu_rect)
        pygame.draw.rect(self.screen, (78, 78, 84), menu_rect, 1)

        for idx, label in enumerate(SPEED_OPTIONS):
            option_rect = pygame.Rect(menu_rect.x, menu_rect.y + idx * option_h, menu_w, option_h)
            self.speed_option_rects[label] = option_rect
            if label == current_label:
                pygame.draw.rect(self.screen, (46, 58, 102), option_rect)
            elif idx > 0:
                pygame.draw.line(self.screen, (60, 60, 66), (option_rect.x + 8, option_rect.y), (option_rect.right - 8, option_rect.y), 1)
            draw_text(self.screen, label, option_rect.x + 16, option_rect.y + 8, (245, 245, 245), scale=2)
