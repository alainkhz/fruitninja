from __future__ import annotations

from collections import deque
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from config import MAX_MISSES
from game.effects import HitEffect, Particle, ScorePopup
from game.history import GameHistoryEntry
from game.menu import MenuButton
from game.objects import GameObject
from game.settings import RuntimeSettings

FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/msjh.ttc"),
    Path("C:/Windows/Fonts/microsoftjhengheiui.ttf"),
    Path("C:/Windows/Fonts/msyh.ttc"),
]


def _frame_scale(frame) -> float:
    height, width = frame.shape[:2]
    return min(width / 1280.0, height / 720.0)


def _px(frame, base: float) -> int:
    return max(1, int(base * _frame_scale(frame)))


@lru_cache(maxsize=64)
def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


class _TextCanvas:
    def __init__(self, frame) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self._frame = frame
        self._image = Image.fromarray(rgb)
        self._draw = ImageDraw.Draw(self._image)

    def text(self, text: str, position: tuple[int, int], font_px: int, color: tuple[int, int, int]) -> None:
        self._draw.text(position, text, font=_load_font(font_px), fill=(color[2], color[1], color[0]))

    def flush(self) -> None:
        self._frame[:] = cv2.cvtColor(np.array(self._image), cv2.COLOR_RGB2BGR)


def _draw_text(
    frame,
    text: str,
    position: tuple[int, int],
    font_px: int,
    color: tuple[int, int, int],
    text_canvas: _TextCanvas | None = None,
) -> None:
    if text_canvas is not None:
        text_canvas.text(text, position, font_px, color)
        return
    canvas = _TextCanvas(frame)
    canvas.text(text, position, font_px, color)
    canvas.flush()


def _measure_text(text: str, font_px: int) -> tuple[int, int]:
    bbox = _load_font(font_px).getbbox(text)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _draw_centered_text(
    frame,
    text: str,
    center_y: int,
    font_px: int,
    color: tuple[int, int, int],
    text_canvas: _TextCanvas | None = None,
) -> None:
    height, width = frame.shape[:2]
    text_w, text_h = _measure_text(text, font_px)
    x = (width - text_w) // 2
    y = max(0, min(height - text_h, center_y - text_h // 2))
    _draw_text(frame, text, (x, y), font_px, color, text_canvas=text_canvas)


def _draw_panel(
    frame,
    left: int,
    top: int,
    right: int,
    bottom: int,
    fill_color: tuple[int, int, int],
    fill_alpha: float,
    border_color: tuple[int, int, int] | None = None,
    border_width: int = 1,
) -> None:
    overlay = frame.copy()
    cv2.rectangle(overlay, (left, top), (right, bottom), fill_color, -1)
    cv2.addWeighted(overlay, fill_alpha, frame, 1.0 - fill_alpha, 0, frame)
    if border_color is not None:
        cv2.rectangle(frame, (left, top), (right, bottom), border_color, border_width)


def _mix_color(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(channel * factor))) for channel in color)


def _get_level_theme(level: int) -> dict[str, tuple[int, int, int] | float]:
    themes = [
        {
            "left_fill": (44, 38, 34),
            "right_fill": (34, 42, 56),
            "left_border": (214, 186, 154),
            "right_border": (152, 198, 225),
            "accent": (130, 235, 255),
            "energy": (255, 196, 90),
            "overlay": (20, 28, 46),
        },
        {
            "left_fill": (34, 46, 40),
            "right_fill": (30, 54, 54),
            "left_border": (166, 215, 168),
            "right_border": (150, 236, 220),
            "accent": (115, 255, 220),
            "energy": (120, 235, 255),
            "overlay": (16, 42, 36),
        },
        {
            "left_fill": (52, 34, 32),
            "right_fill": (58, 38, 26),
            "left_border": (236, 170, 160),
            "right_border": (255, 214, 120),
            "accent": (255, 214, 130),
            "energy": (255, 145, 90),
            "overlay": (42, 18, 16),
        },
        {
            "left_fill": (34, 32, 52),
            "right_fill": (40, 32, 66),
            "left_border": (176, 166, 236),
            "right_border": (210, 170, 255),
            "accent": (206, 182, 255),
            "energy": (255, 116, 205),
            "overlay": (24, 16, 44),
        },
    ]
    return themes[(max(level, 1) - 1) % len(themes)]


