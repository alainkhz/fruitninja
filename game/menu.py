from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MenuButton:
    label: str
    action: str
    description: str
    x: int
    y: int
    width: int
    height: int

    def contains(self, point: tuple[int, int] | None) -> bool:
        if point is None:
            return False
        px, py = point
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height


def _build_vertical_menu(
    frame_width: int,
    frame_height: int,
    labels_and_actions: list[tuple[str, str]],
    top_ratio: float,
    bottom_ratio: float,
    width_ratio: float,
) -> list[MenuButton]:
    count = len(labels_and_actions)
    button_width = int(frame_width * width_ratio)
    x = (frame_width - button_width) // 2

    top = int(frame_height * top_ratio)
    bottom = int(frame_height * bottom_ratio)
    available_height = max(1, bottom - top)
    gap = int(available_height * 0.045)
    button_height = int((available_height - gap * (count - 1)) / count)

    buttons: list[MenuButton] = []
    y = top
    for label, action in labels_and_actions:
        buttons.append(MenuButton(label, action, "", x, y, button_width, button_height))
        y += button_height + gap
    return buttons


def build_main_menu(frame_width: int, frame_height: int) -> list[MenuButton]:
    return _build_vertical_menu(
        frame_width,
        frame_height,
        [
            ("\u958b\u59cb\u904a\u6232", "start_game"),
            ("\u9078\u64c7\u6a21\u5f0f", "show_modes"),
            ("\u6b77\u53f2\u7d00\u9304", "show_history"),
            ("\u8a2d\u5b9a", "show_settings"),
            ("\u96e2\u958b", "exit_game"),
        ],
        top_ratio=0.55,
        bottom_ratio=0.94,
        width_ratio=0.40,
    )


def build_game_over_menu(frame_width: int, frame_height: int) -> list[MenuButton]:
    return _build_vertical_menu(
        frame_width,
        frame_height,
        [
            ("\u518d\u4f86\u4e00\u5c40", "restart_game"),
            ("\u56de\u4e3b\u9078\u55ae", "go_to_menu"),
            ("\u96e2\u958b", "exit_game"),
        ],
        top_ratio=0.62,
        bottom_ratio=0.92,
        width_ratio=0.34,
    )


def build_history_menu(frame_width: int, frame_height: int) -> list[MenuButton]:
    return _build_vertical_menu(
        frame_width,
        frame_height,
        [
            ("\u56de\u4e3b\u9078\u55ae", "go_to_menu"),
        ],
        top_ratio=0.84,
        bottom_ratio=0.94,
        width_ratio=0.30,
    )


def build_mode_menu(frame_width: int, frame_height: int) -> list[MenuButton]:
    return _build_vertical_menu(
        frame_width,
        frame_height,
        [
            ("\u6a19\u6e96\u6a21\u5f0f", "mode_arcade"),
            ("\u79aa\u6a21\u5f0f", "mode_zen"),
            ("\u6311\u6230\u6a21\u5f0f", "mode_challenge"),
            ("\u56de\u4e3b\u9078\u55ae", "go_to_menu"),
        ],
        top_ratio=0.34,
        bottom_ratio=0.74,
        width_ratio=0.35,
    )


def build_settings_menu(frame_width: int, frame_height: int) -> list[MenuButton]:
    return _build_vertical_menu(
        frame_width,
        frame_height,
        [
            ("\u97f3\u6548\u958b\u95dc", "toggle_sound"),
            ("\u93e1\u50cf\u958b\u95dc", "toggle_mirror"),
            ("\u61f8\u505c\u901f\u5ea6", "cycle_hover_speed"),
            ("\u56de\u4e3b\u9078\u55ae", "go_to_menu"),
        ],
        top_ratio=0.40,
        bottom_ratio=0.80,
        width_ratio=0.38,
    )
