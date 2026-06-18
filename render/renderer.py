from __future__ import annotations

from collections import deque
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from config import MAX_MISSES
from game.effects import HitEffect, Particle, ScorePopup
from game.history import GameHistoryEntry
from game.menu import MenuButton
from game.missions import Mission
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


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


def _draw_text(frame, text: str, position: tuple[int, int], font_px: int, color: tuple[int, int, int]) -> None:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb)
    draw = ImageDraw.Draw(image)
    draw.text(position, text, font=_load_font(font_px), fill=(color[2], color[1], color[0]))
    frame[:] = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def _measure_text(text: str, font_px: int) -> tuple[int, int]:
    bbox = _load_font(font_px).getbbox(text)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _draw_centered_text(
    frame,
    text: str,
    center_y: int,
    font_px: int,
    color: tuple[int, int, int],
) -> None:
    height, width = frame.shape[:2]
    text_w, text_h = _measure_text(text, font_px)
    x = (width - text_w) // 2
    y = max(0, min(height - text_h, center_y - text_h // 2))
    _draw_text(frame, text, (x, y), font_px, color)


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

    if fruit_name in {"apple", "gold"}:
        cv2.ellipse(frame, (center[0] + radius // 4, center[1] - radius), (max(1, radius // 3), max(1, radius // 6)), -25, 0, 360, (50, 180, 70), -1)
    elif fruit_name == "orange":
        for angle in range(0, 360, 45):
            rad = np.deg2rad(angle)
            px = int(center[0] + np.cos(rad) * radius * 0.62)
            py = int(center[1] + np.sin(rad) * radius * 0.62)
            cv2.circle(frame, (px, py), max(1, radius // 14), _mix_color(base_color, 0.84), -1)
    elif fruit_name in {"lime", "ice", "shock"}:
        cv2.circle(frame, center, max(1, int(radius * 0.52)), _mix_color(base_color, 0.75), 2)
        cv2.line(frame, (center[0] - radius // 2, center[1]), (center[0] + radius // 2, center[1]), _mix_color(base_color, 0.75), 2)
        cv2.line(frame, (center[0], center[1] - radius // 2), (center[0], center[1] + radius // 2), _mix_color(base_color, 0.75), 2)
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
        "shock": (255, 250, 120),
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
    active_missions: list[Mission],
) -> None:
    left = _px(frame, 20)
    top = _px(frame, 20)
    gap = _px(frame, 32)
    title_px = _px(frame, 34)
    body_px = _px(frame, 25)
    small_px = _px(frame, 21)

    _draw_text(frame, f"\u5206\u6578\uff1a{score}", (left, top), title_px, (255, 255, 255))
    _draw_text(frame, f"\u751f\u547d\uff1a{max(MAX_MISSES - misses, 0)}", (left, top + gap), title_px, (255, 255, 255))
    _draw_text(frame, f"FPS\uff1a{fps:.1f}", (left, top + gap * 2), body_px, (200, 200, 200))
    status_text = "\u8ffd\u8e64\u4e2d" if tracking_active else "\u627e\u4e0d\u5230\u624b"
    status_color = (0, 220, 120) if tracking_active else (0, 0, 255)
    _draw_text(frame, status_text, (left, top + gap * 3), body_px, status_color)

    if combo >= 2:
        _draw_text(frame, f"\u9023\u64ca x{combo}", (left, top + gap * 4), body_px, (80, 220, 255))
        bar_x = left
        bar_y = top + gap * 5
        bar_w = _px(frame, 180)
        bar_h = _px(frame, 12)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (70, 80, 96), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_w * max(0.0, min(1.0, combo_progress))), bar_y + bar_h), (80, 220, 255), -1)

    info_row = 6
    if freeze_seconds_left > 0:
        _draw_text(frame, f"\u51b0\u51cd\uff1a{freeze_seconds_left:.1f}\u79d2", (left, top + gap * info_row), small_px, (255, 240, 140))
        info_row += 1
    if fire_seconds_left > 0:
        _draw_text(frame, f"\u706b\u7130 x2\uff1a{fire_seconds_left:.1f}\u79d2", (left, top + gap * info_row), small_px, (110, 210, 255))
        info_row += 1

    skill_y = top + gap * info_row
    _draw_text(frame, "\u6280\u80fd", (left, skill_y), small_px, (220, 225, 240))
    bar_x = left + _px(frame, 60)
    bar_y = skill_y + _px(frame, 4)
    bar_w = _px(frame, 180)
    bar_h = _px(frame, 12)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (70, 80, 96), -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_w * max(0.0, min(1.0, skill_charge))), bar_y + bar_h), (255, 210, 120), -1)

    skill_state_y = skill_y + gap
    if blade_rush_seconds_left > 0:
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), (50, 90, 150), -1)
        cv2.addWeighted(overlay, 0.12, frame, 0.88, 0, frame)
        _draw_centered_text(frame, "\u5200\u92d2\u885d\u523a\u4e2d", _px(frame, 82), _px(frame, 28), (255, 232, 150))
        _draw_text(frame, f"\u5200\u92d2\u885d\u523a\uff1a{blade_rush_seconds_left:.1f}\u79d2", (left, skill_state_y), small_px, (255, 210, 120))
        skill_state_y += gap

    if active_missions:
        mission_px = _px(frame, 20)
        _draw_text(frame, f"\u4efb\u52d9\uff1a{active_missions[0].description}", (left, frame.shape[0] - _px(frame, 26)), mission_px, (215, 225, 240))


def draw_start_screen(frame, selected_mode: str) -> None:
    height, width = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, height), (18, 20, 32), -1)
    cv2.addWeighted(overlay, 0.48, frame, 0.52, 0, frame)

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
        (28, 34, 48),
        0.58,
        border_color=(166, 184, 220),
        border_width=max(1, _px(frame, 2)),
    )

    _draw_centered_text(frame, "\u93e1\u982d\u6c34\u679c\u5fcd\u8005", int(height * 0.15), _px(frame, 54), (255, 248, 235))
    _draw_centered_text(frame, "\u7528\u98df\u6307\u61f8\u505c\u6309\u9215\u4f86\u9078\u64c7", int(height * 0.24), _px(frame, 31), (230, 235, 245))
    _draw_centered_text(frame, "\u5feb\u901f\u63ee\u52d5\u624b\u6307\u5207\u6c34\u679c", int(height * 0.31), _px(frame, 27), (214, 222, 236))
    _draw_centered_text(frame, f"\u76ee\u524d\u6a21\u5f0f\uff1a{selected_mode}", int(height * 0.38), _px(frame, 28), (255, 235, 175))
    _draw_centered_text(frame, "\u5200\u92d2\u885d\u523a\uff1a\u6a6b\u5411\u5feb\u63ee  \u65cb\u98a8\u65ac\uff1a\u756b\u5708", int(height * 0.44), _px(frame, 22), (215, 225, 240))


