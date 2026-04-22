from __future__ import annotations
import math
from typing import Tuple

import pygame

from .match_engine import PITCH_LENGTH, PITCH_WIDTH
from .models import MatchState, stamina_ratio_for_player

SCREEN_W = 1560
SCREEN_H = 900
TOP_BAR_H = 40
BOTTOM_TICKER_H = 44
VIEWPORT_Y = TOP_BAR_H
VIEWPORT_H = SCREEN_H - TOP_BAR_H - BOTTOM_TICKER_H
SIDE_PANEL_W = 308
PANEL_GAP = 14
SIDE_PANEL = pygame.Rect(0, VIEWPORT_Y, SIDE_PANEL_W, VIEWPORT_H)
PITCH_PANEL = pygame.Rect(SIDE_PANEL_W + PANEL_GAP, VIEWPORT_Y, SCREEN_W - SIDE_PANEL_W - PANEL_GAP, VIEWPORT_H)
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


def configure_display_metrics(width: int, height: int) -> None:
    global SCREEN_W, SCREEN_H, VIEWPORT_H, SIDE_PANEL_W, PANEL_GAP, SIDE_PANEL, PITCH_PANEL, VIEWPORT_PAD_X, PITCH_X, PITCH_Y, PITCH_W, PITCH_H

    SCREEN_W = int(width)
    SCREEN_H = int(height)
    VIEWPORT_H = SCREEN_H - TOP_BAR_H - BOTTOM_TICKER_H
    SIDE_PANEL_W = max(300, int(SCREEN_W * 0.2))
    PANEL_GAP = max(14, SCREEN_W // 120)
    SIDE_PANEL = pygame.Rect(0, VIEWPORT_Y, SIDE_PANEL_W, VIEWPORT_H)
    PITCH_PANEL = pygame.Rect(SIDE_PANEL_W + PANEL_GAP, VIEWPORT_Y, SCREEN_W - SIDE_PANEL_W - PANEL_GAP, VIEWPORT_H)
    VIEWPORT_PAD_X = max(28, SCREEN_W // 56)
    PITCH_X = PITCH_PANEL.x + 62
    PITCH_Y = VIEWPORT_Y
    PITCH_W = max(900, PITCH_PANEL.width - 124)
    PITCH_H = max(560, VIEWPORT_H - 56)

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


def short_display_name(name: str, max_len: int = 14) -> str:
    parts = name.split()
    if not parts:
        return name[:max_len]
    label = parts[-1]
    if len(label) <= max_len:
        return label
    return label[:max_len]


def hex_to_rgb(value: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
    if not isinstance(value, str):
        return fallback
    text = value.strip().lstrip("#")
    if len(text) != 6:
        return fallback
    try:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except ValueError:
        return fallback


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


def scale_points(points: list[Tuple[float, float]], rect: pygame.Rect) -> list[Tuple[int, int]]:
    return [
        (rect.x + int(px * rect.width), rect.y + int(py * rect.height))
        for px, py in points
    ]


class Renderer:
    @staticmethod
    def hex_to_rgb_static(value: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        return hex_to_rgb(value, fallback)

    def __init__(self, width: int = 1560, height: int = 900, fullscreen: bool = False) -> None:
        pygame.init()
        pygame.display.set_caption("FM-Style Match Engine Prototype")
        self.ui_click_targets: dict[str, pygame.Rect] = {}
        self.fullscreen = fullscreen
        self.display_index = 0
        self.screen = pygame.Surface((1, 1))
        self.set_display_mode(width, height, fullscreen, 0)
        self.clock = pygame.time.Clock()
        self.speed_menu_open = False
        self.speed_rect = pygame.Rect(0, 0, 0, 0)
        self.start_rect = pygame.Rect(0, 0, 0, 0)
        self.speed_option_rects: dict[str, pygame.Rect] = {}

    def tick(self) -> float:
        return self.clock.tick(60) / 1000.0

    def set_display_mode(self, width: int, height: int, fullscreen: bool, display_index: int = 0) -> None:
        configure_display_metrics(width, height)
        self.fullscreen = fullscreen
        display_count = max(1, pygame.display.get_num_displays())
        self.display_index = max(0, min(display_count - 1, int(display_index)))
        flags = pygame.FULLSCREEN if fullscreen else 0
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags, display=self.display_index)

    def available_displays(self) -> list[dict]:
        count = max(1, pygame.display.get_num_displays())
        sizes = pygame.display.get_desktop_sizes() or []
        choices: list[dict] = []
        for idx in range(count):
            if idx < len(sizes):
                width, height = sizes[idx]
                label = f"Monitor {idx + 1} ({width}x{height})"
            else:
                label = f"Monitor {idx + 1}"
            choices.append({"value": str(idx), "label": label})
        return choices

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

    def handle_ui_click(self, pos: Tuple[int, int]) -> str | None:
        for action, rect in self.ui_click_targets.items():
            if rect.collidepoint(pos):
                return action
        return None

    def _draw_club_badge(self, badge: dict | None, rect: pygame.Rect) -> None:
        badge = badge or {}
        template_id = str(badge.get("template_id", "1"))
        primary = hex_to_rgb(str(badge.get("primary", "#2E3A6A")), (46, 58, 106))
        secondary = hex_to_rgb(str(badge.get("secondary", "#F5F5F5")), (245, 245, 245))
        border = hex_to_rgb(str(badge.get("border", "#F5F5F5")), (245, 245, 245))

        silhouettes = {
            "1": [(0.5, 0.02), (0.12, 0.1), (0.12, 0.44), (0.18, 0.68), (0.32, 0.88), (0.5, 0.98), (0.68, 0.88), (0.82, 0.68), (0.88, 0.44), (0.88, 0.1)],
            "2": [(0.5, 0.06), (0.16, 0.14), (0.1, 0.36), (0.16, 0.72), (0.32, 0.9), (0.5, 0.98), (0.68, 0.9), (0.84, 0.72), (0.9, 0.36), (0.84, 0.14)],
            "3": [(0.5, 0.05), (0.18, 0.14), (0.18, 0.72), (0.3, 0.88), (0.5, 0.98), (0.7, 0.88), (0.82, 0.72), (0.82, 0.14)],
            "4": [(0.5, 0.04), (0.18, 0.14), (0.18, 0.58), (0.26, 0.78), (0.5, 0.98), (0.74, 0.78), (0.82, 0.58), (0.82, 0.14)],
        }
        points = scale_points(silhouettes.get(template_id, silhouettes["1"]), rect)

        badge_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        local_rect = badge_surface.get_rect()
        local_points = [(x - rect.x, y - rect.y) for x, y in points]
        pygame.draw.polygon(badge_surface, primary, local_points)

        if template_id == "1":
            badge_surface.set_clip(pygame.Rect(local_rect.width // 2, 0, local_rect.width // 2, local_rect.height))
            pygame.draw.polygon(badge_surface, secondary, local_points)
        elif template_id == "2":
            stripe_w = max(8, local_rect.width // 4)
            badge_surface.set_clip(pygame.Rect((local_rect.width - stripe_w) // 2, 0, stripe_w, local_rect.height))
            pygame.draw.polygon(badge_surface, secondary, local_points)
        elif template_id == "3":
            band = [
                (int(local_rect.width * 0.18), int(local_rect.height * 0.2)),
                (int(local_rect.width * 0.36), int(local_rect.height * 0.1)),
                (int(local_rect.width * 0.82), int(local_rect.height * 0.78)),
                (int(local_rect.width * 0.64), int(local_rect.height * 0.88)),
            ]
            pygame.draw.polygon(badge_surface, secondary, band)
        else:
            inner = pygame.Rect(0, 0, max(10, int(local_rect.width * 0.42)), max(12, int(local_rect.height * 0.5)))
            inner.center = (local_rect.centerx, int(local_rect.height * 0.48))
            inner_points = [
                (inner.centerx, inner.top),
                (inner.left, inner.top + inner.height // 5),
                (inner.left, inner.centery + inner.height // 7),
                (inner.centerx, inner.bottom),
                (inner.right, inner.centery + inner.height // 7),
                (inner.right, inner.top + inner.height // 5),
            ]
            pygame.draw.polygon(badge_surface, secondary, inner_points)

        badge_surface.set_clip(None)
        self.screen.blit(badge_surface, rect.topleft)
        pygame.draw.polygon(self.screen, border, points, width=max(2, rect.width // 18))

    def draw(
        self,
        state: MatchState,
        fixture_label: str,
        paused: bool,
        alpha: float = 1.0,
        speed_label: str = "x1",
        clock_seconds: float | None = None,
        commentary_colors: tuple[Tuple[int, int, int], Tuple[int, int, int]] | None = None,
        present: bool = True,
    ) -> None:
        self.ui_click_targets = {}
        self.screen.fill((18, 18, 22))
        self._layout_pitch()
        self._draw_side_panel(state)
        pygame.draw.rect(self.screen, (108, 142, 63), PITCH_PANEL)
        self._draw_pitch()
        self._draw_players_and_ball(state, alpha)
        self._draw_pitch_overlay(state, fixture_label)
        self._draw_scoreboard(state, fixture_label, paused, speed_label, clock_seconds)
        self._draw_events(state, commentary_colors)
        self._draw_goal_banner(state)
        if present:
            pygame.display.flip()

    def _layout_pitch(self) -> None:
        global PITCH_X, PITCH_Y, PITCH_W, PITCH_H

        max_height = VIEWPORT_H - 32
        max_width = PITCH_PANEL.width - VIEWPORT_PAD_X * 2 - 2 * 28
        pitch_ratio = PITCH_LENGTH / PITCH_WIDTH

        pitch_h = max_height
        pitch_w = int(pitch_h * pitch_ratio)
        if pitch_w > max_width:
            pitch_w = max_width
            pitch_h = int(pitch_w / pitch_ratio)

        goal_depth = int((2.2 / PITCH_LENGTH) * pitch_w)
        total_width = pitch_w + goal_depth * 2
        pitch_x = max(PITCH_PANEL.x + VIEWPORT_PAD_X + goal_depth, PITCH_PANEL.x + (PITCH_PANEL.width - total_width) // 2 + goal_depth)
        pitch_y = VIEWPORT_Y + (VIEWPORT_H - pitch_h) // 2

        PITCH_X = pitch_x
        PITCH_Y = pitch_y
        PITCH_W = pitch_w
        PITCH_H = pitch_h

    def _draw_side_panel(self, state: MatchState) -> None:
        panel = SIDE_PANEL.inflate(-10, -10)
        pygame.draw.rect(self.screen, (12, 12, 14), panel, border_radius=4)
        pygame.draw.rect(self.screen, (44, 44, 48), panel, 1, border_radius=4)
        mid_y = panel.y + 8
        section_h = (panel.height - 22) // 2
        self._draw_team_squad_section(
            state.home,
            state,
            pygame.Rect(panel.x + 8, mid_y, panel.width - 16, section_h - 6),
        )
        self._draw_team_squad_section(
            state.away,
            state,
            pygame.Rect(panel.x + 8, mid_y + section_h + 6, panel.width - 16, section_h - 6),
        )

    def _draw_team_squad_section(
        self,
        team,
        state: MatchState,
        rect: pygame.Rect,
    ) -> None:
        primary = hex_to_rgb(team.club.colors.get("primary", "#2E3A6A"), (46, 58, 106))
        secondary = hex_to_rgb(team.club.colors.get("secondary", "#F5F5F5"), (245, 245, 245))
        pygame.draw.rect(self.screen, (18, 18, 22), rect, border_radius=4)
        pygame.draw.rect(self.screen, primary, (rect.x, rect.y, rect.width, 28), border_radius=4)
        draw_text(self.screen, compact_team_name(team.name), rect.x + 10, rect.y + 8, secondary, scale=2)

        col_name = rect.x + 10
        col_avg = rect.right - 106
        col_stam = rect.right - 72
        y = rect.y + 36
        draw_text(self.screen, "XI", col_name, y + 2, (245, 245, 245), scale=1)
        draw_text(self.screen, "AVG", col_avg, y, (180, 180, 186), scale=1)
        draw_text(self.screen, "STM", col_stam, y, (180, 180, 186), scale=1)
        y += 18

        for player in team.xi:
            self._draw_squad_row(
                rect,
                y,
                player.profile.name,
                player.profile.id,
                6.8,
                stamina_ratio_for_player(player.profile.attributes.get("stamina", 70.0), player.fatigue),
                player.yellow_cards,
                player.red_card,
                state.player_goals.get(player.profile.id, 0),
                state.player_assists.get(player.profile.id, 0),
            )
            y += 18

        y += 4
        draw_text(self.screen, "BENCH", col_name, y + 2, (245, 245, 245), scale=1)
        y += 18
        for bench_player in team.bench[:7]:
            self._draw_squad_row(
                rect,
                y,
                bench_player.name,
                bench_player.id,
                6.8,
                max(0.08, min(1.0, bench_player.current_stamina / 100.0)),
                0,
                False,
                state.player_goals.get(bench_player.id, 0),
                state.player_assists.get(bench_player.id, 0),
            )
            y += 18

    def _draw_squad_row(
        self,
        rect: pygame.Rect,
        y: int,
        name: str,
        player_id: str,
        avg_score: float,
        stamina_ratio: float,
        yellow_cards: int,
        red_card: bool,
        goals: int,
        assists: int,
    ) -> None:
        shirt_number = "".join(ch for ch in player_id if ch.isdigit())[-2:] or "0"
        draw_text(self.screen, shirt_number.rjust(2, "0"), rect.x + 8, y + 2, (168, 168, 174), scale=1)
        label = short_display_name(name, 11)
        draw_text(self.screen, label, rect.x + 28, y + 2, (238, 238, 240), scale=1)

        icon_x = rect.right - 132
        if goals > 0:
            self._draw_goal_icon(icon_x, y + 8)
            if goals > 1:
                draw_text(self.screen, str(goals), icon_x + 8, y + 2, (240, 240, 240), scale=1)
            icon_x += 14
        if assists > 0:
            self._draw_assist_icon(icon_x, y + 8)
            if assists > 1:
                draw_text(self.screen, str(assists), icon_x + 8, y + 2, (240, 240, 240), scale=1)

        avg_text = f"{avg_score:.1f}"
        draw_text(self.screen, avg_text, rect.right - 102, y + 2, (220, 220, 224), scale=1)

        bar_rect = pygame.Rect(rect.right - 66, y + 3, 38, 8)
        pygame.draw.rect(self.screen, (38, 38, 42), bar_rect)
        fill_w = max(4, int(bar_rect.width * max(0.0, min(1.0, stamina_ratio))))
        bar_color = (116, 208, 120) if stamina_ratio > 0.55 else (232, 190, 72) if stamina_ratio > 0.3 else (220, 96, 96)
        pygame.draw.rect(self.screen, bar_color, (bar_rect.x, bar_rect.y, fill_w, bar_rect.height))
        pygame.draw.rect(self.screen, (68, 68, 74), bar_rect, 1)

        badge_x = rect.right - 22
        if red_card:
            pygame.draw.rect(self.screen, (206, 54, 54), (badge_x, y + 1, 12, 14))
            draw_text(self.screen, "R", badge_x + 2, y + 4, (255, 255, 255), scale=1)
        elif yellow_cards > 0:
            pygame.draw.rect(self.screen, (236, 202, 56), (badge_x, y + 1, 12, 14))
            draw_text(self.screen, "Y", badge_x + 2, y + 4, (28, 28, 28), scale=1)

    def _draw_goal_icon(self, x: int, y: int) -> None:
        pygame.draw.circle(self.screen, (244, 244, 244), (x, y), 5)
        pygame.draw.circle(self.screen, (18, 18, 22), (x, y), 5, 1)
        pygame.draw.circle(self.screen, (18, 18, 22), (x, y), 2)

    def _draw_assist_icon(self, x: int, y: int) -> None:
        pygame.draw.line(self.screen, (236, 236, 236), (x - 4, y + 3), (x + 3, y - 4), 2)
        pygame.draw.line(self.screen, (236, 236, 236), (x + 1, y - 5), (x + 5, y - 1), 2)
        pygame.draw.line(self.screen, (236, 236, 236), (x + 5, y - 1), (x + 3, y + 2), 2)

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
        self._draw_ball(bx, by)

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
            self._draw_facing_arrow(sx, sy, facing_x, facing_y)
        if has_ball:
            pygame.draw.circle(self.screen, (255, 232, 122), (sx, sy), PLAYER_HAS_BALL_RADIUS, 2)
        shirt_number = "".join(ch for ch in player_id if ch.isdigit())[-2:] or "0"
        draw_text(self.screen, shirt_number, sx - text_width(shirt_number, 1) // 2, sy - 5, (255, 255, 255), scale=1)
        label = (name.split()[-1] if name.split() else name)[:12]
        draw_text(self.screen, label, sx - text_width(label, 1) // 2, sy + 22, (18, 18, 18), scale=1)

    def _draw_facing_arrow(self, sx: int, sy: int, facing_x: float, facing_y: float) -> None:
        mag = math.hypot(facing_x, facing_y)
        if mag < 0.1:
            return
        ux = facing_x / mag
        uy = facing_y / mag
        tip_x = sx + ux * 24
        tip_y = sy + uy * 24
        base_x = sx + ux * 17
        base_y = sy + uy * 17
        perp_x = -uy
        perp_y = ux
        left = (int(base_x + perp_x * 4), int(base_y + perp_y * 4))
        right = (int(base_x - perp_x * 4), int(base_y - perp_y * 4))
        tip = (int(tip_x), int(tip_y))
        pygame.draw.polygon(self.screen, (255, 255, 255), [tip, left, right])

    def _draw_ball(self, x: float, y: float) -> None:
        sx, sy = world_to_screen(x, y)
        pygame.draw.circle(self.screen, (245, 245, 245), (sx, sy), 6)
        pygame.draw.circle(self.screen, (20, 20, 20), (sx, sy), 6, 1)
        pygame.draw.circle(self.screen, (20, 20, 20), (sx, sy), 2)
        pygame.draw.circle(self.screen, (20, 20, 20), (sx - 3, sy - 1), 1)
        pygame.draw.circle(self.screen, (20, 20, 20), (sx + 3, sy - 1), 1)
        pygame.draw.circle(self.screen, (20, 20, 20), (sx - 2, sy + 3), 1)
        pygame.draw.circle(self.screen, (20, 20, 20), (sx + 2, sy + 3), 1)

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

    def _draw_events(self, state: MatchState, commentary_colors: tuple[Tuple[int, int, int], Tuple[int, int, int]] | None = None) -> None:
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
        if commentary_colors is None:
            ticker_primary = hex_to_rgb(state.home.club.colors.get("primary", "#F8BB20"), (248, 187, 32))
            ticker_secondary = hex_to_rgb(state.home.club.colors.get("secondary", "#1C1C1C"), (28, 28, 28))
        else:
            ticker_primary, ticker_secondary = commentary_colors
        pygame.draw.rect(self.screen, ticker_primary, ticker)
        latest = state.events[0] if state.events else None
        ticker_text = "Kick off"
        if latest:
            ticker_text = latest.text[:48]
        draw_text(
            self.screen,
            ticker_text,
            ticker.x + max(16, (ticker.width - text_width(ticker_text, 2)) // 2),
            ticker.y + 11,
            ticker_secondary,
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
        time_box = pygame.Rect(14, 0, 96, TOP_BAR_H)
        home_box = pygame.Rect(time_box.right, 0, 138, TOP_BAR_H)
        score_box = pygame.Rect(home_box.right, 0, 116, TOP_BAR_H)
        away_box = pygame.Rect(score_box.right, 0, 138, TOP_BAR_H)
        pause_box = pygame.Rect(SCREEN_W - 142, 0, 142, TOP_BAR_H)

        home_primary = hex_to_rgb(state.home.club.colors.get("primary", "#F3B729"), (243, 183, 41))
        home_secondary = hex_to_rgb(state.home.club.colors.get("secondary", "#281E0E"), (40, 30, 14))
        away_primary = hex_to_rgb(state.away.club.colors.get("primary", "#2C3A68"), (44, 58, 104))
        away_secondary = hex_to_rgb(state.away.club.colors.get("secondary", "#ECCF61"), (236, 207, 97))

        pygame.draw.rect(self.screen, (10, 10, 12), time_box)
        pygame.draw.rect(self.screen, home_primary, home_box)
        pygame.draw.rect(self.screen, (10, 10, 12), score_box)
        pygame.draw.rect(self.screen, away_primary, away_box)
        pygame.draw.rect(self.screen, (248, 187, 32), pause_box)

        draw_text(self.screen, minute_text, time_box.x + 10, 11, (245, 245, 245), scale=2)

        home_name = compact_team_name(state.home.name)
        away_name = compact_team_name(state.away.name)
        draw_text(self.screen, home_name, home_box.x + 16, 11, home_secondary, scale=2)
        draw_text(self.screen, away_name, away_box.x + 16, 11, away_secondary, scale=2)

        home_score = str(state.home_score)
        away_score = str(state.away_score)
        score_y = 11
        draw_text(self.screen, home_score, score_box.x + 28, score_y, (250, 250, 250), scale=2)
        draw_text(self.screen, away_score, score_box.x + 74, score_y, (250, 250, 250), scale=2)

        speed_w = 84
        speed_h = 28
        speed_x = pause_box.x - 96
        speed_y = 6
        self.speed_rect = pygame.Rect(speed_x, speed_y, speed_w, speed_h)
        pygame.draw.rect(self.screen, (14, 14, 16), self.speed_rect)
        pygame.draw.rect(self.screen, (78, 78, 84), self.speed_rect, 1)
        draw_text(self.screen, speed_label, speed_x + (speed_w - text_width(speed_label, 2)) // 2, 11, (245, 245, 245), scale=2)
        if state.awaiting_start:
            status_text = "START"
            status_color = (255, 250, 215)
        elif paused:
            status_text = "PAUSE"
            status_color = (245, 245, 245)
        else:
            status_text = "LIVE"
            status_color = (230, 245, 255)
        draw_text(self.screen, status_text, pause_box.x + (pause_box.width - text_width(status_text, 2)) // 2, 11, status_color, scale=2)
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

    def draw_app_view(self, view: dict, present: bool = True) -> None:
        self.ui_click_targets = {}
        self.screen.fill((20, 22, 18))
        screen = view.get("screen", "menu")
        if screen == "overview":
            self._draw_overview_background(view)
        else:
            self._draw_app_background()
        if screen == "menu":
            self._draw_main_menu(view)
        elif screen == "new_game_name":
            self._draw_manager_setup(view)
        elif screen == "select_league":
            self._draw_league_select(view)
        elif screen == "select_club":
            self._draw_club_select(view)
        elif screen == "options":
            self._draw_options_screen(view)
        elif screen == "load_game":
            self._draw_load_game_screen(view)
        elif screen == "overview":
            self._draw_overview_screen(view)
        if present:
            pygame.display.flip()

    def _draw_app_background(self) -> None:
        sky = pygame.Rect(0, 0, SCREEN_W, max(120, SCREEN_H // 5))
        pitch = pygame.Rect(0, sky.bottom - 10, SCREEN_W, SCREEN_H - sky.height + 10)
        pygame.draw.rect(self.screen, (22, 24, 28), sky)
        pygame.draw.rect(self.screen, (108, 142, 63), pitch)
        stripe_h = max(70, pitch.height // 6)
        for idx in range(6):
            color = (112, 146, 67) if idx % 2 == 0 else (104, 139, 60)
            pygame.draw.rect(self.screen, color, (0, pitch.y + idx * stripe_h, SCREEN_W, stripe_h + 2))

    def _draw_overview_background(self, view: dict) -> None:
        overview = view.get("overview", {})
        clubs = overview.get("clubs", [])
        club_id = overview.get("club_id")
        primary_hex = next((club["primary_color"] for club in clubs if club["id"] == club_id), "#2E3A6A")
        primary = hex_to_rgb(primary_hex, (46, 58, 106))
        dark = tuple(max(12, int(channel * 0.28)) for channel in primary)
        mid = tuple(max(20, int(channel * 0.52)) for channel in primary)
        self.screen.fill(dark)
        band_h = max(88, SCREEN_H // 7)
        for idx in range(8):
            color = mid if idx % 2 == 0 else primary
            pygame.draw.rect(self.screen, color, (0, idx * band_h, SCREEN_W, band_h + 2))

    def _register_ui(self, action: str, rect: pygame.Rect) -> None:
        self.ui_click_targets[action] = rect

    def _draw_ui_button(
        self,
        rect: pygame.Rect,
        label: str,
        fill: Tuple[int, int, int],
        text: Tuple[int, int, int],
        action: str | None = None,
        scale: int = 2,
    ) -> None:
        pygame.draw.rect(self.screen, fill, rect, border_radius=6)
        pygame.draw.rect(self.screen, (22, 22, 26), rect, 2, border_radius=6)
        draw_text(
            self.screen,
            label,
            rect.x + (rect.width - text_width(label, scale)) // 2,
            rect.y + (rect.height - 7 * scale) // 2,
            text,
            scale=scale,
        )
        if action:
            self._register_ui(action, rect)

    def _draw_panel(
        self,
        rect: pygame.Rect,
        title: str | None = None,
        accent: Tuple[int, int, int] = (248, 187, 32),
        title_color: Tuple[int, int, int] = (24, 24, 28),
    ) -> None:
        pygame.draw.rect(self.screen, (16, 18, 20), rect, border_radius=8)
        pygame.draw.rect(self.screen, (46, 48, 54), rect, 2, border_radius=8)
        if title:
            header = pygame.Rect(rect.x, rect.y, rect.width, 34)
            pygame.draw.rect(self.screen, accent, header, border_top_left_radius=8, border_top_right_radius=8)
            draw_text(self.screen, title, rect.x + 12, rect.y + 10, title_color, scale=2)

    def _draw_main_menu(self, view: dict) -> None:
        title = "TOUCHLINE STORIES"
        subtitle = "SOCCER MANAGER PROTOTYPE"
        title_x = (SCREEN_W - text_width(title, 4)) // 2
        draw_text(self.screen, title, title_x, 92, (245, 245, 245), scale=4)
        draw_text(self.screen, subtitle, (SCREEN_W - text_width(subtitle, 2)) // 2, 140, (248, 187, 32), scale=2)

        card = pygame.Rect((SCREEN_W - 420) // 2, 214, 420, 360)
        self._draw_panel(card)
        buttons = [
            ("NEW GAME", "menu:new_game"),
            ("LOAD GAME", "menu:load_game"),
            ("OPTIONS", "menu:options"),
            ("QUIT", "menu:quit"),
        ]
        for idx, (label, action) in enumerate(buttons):
            button_rect = pygame.Rect(card.x + 48, card.y + 46 + idx * 74, card.width - 96, 52)
            fill = (220, 52, 52) if idx == 0 else (248, 187, 32) if idx == 2 else (36, 52, 96)
            text = (250, 250, 250) if idx != 2 else (24, 24, 28)
            self._draw_ui_button(button_rect, label, fill, text, action)

        footer = view.get("footer_text", "Build your club. Shape the table.")
        draw_text(self.screen, footer, (SCREEN_W - text_width(footer, 2)) // 2, SCREEN_H - 84, (245, 245, 245), scale=2)

    def _draw_manager_setup(self, view: dict) -> None:
        panel = pygame.Rect((SCREEN_W - 560) // 2, 170, 560, 300)
        self._draw_panel(panel, "NEW GAME", (220, 52, 52))
        prompt = "ENTER MANAGER NAME"
        draw_text(self.screen, prompt, panel.x + 28, panel.y + 72, (245, 245, 245), scale=2)
        field = pygame.Rect(panel.x + 28, panel.y + 112, panel.width - 56, 58)
        pygame.draw.rect(self.screen, (28, 30, 34), field, border_radius=6)
        pygame.draw.rect(self.screen, (248, 187, 32), field, 2, border_radius=6)
        value = view.get("manager_name", "")
        shown = value if value else "TYPE HERE"
        color = (245, 245, 245) if value else (160, 160, 166)
        draw_text(self.screen, shown, field.x + 16, field.y + 19, color, scale=2)
        error_text = view.get("error")
        if error_text:
            draw_text(self.screen, error_text[:42], panel.x + 28, panel.y + 184, (240, 108, 108), scale=1)
        self._draw_ui_button(pygame.Rect(panel.x + 28, panel.bottom - 68, 144, 44), "BACK", (36, 52, 96), (245, 245, 245), "back:menu")
        self._draw_ui_button(pygame.Rect(panel.right - 172, panel.bottom - 68, 144, 44), "CONTINUE", (248, 187, 32), (24, 24, 28), "new_game:continue")

    def _draw_league_select(self, view: dict) -> None:
        leagues = view.get("leagues", [])
        panel = pygame.Rect((SCREEN_W - 680) // 2, 144, 680, max(280, 150 + len(leagues) * 82))
        self._draw_panel(panel, "SELECT LEAGUE", (248, 187, 32))
        for idx, league in enumerate(leagues):
            rect = pygame.Rect(panel.x + 28, panel.y + 62 + idx * 78, panel.width - 56, 56)
            self._draw_ui_button(rect, league["name"], (220, 52, 52), (245, 245, 245), f"league:{league['id']}")
        self._draw_ui_button(pygame.Rect(panel.x + 28, panel.bottom - 60, 128, 40), "BACK", (36, 52, 96), (245, 245, 245), "back:new_game_name")

    def _draw_club_select(self, view: dict) -> None:
        clubs = view.get("clubs", [])
        panel = pygame.Rect(100, 110, SCREEN_W - 200, SCREEN_H - 210)
        self._draw_panel(panel, "SELECT CLUB", (248, 187, 32))
        columns = 2
        card_w = (panel.width - 78) // columns
        card_h = 138
        for idx, club in enumerate(clubs):
            row = idx // columns
            col = idx % columns
            x = panel.x + 26 + col * (card_w + 26)
            y = panel.y + 58 + row * (card_h + 26)
            rect = pygame.Rect(x, y, card_w, card_h)
            fill = hex_to_rgb(club.get("primary_color", "#2E3A6A"), (46, 58, 106))
            text = hex_to_rgb(club.get("secondary_color", "#F5F5F5"), (245, 245, 245))
            pygame.draw.rect(self.screen, fill, rect, border_radius=10)
            pygame.draw.rect(self.screen, (16, 18, 22), rect, 2, border_radius=10)
            draw_text(self.screen, club["name"], rect.x + 18, rect.y + 18, text, scale=2)
            meta = f"OVR {club['avg_ovr']:.1f}"
            squad = f"PLAYERS {club['players_count']}"
            draw_text(self.screen, meta, rect.x + 18, rect.y + 58, text, scale=2)
            draw_text(self.screen, squad, rect.x + 18, rect.y + 86, text, scale=2)
            self._register_ui(f"club:{club['id']}", rect)
        self._draw_ui_button(pygame.Rect(panel.x + 26, panel.bottom - 54, 128, 40), "BACK", (36, 52, 96), (245, 245, 245), "back:select_league")

    def _draw_options_screen(self, view: dict) -> None:
        options = view.get("options", {})
        choices = view.get("choices", {})
        panel_w = min(SCREEN_W - 80, 1500)
        panel_h = min(SCREEN_H - 72, 760)
        panel = pygame.Rect((SCREEN_W - panel_w) // 2, max(40, (SCREEN_H - panel_h) // 2), panel_w, panel_h)
        self._draw_panel(panel, "OPTIONS", (248, 187, 32))
        sections = [
            ("DISPLAY RESOLUTION", "resolution"),
            ("WINDOW MODE", "window_mode"),
            ("DISPLAY / MONITOR", "display"),
            ("LANGUAGE", "language"),
        ]
        normal_sections_h = len(sections) * 118
        compact_sections_h = len(sections) * 102
        bind_rows = [
            ("OPEN MENU", "bind_menu"),
            ("PAUSE MATCH", "bind_pause"),
            ("START MATCH", "bind_start"),
            ("SPEED X1", "bind_speed_x1"),
            ("SPEED X2", "bind_speed_x2"),
            ("SPEED X4", "bind_speed_x4"),
        ]
        available_h = panel.height - 66 - 56 - 28
        normal_total_h = normal_sections_h + 34 + len(bind_rows) * 46
        compact_total_h = compact_sections_h + 34 + ((len(bind_rows) + 1) // 2) * 46
        compact = normal_total_h > available_h and compact_total_h <= available_h
        if not compact and normal_total_h > available_h:
            compact = True
        y = panel.y + 66
        for label, key in sections:
            draw_text(self.screen, label, panel.x + 28, y, (245, 245, 245), scale=2)
            y += 34
            row = choices.get(key, [])
            x = panel.x + 28
            for option in row:
                active = options.get(key) == option["value"]
                width = max(150, text_width(option["label"], 2) + 32)
                rect = pygame.Rect(x, y, width, 42)
                fill = (248, 187, 32) if active else (36, 52, 96)
                text = (24, 24, 28) if active else (245, 245, 245)
                self._draw_ui_button(rect, option["label"], fill, text, f"option:{key}:{option['value']}")
                x += width + 14
            y += 68 if compact else 84

        draw_text(self.screen, "KEY BINDS", panel.x + 28, y, (245, 245, 245), scale=2)
        y += 34
        bind_cols = 2 if compact else 1
        bind_col_w = (panel.width - 56 - (bind_cols - 1) * 36) // bind_cols
        bind_row_h = 46
        for idx, (label, key) in enumerate(bind_rows):
            col = idx % bind_cols
            row_idx = idx // bind_cols
            row_x = panel.x + 28 + col * (bind_col_w + 36)
            row_y = y + row_idx * bind_row_h
            draw_text(self.screen, label, row_x, row_y + 10, (210, 210, 214), scale=1)
            row = choices.get(key, [])
            x = row_x + (170 if compact else 240)
            for option in row:
                active = options.get(key) == option["value"]
                width = max(88, text_width(option["label"], 2) + 28)
                rect = pygame.Rect(x, row_y, width, 34)
                fill = (248, 187, 32) if active else (36, 52, 96)
                text = (24, 24, 28) if active else (245, 245, 245)
                self._draw_ui_button(rect, option["label"], fill, text, f"option:{key}:{option['value']}")
                x += width + 12
        bind_rows_used = (len(bind_rows) + bind_cols - 1) // bind_cols
        y += bind_rows_used * bind_row_h
        self._draw_ui_button(pygame.Rect(panel.x + 28, panel.bottom - 56, 128, 40), "BACK", (36, 52, 96), (245, 245, 245), "back:menu")

    def _draw_load_game_screen(self, view: dict) -> None:
        saves = view.get("saves", [])
        panel = pygame.Rect(120, 110, SCREEN_W - 240, SCREEN_H - 190)
        self._draw_panel(panel, "LOAD GAME", (36, 52, 96))
        helper = "PLACEHOLDER SCREEN. EXISTING SAVES CAN STILL BE OPENED."
        draw_text(self.screen, helper, panel.x + 28, panel.y + 54, (245, 245, 245), scale=2)
        y = panel.y + 96
        if not saves:
            draw_text(self.screen, "NO SAVES YET", panel.x + 28, y, (248, 187, 32), scale=2)
        for save in saves[:8]:
            rect = pygame.Rect(panel.x + 28, y, panel.width - 56, 48)
            self._draw_ui_button(rect, f"{save['manager_name']} - {save['club_name']}", (220, 52, 52), (245, 245, 245), f"load:{save['id']}")
            y += 58
        self._draw_ui_button(pygame.Rect(panel.x + 28, panel.bottom - 54, 128, 40), "BACK", (36, 52, 96), (245, 245, 245), "back:menu")

    def _draw_overview_screen(self, view: dict) -> None:
        overview = view.get("overview", {})
        selected_club_id = view.get("selected_club_id", overview.get("club_id"))
        clubs = overview.get("clubs", [])
        players_by_club = overview.get("players_by_club", {})
        standings = overview.get("standings", [])
        fixtures = overview.get("fixtures", [])

        primary = hex_to_rgb(next((club["primary_color"] for club in clubs if club["id"] == overview.get("club_id")), "#D03434"), (208, 52, 52))
        secondary = hex_to_rgb(next((club["secondary_color"] for club in clubs if club["id"] == overview.get("club_id")), "#F5F5F5"), (245, 245, 245))

        top = pygame.Rect(0, 0, SCREEN_W, 62)
        pygame.draw.rect(self.screen, (12, 12, 16), top)
        brand = pygame.Rect(0, 0, 318, 62)
        pygame.draw.rect(self.screen, primary, brand)
        selected_club = next((club for club in clubs if club["id"] == overview.get("club_id")), None)
        badge_rect = pygame.Rect(14, 8, 38, 46)
        self._draw_club_badge(
            {
                "template_id": selected_club.get("badge_template_id", "1") if selected_club else "1",
                "primary": selected_club.get("badge_primary", "#2E3A6A") if selected_club else "#2E3A6A",
                "secondary": selected_club.get("badge_secondary", "#F5F5F5") if selected_club else "#F5F5F5",
                "border": selected_club.get("badge_border", "#F5F5F5") if selected_club else "#F5F5F5",
            },
            badge_rect,
        )
        draw_text(self.screen, overview.get("club_name", "CLUB"), 64, 12, secondary, scale=2)
        manager_name = overview.get("manager_name", "MANAGER")
        draw_text(self.screen, manager_name, 64, 36, secondary, scale=1)
        nav_items = ["OVERVIEW", "SQUAD", "MATCHES", "TRANSFERS", "SCOUTING"]
        x = brand.right + 20
        for idx, item in enumerate(nav_items):
            color = (248, 187, 32) if idx == 0 else (220, 220, 224)
            draw_text(self.screen, item, x, 20, color, scale=2)
            x += text_width(item, 2) + 26

        next_fixture = overview.get("next_fixture")
        right_x = SCREEN_W - 20
        if next_fixture:
            play_rect = pygame.Rect(right_x - 146, 11, 146, 40)
            self._draw_ui_button(play_rect, "PLAY MATCH", primary, secondary, "overview:play_next_match")
            right_x = play_rect.x - 12
        info = f"DAY {overview.get('current_day', 0)}"
        draw_text(self.screen, info, right_x - text_width(info, 2), 20, (245, 245, 245), scale=2)

        players = players_by_club.get(selected_club_id, [])
        players_body_h = 20 + min(18, len(players[:18])) * 18
        players_h = 34 + 14 + players_body_h + 18
        fixtures_count = min(6, len(fixtures))
        standings_count = min(8, len(standings))
        right_body_h = 18 + standings_count * 18 + 18 + 30 + fixtures_count * 18 + (20 if next_fixture else 0)
        right_h = 34 + 14 + 30 + right_body_h + 18
        panel_h = max(players_h, right_h)
        middle = pygame.Rect(20, 84, 350, panel_h)
        right = pygame.Rect(middle.right + 18, 84, SCREEN_W - middle.right - 38, panel_h)
        header_fill = (16, 18, 20)
        self._draw_panel(middle, "PLAYERS", header_fill, (245, 245, 245))
        self._draw_panel(right, "TABLE / FIXTURES", header_fill, (245, 245, 245))
        y = middle.y + 48
        col_pos = middle.x + 16
        col_player = middle.x + 52
        col_ovr = middle.right - 84
        col_stm = middle.right - 34
        draw_text(self.screen, "POS", col_pos, y, (170, 170, 176), scale=1)
        draw_text(self.screen, "PLAYER", col_player, y, (170, 170, 176), scale=1)
        draw_text(self.screen, "OVR", col_ovr - text_width("OVR", 1) // 2, y, (170, 170, 176), scale=1)
        draw_text(self.screen, "STM", col_stm - text_width("STM", 1) // 2, y, (170, 170, 176), scale=1)
        y += 20
        for player in players[:18]:
            draw_text(self.screen, player["position"], col_pos, y, (245, 245, 245), scale=1)
            draw_text(self.screen, short_display_name(player["name"], 14), col_player, y, (245, 245, 245), scale=1)
            ovr_text = str(player["ovr"])
            stm_text = str(int(player["current_stamina"]))
            draw_text(self.screen, ovr_text, col_ovr - text_width(ovr_text, 1) // 2, y, (245, 245, 245), scale=1)
            draw_text(self.screen, stm_text, col_stm - text_width(stm_text, 1) // 2, y, (245, 245, 245), scale=1)
            y += 18

        draw_text(self.screen, "TABLE", right.x + 16, right.y + 48, (248, 187, 32), scale=2)
        y = right.y + 78
        table_x = right.x + 16
        col_t_pos = table_x
        col_t_club = table_x + 24
        col_t_mp = right.right - 180
        col_t_w = right.right - 156
        col_t_d = right.right - 138
        col_t_l = right.right - 120
        col_t_gd = right.right - 96
        col_t_gls = right.right - 62
        col_t_p = right.right - 18
        for label, center_x in (
            ("POS", col_t_pos + 6),
            ("CLUB", col_t_club),
            ("MP", col_t_mp),
            ("W", col_t_w),
            ("D", col_t_d),
            ("L", col_t_l),
            ("GD", col_t_gd),
            ("GLS", col_t_gls),
            ("P", col_t_p),
        ):
            if label == "CLUB":
                draw_text(self.screen, label, center_x, y, (170, 170, 176), scale=1)
            else:
                draw_text(self.screen, label, center_x - text_width(label, 1) // 2, y, (170, 170, 176), scale=1)
        y += 18
        for idx, row in enumerate(standings[:8], start=1):
            goals_pair = f"{row['goals_for']}-{row['goals_against']}"
            gd = f"{row['goal_difference']:+d}"
            color = (245, 245, 245) if row["club_id"] != overview.get("club_id") else (248, 187, 32)
            draw_text(self.screen, str(idx), col_t_pos, y, color, scale=1)
            draw_text(self.screen, short_display_name(row["club_name"], 10), col_t_club, y, color, scale=1)
            for value, center_x in (
                (str(row["played"]), col_t_mp),
                (str(row["wins"]), col_t_w),
                (str(row["draws"]), col_t_d),
                (str(row["losses"]), col_t_l),
                (gd, col_t_gd),
                (goals_pair, col_t_gls),
                (str(row["points"]), col_t_p),
            ):
                draw_text(self.screen, value, center_x - text_width(value, 1) // 2, y, color, scale=1)
            y += 18

        y += 18
        draw_text(self.screen, "OPENING FIXTURES", right.x + 16, y, (248, 187, 32), scale=2)
        y += 30
        for fixture in fixtures[:6]:
            score = "--" if fixture["home_goals"] is None else f"{fixture['home_goals']}-{fixture['away_goals']}"
            line = f"MD{fixture['match_day']:>2} {short_display_name(fixture['home_name'], 8)} {score} {short_display_name(fixture['away_name'], 8)}"
            draw_text(self.screen, line, right.x + 16, y, (245, 245, 245), scale=1)
            y += 18

        if next_fixture:
            subtitle = f"MD{next_fixture['match_day']} {short_display_name(next_fixture['home_name'], 8)} VS {short_display_name(next_fixture['away_name'], 8)}"
            y += 12
            draw_text(self.screen, subtitle, right.x + 16, y, (245, 245, 245), scale=1)

    def draw_modal(self, modal: dict) -> None:
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        buttons = modal.get("buttons", [])
        panel_h = max(240, 140 + len(buttons) * 54)
        panel = pygame.Rect((SCREEN_W - 460) // 2, (SCREEN_H - panel_h) // 2, 460, panel_h)
        self._draw_panel(panel, None)
        title = modal.get("title", "CONFIRM")
        message = modal.get("message", "")
        draw_text(self.screen, title, panel.x + (panel.width - text_width(title, 3)) // 2, panel.y + 28, (245, 245, 245), scale=3)

        lines = [line for line in message.split("\n") if line]
        line_y = panel.y + 84
        for line in lines[:3]:
            draw_text(self.screen, line, panel.x + (panel.width - text_width(line, 2)) // 2, line_y, (248, 187, 32), scale=2)
            line_y += 28

        button_w = 200
        button_h = 40
        start_x = panel.x + (panel.width - button_w) // 2
        button_y = line_y + 18
        for idx, button in enumerate(buttons):
            rect = pygame.Rect(start_x, button_y + idx * (button_h + 12), button_w, button_h)
            fill = button.get("fill", (36, 52, 96))
            text = button.get("text_color", (245, 245, 245))
            self._draw_ui_button(rect, button["label"], fill, text, button.get("action"))
