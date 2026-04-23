from __future__ import annotations
import math
from typing import Tuple

import pygame

from .loader import available_formations, formation_slots, position_fit_label
from .match_engine import PITCH_LENGTH, PITCH_WIDTH
from .models import (
    DEFAULT_PLAYER_INSTRUCTIONS,
    DEFAULT_TEAM_INSTRUCTIONS,
    PLAYER_INSTRUCTION_LABELS,
    TEAM_INSTRUCTION_LABELS,
    TEAM_INSTRUCTION_OPTIONS,
    MatchState,
    stamina_ratio_for_player,
)

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
SPEED_OPTIONS = ("X1", "X2", "X4", "X8")
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
    '%': ["11001","11010","00100","01000","10110","00110","00000"],
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


def next_instruction_value(key: str, current: str) -> str:
    options = TEAM_INSTRUCTION_OPTIONS.get(key, [])
    if not options:
        return current
    try:
        index = options.index(current)
    except ValueError:
        return options[0]
    return options[(index + 1) % len(options)]


def previous_instruction_value(key: str, current: str) -> str:
    options = TEAM_INSTRUCTION_OPTIONS.get(key, [])
    if not options:
        return current
    try:
        index = options.index(current)
    except ValueError:
        return options[0]
    return options[max(0, index - 1)]