def draw_game_over_screen(frame, score: int, completed_missions: list[Mission] | None = None) -> None:
    height, width = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, height), (24, 12, 18), -1)
    cv2.addWeighted(overlay, 0.46, frame, 0.54, 0, frame)
    _draw_centered_text(frame, "\u904a\u6232\u7d50\u675f", int(height * 0.14), _px(frame, 34), (255, 150, 150))
    _draw_centered_text(frame, f"\u6700\u7d42\u5206\u6578\uff1a{score}", int(height * 0.23), _px(frame, 24), (255, 248, 235))
    _draw_centered_text(frame, "\u61f8\u505c\u6309\u9215\u7e7c\u7e8c", int(height * 0.30), _px(frame, 17), (220, 225, 235))
    if completed_missions:
        _draw_centered_text(frame, "\u5b8c\u6210\u4efb\u52d9", int(height * 0.38), _px(frame, 18), (255, 235, 175))
        for index, mission in enumerate(completed_missions[:3]):
            _draw_centered_text(frame, f"- {mission.title}", int(height * (0.43 + index * 0.045)), _px(frame, 16), (235, 238, 245))


def draw_history_screen(frame, history_entries: list[GameHistoryEntry], summary: dict[str, float | int]) -> None:
    height, width = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, height), (16, 18, 28), -1)
    cv2.addWeighted(overlay, 0.58, frame, 0.42, 0, frame)

    _draw_centered_text(frame, "\u6b77\u53f2\u7d00\u9304", int(height * 0.10), _px(frame, 40), (255, 248, 235))
    summary_text = f"\u5834\u6b21 {summary['games_played']}  \u6700\u9ad8 {summary['best_score']}  \u5e73\u5747 {summary['average_score']}  \u6700\u4f73\u9023\u64ca x{summary['best_combo']}"
    _draw_centered_text(frame, summary_text, int(height * 0.17), _px(frame, 20), (215, 225, 240))

    top = int(height * 0.24)
    left = int(width * 0.06)
    panel_width = int(width * 0.88)
    panel_height = int(height * 0.50)
    fill = frame.copy()
    cv2.rectangle(fill, (left, top), (left + panel_width, top + panel_height), (34, 42, 64), -1)
    cv2.addWeighted(fill, 0.38, frame, 0.62, 0, frame)
    cv2.rectangle(frame, (left, top), (left + panel_width, top + panel_height), (124, 146, 182), max(1, _px(frame, 2)))

    if not history_entries:
        _draw_centered_text(frame, "\u9084\u6c92\u6709\u904a\u73a9\u7d00\u9304", top + panel_height // 2, _px(frame, 20), (225, 230, 235))
        return

    header_px = _px(frame, 19)
    row_px = _px(frame, 18)
    row_height = int(panel_height * 0.17)
    columns = [
        ("\u6642\u9593", 0.04),
        ("\u5206\u6578", 0.42),
        ("\u6642\u9577", 0.56),
        ("\u6c34\u679c", 0.70),
        ("\u9023\u64ca", 0.82),
        ("\u7d50\u675f", 0.91),
    ]
    for title, ratio in columns:
        _draw_text(frame, title, (left + int(panel_width * ratio), top + _px(frame, 10)), header_px, (255, 235, 185))

    for row_index, entry in enumerate(history_entries[:4]):
        y = top + row_height + row_index * row_height
        row_color = (48, 57, 84) if row_index % 2 == 0 else (40, 48, 72)
        cv2.rectangle(frame, (left + _px(frame, 6), y - _px(frame, 4)), (left + panel_width - _px(frame, 6), y + row_height - _px(frame, 6)), row_color, -1)
        values = [
            (entry.played_at[5:16], 0.04),
            (str(entry.score), 0.42),
            (f"{entry.duration_seconds:.1f}s", 0.56),
            (str(entry.fruits_sliced), 0.70),
            (f"x{entry.max_combo}", 0.82),
            (entry.end_reason, 0.91),
        ]
        for value, ratio in values:
            _draw_text(frame, value, (left + int(panel_width * ratio), y), row_px, (235, 238, 245))


def draw_mode_screen(frame, selected_mode: str) -> None:
    height, width = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, height), (15, 24, 34), -1)
    cv2.addWeighted(overlay, 0.56, frame, 0.44, 0, frame)
    _draw_centered_text(frame, "\u9078\u64c7\u6a21\u5f0f", int(height * 0.16), _px(frame, 34), (255, 248, 235))
    _draw_centered_text(frame, f"\u76ee\u524d\uff1a{selected_mode}", int(height * 0.24), _px(frame, 20), (220, 225, 235))
    _draw_centered_text(frame, "\u6a19\u6e96\u504f\u5747\u8861  \u79aa\u6a21\u5f0f\u7121\u70b8\u5f48  \u6311\u6230\u6a21\u5f0f\u66f4\u5feb\u66f4\u96aa", int(height * 0.30), _px(frame, 15), (205, 215, 230))