def _draw_energy_bar(
    frame,
    left: int,
    top: int,
    width: int,
    height: int,
    progress: float,
    fill_color: tuple[int, int, int],
    border_color: tuple[int, int, int],
) -> None:
    progress = max(0.0, min(1.0, progress))
    cv2.rectangle(frame, (left, top), (left + width, top + height), (54, 54, 62), -1)
    inner_left = left + 2
    inner_top = top + 2
    inner_width = max(1, width - 4)
    inner_height = max(1, height - 4)
    fill_width = int(inner_width * progress)
    if fill_width > 0:
        for step in range(fill_width):
            blend = 0.72 + 0.48 * (step / max(1, fill_width))
            column_color = _mix_color(fill_color, blend)
            cv2.line(
                frame,
                (inner_left + step, inner_top),
                (inner_left + step, inner_top + inner_height),
                column_color,
                1,
            )
        glow = frame.copy()
        cv2.rectangle(glow, (inner_left, inner_top), (inner_left + fill_width, inner_top + inner_height), fill_color, -1)
        cv2.addWeighted(glow, 0.18, frame, 0.82, 0, frame)
    for notch in range(1, 5):
        notch_x = left + int(width * notch / 5.0)
        cv2.line(frame, (notch_x, top + 1), (notch_x, top + height - 1), (82, 84, 94), 1)
    cv2.rectangle(frame, (left, top), (left + width, top + height), border_color, 1)