def instruction_preview_labels(key: str, current: str) -> tuple[str | None, str, str | None]:
    options = TEAM_INSTRUCTION_OPTIONS.get(key, [])
    if not options:
        return None, current, None
    try:
        index = options.index(current)
    except ValueError:
        index = 0
    current_key = options[index]
    left = options[index - 1] if index > 0 else None
    right = options[index + 1] if index < len(options) - 1 else None
    labels = TEAM_INSTRUCTION_LABELS.get(key, {})
    return (
        labels.get(left) if left else None,
        labels.get(current_key, current_key.replace("_", " ").upper()),
        labels.get(right) if right else None,
    )


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
        pygame.display.set_caption("MY MANAGER CAREER")
        self.ui_click_targets: dict[str, pygame.Rect] = {}
        self.sub_row_targets: dict[str, dict[str, object]] = {}
        self.squad_targets: dict[str, dict[str, object]] = {}
        self.squad_slider_targets: dict[str, dict[str, object]] = {}
        self.match_slider_targets: dict[str, dict[str, object]] = {}
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
        self.fullscreen = fullscreen
        display_count = max(1, pygame.display.get_num_displays())
        self.display_index = max(0, min(display_count - 1, int(display_index)))
        desktop_sizes = pygame.display.get_desktop_sizes() or []
        if self.display_index < len(desktop_sizes):
            desktop_w, desktop_h = desktop_sizes[self.display_index]
        else:
            desktop_w, desktop_h = width, height
        target_w = int(width)
        target_h = int(height)
        if not fullscreen:
            target_w = min(target_w, max(960, int(desktop_w) - 80))
            target_h = min(target_h, max(640, int(desktop_h) - 80))
        configure_display_metrics(target_w, target_h)
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

    def handle_sub_row_hit(self, pos: Tuple[int, int]) -> dict[str, object] | None:
        for info in self.sub_row_targets.values():
            rect = info.get("rect")
            if isinstance(rect, pygame.Rect) and rect.collidepoint(pos):
                return info
        return None

    def handle_squad_hit(self, pos: Tuple[int, int]) -> dict[str, object] | None:
        for info in self.squad_targets.values():
            rect = info.get("rect")
            if isinstance(rect, pygame.Rect) and rect.collidepoint(pos):
                return info
        return None

    def handle_squad_slider_hit(self, pos: Tuple[int, int]) -> dict[str, object] | None:
        for info in self.squad_slider_targets.values():
            rect = info.get("rect")
            if isinstance(rect, pygame.Rect) and rect.collidepoint(pos):
                return info
        return None

    def get_squad_slider_target(self, player_id: str, key: str) -> dict[str, object] | None:
        return self.squad_slider_targets.get(f"{player_id}:{key}")

    def handle_match_slider_hit(self, pos: Tuple[int, int]) -> dict[str, object] | None:
        for info in self.match_slider_targets.values():
            rect = info.get("rect")
            if isinstance(rect, pygame.Rect) and rect.collidepoint(pos):
                return info
        return None

    def get_match_slider_target(self, player_id: str, key: str) -> dict[str, object] | None:
        return self.match_slider_targets.get(f"{player_id}:{key}")

    def _draw_club_badge(self, badge: dict | None, rect: pygame.Rect) -> None:
        badge = badge or {}
        template_id = str(badge.get("template_id", badge.get("badge_id", "1")))
        primary = hex_to_rgb(str(badge.get("primary", badge.get("badge_primary", "#2E3A6A"))), (46, 58, 106))
        secondary = hex_to_rgb(str(badge.get("secondary", badge.get("badge_secondary", "#F5F5F5"))), (245, 245, 245))
        border = hex_to_rgb(str(badge.get("border", badge.get("badge_border", "#F5F5F5"))), (245, 245, 245))

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
            stripe_w = max(2, min(local_rect.width // 3, max(3, local_rect.width // 4)))
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
        pygame.draw.polygon(self.screen, border, points, width=1 if rect.width <= 14 else max(2, rect.width // 18))

    def draw(
        self,
        state: MatchState,
        fixture_label: str,
        paused: bool,
        alpha: float = 1.0,
        speed_label: str = "x1",
        clock_seconds: float | None = None,
        commentary_colors: tuple[Tuple[int, int, int], Tuple[int, int, int]] | None = None,
        selected_player_id: str | None = None,
        managed_side: str | None = None,
        subs_mode: bool = False,
        draft_xi_ids: list[str] | None = None,
        draft_bench_ids: list[str] | None = None,
        drag_player_id: str | None = None,
        drag_pos: tuple[int, int] | None = None,
        hover_player_id: str | None = None,
        sub_animation: dict | None = None,
        instruction_mode: str | None = None,
        live_formation: str | None = None,
        live_team_instructions: dict[str, str] | None = None,
        live_player_instructions: dict[str, dict[str, int]] | None = None,
        selected_player_id_for_instructions: str | None = None,
        instruction_animation: dict | None = None,
        instructions_pending: bool = False,
        subs_pending: bool = False,
        present: bool = True,
    ) -> None:
        self.ui_click_targets = {}
        self.sub_row_targets = {}
        self.squad_slider_targets = {}
        self.match_slider_targets = {}
        self.screen.fill((18, 18, 22))
        self._layout_pitch()
        if state.is_finished:
            report_view = pygame.Rect(0, VIEWPORT_Y, SCREEN_W, VIEWPORT_H)
            pygame.draw.rect(self.screen, (108, 142, 63), report_view)
            self._draw_post_match_screen(state, selected_player_id)
            self._draw_finished_match_top_bar()
        else:
            self._draw_side_panel(state, managed_side, subs_mode, draft_xi_ids, draft_bench_ids, drag_player_id, hover_player_id, subs_pending)
            pygame.draw.rect(self.screen, (108, 142, 63), PITCH_PANEL)
            self._draw_pitch()
            self._draw_players_and_ball(state, alpha)
            self._draw_pitch_overlay(state, fixture_label)
            self._draw_scoreboard(state, fixture_label, paused, speed_label, clock_seconds, managed_side)
            self._draw_events(state, commentary_colors, instruction_mode, instructions_pending, managed_side)
        self._draw_goal_banner(state)
        if drag_player_id and drag_pos and not state.is_finished:
            self._draw_drag_preview(state, managed_side, drag_player_id, drag_pos)
        if sub_animation and not state.is_finished:
            self._draw_substitution_animation(state, sub_animation)
        if instruction_animation and not state.is_finished:
            self._draw_instruction_change_animation(instruction_animation)
        if instruction_mode and not state.is_finished:
            self._draw_match_instruction_overlay(
                state,
                managed_side,
                instruction_mode,
                live_formation or "4-3-3",
                live_team_instructions or dict(DEFAULT_TEAM_INSTRUCTIONS),
                live_player_instructions or {},
                selected_player_id_for_instructions,
            )
        if present:
            pygame.display.flip()

    def _draw_finished_match_top_bar(self) -> None:
        panel = pygame.Rect(0, 0, SCREEN_W, TOP_BAR_H)
        pygame.draw.rect(self.screen, (10, 10, 12), panel)
        pause_box = pygame.Rect(SCREEN_W - 142, 0, 142, TOP_BAR_H)
        pygame.draw.rect(self.screen, (88, 170, 104), pause_box)
        draw_text(
            self.screen,
            "CONTINUE",
            pause_box.x + (pause_box.width - text_width("CONTINUE", 2)) // 2,
            11,
            (245, 255, 245),
            scale=2,
        )
        self.start_rect = pause_box
        self.speed_rect = None
        self.speed_option_rects = {}

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

    def _draw_side_panel(
        self,
        state: MatchState,
        managed_side: str | None = None,
        subs_mode: bool = False,
        draft_xi_ids: list[str] | None = None,
        draft_bench_ids: list[str] | None = None,
        drag_player_id: str | None = None,
        hover_player_id: str | None = None,
        subs_pending: bool = False,
    ) -> None:
        panel = SIDE_PANEL.inflate(-10, -10)
        pygame.draw.rect(self.screen, (12, 12, 14), panel, border_radius=4)
        pygame.draw.rect(self.screen, (44, 44, 48), panel, 1, border_radius=4)
        mid_y = panel.y + 8
        section_h = (panel.height - 22) // 2
        self._draw_team_squad_section(
            state.home,
            state,
            pygame.Rect(panel.x + 8, mid_y, panel.width - 16, section_h - 6),
            is_managed_team=managed_side == "home",
            subs_mode=subs_mode,
            draft_xi_ids=draft_xi_ids if managed_side == "home" else None,
            draft_bench_ids=draft_bench_ids if managed_side == "home" else None,
            drag_player_id=drag_player_id if managed_side == "home" else None,
            hover_player_id=hover_player_id if managed_side == "home" else None,
            subs_pending=subs_pending if managed_side == "home" else False,
        )
        self._draw_team_squad_section(
            state.away,
            state,
            pygame.Rect(panel.x + 8, mid_y + section_h + 6, panel.width - 16, section_h - 6),
            is_managed_team=managed_side == "away",
            subs_mode=subs_mode,
            draft_xi_ids=draft_xi_ids if managed_side == "away" else None,
            draft_bench_ids=draft_bench_ids if managed_side == "away" else None,
            drag_player_id=drag_player_id if managed_side == "away" else None,
            hover_player_id=hover_player_id if managed_side == "away" else None,
            subs_pending=subs_pending if managed_side == "away" else False,
        )

    def _draw_team_squad_section(
        self,
        team,
        state: MatchState,
        rect: pygame.Rect,
        is_managed_team: bool = False,
        subs_mode: bool = False,
        draft_xi_ids: list[str] | None = None,
        draft_bench_ids: list[str] | None = None,
        drag_player_id: str | None = None,
        hover_player_id: str | None = None,
        subs_pending: bool = False,
    ) -> None:
        primary = hex_to_rgb(team.club.colors.get("primary", "#2E3A6A"), (46, 58, 106))
        secondary = hex_to_rgb(team.club.colors.get("secondary", "#F5F5F5"), (245, 245, 245))
        pygame.draw.rect(self.screen, (18, 18, 22), rect, border_radius=4)
        pygame.draw.rect(self.screen, primary, (rect.x, rect.y, rect.width, 28), border_radius=4)
        draw_text(self.screen, compact_team_name(team.name), rect.x + 10, rect.y + 8, secondary, scale=2)
        if is_managed_team:
            counter_text = f"{5 - team.substitutions_used} SUBS {3 - team.substitution_windows_used} WIN"
            draw_text(self.screen, counter_text, rect.right - text_width(counter_text, 1) - 10, rect.y + 10, secondary, scale=1)

        col_name = rect.x + 10
        col_avg = rect.right - 106
        col_stam = rect.right - 72
        y = rect.y + 36
        draw_text(self.screen, "XI", col_name, y + 2, (245, 245, 245), scale=1)
        draw_text(self.screen, "AVG", col_avg, y, (180, 180, 186), scale=1)
        draw_text(self.screen, "STM", col_stam, y, (180, 180, 186), scale=1)
        y += 18
        row_h = 18
        xi_lookup = {player.profile.id: player for player in team.xi}
        profile_lookup = {profile.id: profile for profile in team.club.players}
        xi_ids = draft_xi_ids if is_managed_team and draft_xi_ids else [player.profile.id for player in team.xi]

        for player_id in xi_ids:
            live_player = xi_lookup.get(player_id)
            profile = live_player.profile if live_player else profile_lookup.get(player_id)
            if profile is None:
                continue
            avg_score = self._player_rating(state, player_id)
            stamina_ratio = (
                stamina_ratio_for_player(profile.attributes.get("stamina", 70.0), live_player.fatigue)
                if live_player
                else max(0.08, min(1.0, profile.current_stamina / 100.0))
            )
            yellow_cards = live_player.yellow_cards if live_player else int(state.player_match_stats.get(player_id, {}).get("yellow_cards", 0.0))
            red_card = live_player.red_card if live_player else bool(state.player_match_stats.get(player_id, {}).get("red_cards", 0.0))
            row_fill = None
            if subs_mode and is_managed_team and player_id != drag_player_id:
                row_fill = (28, 30, 36)
            if hover_player_id == player_id:
                row_fill = (76, 128, 84)
            self._draw_squad_row(
                rect,
                y,
                profile.name,
                player_id,
                avg_score,
                stamina_ratio,
                yellow_cards,
                red_card,
                state.player_goals.get(player_id, 0),
                state.player_assists.get(player_id, 0),
                row_fill=row_fill,
            )
            if subs_mode and is_managed_team:
                self.sub_row_targets[player_id] = {
                    "player_id": player_id,
                    "group": "xi",
                    "rect": pygame.Rect(rect.x + 4, y - 1, rect.width - 8, row_h),
                    "unavailable": False,
                }
            y += 18

        y += 4
        draw_text(self.screen, "BENCH", col_name, y + 2, (245, 245, 245), scale=1)
        y += 18
        bench_ids = draft_bench_ids if is_managed_team and draft_bench_ids else [player.id for player in team.bench]
        for bench_player_id in bench_ids[:7]:
            bench_player = profile_lookup.get(bench_player_id)
            if bench_player is None:
                continue
            unavailable = bench_player.id in team.subbed_out_ids
            row_fill = None
            if subs_mode and is_managed_team and bench_player.id != drag_player_id:
                row_fill = (28, 30, 36) if not unavailable else (72, 34, 34)
            if hover_player_id == bench_player.id:
                row_fill = (76, 128, 84)
            self._draw_squad_row(
                rect,
                y,
                bench_player.name,
                bench_player.id,
                self._player_rating(state, bench_player.id),
                max(0.08, min(1.0, bench_player.current_stamina / 100.0)),
                0,
                False,
                state.player_goals.get(bench_player.id, 0),
                state.player_assists.get(bench_player.id, 0),
                row_fill=row_fill,
                subbed_out=unavailable,
            )
            if subs_mode and is_managed_team:
                self.sub_row_targets[bench_player.id] = {
                    "player_id": bench_player.id,
                    "group": "bench",
                    "rect": pygame.Rect(rect.x + 4, y - 1, rect.width - 8, row_h),
                    "unavailable": unavailable,
                }
            y += 18
        if is_managed_team:
            self._draw_sub_controls(rect, team, subs_mode, subs_pending)

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
        row_fill: Tuple[int, int, int] | None = None,
        subbed_out: bool = False,
    ) -> None:
        row_rect = pygame.Rect(rect.x + 4, y - 1, rect.width - 8, 18)
        if row_fill:
            pygame.draw.rect(self.screen, row_fill, row_rect, border_radius=3)
            pygame.draw.rect(self.screen, (58, 58, 64), row_rect, 1, border_radius=3)
        shirt_number = "".join(ch for ch in player_id if ch.isdigit())[-2:] or "0"
        draw_text(self.screen, shirt_number.rjust(2, "0"), rect.x + 8, y + 2, (168, 168, 174), scale=1)
        label = short_display_name(name, 11)
        draw_text(self.screen, label, rect.x + 28, y + 2, (238, 238, 240), scale=1)

        icon_slots = (1 if goals > 0 else 0) + (1 if assists > 0 else 0)
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
        if subbed_out:
            self._draw_subbed_out_indicator(rect.right - 146 - icon_slots * 18, y + 8)

    def _draw_sub_controls(self, rect: pygame.Rect, team, subs_mode: bool, subs_pending: bool = False) -> None:
        button_rect = pygame.Rect(rect.x + 10, rect.bottom - 36, rect.width - 20, 26)
        if subs_mode:
            half_w = (button_rect.width - 8) // 2
            cancel_rect = pygame.Rect(button_rect.x, button_rect.y, half_w, button_rect.height)
            confirm_rect = pygame.Rect(cancel_rect.right + 8, button_rect.y, button_rect.width - half_w - 8, button_rect.height)
            self._draw_ui_button(cancel_rect, "CANCEL", (70, 74, 92), (245, 245, 245), "match:subs:cancel", scale=2)
            self._draw_ui_button(confirm_rect, "CONFIRM", (88, 170, 104), (18, 18, 22), "match:subs:confirm", scale=2)
            return
        if subs_pending:
            self._draw_ui_button(button_rect, "WAIT STOPPAGE", (92, 72, 28), (245, 245, 245), scale=2)
            return
        if team.substitutions_used >= 5 or team.substitution_windows_used >= 3:
            self._draw_ui_button(button_rect, "NO SUB WINDOWS", (56, 58, 64), (188, 188, 194), scale=2)
        else:
            self._draw_ui_button(button_rect, "MAKE SUBS", (36, 52, 96), (245, 245, 245), "match:subs:start", scale=2)

    def _draw_drag_preview(
        self,
        state: MatchState,
        managed_side: str | None,
        player_id: str,
        drag_pos: tuple[int, int],
    ) -> None:
        if not managed_side:
            return
        team = state.home if managed_side == "home" else state.away
        profile_lookup = {profile.id: profile for profile in team.club.players}
        player = next((p for p in team.xi if p.profile.id == player_id), None)
        preview_rect = pygame.Rect(0, 0, SIDE_PANEL_W - 36, 20)
        preview = pygame.Surface(preview_rect.size, pygame.SRCALPHA)
        screen_backup = self.screen
        self.screen = preview
        if player:
            self._draw_squad_row(
                preview.get_rect(),
                1,
                player.profile.name,
                player.profile.id,
                self._player_rating(state, player.profile.id),
                stamina_ratio_for_player(player.profile.attributes.get("stamina", 70.0), player.fatigue),
                player.yellow_cards,
                player.red_card,
                state.player_goals.get(player.profile.id, 0),
                state.player_assists.get(player.profile.id, 0),
                row_fill=(20, 20, 24),
            )
        else:
            bench_player = profile_lookup.get(player_id)
            if bench_player is None:
                self.screen = screen_backup
                return
            self._draw_squad_row(
                preview.get_rect(),
                1,
                bench_player.name,
                bench_player.id,
                self._player_rating(state, bench_player.id),
                max(0.08, min(1.0, bench_player.current_stamina / 100.0)),
                int(state.player_match_stats.get(bench_player.id, {}).get("yellow_cards", 0.0)),
                bool(state.player_match_stats.get(bench_player.id, {}).get("red_cards", 0.0)),
                state.player_goals.get(bench_player.id, 0),
                state.player_assists.get(bench_player.id, 0),
                row_fill=(20, 20, 24),
                subbed_out=bench_player.id in team.subbed_out_ids,
            )
        self.screen = screen_backup
        self.screen.blit(preview, (drag_pos[0] - preview_rect.width // 2, drag_pos[1] - preview_rect.height // 2))

    def _draw_substitution_animation(self, state: MatchState, animation: dict) -> None:
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 96))
        self.screen.blit(overlay, (0, 0))

        pairs = list(animation.get("pairs", []))
        panel_h = 72 + min(5, len(pairs)) * 28
        panel = pygame.Rect(0, 0, min(520, SCREEN_W - 120), panel_h)
        panel.center = (SCREEN_W // 2, VIEWPORT_Y + VIEWPORT_H // 2)
        pygame.draw.rect(self.screen, (16, 18, 22), panel, border_radius=8)
        pygame.draw.rect(self.screen, (76, 76, 84), panel, 2, border_radius=8)
        draw_text(self.screen, "SUBSTITUTION", panel.x + (panel.width - text_width("SUBSTITUTION", 2)) // 2, panel.y + 12, (245, 245, 245), scale=2)

        pairs = pairs[:5]
        team = state.home if animation.get("side") == "home" else state.away
        profile_lookup = {profile.id: profile for profile in team.club.players}
        for idx, (outgoing_id, incoming_id) in enumerate(pairs):
            row_y = panel.y + 46 + idx * 28
            outgoing = profile_lookup.get(outgoing_id)
            incoming = profile_lookup.get(incoming_id)
            outgoing_name = short_display_name(outgoing.name if outgoing else outgoing_id, 14)
            incoming_name = short_display_name(incoming.name if incoming else incoming_id, 14)
            draw_text(self.screen, outgoing_name, panel.x + 22, row_y, (236, 236, 240), scale=2)
            self._draw_subbed_out_indicator(panel.centerx - 18, row_y + 7)
            pygame.draw.line(self.screen, (116, 208, 120), (panel.centerx + 4, row_y + 7), (panel.centerx + 16, row_y + 7), 2)
            pygame.draw.polygon(self.screen, (116, 208, 120), [(panel.centerx + 22, row_y + 7), (panel.centerx + 14, row_y + 2), (panel.centerx + 14, row_y + 12)])
            draw_text(self.screen, incoming_name, panel.centerx + 32, row_y, (116, 208, 120), scale=2)

    def _draw_goal_icon(self, x: int, y: int) -> None:
        pygame.draw.circle(self.screen, (244, 244, 244), (x, y), 5)
        pygame.draw.circle(self.screen, (18, 18, 22), (x, y), 5, 1)
        pygame.draw.circle(self.screen, (18, 18, 22), (x, y), 2)

    def _draw_assist_icon(self, x: int, y: int) -> None:
        boot = [
            (x - 5, y + 2),
            (x - 2, y - 4),
            (x + 2, y - 4),
            (x + 4, y - 1),
            (x + 5, y + 1),
            (x + 2, y + 2),
            (x + 1, y + 5),
            (x - 4, y + 5),
        ]
        pygame.draw.polygon(self.screen, (236, 236, 236), boot)
        pygame.draw.line(self.screen, (18, 18, 22), (x - 1, y - 3), (x + 2, y - 3), 1)
        pygame.draw.line(self.screen, (18, 18, 22), (x - 3, y + 4), (x + 2, y + 4), 1)
        pygame.draw.circle(self.screen, (236, 236, 236), (x + 6, y - 4), 1)

    def _draw_subbed_out_indicator(self, x: int, y: int) -> None:
        points = [(x + 5, y - 5), (x - 4, y), (x + 5, y + 5)]
        pygame.draw.polygon(self.screen, (218, 78, 78), points)
        pygame.draw.line(self.screen, (218, 78, 78), (x + 6, y), (x + 12, y), 2)

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

    def _draw_ball_icon(self, surface: pygame.Surface, center: tuple[int, int], radius: int) -> None:
        cx, cy = center
        outline = (18, 18, 22)
        pygame.draw.circle(surface, (245, 245, 245), center, radius)
        pygame.draw.circle(surface, outline, center, radius, max(1, radius // 5))
        center_patch = []
        for idx in range(5):
            angle = math.radians(-90 + idx * 72)
            center_patch.append((int(cx + math.cos(angle) * radius * 0.32), int(cy + math.sin(angle) * radius * 0.32)))
        pygame.draw.polygon(surface, outline, center_patch)

        seam_arcs = [
            pygame.Rect(cx - radius + 1, cy - radius // 2, radius + 1, radius),
            pygame.Rect(cx - 1, cy - radius // 2, radius + 1, radius),
            pygame.Rect(cx - radius // 2, cy - radius + 1, radius, radius + 1),
        ]
        pygame.draw.arc(surface, outline, seam_arcs[0], math.radians(300), math.radians(60), 1)
        pygame.draw.arc(surface, outline, seam_arcs[1], math.radians(120), math.radians(240), 1)
        pygame.draw.arc(surface, outline, seam_arcs[2], math.radians(200), math.radians(340), 1)

        for px, py in center_patch:
            pygame.draw.line(surface, outline, (cx, cy), (px, py), 1)

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
        managed_side: str | None = None,
    ) -> None:
        panel = pygame.Rect(0, 0, SCREEN_W, TOP_BAR_H)
        pygame.draw.rect(self.screen, (10, 10, 12), panel)
        shown_seconds = state.elapsed_seconds if clock_seconds is None else clock_seconds
        minute = min(90, int(shown_seconds // 60))
        second = int(shown_seconds % 60)
        minute_text = f"{minute:02d}:{second:02d}"
        self._draw_top_bar(state, minute_text, paused, speed_label, managed_side)

    def _draw_events(
        self,
        state: MatchState,
        commentary_colors: tuple[Tuple[int, int, int], Tuple[int, int, int]] | None = None,
        instruction_mode: str | None = None,
        instructions_pending: bool = False,
        managed_side: str | None = None,
    ) -> None:
        panel = pygame.Rect(0, SCREEN_H - BOTTOM_TICKER_H, SCREEN_W, BOTTOM_TICKER_H)
        pygame.draw.rect(self.screen, (12, 12, 14), panel)
        left_pad = 14
        right_pad = 14
        icon_box = pygame.Rect(left_pad, SCREEN_H - BOTTOM_TICKER_H + 6, 54, BOTTOM_TICKER_H - 12)
        right_icon_box = pygame.Rect(SCREEN_W - right_pad - 54, SCREEN_H - BOTTOM_TICKER_H + 6, 54, BOTTOM_TICKER_H - 12)
        team_fill = (30, 58, 102) if instruction_mode == "team" else (18, 20, 24)
        player_fill = (30, 58, 102) if instruction_mode == "player" else (18, 20, 24)
        if instructions_pending and instruction_mode is None:
            team_fill = (92, 72, 28)
            player_fill = (92, 72, 28)
        pygame.draw.rect(self.screen, team_fill, icon_box, border_radius=6)
        pygame.draw.rect(self.screen, player_fill, right_icon_box, border_radius=6)
        pygame.draw.rect(self.screen, (72, 76, 88), icon_box, 1, border_radius=6)
        pygame.draw.rect(self.screen, (72, 76, 88), right_icon_box, 1, border_radius=6)
        if managed_side in ("home", "away"):
            self._draw_tactics_board_icon(icon_box, (240, 240, 244))
            self._draw_player_button_icon(right_icon_box, (240, 240, 244))
            self._register_ui("match:instructions:team", icon_box)
            self._register_ui("match:instructions:player", right_icon_box)

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

    def _draw_tactics_board_icon(self, rect: pygame.Rect, color: Tuple[int, int, int]) -> None:
        board = rect.inflate(-18, -12)
        pygame.draw.rect(self.screen, color, board, 2, border_radius=3)
        pygame.draw.line(self.screen, color, (board.centerx, board.y + 2), (board.centerx, board.bottom - 2), 1)
        pygame.draw.circle(self.screen, color, (board.x + 8, board.y + 8), 3, 1)
        pygame.draw.circle(self.screen, color, (board.right - 8, board.bottom - 8), 3, 1)
        pygame.draw.line(self.screen, color, (board.x + 10, board.bottom - 8), (board.centerx - 2, board.centery), 1)
        pygame.draw.line(self.screen, color, (board.centerx + 2, board.centery), (board.right - 10, board.y + 8), 1)
        pygame.draw.line(self.screen, color, (board.centerx - 2, board.centery), (board.centerx + 4, board.centery - 4), 1)
        pygame.draw.line(self.screen, color, (board.centerx - 2, board.centery), (board.centerx + 4, board.centery + 4), 1)

    def _draw_player_button_icon(self, rect: pygame.Rect, color: Tuple[int, int, int]) -> None:
        cx = rect.centerx
        pygame.draw.circle(self.screen, color, (cx, rect.y + 11), 5, 1)
        body = pygame.Rect(cx - 9, rect.y + 18, 18, 10)
        pygame.draw.rect(self.screen, color, body, 1, border_radius=4)
        pygame.draw.line(self.screen, color, (cx - 12, rect.bottom - 8), (cx + 12, rect.bottom - 8), 1)

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

    def _team_stat_value(self, stats: dict, key: str) -> str:
        if key == "possession_seconds":
            home = stats["home"]["possession_seconds"]
            away = stats["away"]["possession_seconds"]
            total = max(1.0, home + away)
            return f"{int(round(home / total * 100))}%|{int(round(away / total * 100))}%"
        if key == "passing":
            home_attempted = max(1.0, stats["home"]["passes_attempted"])
            away_attempted = max(1.0, stats["away"]["passes_attempted"])
            home_pct = int(round(stats["home"]["passes_completed"] / home_attempted * 100))
            away_pct = int(round(stats["away"]["passes_completed"] / away_attempted * 100))
            return f"{home_pct}%|{away_pct}%"
        home_value = int(round(stats["home"][key]))
        away_value = int(round(stats["away"][key]))
        return f"{home_value}|{away_value}"

    def _report_players_with_minutes(self, report: dict, side: str) -> list[dict]:
        players = report.get("players", {}).get(side, [])
        filtered = [
            player
            for player in players
            if float(report.get("player_stats", {}).get(player["id"], {}).get("minutes", player.get("minutes", 0.0))) > 0.01
        ]
        filtered.sort(
            key=lambda player: (
                -float(report.get("player_stats", {}).get(player["id"], {}).get("minutes", player.get("minutes", 0.0))),
                player.get("name", ""),
            )
        )
        return filtered

    def _player_rating(self, state: MatchState, player_id: str) -> float:
        stats = state.player_match_stats.get(player_id, {})
        player = next((p for p in state.home.xi + state.away.xi if p.profile.id == player_id), None)
        if player and player.slot == "GK":
            rating = 6.6
            rating += stats.get("goalkeeper_saves", 0.0) * 0.18
            rating += stats.get("passes_completed", 0.0) * 0.006
            rating += stats.get("long_balls_completed", 0.0) * 0.04
            rating += stats.get("ball_recoveries", 0.0) * 0.03
            rating += stats.get("assists", 0.0) * 0.55
            rating += stats.get("goals", 0.0) * 0.85
            rating -= stats.get("goalkeeper_goals_conceded", 0.0) * 0.32
            rating -= stats.get("fouls_committed", 0.0) * 0.06
            rating -= stats.get("yellow_cards", 0.0) * 0.22
            rating -= stats.get("red_cards", 0.0) * 1.0
            return max(5.0, min(10.0, rating))
        rating = 6.6
        rating += stats.get("goals", 0.0) * 0.85
        rating += stats.get("assists", 0.0) * 0.55
        rating += stats.get("shots_on_target", 0.0) * 0.08
        rating += stats.get("passes_completed", 0.0) * 0.01
        rating += stats.get("tackles", 0.0) * 0.08
        rating += stats.get("interceptions", 0.0) * 0.08
        rating += stats.get("clearances", 0.0) * 0.03
        rating += stats.get("dribbles_completed", 0.0) * 0.05
        rating -= stats.get("fouls_committed", 0.0) * 0.06
        rating -= stats.get("yellow_cards", 0.0) * 0.22
        rating -= stats.get("red_cards", 0.0) * 1.0
        return max(5.0, min(10.0, rating))

    def _format_goal_scorers(self, state: MatchState, team) -> str:
        items = []
        for player in team.xi:
            goals = state.player_goals.get(player.profile.id, 0)
            if goals:
                suffix = f" x{goals}" if goals > 1 else ""
                items.append(f"{player.short_name}{suffix}")
        return ", ".join(items) if items else "-"

    def _report_player_rating(self, report: dict, player_id: str) -> float:
        stats = report.get("player_stats", {}).get(player_id, {})
        player = next(
            (p for p in report.get("players", {}).get("home", []) + report.get("players", {}).get("away", []) if p["id"] == player_id),
            None,
        )
        if player and player.get("position") == "GK":
            rating = 6.6
            rating += float(stats.get("goalkeeper_saves", 0.0)) * 0.18
            rating += float(stats.get("passes_completed", 0.0)) * 0.006
            rating += float(stats.get("long_balls_completed", 0.0)) * 0.04
            rating += float(stats.get("ball_recoveries", 0.0)) * 0.03
            rating += float(stats.get("assists", 0.0)) * 0.55
            rating += float(stats.get("goals", 0.0)) * 0.85
            rating -= float(stats.get("goalkeeper_goals_conceded", 0.0)) * 0.32
            rating -= float(stats.get("fouls_committed", 0.0)) * 0.06
            rating -= float(stats.get("yellow_cards", 0.0)) * 0.22
            rating -= float(stats.get("red_cards", 0.0)) * 1.0
            return max(5.0, min(10.0, rating))
        rating = 6.6
        rating += float(stats.get("goals", 0.0)) * 0.85
        rating += float(stats.get("assists", 0.0)) * 0.55
        rating += float(stats.get("shots_on_target", 0.0)) * 0.08
        rating += float(stats.get("passes_completed", 0.0)) * 0.01
        rating += float(stats.get("tackles", 0.0)) * 0.08
        rating += float(stats.get("interceptions", 0.0)) * 0.08
        rating += float(stats.get("clearances", 0.0)) * 0.03
        rating += float(stats.get("dribbles_completed", 0.0)) * 0.05
        rating -= float(stats.get("fouls_committed", 0.0)) * 0.06
        rating -= float(stats.get("yellow_cards", 0.0)) * 0.22
        rating -= float(stats.get("red_cards", 0.0)) * 1.0
        return max(5.0, min(10.0, rating))

    def _format_report_goal_scorers(self, report: dict, side: str) -> str:
        players = report.get("players", {}).get(side, [])
        goals_by_player = report.get("player_goals", {})
        items = []
        for player in players:
            goals = int(goals_by_player.get(player["id"], 0))
            if goals:
                suffix = f" x{goals}" if goals > 1 else ""
                items.append(f"{player.get('short_name', player.get('name', 'PLAYER'))}{suffix}")
        return ", ".join(items) if items else "-"

    def _draw_post_match_report(self, report: dict, selected_player_id: str | None, panel: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, (16, 18, 22), panel, border_radius=10)
        pygame.draw.rect(self.screen, (42, 44, 50), panel, 2, border_radius=10)

        home = report["home"]
        away = report["away"]
        home_primary = hex_to_rgb(home["primary_color"], (208, 52, 52))
        away_primary = hex_to_rgb(away["primary_color"], (57, 112, 208))
        home_secondary = hex_to_rgb(home["secondary_color"], (245, 245, 245))
        away_secondary = hex_to_rgb(away["secondary_color"], (245, 245, 245))

        title = "FULL TIME"
        draw_text(self.screen, title, panel.x + (panel.width - text_width(title, 4)) // 2, panel.y + 18, (245, 245, 245), scale=4)

        score_band = pygame.Rect(panel.x + 18, panel.y + 68, panel.width - 36, 92)
        pygame.draw.rect(self.screen, (12, 14, 18), score_band, border_radius=10)
        pygame.draw.rect(self.screen, (50, 52, 58), score_band, 1, border_radius=10)
        pygame.draw.rect(self.screen, home_primary, (score_band.x, score_band.y, score_band.width // 2, 10), border_top_left_radius=10)
        pygame.draw.rect(self.screen, away_primary, (score_band.centerx, score_band.y, score_band.width - score_band.width // 2, 10), border_top_right_radius=10)

        home_badge = pygame.Rect(score_band.x + 20, score_band.y + 20, 42, 48)
        away_badge = pygame.Rect(score_band.right - 62, score_band.y + 20, 42, 48)
        self._draw_club_badge(home["badge"], home_badge)
        self._draw_club_badge(away["badge"], away_badge)
        draw_text(self.screen, compact_team_name(home["name"]), home_badge.right + 12, score_band.y + 24, home_secondary, scale=3)
        away_name = compact_team_name(away["name"])
        draw_text(self.screen, away_name, away_badge.x - 12 - text_width(away_name, 3), score_band.y + 24, away_secondary, scale=3)

        score_text = f"{report['home_score']} - {report['away_score']}"
        draw_text(self.screen, score_text, score_band.x + (score_band.width - text_width(score_text, 4)) // 2, score_band.y + 22, (245, 245, 245), scale=4)
        draw_text(self.screen, self._format_report_goal_scorers(report, "home"), score_band.x + 18, score_band.bottom - 20, (190, 194, 204), scale=1)
        away_scorers = self._format_report_goal_scorers(report, "away")
        draw_text(self.screen, away_scorers, score_band.right - 18 - text_width(away_scorers, 1), score_band.bottom - 20, (190, 194, 204), scale=1)

        sections_top = panel.y + 174
        sections_gap = 16
        stats_h = 34 + 16 + 9 * 34 + 12
        player_h = panel.bottom - sections_top - stats_h - sections_gap - 18
        stats_rect = pygame.Rect(panel.x + 18, sections_top, panel.width - 36, stats_h)
        player_rect = pygame.Rect(panel.x + 18, stats_rect.bottom + sections_gap, panel.width - 36, player_h)
        pygame.draw.rect(self.screen, (12, 14, 18), stats_rect, border_radius=8)
        pygame.draw.rect(self.screen, (12, 14, 18), player_rect, border_radius=8)
        pygame.draw.rect(self.screen, (50, 52, 58), stats_rect, 1, border_radius=8)
        pygame.draw.rect(self.screen, (50, 52, 58), player_rect, 1, border_radius=8)
        left_header = pygame.Rect(stats_rect.x, stats_rect.y, stats_rect.width, 34)
        right_header = pygame.Rect(player_rect.x, player_rect.y, player_rect.width, 34)
        pygame.draw.rect(self.screen, (248, 187, 32), left_header, border_top_left_radius=8, border_top_right_radius=8)
        pygame.draw.rect(self.screen, (36, 52, 96), right_header, border_top_left_radius=8, border_top_right_radius=8)
        left_title = "MATCH STATISTICS"
        right_title = "PLAYER STATISTICS"
        draw_text(
            self.screen,
            left_title,
            left_header.x + (left_header.width - text_width(left_title, 2)) // 2,
            left_header.y + 10,
            (24, 24, 28),
            scale=2,
        )
        draw_text(
            self.screen,
            right_title,
            right_header.x + (right_header.width - text_width(right_title, 2)) // 2,
            right_header.y + 10,
            (245, 245, 245),
            scale=2,
        )

        stat_rows = [
            ("BALL POSSESSION", "possession_seconds"),
            ("SHOT ON TARGET", "shots_on_target"),
            ("SHOT OFF TARGET", "shots_off_target"),
            ("PASSING", "passing"),
            ("CORNERS", "corners"),
            ("OFFSIDE", "offsides"),
            ("FOULS", "fouls"),
            ("YELLOW CARD", "yellow_cards"),
            ("RED CARD", "red_cards"),
        ]
        team_stats = report["team_stats"]
        y = stats_rect.y + 50
        row_h = 28
        row_gap = 6
        value_w = 78
        label_w = 220
        for label, key in stat_rows:
            if key == "possession_seconds":
                home_v = team_stats["home"]["possession_seconds"]
                away_v = team_stats["away"]["possession_seconds"]
                total = max(1.0, home_v + away_v)
                home_value = f"{int(round(home_v / total * 100))}%"
                away_value = f"{int(round(away_v / total * 100))}%"
            elif key == "passing":
                home_attempted = max(1.0, team_stats["home"]["passes_attempted"])
                away_attempted = max(1.0, team_stats["away"]["passes_attempted"])
                home_value = f"{int(round(team_stats['home']['passes_completed'] / home_attempted * 100))}%"
                away_value = f"{int(round(team_stats['away']['passes_completed'] / away_attempted * 100))}%"
            else:
                home_value = str(int(round(team_stats["home"].get(key, 0.0))))
                away_value = str(int(round(team_stats["away"].get(key, 0.0))))
            row_rect = pygame.Rect(stats_rect.x + 12, y, stats_rect.width - 24, row_h)
            pygame.draw.rect(self.screen, (18, 20, 26), row_rect, border_radius=5)
            pygame.draw.rect(self.screen, (38, 40, 46), row_rect, 1, border_radius=5)
            home_box = pygame.Rect(row_rect.x + 4, row_rect.y + 4, value_w, row_h - 8)
            away_box = pygame.Rect(row_rect.right - value_w - 4, row_rect.y + 4, value_w, row_h - 8)
            label_box = pygame.Rect(row_rect.centerx - label_w // 2, row_rect.y + 4, label_w, row_h - 8)
            pygame.draw.rect(self.screen, home_primary, home_box, border_radius=4)
            pygame.draw.rect(self.screen, (24, 26, 32), label_box, border_radius=4)
            pygame.draw.rect(self.screen, away_primary, away_box, border_radius=4)
            draw_text(self.screen, home_value, home_box.x + (home_box.width - text_width(home_value, 1)) // 2, home_box.y + 5, home_secondary, scale=1)
            draw_text(self.screen, label, label_box.x + (label_box.width - text_width(label, 1)) // 2, label_box.y + 5, (236, 236, 240), scale=1)
            draw_text(self.screen, away_value, away_box.x + (away_box.width - text_width(away_value, 1)) // 2, away_box.y + 5, away_secondary, scale=1)
            y += row_h + row_gap

        home_players = self._report_players_with_minutes(report, "home")
        away_players = self._report_players_with_minutes(report, "away")
        if not selected_player_id:
            if home_players:
                selected_player_id = home_players[0]["id"]
            elif away_players:
                selected_player_id = away_players[0]["id"]

        max_list_count = max(len(home_players), len(away_players), 1)
        detail_min_w = 430
        if max_list_count > 11:
            squad_w = min(260, max(220, (player_rect.width - detail_min_w - 48) // 2))
        else:
            squad_w = 180
        squad_w = max(180, min(squad_w, (player_rect.width - detail_min_w - 48) // 2))
        list_header_h = 28
        home_list = pygame.Rect(player_rect.x + 12, player_rect.y + 48, squad_w, player_rect.height - 60)
        detail_rect = pygame.Rect(home_list.right + 12, player_rect.y + 48, player_rect.width - squad_w * 2 - 48, player_rect.height - 60)
        away_list = pygame.Rect(detail_rect.right + 12, player_rect.y + 48, squad_w, player_rect.height - 60)
        for rect in (home_list, detail_rect, away_list):
            pygame.draw.rect(self.screen, (18, 20, 26), rect, border_radius=6)
            pygame.draw.rect(self.screen, (50, 52, 58), rect, 1, border_radius=6)
        for rect, title_text in ((home_list, "HOME SQUAD"), (detail_rect, "PLAYER CARD"), (away_list, "AWAY SQUAD")):
            header = pygame.Rect(rect.x, rect.y, rect.width, list_header_h)
            pygame.draw.rect(self.screen, (24, 26, 32), header, border_top_left_radius=6, border_top_right_radius=6)
            draw_text(self.screen, title_text, header.x + (header.width - text_width(title_text, 1)) // 2, header.y + 8, (248, 187, 32), scale=1)

        def draw_squad_list(players: list[dict], rect: pygame.Rect, fill_color: Tuple[int, int, int]) -> None:
            if not players:
                return

            inner_x = rect.x + 6
            inner_y = rect.y + list_header_h + 6
            inner_w = rect.width - 12
            inner_h = rect.height - list_header_h - 12
            row_gap = 3 if len(players) > 11 else 4
            row_h = max(14, min(26, (inner_h - row_gap * max(0, len(players) - 1)) // len(players)))
            compact = row_h < 22

            for idx, player in enumerate(players):
                row_y = inner_y + idx * (row_h + row_gap)
                row_rect = pygame.Rect(inner_x, row_y, inner_w, row_h)
                is_selected = player["id"] == selected_player_id
                if is_selected:
                    pygame.draw.rect(self.screen, fill_color, row_rect, border_radius=4)
                    pygame.draw.rect(self.screen, (248, 187, 32), row_rect, 2, border_radius=4)
                else:
                    pygame.draw.rect(self.screen, (24, 26, 32), row_rect, border_radius=4)

                label = player.get("short_name", player.get("name", "PLAYER"))[:10 if compact else 12]
                text_y = row_rect.y + max(5, (row_rect.height - 7) // 2)
                draw_text(self.screen, label, row_rect.x + 6, text_y, (245, 245, 245), scale=1)

                rating = f"{self._report_player_rating(report, player['id']):.1f}"
                draw_text(self.screen, rating, row_rect.right - 8 - text_width(rating, 1), text_y, (245, 245, 245), scale=1)
                self._register_ui(f"match:player:{player['id']}", row_rect)

        draw_squad_list(home_players, home_list, home_primary)
        draw_squad_list(away_players, away_list, away_primary)

        selected_player = None
        for player in home_players + away_players:
            if player["id"] == selected_player_id:
                selected_player = player
                break
        if not selected_player:
            if home_players:
                selected_player = home_players[0]
                selected_player_id = selected_player["id"]
            elif away_players:
                selected_player = away_players[0]
                selected_player_id = selected_player["id"]
        if selected_player:
            stats = report.get("player_stats", {}).get(selected_player["id"], {})
            selected_side = selected_player["side"]
            card_fill = home_primary if selected_side == "home" else away_primary
            card_text = home_secondary if selected_side == "home" else away_secondary
            selected_badge = home["badge"] if selected_side == "home" else away["badge"]
            card_top = pygame.Rect(detail_rect.x + 12, detail_rect.y + 38, detail_rect.width - 24, 74)
            pygame.draw.rect(self.screen, card_fill, card_top, border_radius=8)
            pygame.draw.rect(self.screen, (22, 22, 26), card_top, 2, border_radius=8)
            draw_text(self.screen, selected_player["name"][:22], card_top.x + 16, card_top.y + 12, card_text, scale=2)
            meta = f"{selected_player['position']}  OVR {selected_player['ovr']}"
            draw_text(self.screen, meta, card_top.x + 16, card_top.y + 40, card_text, scale=1)
            self._draw_club_badge(selected_badge, pygame.Rect(card_top.right - 54, card_top.y + 12, 38, 46))
            if selected_player["position"] == "GK":
                detail_rows = [
                    ("Saves", int(stats.get("goalkeeper_saves", 0.0))),
                    ("Goals conceded", int(stats.get("goalkeeper_goals_conceded", 0.0))),
                    ("Ball recovery", int(stats.get("ball_recoveries", 0.0))),
                    ("Passes", int(stats.get("passes_attempted", 0.0))),
                    ("Accurate passes", int(stats.get("passes_completed", 0.0))),
                    ("Pass accuracy", f"{int(round((stats.get('passes_completed', 0.0) / max(1.0, stats.get('passes_attempted', 0.0))) * 100))}%"),
                    ("Long balls", int(stats.get("long_balls_attempted", 0.0))),
                    ("Long ball accuracy", f"{int(round((stats.get('long_balls_completed', 0.0) / max(1.0, stats.get('long_balls_attempted', 0.0))) * 100))}%"),
                    ("Minutes played", int(round(stats.get("minutes", 0.0)))),
                    ("Fouls committed", int(stats.get("fouls_committed", 0.0))),
                    ("Fouls suffered", int(stats.get("fouls_suffered", 0.0))),
                    ("Yellow cards", int(stats.get("yellow_cards", 0.0))),
                    ("Red cards", int(stats.get("red_cards", 0.0))),
                    ("Goals", int(stats.get("goals", 0.0))),
                    ("Assists", int(stats.get("assists", 0.0))),
                    ("Player rating", f"{self._report_player_rating(report, selected_player['id']):.1f}"),
                ]
            else:
                detail_rows = [
                    ("Goals", int(stats.get("goals", 0.0))),
                    ("Assists", int(stats.get("assists", 0.0))),
                    ("Shots on target", int(stats.get("shots_on_target", 0.0))),
                    ("Shots off target", int(stats.get("shots_off_target", 0.0))),
                    ("Passing", f"{int(round((stats.get('passes_completed', 0.0) / max(1.0, stats.get('passes_attempted', 0.0))) * 100))}%"),
                    ("Tackles", int(stats.get("tackles", 0.0))),
                    ("Interceptions", int(stats.get("interceptions", 0.0))),
                    ("Clearances", int(stats.get("clearances", 0.0))),
                    ("Fouls committed", int(stats.get("fouls_committed", 0.0))),
                    ("Fouls suffered", int(stats.get("fouls_suffered", 0.0))),
                    ("Yellow cards", int(stats.get("yellow_cards", 0.0))),
                    ("Red cards", int(stats.get("red_cards", 0.0))),
                    ("Dribbles", int(stats.get("dribbles_completed", 0.0))),
                    ("Duels won", f"{int(stats.get('duels_won', 0.0))}/{int(stats.get('duels_total', 0.0))}"),
                    ("Minutes", int(round(stats.get("minutes", 0.0)))),
                    ("Player rating", f"{self._report_player_rating(report, selected_player['id']):.1f}"),
                ]
            rows_top = card_top.bottom + 14
            available_h = detail_rect.bottom - rows_top - 10
            columns = 2 if len(detail_rows) * 24 > available_h and detail_rect.width >= 420 else 1
            rows_per_col = (len(detail_rows) + columns - 1) // columns
            col_gap = 12
            col_w = (detail_rect.width - 24 - (columns - 1) * col_gap) // columns
            row_step = 24
            for idx, (label, value) in enumerate(detail_rows):
                col = idx // rows_per_col
                row = idx % rows_per_col
                col_x = detail_rect.x + 12 + col * (col_w + col_gap)
                row_y = rows_top + row * row_step
                stat_row = pygame.Rect(col_x, row_y - 3, col_w, 20)
                pygame.draw.rect(self.screen, (22, 24, 30), stat_row, border_radius=4)
                draw_text(self.screen, str(label), col_x + 8, row_y, (245, 245, 245), scale=1)
                value_text = str(value)
                draw_text(self.screen, value_text, col_x + col_w - 8 - text_width(value_text, 1), row_y, (245, 245, 245), scale=1)
                bar_color = home_primary if idx % 2 == 0 else away_primary
                pygame.draw.line(self.screen, bar_color, (col_x + 8, row_y + 13), (col_x + col_w - 8, row_y + 13), 2)

    def _draw_post_match_screen(self, state: MatchState, selected_player_id: str | None) -> None:
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
        report = {
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
            "home_score": state.home_score,
            "away_score": state.away_score,
            "team_stats": state.team_match_stats,
            "player_stats": state.player_match_stats,
            "player_goals": state.player_goals,
            "player_assists": state.player_assists,
            "players": {
                "home": report_players(state.home, "home"),
                "away": report_players(state.away, "away"),
            },
        }
        panel = pygame.Rect(14, VIEWPORT_Y + 10, SCREEN_W - 28, VIEWPORT_H - 18)
        self._draw_post_match_report(report, selected_player_id, panel)

    def draw_match_report_view(self, report: dict, selected_player_id: str | None, present: bool = True) -> None:
        self.ui_click_targets = {}
        self.screen.fill((18, 18, 22))
        self._layout_pitch()
        pygame.draw.rect(self.screen, (10, 10, 12), pygame.Rect(0, 0, SCREEN_W, TOP_BAR_H))
        report_view = pygame.Rect(0, VIEWPORT_Y, SCREEN_W, VIEWPORT_H)
        pygame.draw.rect(self.screen, (108, 142, 63), report_view)
        panel = pygame.Rect(14, VIEWPORT_Y + 10, SCREEN_W - 28, VIEWPORT_H - 18)
        self._draw_post_match_report(report, selected_player_id, panel)
        self._draw_ui_button(
            pygame.Rect(panel.right - 120, 3, 120, 34),
            "BACK",
            (36, 52, 96),
            (245, 245, 245),
            "back:match_report",
            scale=2,
        )
        if present:
            pygame.display.flip()

    def _draw_top_bar(self, state: MatchState, minute_text: str, paused: bool, speed_label: str, managed_side: str | None = None) -> None:
        time_box = pygame.Rect(14, 0, 96, TOP_BAR_H)
        home_box = pygame.Rect(time_box.right, 0, 160, TOP_BAR_H)
        score_box = pygame.Rect(home_box.right, 0, 116, TOP_BAR_H)
        away_box = pygame.Rect(score_box.right, 0, 160, TOP_BAR_H)
        pause_box = pygame.Rect(SCREEN_W - 142, 0, 142, TOP_BAR_H)

        home_primary = hex_to_rgb(state.home.club.colors.get("primary", "#F3B729"), (243, 183, 41))
        home_secondary = hex_to_rgb(state.home.club.colors.get("secondary", "#281E0E"), (40, 30, 14))
        away_primary = hex_to_rgb(state.away.club.colors.get("primary", "#2C3A68"), (44, 58, 104))
        away_secondary = hex_to_rgb(state.away.club.colors.get("secondary", "#ECCF61"), (236, 207, 97))

        pygame.draw.rect(self.screen, (10, 10, 12), time_box)
        pygame.draw.rect(self.screen, home_primary, home_box)
        pygame.draw.rect(self.screen, (10, 10, 12), score_box)
        pygame.draw.rect(self.screen, away_primary, away_box)
        managed_primary = (
            hex_to_rgb((state.home if managed_side == "home" else state.away).club.colors.get("primary", "#2E3A6A"), (46, 58, 106))
            if managed_side in ("home", "away")
            else (46, 58, 106)
        )
        managed_secondary = (
            hex_to_rgb((state.home if managed_side == "home" else state.away).club.colors.get("secondary", "#F5F5F5"), (245, 245, 245))
            if managed_side in ("home", "away")
            else (245, 245, 245)
        )
        status_fill = (248, 187, 32)
        status_color = (245, 245, 245)
        if state.is_finished or state.awaiting_start:
            status_fill = (88, 170, 104)
            status_color = (245, 255, 245)
        else:
            status_fill = managed_primary
            status_color = managed_secondary
        pygame.draw.rect(self.screen, status_fill, pause_box)

        draw_text(self.screen, minute_text, time_box.x + 10, 11, (245, 245, 245), scale=2)

        badge_h = 24
        badge_w = 20
        home_badge = pygame.Rect(home_box.x + 10, (TOP_BAR_H - badge_h) // 2, badge_w, badge_h)
        away_badge = pygame.Rect(away_box.x + 10, (TOP_BAR_H - badge_h) // 2, badge_w, badge_h)
        self._draw_club_badge(
            {
                "template_id": state.home.club.badge_id,
                "primary": state.home.club.badge_primary,
                "secondary": state.home.club.badge_secondary,
                "border": state.home.club.badge.get("border", "#F5F5F5"),
            },
            home_badge,
        )
        self._draw_club_badge(
            {
                "template_id": state.away.club.badge_id,
                "primary": state.away.club.badge_primary,
                "secondary": state.away.club.badge_secondary,
                "border": state.away.club.badge.get("border", "#F5F5F5"),
            },
            away_badge,
        )
        home_name = compact_team_name(state.home.name)
        away_name = compact_team_name(state.away.name)
        draw_text(self.screen, home_name, home_badge.right + 8, 11, home_secondary, scale=2)
        draw_text(self.screen, away_name, away_badge.right + 8, 11, away_secondary, scale=2)

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
        if state.is_finished:
            status_text = "CONTINUE"
        elif state.awaiting_start:
            status_text = "START"
        elif paused:
            status_text = "PAUSE"
        else:
            status_text = "LIVE"
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
        self.squad_targets = {}
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

    def _draw_icon_button(
        self,
        rect: pygame.Rect,
        label: str,
        fill: Tuple[int, int, int],
        text: Tuple[int, int, int],
        action: str,
        icon: str | None = None,
    ) -> None:
        pygame.draw.rect(self.screen, fill, rect, border_radius=6)
        pygame.draw.rect(self.screen, (22, 22, 26), rect, 2, border_radius=6)
        content_left = rect.x + 16
        if icon == "ball":
            cx = rect.x + 22
            cy = rect.centery
            self._draw_ball_icon(self.screen, (cx, cy), 9)
            content_left = cx + 18
        draw_text(
            self.screen,
            label,
            content_left,
            rect.y + (rect.height - 14) // 2,
            text,
            scale=2,
        )
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
        title = "MY MANAGER CAREER"
        subtitle = "REALISTIC FOOTBALL ENGINE"
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
            ("SPEED X8", "bind_speed_x8"),
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
        selected_save_id = view.get("selected_save_id")
        panel = pygame.Rect(120, 110, SCREEN_W - 240, SCREEN_H - 190)
        self._draw_panel(panel, "LOAD GAME", (36, 52, 96))
        helper = "SELECT A SAVE, THEN LOAD OR DELETE IT."
        draw_text(self.screen, helper, panel.x + 28, panel.y + 54, (245, 245, 245), scale=2)
        y = panel.y + 96
        if not saves:
            draw_text(self.screen, "NO SAVES YET", panel.x + 28, y, (248, 187, 32), scale=2)
        for save in saves[:8]:
            rect = pygame.Rect(panel.x + 28, y, panel.width - 56, 48)
            is_selected = save["id"] == selected_save_id
            fill = (220, 52, 52) if is_selected else (28, 30, 34)
            border = (248, 187, 32) if is_selected else (46, 48, 54)
            pygame.draw.rect(self.screen, fill, rect, border_radius=6)
            pygame.draw.rect(self.screen, border, rect, 2, border_radius=6)
            label = f"{save['manager_name']} - {save['club_name']}"
            draw_text(self.screen, label, rect.x + 16, rect.y + 16, (245, 245, 245), scale=2)
            self._register_ui(f"select_save:{save['id']}", rect)
            y += 58
        action_y = panel.bottom - 54
        if selected_save_id is not None:
            self._draw_ui_button(
                pygame.Rect(panel.right - 318, action_y, 128, 40),
                "DELETE",
                (206, 54, 54),
                (245, 245, 245),
                "load_game:delete_selected",
            )
            self._draw_ui_button(
                pygame.Rect(panel.right - 172, action_y, 128, 40),
                "LOAD",
                (248, 187, 32),
                (24, 24, 28),
                "load_game:load_selected",
            )
        self._draw_ui_button(pygame.Rect(panel.x + 28, panel.bottom - 54, 128, 40), "BACK", (36, 52, 96), (245, 245, 245), "back:menu")

    def _draw_overview_screen(self, view: dict) -> None:
        overview = view.get("overview", {})
        selected_club_id = view.get("selected_club_id", overview.get("club_id"))
        overview_tab = str(view.get("overview_tab", "overview"))
        squad_draft = view.get("squad_draft", {})
        clubs = overview.get("clubs", [])
        players_by_club = overview.get("players_by_club", {})
        standings = overview.get("standings", [])
        fixtures = overview.get("fixtures", [])

        primary = hex_to_rgb(next((club["primary_color"] for club in clubs if club["id"] == overview.get("club_id")), "#D03434"), (208, 52, 52))
        secondary = hex_to_rgb(next((club["secondary_color"] for club in clubs if club["id"] == overview.get("club_id")), "#F5F5F5"), (245, 245, 245))

        self._draw_overview_header(overview, clubs, primary, secondary, overview_tab)
        if overview_tab.startswith("squad_"):
            if overview_tab == "squad_tactics":
                self._draw_overview_tactics_tab(view, overview, primary, secondary)
            else:
                self._draw_overview_formation_tab(view, overview, clubs, primary, secondary, squad_draft)
            return

        self._draw_overview_home_tab(view, overview, selected_club_id, clubs, players_by_club, standings, fixtures, primary, secondary)

    def _draw_overview_header(
        self,
        overview: dict,
        clubs: list[dict],
        primary: Tuple[int, int, int],
        secondary: Tuple[int, int, int],
        overview_tab: str,
    ) -> None:
        top_h = 62
        top = pygame.Rect(0, 0, SCREEN_W, top_h)
        pygame.draw.rect(self.screen, (12, 12, 16), top)
        brand = pygame.Rect(0, 0, 318, top_h)
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
        nav_items = [
            ("OVERVIEW", "overview"),
            ("SQUAD", "squad"),
            ("MATCHES", "matches"),
            ("TRANSFERS", "transfers"),
            ("SCOUTING", "scouting"),
        ]
        x = brand.right + 20
        squad_submenu_anchor_x = x
        for label, tab_key in nav_items:
            active = overview_tab == tab_key or (tab_key == "squad" and overview_tab.startswith("squad_"))
            color = (248, 187, 32) if active else (220, 220, 224)
            rect = pygame.Rect(x - 6, 10, text_width(label, 2) + 12, 28)
            draw_text(self.screen, label, x, 20, color, scale=2)
            action = "overview_tab:squad_formation" if tab_key == "squad" else f"overview_tab:{tab_key}"
            self._register_ui(action, rect)
            if tab_key == "squad" and overview_tab.startswith("squad_"):
                sub_x = squad_submenu_anchor_x
                sub_y = 44
                for sub_label, sub_tab in (("TACTICS", "squad_formation"), ("TRAINING", "squad_tactics")):
                    sub_color = (248, 187, 32) if overview_tab == sub_tab else (170, 174, 182)
                    sub_rect = pygame.Rect(sub_x - 3, sub_y - 2, text_width(sub_label, 1) + 6, 12)
                    draw_text(self.screen, sub_label, sub_x, sub_y, sub_color, scale=1)
                    self._register_ui(f"overview_tab:{sub_tab}", sub_rect)
                    sub_x += text_width(sub_label, 1) + 12
            x += text_width(label, 2) + 26

        next_fixture = overview.get("next_fixture")
        today_fixture = overview.get("today_fixture")
        right_x = SCREEN_W - 20
        if today_fixture:
            play_rect = pygame.Rect(right_x - 176, 11, 176, 40)
            self._draw_icon_button(play_rect, "PLAY MATCH", (46, 160, 67), (245, 245, 245), "overview:play_next_match", icon="ball")
            right_x = play_rect.x - 12
        else:
            advance_rect = pygame.Rect(right_x - 146, 11, 146, 40)
            self._draw_ui_button(advance_rect, "ADVANCE", primary, secondary, "overview:advance_day")
            right_x = advance_rect.x - 12
        info = overview.get("current_date_label", "")
        draw_text(self.screen, info, right_x - text_width(info, 2), 20, (245, 245, 245), scale=2)

    def _draw_overview_home_tab(
        self,
        view: dict,
        overview: dict,
        selected_club_id: str | None,
        clubs: list[dict],
        players_by_club: dict,
        standings: list[dict],
        fixtures: list[dict],
        primary: Tuple[int, int, int],
        secondary: Tuple[int, int, int],
    ) -> None:
        next_fixture = overview.get("next_fixture")
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
            club_meta = next((club for club in clubs if club["id"] == row["club_id"]), None)
            badge_rect = pygame.Rect(col_t_club, y - 3, 12, 14)
            if club_meta:
                self._draw_club_badge(
                    {
                        "template_id": club_meta.get("badge_template_id", "1"),
                        "primary": club_meta.get("badge_primary", "#2E3A6A"),
                        "secondary": club_meta.get("badge_secondary", "#F5F5F5"),
                        "border": club_meta.get("badge_border", "#F5F5F5"),
                    },
                    badge_rect,
                )
            draw_text(self.screen, short_display_name(row["club_name"], 10), badge_rect.right + 6, y, color, scale=1)
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
            date_label = fixture.get("fixture_date_label", "")[:6]
            line = f"{date_label} {short_display_name(fixture['home_name'], 8)} {score} {short_display_name(fixture['away_name'], 8)}"
            color = (248, 187, 32) if fixture.get("has_report") else (245, 245, 245)
            draw_text(self.screen, line, right.x + 16, y, color, scale=1)
            if fixture.get("has_report"):
                self._register_ui(f"overview:fixture:{fixture['id']}", pygame.Rect(right.x + 12, y - 2, right.width - 24, 16))
            y += 18

        if next_fixture:
            subtitle = f"{next_fixture.get('fixture_date_label', '')} {short_display_name(next_fixture['home_name'], 8)} VS {short_display_name(next_fixture['away_name'], 8)}"
            y += 12
            draw_text(self.screen, subtitle, right.x + 16, y, (245, 245, 245), scale=1)

    def _draw_overview_formation_tab(
        self,
        view: dict,
        overview: dict,
        clubs: list[dict],
        primary: Tuple[int, int, int],
        secondary: Tuple[int, int, int],
        squad_draft: dict,
    ) -> None:
        managed_club_id = overview.get("club_id")
        club = next((entry for entry in clubs if entry["id"] == managed_club_id), None)
        players = overview.get("players_by_club", {}).get(managed_club_id, [])
        players_by_id = {player["id"]: player for player in players}
        xi_ids = list(squad_draft.get("xi_ids", []))
        bench_ids = list(squad_draft.get("bench_ids", []))
        formation = str(squad_draft.get("formation", "4-3-3"))
        instructions = dict(DEFAULT_TEAM_INSTRUCTIONS)
        instructions.update(squad_draft.get("instructions", {}))
        player_instructions = dict(squad_draft.get("player_instructions", {}))
        drag_player_id = squad_draft.get("drag_player_id")
        hover_target_id = squad_draft.get("hover_target_id")
        hover_player_id = squad_draft.get("hover_player_id")
        selected_player_id = squad_draft.get("selected_player_id")
        drag_pos = squad_draft.get("drag_pos")

        content_y = 74
        content_h = SCREEN_H - content_y - 24
        panel = pygame.Rect(20, content_y, SCREEN_W - 40, content_h)
        self._draw_panel(panel, "TACTICS", (16, 18, 20), (245, 245, 245))

        selector_y = panel.y + 48
        selector_x = panel.x + 14
        for name in available_formations():
            width = text_width(name, 1) + 18
            rect = pygame.Rect(selector_x, selector_y, width, 24)
            active = formation == name
            fill = (248, 187, 32) if active else (36, 52, 96)
            text = (24, 24, 28) if active else (245, 245, 245)
            self._draw_ui_button(rect, name, fill, text, f"squad:formation:{name}", scale=1)
            selector_x += width + 8

        pitch_w = max(360, min(int(panel.width * 0.6), panel.width - 320))
        pitch_rect = pygame.Rect(panel.x + 18, panel.y + 84, pitch_w, min(448, panel.height - 228))
        pygame.draw.rect(self.screen, (26, 30, 38), pitch_rect, border_radius=10)
        pygame.draw.rect(self.screen, (64, 70, 82), pitch_rect, 2, border_radius=10)
        inner_pitch = pitch_rect.inflate(-24, -24)
        pygame.draw.rect(self.screen, (42, 46, 54), inner_pitch, border_radius=8)
        pygame.draw.rect(self.screen, (92, 96, 108), inner_pitch, 2, border_radius=8)
        pygame.draw.line(self.screen, (92, 96, 108), (inner_pitch.x + inner_pitch.width // 2, inner_pitch.y), (inner_pitch.x + inner_pitch.width // 2, inner_pitch.bottom), 1)
        pygame.draw.circle(self.screen, (92, 96, 108), inner_pitch.center, 34, 1)
        for ratio in (0.25, 0.5, 0.75):
            lane_y = inner_pitch.y + int(inner_pitch.height * ratio)
            pygame.draw.line(self.screen, (54, 70, 72), (inner_pitch.x, lane_y), (inner_pitch.right, lane_y), 1)

        slots = formation_slots(formation)
        layout_map = self._formation_preview_layout(formation, inner_pitch)
        slot_counts: dict[str, int] = {}
        for idx, slot in enumerate(slots):
            slot_counts[slot] = slot_counts.get(slot, 0) + 1
            slot_key = f"{slot}{slot_counts[slot]}" if slots.count(slot) > 1 else slot
            player_id = xi_ids[idx] if idx < len(xi_ids) else None
            player = players_by_id.get(player_id or "")
            node = layout_map.get(slot_key, inner_pitch.center)
            fit = position_fit_label(player["position"], slot) if player else "wrong"
            outline = (90, 188, 108) if fit == "natural" else (228, 190, 84) if fit == "cover" else (210, 86, 86)
            role_w = max(44, text_width(slot, 1) + 18)
            role_rect = pygame.Rect(0, 0, role_w, 16)
            role_rect.midbottom = (node[0], node[1] - 4)
            is_selected = player_id == selected_player_id
            fill = (44, 50, 60) if hover_target_id != player_id else (76, 128, 84)
            if is_selected:
                fill = (58, 70, 110)
            pygame.draw.rect(self.screen, fill, role_rect, border_radius=8)
            pygame.draw.rect(self.screen, outline, role_rect, 1, border_radius=8)
            draw_text(self.screen, slot, role_rect.x + (role_rect.width - text_width(slot, 1)) // 2, role_rect.y + 4, (230, 234, 240), scale=1)
            if player:
                name = short_display_name(player["name"], 12)
                name_x = node[0] - text_width(name, 1) // 2
                draw_text(self.screen, name, name_x, node[1] + 2, (245, 245, 245), scale=1)
                hit_rect = pygame.Rect(0, 0, max(role_rect.width, text_width(name, 1) + 12), 34)
                hit_rect.center = (node[0], node[1] + 5)
                self.squad_targets[f"xi:{player_id}"] = {"player_id": player_id, "group": "xi", "rect": hit_rect}
            else:
                draw_text(self.screen, "--", node[0] - text_width("--", 1) // 2, node[1] + 2, (160, 164, 172), scale=1)

        cards_x = pitch_rect.right + 18
        cards_w = panel.right - cards_x - 18
        cards_title_y = panel.y + 88
        draw_text(self.screen, "TEAM INSTRUCTIONS", cards_x, cards_title_y - 18, (248, 187, 32), scale=1)
        cards = [
            ("passing", "PASSING"),
            ("tempo", "TEMPO"),
            ("width", "WIDTH"),
            ("gameplan", "GAMEPLAN"),
            ("playstyle", "PLAYSTYLE"),
            ("time_management", "TIME MANAGEMENT"),
            ("set_pieces", "SET PIECES"),
        ]
        card_gap = 12
        card_columns = 2 if cards_w >= 420 else 1
        card_w = cards_w if card_columns == 1 else (cards_w - card_gap) // 2
        card_h = 90
        for idx, (key, title) in enumerate(cards):
            col = idx % card_columns
            row = idx // card_columns
            card = pygame.Rect(cards_x + col * (card_w + card_gap), cards_title_y + row * (card_h + 12), card_w, card_h)
            current_value = str(instructions.get(key, DEFAULT_TEAM_INSTRUCTIONS[key]))
            pygame.draw.rect(self.screen, (22, 24, 30), card, border_radius=10)
            pygame.draw.rect(self.screen, (58, 62, 76), card, 1, border_radius=10)
            draw_text(self.screen, title, card.x + 12, card.y + 10, (248, 187, 32), scale=1)
            icon_rect = pygame.Rect(card.x + 10, card.y + 28, card.width - 20, 32)
            self._draw_instruction_icon(key, icon_rect, secondary)
            self._draw_team_instruction_preview(card, key, current_value)

        legend_y = pitch_rect.bottom + 12
        draw_text(self.screen, "POSITION FIT", panel.x + 18, legend_y, (248, 187, 32), scale=1)
        for idx, (label, color) in enumerate((("NATURAL", (90, 188, 108)), ("COVER", (228, 190, 84)), ("WRONG", (210, 86, 86)))):
            lx = panel.x + 112 + idx * 86
            pygame.draw.rect(self.screen, color, pygame.Rect(lx, legend_y + 1, 10, 10))
            draw_text(self.screen, label, lx + 16, legend_y, (220, 224, 232), scale=1)

        bench_rect = pygame.Rect(panel.x + 18, legend_y + 24, pitch_rect.width, panel.bottom - legend_y - 52)
        pygame.draw.rect(self.screen, (18, 20, 26), bench_rect, border_radius=8)
        pygame.draw.rect(self.screen, (50, 52, 58), bench_rect, 1, border_radius=8)
        header = pygame.Rect(bench_rect.x, bench_rect.y, bench_rect.width, 24)
        pygame.draw.rect(self.screen, (24, 26, 32), header, border_top_left_radius=8, border_top_right_radius=8)
        draw_text(self.screen, "BENCH", header.x + 8, header.y + 7, (248, 187, 32), scale=1)
        helper = "DRAG ACROSS THE PITCH TO SWAP XI ROLES OR DRAG BETWEEN PITCH AND BENCH TO CHANGE THE LINEUP."
        helper_y = bench_rect.y - 15
        draw_text(self.screen, helper, cards_x, helper_y, (190, 194, 204), scale=1)
        row_y = bench_rect.y + 32
        row_h = 24
        row_gap = 6
        visible_bench_ids = [player_id for player_id in bench_ids[:12] if players_by_id.get(player_id)]
        for idx, player_id in enumerate(visible_bench_ids):
            player = players_by_id.get(player_id)
            if not player:
                continue
            row_rect = pygame.Rect(bench_rect.x + 8, row_y + idx * (row_h + row_gap), bench_rect.width - 16, row_h)
            is_selected = player_id == selected_player_id
            fill = (24, 26, 32) if hover_target_id != player_id else (76, 128, 84)
            if is_selected:
                fill = (50, 58, 84)
            pygame.draw.rect(self.screen, fill, row_rect, border_radius=6)
            pygame.draw.rect(self.screen, (84, 88, 98) if is_selected else (58, 60, 68), row_rect, 1, border_radius=6)
            draw_text(self.screen, player["position"], row_rect.x + 8, row_rect.y + 8, (170, 174, 182), scale=1)
            draw_text(self.screen, short_display_name(player["name"], 14), row_rect.x + 40, row_rect.y + 8, (245, 245, 245), scale=1)
            ovr = str(player["ovr"])
            draw_text(self.screen, ovr, row_rect.right - 8 - text_width(ovr, 1), row_rect.y + 8, (245, 245, 245), scale=1)
            self.squad_targets[f"bench:{player_id}"] = {"player_id": player_id, "group": "bench", "rect": row_rect}
            if row_rect.bottom + row_h > bench_rect.bottom:
                break

        detail_rect = pygame.Rect(cards_x, legend_y + 24, cards_w, panel.bottom - legend_y - 52)
        pygame.draw.rect(self.screen, (18, 20, 26), detail_rect, border_radius=8)
        pygame.draw.rect(self.screen, (50, 52, 58), detail_rect, 1, border_radius=8)
        compare_player_id = None
        if drag_player_id and str(drag_player_id) == str(selected_player_id) and hover_target_id and hover_target_id != selected_player_id:
            compare_player_id = hover_target_id
        self._draw_player_detail_panel(
            detail_rect,
            players_by_id,
            selected_player_id,
            compare_player_id,
            player_instructions,
        )

        if drag_player_id and drag_pos:
            player = players_by_id.get(str(drag_player_id))
            if player:
                preview = pygame.Rect(0, 0, 144, 24)
                pygame.draw.rect(self.screen, (16, 18, 22), preview.move(drag_pos[0] - 72, drag_pos[1] - 12), border_radius=6)
                pygame.draw.rect(self.screen, (248, 187, 32), preview.move(drag_pos[0] - 72, drag_pos[1] - 12), 1, border_radius=6)
                draw_text(self.screen, short_display_name(player["name"], 14), drag_pos[0] - 62, drag_pos[1] - 5, (245, 245, 245), scale=1)

    def _draw_overview_tactics_tab(
        self,
        view: dict,
        overview: dict,
        primary: Tuple[int, int, int],
        secondary: Tuple[int, int, int],
    ) -> None:
        squad_draft = view.get("squad_draft", {})
        instructions = dict(DEFAULT_TEAM_INSTRUCTIONS)
        instructions.update(squad_draft.get("instructions", {}))
        content_y = 106
        content_h = SCREEN_H - content_y - 24
        left = pygame.Rect(20, content_y, (SCREEN_W - 58) // 2, content_h)
        right = pygame.Rect(left.right + 18, content_y, SCREEN_W - left.right - 38, content_h)
        self._draw_panel(left, "TRAINING HUB", (16, 18, 20), (245, 245, 245))
        self._draw_panel(right, "TRAINING NOTES", (16, 18, 20), (245, 245, 245))

        settings = [
            ("Passing", TEAM_INSTRUCTION_LABELS["passing"][instructions["passing"]]),
            ("Width", TEAM_INSTRUCTION_LABELS["width"][instructions["width"]]),
            ("Playstyle", TEAM_INSTRUCTION_LABELS["playstyle"][instructions["playstyle"]]),
            ("Tempo", TEAM_INSTRUCTION_LABELS["tempo"][instructions["tempo"]]),
            ("Gameplan", TEAM_INSTRUCTION_LABELS["gameplan"][instructions["gameplan"]]),
        ]
        chip_y = left.y + 52
        for label, value in settings:
            card = pygame.Rect(left.x + 18, chip_y, left.width - 36, 54)
            pygame.draw.rect(self.screen, (22, 24, 30), card, border_radius=8)
            pygame.draw.rect(self.screen, (54, 58, 70), card, 1, border_radius=8)
            draw_text(self.screen, label.upper(), card.x + 12, card.y + 10, (248, 187, 32), scale=1)
            draw_text(self.screen, value, card.x + 12, card.y + 28, (245, 245, 245), scale=1)
            chip_y += 64

        columns = [
            ("PASSING", [TEAM_INSTRUCTION_LABELS["passing"][instructions["passing"]], "AFFECTS PASS RISK", "LIVE IN ENGINE", "CLICK IN TACTICS"]),
            ("WIDTH", [TEAM_INSTRUCTION_LABELS["width"][instructions["width"]], "CENTER OR WINGS", "SHAPE + THROW-INS", "LIVE IN ENGINE"]),
            ("SET PIECES", [TEAM_INSTRUCTION_LABELS["set_pieces"][instructions["set_pieces"]], "CORNERS", "FREE KICKS", "THROW-INS"]),
            ("CLOCK", [TEAM_INSTRUCTION_LABELS["time_management"][instructions["time_management"]], "LEAD MANAGEMENT", "GAME STATE RULES", "LIVE IN ENGINE"]),
        ]
        card_w = (right.width - 54) // 2
        card_h = 132
        start_x = right.x + 18
        start_y = right.y + 52
        for idx, (title, items) in enumerate(columns):
            col = idx % 2
            row = idx // 2
            card = pygame.Rect(start_x + col * (card_w + 18), start_y + row * (card_h + 18), card_w, card_h)
            pygame.draw.rect(self.screen, (22, 24, 30), card, border_radius=8)
            pygame.draw.rect(self.screen, (54, 58, 70), card, 1, border_radius=8)
            draw_text(self.screen, title, card.x + 12, card.y + 10, (248, 187, 32), scale=1)
            line_y = card.y + 34
            for item in items:
                draw_text(self.screen, item.upper(), card.x + 12, line_y, (210, 214, 224), scale=1)
                line_y += 20

        helper = "Use TACTICS to change the live instructions quickly. This panel now mirrors the real saved settings."
        draw_text(self.screen, helper[:86], right.x + 18, right.bottom - 28, (190, 194, 204), scale=1)

    def _draw_team_instruction_preview(self, card: pygame.Rect, key: str, current_value: str, action_prefix: str = "squad") -> None:
        left_label, center_label, right_label = instruction_preview_labels(key, current_value)
        center_y = card.bottom - 18
        left_rect = pygame.Rect(card.x + 8, center_y + 2, 7, 7)
        right_rect = pygame.Rect(card.right - 15, center_y + 2, 7, 7)
        left_enabled = left_label is not None
        right_enabled = right_label is not None
        left_color = (220, 224, 232) if left_enabled else (88, 92, 104)
        right_color = (220, 224, 232) if right_enabled else (88, 92, 104)
        pygame.draw.polygon(
            self.screen,
            left_color,
            [(left_rect.right, left_rect.y), (left_rect.x, left_rect.centery), (left_rect.right, left_rect.bottom)],
            0,
        )
        pygame.draw.polygon(
            self.screen,
            right_color,
            [(right_rect.x, right_rect.y), (right_rect.right, right_rect.centery), (right_rect.x, right_rect.bottom)],
            0,
        )
        if left_label:
            draw_text(self.screen, left_label, card.x + 28, center_y, (112, 116, 128), scale=1)
        center_x = card.centerx - text_width(center_label, 1) // 2
        draw_text(self.screen, center_label, center_x, center_y, (245, 245, 245), scale=1)
        if right_label:
            draw_text(self.screen, right_label, card.right - 28 - text_width(right_label, 1), center_y, (112, 116, 128), scale=1)
        if left_enabled:
            self._register_ui(f"{action_prefix}:instruction_step:{key}:-1", left_rect.inflate(8, 8))
        if right_enabled:
            self._register_ui(f"{action_prefix}:instruction_step:{key}:1", right_rect.inflate(8, 8))

    def _attribute_profile(self, player: dict) -> dict[str, float]:
        attrs = dict(player.get("attributes", {}))
        fallback = float(player.get("ovr", 70))

        def avg(*keys: str) -> float:
            values = [float(attrs.get(key, fallback)) for key in keys]
            return sum(values) / max(1, len(values))

        return {
            "MENTAL": avg("anticipation", "composure", "concentration", "decisions", "teamwork", "work_rate"),
            "DEFENDING": avg("tackling", "marking", "positioning", "heading", "strength", "bravery"),
            "PHYSICAL": avg("strength", "balance", "jumping_reach", "natural_fitness", "stamina"),
            "SPEED": avg("acceleration", "pace", "agility"),
            "VISION": avg("vision", "passing", "short_passing", "long_passing", "technique", "crossing"),
            "ATTACKING": avg("finishing", "dribbling", "first_touch", "off_ball", "long_shots", "technique"),
        }

    def _draw_attribute_radar(self, rect: pygame.Rect, player: dict) -> None:
        values = self._attribute_profile(player)
        labels = list(values.keys())
        center = (rect.centerx, rect.centery + 8)
        radius = max(36, min(rect.width, rect.height) // 2 - 36)
        rings = [0.28, 0.48, 0.68, 0.88]
        ring_colors = [(42, 46, 54), (54, 60, 70), (68, 76, 88), (84, 94, 108)]
        for scale, color in zip(reversed(rings), reversed(ring_colors)):
            ring_points = []
            for idx in range(len(labels)):
                angle = (-math.pi / 2) + idx * (math.pi * 2 / len(labels))
                ring_points.append(
                    (
                        int(center[0] + math.cos(angle) * radius * scale),
                        int(center[1] + math.sin(angle) * radius * scale),
                    )
                )
            pygame.draw.polygon(self.screen, color, ring_points)
            pygame.draw.polygon(self.screen, (94, 100, 114), ring_points, 1)
        value_points = []
        for idx, label in enumerate(labels):
            angle = (-math.pi / 2) + idx * (math.pi * 2 / len(labels))
            scale = max(0.18, min(0.78, float(values[label]) / 115.0))
            value_points.append(
                (
                    int(center[0] + math.cos(angle) * radius * scale),
                    int(center[1] + math.sin(angle) * radius * scale),
                )
            )
        pygame.draw.polygon(self.screen, (250, 231, 156), value_points)
        pygame.draw.polygon(self.screen, (242, 132, 108), value_points, 2)
        for idx, label in enumerate(labels):
            angle = (-math.pi / 2) + idx * (math.pi * 2 / len(labels))
            label_x = int(center[0] + math.cos(angle) * (radius + 34))
            label_y = int(center[1] + math.sin(angle) * (radius + 26))
            value_text = str(int(round(values[label])))
            draw_text(self.screen, label, label_x - text_width(label, 1) // 2, label_y - 12, (220, 224, 232), scale=1)
            draw_text(self.screen, value_text, label_x - text_width(value_text, 1) // 2, label_y + 4, (248, 187, 32), scale=1)

    def _draw_foot_icon(self, rect: pygame.Rect, active: bool, flip: bool = False) -> None:
        color = (248, 187, 32) if active else (94, 98, 110)
        sole = [
            (0.22, 0.08), (0.48, 0.06), (0.66, 0.16), (0.76, 0.34),
            (0.76, 0.56), (0.62, 0.8), (0.4, 0.92), (0.24, 0.8), (0.18, 0.5), (0.18, 0.24),
        ]
        toes = [(0.68, 0.14), (0.84, 0.18), (0.9, 0.28), (0.84, 0.38), (0.7, 0.34)]
        if flip:
            sole = [(1.0 - px, py) for px, py in sole]
            toes = [(1.0 - px, py) for px, py in toes]
        pygame.draw.polygon(self.screen, color, scale_points(sole, rect), 2)
        pygame.draw.polygon(self.screen, color, scale_points(toes, rect), 2)

    def _draw_stat_icon(self, kind: str, rect: pygame.Rect, color: Tuple[int, int, int]) -> None:
        if kind == "apps":
            body = rect.inflate(-4, -2)
            pygame.draw.rect(self.screen, color, body, 1, border_radius=2)
            pygame.draw.line(self.screen, color, (body.x + 3, body.y + 5), (body.right - 3, body.y + 5), 1)
            pygame.draw.line(self.screen, color, (body.x + 4, body.y - 1), (body.x + 4, body.y + 5), 1)
            pygame.draw.line(self.screen, color, (body.right - 4, body.y - 1), (body.right - 4, body.y + 5), 1)
        elif kind == "goals":
            pygame.draw.circle(self.screen, color, rect.center, max(5, rect.width // 3), 1)
            pygame.draw.line(self.screen, color, (rect.centerx - 3, rect.centery), (rect.centerx + 3, rect.centery), 1)
            pygame.draw.line(self.screen, color, (rect.centerx, rect.centery - 3), (rect.centerx, rect.centery + 3), 1)
        else:
            boot_rect = rect.inflate(-2, -3)
            boot = [(0.1, 0.5), (0.42, 0.5), (0.58, 0.62), (0.84, 0.62), (0.9, 0.8), (0.18, 0.8), (0.08, 0.66)]
            pygame.draw.polygon(self.screen, color, scale_points(boot, boot_rect), 1)
            pygame.draw.line(self.screen, color, (boot_rect.x + 4, boot_rect.y + 6), (boot_rect.x + 10, boot_rect.y + 6), 1)

    def _draw_stat_chip(self, rect: pygame.Rect, kind: str, value: int) -> None:
        icon_rect = pygame.Rect(rect.x, rect.y, 16, 16)
        self._draw_stat_icon(kind, icon_rect, (200, 204, 212))
        value_text = str(int(value))
        draw_text(self.screen, value_text, icon_rect.right + 5, rect.y + 4, (220, 224, 232), scale=1)

    def _draw_slider_control(
        self,
        rect: pygame.Rect,
        player_id: str,
        key: str,
        value: int,
        target_store: str = "squad",
    ) -> None:
        title = key.upper()
        low_label, high_label = PLAYER_INSTRUCTION_LABELS[key]
        draw_text(self.screen, title, rect.x, rect.y, (248, 187, 32), scale=1)
        value_text = f"{value}%"
        draw_text(self.screen, value_text, rect.right - text_width(value_text, 1), rect.y, (245, 245, 245), scale=1)
        track = pygame.Rect(rect.x, rect.y + 20, rect.width, 12)
        pygame.draw.rect(self.screen, (34, 38, 46), track, border_radius=6)
        fill_w = max(8, int(track.width * (value / 100.0)))
        fill_color = (84, 148, 98) if value <= 50 else (206, 96, 84)
        pygame.draw.rect(self.screen, fill_color, pygame.Rect(track.x, track.y, fill_w, track.height), border_radius=6)
        pygame.draw.rect(self.screen, (78, 82, 94), track, 1, border_radius=6)
        knob_x = track.x + int(track.width * (value / 100.0))
        knob_rect = pygame.Rect(knob_x - 5, track.y - 5, 10, track.height + 10)
        pygame.draw.rect(self.screen, (240, 240, 244), knob_rect, border_radius=4)
        pygame.draw.rect(self.screen, (26, 28, 34), knob_rect, 1, border_radius=4)
        draw_text(self.screen, low_label, rect.x, rect.y + 38, (170, 174, 182), scale=1)
        draw_text(self.screen, high_label, rect.right - text_width(high_label, 1), rect.y + 38, (170, 174, 182), scale=1)
        target_map = self.squad_slider_targets if target_store == "squad" else self.match_slider_targets
        target_map[f"{player_id}:{key}"] = {
            "player_id": player_id,
            "key": key,
            "rect": pygame.Rect(track.x - 4, track.y - 6, track.width + 8, track.height + 12),
            "track": track.copy(),
        }

    def _draw_single_player_focus(self, rect: pygame.Rect, player: dict, instructions: dict[str, int], target_store: str = "squad") -> None:
        stacked = rect.width < 520
        if stacked:
            info_h = min(rect.height - 140, max(260, int(rect.height * 0.58)))
            info_rect = pygame.Rect(rect.x + 18, rect.y + 18, rect.width - 36, info_h)
            side_rect = pygame.Rect(rect.x + 18, info_rect.bottom + 14, rect.width - 36, rect.bottom - info_rect.bottom - 32)
        else:
            info_w = max(220, min(290, rect.width // 2 - 18))
            info_rect = pygame.Rect(rect.x + 18, rect.y + 18, info_w, rect.height - 36)
            side_rect = pygame.Rect(info_rect.right + 18, rect.y + 18, rect.right - info_rect.right - 36, rect.height - 36)
        name = player["name"].upper()
        number = "".join(ch for ch in player["id"] if ch.isdigit())[-2:] or "0"
        preferred_foot = str(player.get("preferred_foot", "right")).lower()
        draw_text(self.screen, name, info_rect.x, info_rect.y, (248, 187, 32), scale=2)
        draw_text(self.screen, number.rjust(2, "0"), info_rect.right - text_width(number.rjust(2, "0"), 2), info_rect.y, (248, 187, 32), scale=2)
        draw_text(self.screen, player["position"], info_rect.x, info_rect.y + 28, (170, 174, 182), scale=1)
        foot_left_rect = pygame.Rect(info_rect.x + 34, info_rect.y + 26, 14, 18)
        foot_right_rect = pygame.Rect(info_rect.x + 54, info_rect.y + 26, 14, 18)
        self._draw_foot_icon(foot_left_rect, preferred_foot == "left", flip=False)
        self._draw_foot_icon(foot_right_rect, preferred_foot == "right", flip=True)
        stats_y = info_rect.y + 52
        self._draw_stat_chip(pygame.Rect(info_rect.x, stats_y, 48, 18), "apps", int(player.get("apps", 0)))
        self._draw_stat_chip(pygame.Rect(info_rect.x + 74, stats_y, 48, 18), "goals", int(player.get("goals", 0)))
        self._draw_stat_chip(pygame.Rect(info_rect.x + 148, stats_y, 48, 18), "assists", int(player.get("assists", 0)))
        radar_size = min(info_rect.width - 12, info_rect.height - 108, 270 if not stacked else 230)
        radar_rect = pygame.Rect(info_rect.x + (info_rect.width - radar_size) // 2, info_rect.y + 82, radar_size, radar_size)
        self._draw_attribute_radar(radar_rect, player)

        draw_text(self.screen, "PLAYER INSTRUCTIONS", side_rect.x, side_rect.y, (248, 187, 32), scale=1)
        slider_gap = 18 if stacked else 20
        pressure_rect = pygame.Rect(side_rect.x, side_rect.y + 28, side_rect.width, 82)
        mindset_rect = pygame.Rect(side_rect.x, pressure_rect.bottom + slider_gap, side_rect.width, 82)
        self._draw_slider_control(pressure_rect, player["id"], "pressure", int(instructions.get("pressure", 50)), target_store=target_store)
        self._draw_slider_control(mindset_rect, player["id"], "mindset", int(instructions.get("mindset", 50)), target_store=target_store)
        helper_a = "PLAYER SLIDERS OVERRIDE TEAM TENDENCIES."
        helper_b = "50% MEANS BALANCED WITH THE TEAM PLAN."
        helper_y = max(mindset_rect.bottom + 10, side_rect.bottom - 36)
        draw_text(self.screen, helper_a, side_rect.x, helper_y, (170, 174, 182), scale=1)
        draw_text(self.screen, helper_b, side_rect.x, helper_y + 16, (170, 174, 182), scale=1)

    def _draw_compare_player_card(self, rect: pygame.Rect, player: dict, tint: Tuple[int, int, int]) -> None:
        pygame.draw.rect(self.screen, (20, 22, 28), rect, border_radius=8)
        pygame.draw.rect(self.screen, tint, rect, 1, border_radius=8)
        name = short_display_name(player["name"], 18).upper()
        draw_text(self.screen, name, rect.x + 12, rect.y + 10, tint, scale=1)
        meta = f"{player['position']}  OVR {player['ovr']}"
        draw_text(self.screen, meta, rect.x + 12, rect.y + 28, (170, 174, 182), scale=1)
        season = f"{int(player.get('apps', 0))} APPS  {int(player.get('goals', 0))} G  {int(player.get('assists', 0))} A"
        draw_text(self.screen, season, rect.x + 12, rect.y + 44, (220, 224, 232), scale=1)
        radar_rect = pygame.Rect(rect.x + 10, rect.y + 72, rect.width - 20, rect.height - 86)
        self._draw_attribute_radar(radar_rect, player)

    def _draw_player_detail_panel(
        self,
        rect: pygame.Rect,
        players_by_id: dict[str, dict],
        selected_player_id: str | None,
        compare_player_id: str | None,
        player_instruction_map: dict[str, dict[str, int]],
    ) -> None:
        selected = players_by_id.get(str(selected_player_id or ""))
        compare = players_by_id.get(str(compare_player_id or ""))
        if not selected:
            draw_text(self.screen, "SELECT A PLAYER TO VIEW DETAILS.", rect.x + 18, rect.y + 18, (170, 174, 182), scale=1)
            return
        if compare:
            if rect.width < 520:
                left = pygame.Rect(rect.x + 14, rect.y + 14, rect.width - 28, (rect.height - 42) // 2)
                right = pygame.Rect(rect.x + 14, left.bottom + 14, rect.width - 28, rect.height - left.height - 42)
            else:
                left = pygame.Rect(rect.x + 14, rect.y + 14, (rect.width - 42) // 2, rect.height - 28)
                right = pygame.Rect(left.right + 14, rect.y + 14, (rect.width - 42) // 2, rect.height - 28)
            self._draw_compare_player_card(left, selected, (84, 148, 98))
            self._draw_compare_player_card(right, compare, (206, 96, 84))
            return
        instructions = dict(DEFAULT_PLAYER_INSTRUCTIONS)
        instructions.update(player_instruction_map.get(selected["id"], {}))
        self._draw_single_player_focus(rect, selected, instructions)

    def _formation_preview_layout(self, formation: str, rect: pygame.Rect) -> dict[str, tuple[int, int]]:
        templates: dict[str, list[tuple[str, float, float]]] = {
            "4-3-3": [("GK", 0.5, 0.88), ("LB", 0.18, 0.68), ("CB1", 0.38, 0.7), ("CB2", 0.62, 0.7), ("RB", 0.82, 0.68), ("DM", 0.5, 0.54), ("CM", 0.34, 0.4), ("AM", 0.66, 0.4), ("LW", 0.16, 0.22), ("ST", 0.5, 0.16), ("RW", 0.84, 0.22)],
            "4-2-3-1": [("GK", 0.5, 0.88), ("LB", 0.18, 0.68), ("CB1", 0.38, 0.7), ("CB2", 0.62, 0.7), ("RB", 0.82, 0.68), ("DM1", 0.38, 0.52), ("DM2", 0.62, 0.52), ("AM", 0.5, 0.34), ("LW", 0.18, 0.24), ("RW", 0.82, 0.24), ("ST", 0.5, 0.14)],
            "4-4-2": [("GK", 0.5, 0.88), ("LB", 0.18, 0.68), ("CB1", 0.38, 0.7), ("CB2", 0.62, 0.7), ("RB", 0.82, 0.68), ("CM1", 0.38, 0.48), ("CM2", 0.62, 0.48), ("LW", 0.18, 0.34), ("RW", 0.82, 0.34), ("ST1", 0.4, 0.16), ("ST2", 0.6, 0.16)],
            "4-1-4-1": [("GK", 0.5, 0.88), ("LB", 0.18, 0.68), ("CB1", 0.38, 0.7), ("CB2", 0.62, 0.7), ("RB", 0.82, 0.68), ("DM", 0.5, 0.56), ("CM1", 0.36, 0.38), ("CM2", 0.64, 0.38), ("LW", 0.18, 0.24), ("RW", 0.82, 0.24), ("ST", 0.5, 0.14)],
        }
        layout = {}
        for key, px, py in templates.get(formation, templates["4-3-3"]):
            layout[key] = (rect.x + int(rect.width * px), rect.y + int(rect.height * py))
        return layout

    def _tactic_band_label(self, primary: Tuple[int, int, int], fallback: str) -> str:
        if sum(primary) > 420:
            return fallback
        return fallback

    def _draw_instruction_icon(self, title: str, rect: pygame.Rect, color: Tuple[int, int, int]) -> None:
        cx = rect.centerx
        cy = rect.centery
        if title == "passing":
            for idx, offset in enumerate((-10, 0, 10)):
                start = (rect.x + 12, cy + offset)
                end = (rect.right - 18, cy + offset - 4)
                pygame.draw.line(self.screen, color if idx == 1 else (96, 100, 118), start, end, 2)
                pygame.draw.line(self.screen, color if idx == 1 else (96, 100, 118), (end[0] - 6, end[1] - 4), end, 2)
                pygame.draw.line(self.screen, color if idx == 1 else (96, 100, 118), (end[0] - 6, end[1] + 4), end, 2)
        elif title == "tempo":
            pygame.draw.arc(self.screen, color, pygame.Rect(cx - 28, cy - 20, 56, 40), math.pi, 2 * math.pi, 3)
            pygame.draw.line(self.screen, (220, 64, 64), (cx, cy), (cx + 14, cy - 10), 3)
        elif title == "width":
            box = pygame.Rect(cx - 26, cy - 14, 52, 28)
            pygame.draw.rect(self.screen, color, box, 2)
            pygame.draw.line(self.screen, color, (box.x + 8, cy), (box.right - 8, cy), 2)
            pygame.draw.line(self.screen, color, (box.x + 8, cy), (box.x + 16, cy - 5), 2)
            pygame.draw.line(self.screen, color, (box.x + 8, cy), (box.x + 16, cy + 5), 2)
            pygame.draw.line(self.screen, color, (box.right - 8, cy), (box.right - 16, cy - 5), 2)
            pygame.draw.line(self.screen, color, (box.right - 8, cy), (box.right - 16, cy + 5), 2)
        elif title == "gameplan":
            for radius in (10, 18, 26):
                pygame.draw.circle(self.screen, (112, 46, 54), (cx, cy), radius, 2)
            pygame.draw.circle(self.screen, color, (cx, cy), 6)
        elif title == "playstyle":
            pygame.draw.circle(self.screen, color, (cx, cy), 12, 2)
            pent = [(cx, cy - 6), (cx + 6, cy - 2), (cx + 4, cy + 6), (cx - 4, cy + 6), (cx - 6, cy - 2)]
            pygame.draw.polygon(self.screen, color, pent, 2)
            for dx, dy in ((-22, -8), (20, -6), (-18, 12), (18, 12)):
                pygame.draw.circle(self.screen, (96, 100, 118), (cx + dx, cy + dy), 2)
        elif title == "time_management":
            pygame.draw.circle(self.screen, color, (cx, cy), 18, 2)
            pygame.draw.line(self.screen, color, (cx, cy), (cx, cy - 10), 2)
            pygame.draw.line(self.screen, color, (cx, cy), (cx + 8, cy + 4), 2)
            pygame.draw.line(self.screen, color, (cx - 5, cy - 22), (cx + 5, cy - 22), 2)
        else:
            pygame.draw.line(self.screen, color, (cx - 18, cy + 12), (cx - 18, cy - 12), 2)
            pygame.draw.polygon(self.screen, color, [(cx - 18, cy - 12), (cx - 6, cy - 8), (cx - 18, cy - 4)], 0)
            pygame.draw.arc(self.screen, (220, 64, 64), pygame.Rect(cx - 2, cy - 18, 32, 28), 4.8, 5.8, 2)
            pygame.draw.line(self.screen, (220, 64, 64), (cx + 22, cy - 10), (cx + 28, cy - 16), 2)

    def _match_popup_players(self, state: MatchState, side: str) -> list[dict]:
        team = state.home if side == "home" else state.away
        rows: list[dict] = []
        for player in team.xi:
            stats = state.player_match_stats.get(player.profile.id, {})
            rows.append(
                {
                    "id": player.profile.id,
                    "name": player.profile.name,
                    "position": player.profile.position,
                    "ovr": player.profile.ovr,
                    "attributes": dict(player.profile.attributes),
                    "preferred_foot": player.profile.preferred_foot,
                    "apps": 1,
                    "goals": int(stats.get("goals", 0.0)),
                    "assists": int(stats.get("assists", 0.0)),
                    "role": "XI",
                    "rating": self._player_rating(state, player.profile.id),
                }
            )
        for profile in team.bench:
            stats = state.player_match_stats.get(profile.id, {})
            rows.append(
                {
                    "id": profile.id,
                    "name": profile.name,
                    "position": profile.position,
                    "ovr": profile.ovr,
                    "attributes": dict(profile.attributes),
                    "preferred_foot": profile.preferred_foot,
                    "apps": 0,
                    "goals": int(stats.get("goals", 0.0)),
                    "assists": int(stats.get("assists", 0.0)),
                    "role": "BENCH",
                    "rating": self._player_rating(state, profile.id),
                }
            )
        return rows

    def _draw_match_instruction_overlay(
        self,
        state: MatchState,
        managed_side: str | None,
        mode: str,
        formation: str,
        instructions: dict[str, str],
        player_instructions: dict[str, dict[str, int]],
        selected_player_id: str | None,
    ) -> None:
        if managed_side not in ("home", "away"):
            return
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 168))
        self.screen.blit(overlay, (0, 0))
        panel_w = min(1080, SCREEN_W - 96)
        panel_h = min(700, SCREEN_H - 112)
        panel = pygame.Rect((SCREEN_W - panel_w) // 2, (SCREEN_H - panel_h) // 2, panel_w, panel_h)
        self._draw_panel(panel)
        title = "TEAM INSTRUCTIONS" if mode == "team" else "PLAYER INSTRUCTIONS"
        draw_text(self.screen, title, panel.x + 22, panel.y + 18, (248, 187, 32), scale=2)
        managed_team = state.home if managed_side == "home" else state.away
        club_name = compact_team_name(managed_team.name)
        draw_text(self.screen, club_name, panel.right - text_width(club_name, 2) - 22, panel.y + 18, (220, 224, 232), scale=2)
        if mode == "team":
            inner = pygame.Rect(panel.x + 22, panel.y + 56, panel.width - 44, panel.height - 128)
            formation_rect = pygame.Rect(inner.x, inner.y, inner.width, 44)
            pygame.draw.rect(self.screen, (20, 22, 28), formation_rect, border_radius=8)
            pygame.draw.rect(self.screen, (72, 76, 88), formation_rect, 1, border_radius=8)
            draw_text(self.screen, "FORMATION", formation_rect.x + 14, formation_rect.y + 14, (248, 187, 32), scale=1)
            fx = formation_rect.x + 116
            for name in available_formations():
                w = text_width(name, 1) + 18
                button = pygame.Rect(fx, formation_rect.y + 8, w, 26)
                active = formation == name
                fill = (248, 187, 32) if active else (36, 52, 96)
                text = (24, 24, 28) if active else (245, 245, 245)
                self._draw_ui_button(button, name, fill, text, f"match:formation:{name}", scale=1)
                fx += w + 8
            cards = list(instructions.items())
            inner = pygame.Rect(inner.x, formation_rect.bottom + 14, inner.width, inner.height - 58)
            columns = 2 if inner.width >= 520 else 1
            gap = 14
            card_w = (inner.width - gap) // columns if columns == 2 else inner.width
            card_h = 108
            for idx, (key, value) in enumerate(cards):
                row = idx // columns
                col = idx % columns
                card = pygame.Rect(inner.x + col * (card_w + gap), inner.y + row * (card_h + gap), card_w, card_h)
                pygame.draw.rect(self.screen, (24, 26, 32), card, border_radius=8)
                pygame.draw.rect(self.screen, (72, 76, 88), card, 1, border_radius=8)
                draw_text(self.screen, key.replace("_", " ").upper(), card.x + 14, card.y + 12, (248, 187, 32), scale=1)
                icon_rect = pygame.Rect(card.centerx - 34, card.y + 26, 68, 38)
                self._draw_instruction_icon(key, icon_rect, (228, 232, 238))
                self._draw_team_instruction_preview(card, key, str(value), action_prefix="match:team")
        else:
            list_rect = pygame.Rect(panel.x + 22, panel.y + 56, min(270, panel.width // 3), panel.height - 128)
            detail_rect = pygame.Rect(list_rect.right + 18, list_rect.y, panel.right - list_rect.right - 40, list_rect.height)
            pygame.draw.rect(self.screen, (20, 22, 28), list_rect, border_radius=8)
            pygame.draw.rect(self.screen, (72, 76, 88), list_rect, 1, border_radius=8)
            draw_text(self.screen, "SQUAD", list_rect.x + 12, list_rect.y + 10, (248, 187, 32), scale=1)
            players = self._match_popup_players(state, managed_side)
            y = list_rect.y + 34
            row_h = 24
            for player in players[:18]:
                row = pygame.Rect(list_rect.x + 8, y, list_rect.width - 16, row_h)
                selected = str(player["id"]) == str(selected_player_id)
                if selected:
                    pygame.draw.rect(self.screen, (36, 78, 124), row, border_radius=4)
                pygame.draw.rect(self.screen, (58, 62, 74), row, 1, border_radius=4)
                draw_text(self.screen, str(player["role"]), row.x + 6, row.y + 7, (168, 172, 182), scale=1)
                draw_text(self.screen, short_display_name(str(player["name"]), 12), row.x + 34, row.y + 7, (245, 245, 245), scale=1)
                rating = f"{float(player['rating']):.1f}"
                draw_text(self.screen, rating, row.right - text_width(rating, 1) - 8, row.y + 7, (220, 224, 232), scale=1)
                self._register_ui(f"match:instruction_player:select:{player['id']}", row)
                y += row_h + 6
                if y + row_h > list_rect.bottom - 8:
                    break
            selected = next((player for player in players if str(player["id"]) == str(selected_player_id)), None)
            if selected:
                values = dict(DEFAULT_PLAYER_INSTRUCTIONS)
                values.update(player_instructions.get(selected["id"], {}))
                self._draw_single_player_focus(detail_rect, selected, values, target_store="match")
        cancel_rect = pygame.Rect(panel.x + 22, panel.bottom - 50, 150, 32)
        confirm_rect = pygame.Rect(panel.right - 172, panel.bottom - 50, 150, 32)
        self._draw_ui_button(cancel_rect, "CANCEL", (70, 74, 92), (245, 245, 245), "match:instructions:cancel", scale=2)
        self._draw_ui_button(confirm_rect, "CONFIRM", (88, 170, 104), (18, 18, 22), "match:instructions:confirm", scale=2)

    def _draw_instruction_change_animation(self, animation: dict) -> None:
        panel = pygame.Rect(0, 0, min(420, SCREEN_W - 120), 72)
        panel.center = (SCREEN_W // 2, TOP_BAR_H + 74)
        pygame.draw.rect(self.screen, (18, 20, 24), panel, border_radius=8)
        pygame.draw.rect(self.screen, (88, 170, 104), panel, 2, border_radius=8)
        cx = panel.x + 28
        cy = panel.centery
        pygame.draw.circle(self.screen, (88, 170, 104), (cx, cy), 14, 2)
        pygame.draw.line(self.screen, (88, 170, 104), (cx - 5, cy + 1), (cx - 1, cy + 6), 3)
        pygame.draw.line(self.screen, (88, 170, 104), (cx - 1, cy + 6), (cx + 7, cy - 6), 3)
        message = str(animation.get("message", "INSTRUCTIONS CHANGED!"))
        draw_text(self.screen, message, panel.x + 52, panel.y + 28, (245, 245, 245), scale=2)

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