def draw_settings_screen(frame, settings: RuntimeSettings) -> None:
    height, width = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, height), (20, 22, 26), -1)
    cv2.addWeighted(overlay, 0.60, frame, 0.40, 0, frame)
    _draw_centered_text(frame, "\u8a2d\u5b9a", int(height * 0.16), _px(frame, 34), (255, 248, 235))
    sound_text = "\u958b" if settings.sound_enabled else "\u95dc"
    mirror_text = "\u958b" if settings.mirror_camera else "\u95dc"
    _draw_centered_text(frame, f"\u97f3\u6548\uff1a{sound_text}", int(height * 0.24), _px(frame, 19), (220, 225, 235))
    _draw_centered_text(frame, f"\u93e1\u50cf\uff1a{mirror_text}", int(height * 0.29), _px(frame, 19), (220, 225, 235))
    _draw_centered_text(frame, f"\u61f8\u505c\u78ba\u8a8d\uff1a{settings.hover_seconds:.1f}\u79d2", int(height * 0.34), _px(frame, 19), (220, 225, 235))


def draw_menu_buttons(frame, buttons: list[MenuButton], hovered_action: str | None, hover_progress: float) -> None:
    label_px = _px(frame, 30)
    progress_h = _px(frame, 8)
    border_w = max(1, _px(frame, 2))

    for button in buttons:
        is_hovered = button.action == hovered_action
        base_color = (54, 68, 102) if not is_hovered else (88, 124, 198)
        border_color = (205, 220, 255) if is_hovered else (154, 172, 205)
        _draw_panel(
            frame,
            button.x,
            button.y,
            button.x + button.width,
            button.y + button.height,
            base_color,
            0.52,
            border_color=border_color,
            border_width=border_w,
        )

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

        _draw_centered_text(frame, button.label, button.y + button.height // 2, label_px, (255, 250, 240))


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
        thickness = max(1, _px(frame, 6 * alpha))
        cv2.circle(frame, (int(effect.x), int(effect.y)), max(1, int(effect.radius)), color, thickness)

    for particle in particles:
        if particle.ttl <= 0:
            continue
        cv2.circle(frame, (int(particle.x), int(particle.y)), max(1, int(particle.radius)), particle.color, -1)

    popup_px = _px(frame, 18)
    for popup in popups:
        if popup.ttl <= 0:
            continue
        _draw_text(frame, popup.text, (int(popup.x), int(popup.y)), popup_px, popup.color)