def _draw_fruit(
    frame,
    center: tuple[int, int],
    radius: int,
    fruit_name: str,
    base_color: tuple[int, int, int],
    effect: str,
) -> None:
    outline = _mix_color(base_color, 0.72)
    highlight = _mix_color(base_color, 1.2)
    cv2.circle(frame, center, radius, outline, -1)
    cv2.circle(frame, center, max(1, int(radius * 0.82)), base_color, -1)
    cv2.circle(frame, (int(center[0] - radius * 0.3), int(center[1] - radius * 0.28)), max(1, int(radius * 0.25)), highlight, -1)

    if fruit_name == "classic":
        cv2.ellipse(frame, center, (max(1, int(radius * 0.70)), max(1, int(radius * 0.46))), 18, 0, 360, _mix_color(base_color, 0.82), 2)
        cv2.ellipse(frame, center, (max(1, int(radius * 0.46)), max(1, int(radius * 0.28))), -18, 0, 360, _mix_color(base_color, 1.08), 2)
        for offset in (-0.34, 0.0, 0.34):
            px = int(center[0] + radius * offset)
            cv2.line(frame, (px, int(center[1] - radius * 0.48)), (px, int(center[1] + radius * 0.48)), _mix_color(base_color, 0.90), 1)
    elif fruit_name in {"apple", "gold"}:
        cv2.ellipse(frame, (center[0] + radius // 4, center[1] - radius), (max(1, radius // 3), max(1, radius // 6)), -25, 0, 360, (50, 180, 70), -1)
    elif fruit_name == "orange":
        for angle in range(0, 360, 45):
            rad = np.deg2rad(angle)
            px = int(center[0] + np.cos(rad) * radius * 0.62)
            py = int(center[1] + np.sin(rad) * radius * 0.62)
            cv2.circle(frame, (px, py), max(1, radius // 14), _mix_color(base_color, 0.84), -1)
    elif fruit_name in {"lime", "ice"}:
        cv2.circle(frame, center, max(1, int(radius * 0.52)), _mix_color(base_color, 0.75), 2)
        cv2.line(frame, (center[0] - radius // 2, center[1]), (center[0] + radius // 2, center[1]), _mix_color(base_color, 0.75), 2)
        cv2.line(frame, (center[0], center[1] - radius // 2), (center[0], center[1] + radius // 2), _mix_color(base_color, 0.75), 2)
    elif fruit_name == "shock":
        core_color = (80, 255, 255)
        cv2.circle(frame, center, max(1, int(radius * 0.62)), (0, 110, 170), -1)
        cv2.circle(frame, center, max(1, int(radius * 0.72)), (0, 245, 255), 2)
        cv2.circle(frame, center, max(1, int(radius * 0.92)), (0, 255, 255), 2)
        bolt = np.array(
            [
                (center[0] - int(radius * 0.16), center[1] - int(radius * 0.50)),
                (center[0] + int(radius * 0.02), center[1] - int(radius * 0.10)),
                (center[0] - int(radius * 0.05), center[1] - int(radius * 0.10)),
                (center[0] + int(radius * 0.16), center[1] + int(radius * 0.46)),
                (center[0] - int(radius * 0.02), center[1] + int(radius * 0.08)),
                (center[0] + int(radius * 0.05), center[1] + int(radius * 0.08)),
            ],
            dtype=np.int32,
        )
        cv2.fillConvexPoly(frame, bolt, (40, 240, 255))
        cv2.polylines(frame, [bolt], False, (180, 255, 255), 2)
        for angle in (18, 155, 285):
            rad = np.deg2rad(angle)
            start = (int(center[0] + np.cos(rad) * radius * 0.76), int(center[1] + np.sin(rad) * radius * 0.76))
            end = (int(center[0] + np.cos(rad) * radius * 1.10), int(center[1] + np.sin(rad) * radius * 1.10))
            cv2.line(frame, start, end, core_color, 2)
    elif fruit_name == "peach":
        cv2.ellipse(frame, center, (max(1, radius // 4), max(1, radius // 2)), 0, 0, 360, _mix_color(base_color, 0.72), 2)
    elif fruit_name == "fire":
        flame_points = [(center[0], center[1] - radius), (center[0] - radius // 3, center[1] - radius // 5), (center[0], center[1] + radius // 3), (center[0] + radius // 3, center[1] - radius // 6)]
        cv2.fillConvexPoly(frame, np.array(flame_points, dtype=np.int32), (120, 220, 255))

    cv2.line(frame, (center[0], center[1] - radius), (center[0] + radius // 7, center[1] - radius - max(1, radius // 3)), (70, 90, 40), 2)

    ring = {
        "gold": (120, 240, 255),
        "freeze": (255, 255, 220),
        "fire": (100, 210, 255),
        "shock": (0, 255, 255),
    }.get(effect)
    if ring:
        cv2.circle(frame, center, radius + 2, ring, 2)


def _draw_bomb(frame, center: tuple[int, int], radius: int) -> None:
    cv2.circle(frame, center, radius, (40, 40, 40), -1)
    cv2.circle(frame, center, max(1, radius // 3), (20, 20, 110), -1)
    cv2.line(frame, (center[0], center[1] - radius), (center[0] + radius // 3, center[1] - radius - max(1, radius // 3)), (70, 200, 240), 2)
    cv2.circle(frame, (center[0] + radius // 3, center[1] - radius - max(1, radius // 3)), max(1, radius // 8), (60, 220, 255), -1)


def draw_objects(frame, objects: list[GameObject]) -> None:
    for game_object in objects:
        if not game_object.is_alive:
            continue
        center = (int(game_object.x), int(game_object.y))
        if game_object.kind == "bomb":
            _draw_bomb(frame, center, game_object.radius)
        else:
            _draw_fruit(frame, center, game_object.radius, game_object.fruit_name, game_object.color, game_object.effect)


def draw_trail(frame, trail: deque[tuple[int, int]]) -> None:
    trail_points = list(trail)
    for index in range(1, len(trail_points)):
        start = trail_points[index - 1]
        end = trail_points[index]
        intensity = int(255 * index / len(trail_points))
        thickness = max(1, _px(frame, 4 + index * 0.2))
        cv2.line(frame, start, end, (255, intensity, intensity), thickness)


def draw_hud(
    frame,
    score: int,
    misses: int,
    fps: float,
    tracking_active: bool,
    combo: int,
    freeze_seconds_left: float,
    fire_seconds_left: float,
    combo_progress: float,
    skill_charge: float,
    blade_rush_seconds_left: float,
    level: int,
    next_level_score: int,
    level_progress: float,
    level_banner_text: str,
    level_banner_seconds_left: float,
) -> None:
    def hud_px(base: float, minimum: int) -> int:
        return max(minimum, _px(frame, base))

    theme = _get_level_theme(level)
    panel_margin = _px(frame, 14)
    panel_gap = _px(frame, 12)
    panel_top = _px(frame, 14)
    left_panel_w = max(hud_px(145, 145), int(frame.shape[1] * 0.22))
    right_panel_w = max(hud_px(195, 195), int(frame.shape[1] * 0.27))
    left_panel_h = hud_px(102, 102)
    right_panel_h = hud_px(132, 132)
    left = panel_margin
    right = frame.shape[1] - panel_margin - right_panel_w
    if right < left + left_panel_w + panel_gap:
        right = left + left_panel_w + panel_gap
    top = panel_top
    inner_pad = hud_px(10, 10)
    row_gap = hud_px(19, 18)
    score_px = hud_px(24, 24)
    title_px = hud_px(16, 16)
    body_px = hud_px(15, 14)
    small_px = hud_px(13, 12)

    theme_overlay = frame.copy()
    cv2.rectangle(theme_overlay, (0, 0), (frame.shape[1], frame.shape[0]), theme["overlay"], -1)
    cv2.addWeighted(theme_overlay, 0.05, frame, 0.95, 0, frame)

    _draw_panel(
        frame,
        left,
        top,
        left + left_panel_w,
        top + left_panel_h,
        theme["left_fill"],
        0.46,
        border_color=theme["left_border"],
        border_width=max(1, _px(frame, 2)),
    )
    _draw_panel(
        frame,
        right,
        top,
        right + right_panel_w,
        top + right_panel_h,
        theme["right_fill"],
        0.46,
        border_color=theme["right_border"],
        border_width=max(1, _px(frame, 2)),
    )

    if combo >= 2:
        combo_bar_x = left + inner_pad
        combo_bar_y = top + inner_pad + row_gap * 4 + hud_px(4, 4)
        combo_bar_w = left_panel_w - inner_pad * 2
        combo_bar_h = hud_px(8, 8)
        _draw_energy_bar(frame, combo_bar_x, combo_bar_y, combo_bar_w, combo_bar_h, combo_progress, (80, 220, 255), theme["left_border"])

    level_bar_x = right + inner_pad
    level_bar_y = top + inner_pad + row_gap * 3 + hud_px(2, 2)
    level_bar_w = right_panel_w - inner_pad * 2
    level_bar_h = hud_px(8, 8)
    _draw_energy_bar(frame, level_bar_x, level_bar_y, level_bar_w, level_bar_h, level_progress, theme["accent"], theme["right_border"])

    skill_bar_x = right + inner_pad
    skill_bar_y = top + inner_pad + row_gap * 5 + hud_px(2, 2)
    skill_bar_w = right_panel_w - inner_pad * 2
    skill_bar_h = hud_px(10, 10)
    _draw_energy_bar(frame, skill_bar_x, skill_bar_y, skill_bar_w, skill_bar_h, skill_charge, theme["energy"], theme["right_border"])

    if blade_rush_seconds_left > 0:
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), theme["accent"], -1)
        cv2.addWeighted(overlay, 0.08, frame, 0.92, 0, frame)

    text_canvas = _TextCanvas(frame)
    left_x = left + inner_pad
    right_x = right + inner_pad
    base_y = top + inner_pad

    _draw_text(frame, "\u751f\u547d", (left_x, base_y), title_px, (255, 228, 228), text_canvas=text_canvas)
    life_y = base_y + row_gap
    life_count = max(MAX_MISSES - misses, 0)
    for index in range(MAX_MISSES):
        heart_char = "\u2665"
        heart_x = left_x + index * hud_px(18, 18)
        heart_color = (120, 128, 150) if index >= life_count else (90, 120, 255)
        _draw_text(frame, heart_char, (heart_x, life_y), body_px, heart_color, text_canvas=text_canvas)
    _draw_text(frame, f"FPS {fps:.1f}", (left_x, base_y + row_gap * 2), body_px, (210, 214, 220), text_canvas=text_canvas)
    status_text = "\u8ffd\u8e64\u4e2d" if tracking_active else "\u627e\u4e0d\u5230\u624b"
    status_color = (0, 220, 120) if tracking_active else (0, 0, 255)
    _draw_text(frame, status_text, (left_x, base_y + row_gap * 3), body_px, status_color, text_canvas=text_canvas)

    if combo >= 2:
        _draw_text(frame, f"\u9023\u64ca x{combo}", (left_x, base_y + row_gap * 4), small_px, (80, 220, 255), text_canvas=text_canvas)

    _draw_text(frame, f"\u5206\u6578 {score}", (right_x, base_y), score_px, (255, 248, 240), text_canvas=text_canvas)
    _draw_text(frame, f"\u95dc\u5361 {level}", (right_x, int(base_y + row_gap * 1.2)), title_px, (235, 245, 255), text_canvas=text_canvas)
    _draw_text(frame, f"\u4e0b\u95dc {score} / {next_level_score}", (right_x, int(base_y + row_gap * 2.2)), small_px, (215, 225, 235), text_canvas=text_canvas)
    _draw_text(frame, "\u6280\u80fd", (right_x, int(base_y + row_gap * 4.2)), body_px, (235, 240, 245), text_canvas=text_canvas)

    if blade_rush_seconds_left > 0:
        _draw_centered_text(frame, "\u5200\u92d2\u885d\u523a\u4e2d", hud_px(82, 82), hud_px(30, 28), (255, 232, 150), text_canvas=text_canvas)
        _draw_text(frame, f"\u5200\u92d2\u885d\u523a {blade_rush_seconds_left:.1f}s", (right_x, int(base_y + row_gap * 6.1)), small_px, (255, 210, 120), text_canvas=text_canvas)
    else:
        _draw_text(frame, "\u5200\u92d2\u885d\u523a \u5f85\u547d", (right_x, int(base_y + row_gap * 6.1)), small_px, (220, 210, 170), text_canvas=text_canvas)

    status_row_y = int(base_y + row_gap * 7.1)
    if freeze_seconds_left > 0:
        _draw_text(frame, f"\u51b0\u51cd {freeze_seconds_left:.1f}s", (right_x, status_row_y), small_px, (255, 240, 140), text_canvas=text_canvas)
        status_row_y += hud_px(24, 22)
    if fire_seconds_left > 0:
        _draw_text(frame, f"\u706b\u7130 x2 {fire_seconds_left:.1f}s", (right_x, status_row_y), small_px, (110, 210, 255), text_canvas=text_canvas)

    if level_banner_seconds_left > 0 and level_banner_text:
        alpha = max(0.0, min(1.0, level_banner_seconds_left / 1.2))
        overlay = frame.copy()
        banner_top = int(frame.shape[0] * 0.10)
        banner_bottom = int(frame.shape[0] * 0.28)
        cv2.rectangle(overlay, (_px(frame, 18), banner_top), (frame.shape[1] - _px(frame, 18), banner_bottom), theme["accent"], -1)
        cv2.addWeighted(overlay, 0.10 + alpha * 0.10, frame, 0.90 - alpha * 0.10, 0, frame)
        for ring in range(3):
            ring_margin = _px(frame, 18 + ring * 14)
            cv2.rectangle(
                frame,
                (ring_margin, banner_top + ring * 4),
                (frame.shape[1] - ring_margin, banner_bottom - ring * 4),
                _mix_color(theme["accent"], 1.0 + ring * 0.18),
                max(1, _px(frame, 2)),
            )
        _draw_centered_text(frame, level_banner_text, banner_top + hud_px(42, 42), hud_px(34, 32), (255, 250, 225), text_canvas=text_canvas)
        _draw_centered_text(frame, "\u901f\u5ea6\u63d0\u5347  \u6c34\u679c\u66f4\u72c2", banner_top + hud_px(88, 88), hud_px(19, 18), (240, 245, 255), text_canvas=text_canvas)

    text_canvas.flush()


def draw_start_screen(frame, selected_mode: str) -> None:
    height, width = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, height), (24, 20, 28), -1)
    cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)

    panel_left = int(width * 0.10)
    panel_right = int(width * 0.90)
    panel_top = int(height * 0.08)
    panel_bottom = int(height * 0.46)
    _draw_panel(
        frame,
        panel_left,
        panel_top,
        panel_right,
        panel_bottom,
        (46, 34, 34),
        0.20,
        border_color=(166, 184, 220),
        border_width=max(1, _px(frame, 2)),
    )

    text_canvas = _TextCanvas(frame)
    _draw_centered_text(frame, "\u93e1\u982d\u6c34\u679c\u5fcd\u8005", int(height * 0.15), _px(frame, 54), (255, 248, 235), text_canvas=text_canvas)
    _draw_centered_text(frame, "\u7528\u98df\u6307\u61f8\u505c\u6309\u9215\u4f86\u9078\u64c7", int(height * 0.24), _px(frame, 31), (230, 235, 245), text_canvas=text_canvas)
    _draw_centered_text(frame, "\u5feb\u901f\u63ee\u52d5\u624b\u6307\u5207\u6c34\u679c", int(height * 0.31), _px(frame, 27), (214, 222, 236), text_canvas=text_canvas)
    _draw_centered_text(frame, f"\u76ee\u524d\u6a21\u5f0f\uff1a{selected_mode}", int(height * 0.38), _px(frame, 28), (255, 235, 175), text_canvas=text_canvas)
    _draw_centered_text(frame, "\u5200\u92d2\u885d\u523a\uff1a\u6a6b\u5411\u5feb\u63ee  \u65cb\u98a8\u65ac\uff1a\u756b\u5708", int(height * 0.44), _px(frame, 22), (215, 225, 240), text_canvas=text_canvas)
    text_canvas.flush()


def draw_game_over_screen(frame, score: int, highest_level: int) -> None:
    height, width = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, height), (24, 12, 18), -1)
    cv2.addWeighted(overlay, 0.46, frame, 0.54, 0, frame)

    text_canvas = _TextCanvas(frame)
    _draw_centered_text(frame, "\u904a\u6232\u7d50\u675f", int(height * 0.14), _px(frame, 34), (255, 150, 150), text_canvas=text_canvas)
    _draw_centered_text(frame, f"\u6700\u7d42\u5206\u6578\uff1a{score}", int(height * 0.23), _px(frame, 24), (255, 248, 235), text_canvas=text_canvas)
    _draw_centered_text(frame, f"\u6700\u9ad8\u95dc\u5361\uff1a{highest_level}", int(height * 0.29), _px(frame, 21), (180, 235, 255), text_canvas=text_canvas)
    _draw_centered_text(frame, "\u61f8\u505c\u6309\u9215\u7e7c\u7e8c", int(height * 0.35), _px(frame, 17), (220, 225, 235), text_canvas=text_canvas)
    text_canvas.flush()


def draw_history_screen(frame, history_entries: list[GameHistoryEntry], summary: dict[str, float | int]) -> None:
    height, width = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, height), (16, 18, 28), -1)
    cv2.addWeighted(overlay, 0.58, frame, 0.42, 0, frame)

    top = int(height * 0.24)
    left = int(width * 0.06)
    panel_width = int(width * 0.88)
    panel_height = int(height * 0.50)
    fill = frame.copy()
    cv2.rectangle(fill, (left, top), (left + panel_width, top + panel_height), (34, 42, 64), -1)
    cv2.addWeighted(fill, 0.38, frame, 0.62, 0, frame)
    cv2.rectangle(frame, (left, top), (left + panel_width, top + panel_height), (124, 146, 182), max(1, _px(frame, 2)))

    text_canvas = _TextCanvas(frame)
    _draw_centered_text(frame, "\u6b77\u53f2\u7d00\u9304", int(height * 0.10), _px(frame, 40), (255, 248, 235), text_canvas=text_canvas)
    summary_text = f"\u5834\u6b21 {summary['games_played']}  \u6700\u9ad8 {summary['best_score']}  \u6700\u9ad8\u95dc\u5361 {summary['best_level']}  \u6700\u4f73\u9023\u64ca x{summary['best_combo']}"
    _draw_centered_text(frame, summary_text, int(height * 0.17), _px(frame, 20), (215, 225, 240), text_canvas=text_canvas)

    if not history_entries:
        _draw_centered_text(frame, "\u9084\u6c92\u6709\u904a\u73a9\u7d00\u9304", top + panel_height // 2, _px(frame, 20), (225, 230, 235), text_canvas=text_canvas)
        text_canvas.flush()
        return

    header_px = _px(frame, 19)
    row_px = _px(frame, 18)
    row_height = int(panel_height * 0.17)
    columns = [
        ("\u6642\u9593", 0.04),
        ("\u5206\u6578", 0.42),
        ("\u95dc\u5361", 0.54),
        ("\u6642\u9577", 0.65),
        ("\u6c34\u679c", 0.77),
        ("\u9023\u64ca", 0.87),
        ("\u7d50\u675f", 0.95),
    ]
    for title, ratio in columns:
        _draw_text(frame, title, (left + int(panel_width * ratio), top + _px(frame, 10)), header_px, (255, 235, 185), text_canvas=text_canvas)

    for row_index, entry in enumerate(history_entries[:4]):
        y = top + row_height + row_index * row_height
        row_color = (48, 57, 84) if row_index % 2 == 0 else (40, 48, 72)
        cv2.rectangle(frame, (left + _px(frame, 6), y - _px(frame, 4)), (left + panel_width - _px(frame, 6), y + row_height - _px(frame, 6)), row_color, -1)
        values = [
            (entry.played_at[5:16], 0.04),
            (str(entry.score), 0.42),
            (str(entry.highest_level), 0.54),
            (f"{entry.duration_seconds:.1f}s", 0.65),
            (str(entry.fruits_sliced), 0.77),
            (f"x{entry.max_combo}", 0.87),
            (entry.end_reason, 0.95),
        ]
        for value, ratio in values:
            _draw_text(frame, value, (left + int(panel_width * ratio), y), row_px, (235, 238, 245), text_canvas=text_canvas)
    text_canvas.flush()


def draw_mode_screen(frame, selected_mode: str) -> None:
    height, width = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, height), (15, 24, 34), -1)
    cv2.addWeighted(overlay, 0.56, frame, 0.44, 0, frame)

    text_canvas = _TextCanvas(frame)
    _draw_centered_text(frame, "\u9078\u64c7\u6a21\u5f0f", int(height * 0.16), _px(frame, 34), (255, 248, 235), text_canvas=text_canvas)
    _draw_centered_text(frame, f"\u76ee\u524d\uff1a{selected_mode}", int(height * 0.24), _px(frame, 20), (220, 225, 235), text_canvas=text_canvas)
    _draw_centered_text(frame, "\u6a19\u6e96\u504f\u5747\u8861  \u79aa\u6a21\u5f0f\u7121\u70b8\u5f48  \u6311\u6230\u6a21\u5f0f\u66f4\u5feb\u66f4\u96aa", int(height * 0.30), _px(frame, 15), (205, 215, 230), text_canvas=text_canvas)
    text_canvas.flush()


def draw_settings_screen(frame, settings: RuntimeSettings) -> None:
    height, width = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, height), (20, 22, 26), -1)
    cv2.addWeighted(overlay, 0.60, frame, 0.40, 0, frame)

    text_canvas = _TextCanvas(frame)
    _draw_centered_text(frame, "\u8a2d\u5b9a", int(height * 0.16), _px(frame, 34), (255, 248, 235), text_canvas=text_canvas)
    sound_text = "\u958b" if settings.sound_enabled else "\u95dc"
    mirror_text = "\u958b" if settings.mirror_camera else "\u95dc"
    _draw_centered_text(frame, f"\u97f3\u6548\uff1a{sound_text}", int(height * 0.24), _px(frame, 19), (220, 225, 235), text_canvas=text_canvas)
    _draw_centered_text(frame, f"\u93e1\u50cf\uff1a{mirror_text}", int(height * 0.29), _px(frame, 19), (220, 225, 235), text_canvas=text_canvas)
    _draw_centered_text(frame, f"\u61f8\u505c\u78ba\u8a8d\uff1a{settings.hover_seconds:.1f}\u79d2", int(height * 0.34), _px(frame, 19), (220, 225, 235), text_canvas=text_canvas)
    text_canvas.flush()


def draw_menu_buttons(frame, buttons: list[MenuButton], hovered_action: str | None, hover_progress: float) -> None:
    label_px = _px(frame, 30)
    progress_h = _px(frame, 8)
    border_w = max(1, _px(frame, 2))

    for button in buttons:
        is_hovered = button.action == hovered_action
        base_color = (78, 56, 48) if not is_hovered else (100, 134, 204)
        border_color = (205, 220, 255) if is_hovered else (154, 172, 205)
        _draw_panel(frame, button.x, button.y, button.x + button.width, button.y + button.height, base_color, 0.24, border_color=border_color, border_width=border_w)

        if is_hovered:
            progress_width = int((button.width - border_w * 4) * max(0.0, min(1.0, hover_progress)))
            if progress_width > 0:
                cv2.rectangle(
                    frame,
                    (button.x + border_w * 2, button.y + button.height - progress_h - border_w * 2),
                    (button.x + border_w * 2 + progress_width, button.y + button.height - border_w * 2),
                    (255, 225, 120),
                    -1,
                )

    text_canvas = _TextCanvas(frame)
    for button in buttons:
        _draw_centered_text(frame, button.label, button.y + button.height // 2, label_px, (255, 250, 240), text_canvas=text_canvas)
    text_canvas.flush()


def draw_menu_pointer_hint(frame, finger_tip: tuple[int, int] | None) -> None:
    if finger_tip is None:
        return
    radius = _px(frame, 14)
    cv2.circle(frame, finger_tip, radius, (255, 255, 255), max(1, _px(frame, 2)))
    cv2.circle(frame, finger_tip, max(1, radius // 3), (90, 220, 255), -1)


def draw_hit_effects(frame, hit_effects: list[HitEffect], particles: list[Particle], popups: list[ScorePopup]) -> None:
    for effect in hit_effects:
        if effect.ttl <= 0:
            continue
        alpha = max(0.0, min(1.0, effect.ttl / 0.45))
        color = _mix_color(effect.color, 0.75 + 0.4 * alpha)
        if effect.effect_type == "cyclone":
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), (110, 70, 25), -1)
            cv2.addWeighted(overlay, 0.10 * alpha, frame, 1.0 - (0.10 * alpha), 0, frame)
            for ring_scale, ring_alpha in ((1.0, 1.0), (0.72, 0.9), (0.44, 0.8)):
                ring_radius = max(1, int(effect.radius * ring_scale))
                ring_thickness = max(2, _px(frame, 10 * alpha * ring_alpha))
                cv2.circle(frame, (int(effect.x), int(effect.y)), ring_radius, (255, 245, 170), ring_thickness)
            for angle in range(0, 360, 30):
                rad = np.deg2rad(angle)
                start = (int(effect.x + np.cos(rad) * effect.radius * 0.20), int(effect.y + np.sin(rad) * effect.radius * 0.20))
                end = (int(effect.x + np.cos(rad) * effect.radius * 0.95), int(effect.y + np.sin(rad) * effect.radius * 0.95))
                cv2.line(frame, start, end, (255, 235, 130), max(1, _px(frame, 4 * alpha)))
            swirl_points = []
            for step in range(28):
                angle = step * 0.55 + (1.0 - alpha) * 2.8
                radius = effect.radius * (0.18 + step / 34.0)
                swirl_points.append((int(effect.x + np.cos(angle) * radius), int(effect.y + np.sin(angle) * radius)))
            cv2.polylines(frame, [np.array(swirl_points, dtype=np.int32)], False, (255, 255, 210), max(1, _px(frame, 5 * alpha)))
        else:
            thickness = max(1, _px(frame, 6 * alpha))
            cv2.circle(frame, (int(effect.x), int(effect.y)), max(1, int(effect.radius)), color, thickness)

    for particle in particles:
        if particle.ttl <= 0:
            continue
        cv2.circle(frame, (int(particle.x), int(particle.y)), max(1, int(particle.radius)), particle.color, -1)

    popup_px = _px(frame, 18)
    text_canvas = _TextCanvas(frame)
    for popup in popups:
        if popup.ttl <= 0:
            continue
        _draw_text(frame, popup.text, (int(popup.x), int(popup.y)), popup_px, popup.color, text_canvas=text_canvas)
    text_canvas.flush()
