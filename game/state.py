from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from config import MAX_MISSES
from game.history import GameHistoryEntry
from game.settings import RuntimeSettings
from game.effects import HitEffect, Particle, ScorePopup
from game.menu import MenuButton
from game.objects import GameObject


@dataclass
class GameState:
    mode: str = "start"
    score: int = 0
    misses: int = 0
    combo: int = 0
    objects: list[GameObject] = field(default_factory=list)
    hit_effects: list[HitEffect] = field(default_factory=list)
    particles: list[Particle] = field(default_factory=list)
    score_popups: list[ScorePopup] = field(default_factory=list)
    trail: deque[tuple[int, int]] = field(default_factory=deque)
    last_slice_segment: tuple[tuple[int, int], tuple[int, int]] | None = None
    freeze_until: float = 0.0
    fire_until: float = 0.0
    combo_flash_until: float = 0.0
    skill_charge: float = 0.0
    blade_rush_until: float = 0.0
    blade_rush_cooldown_until: float = 0.0
    cyclone_cooldown_until: float = 0.0
    menu_buttons: list[MenuButton] = field(default_factory=list)
    hovered_button_action: str | None = None
    hover_started_at: float = 0.0
    session_started_at: float = 0.0
    fruits_sliced: int = 0
    gold_sliced: int = 0
    freeze_sliced: int = 0
    fire_sliced: int = 0
    shock_sliced: int = 0
    bombs_hit: int = 0
    max_combo: int = 0
    level: int = 1
    next_level_score: int = 200
    highest_level_reached: int = 1
    level_transition_until: float = 0.0
    level_banner_text: str = ""
    history_entries: list[GameHistoryEntry] = field(default_factory=list)
    settings: RuntimeSettings = field(default_factory=RuntimeSettings)

    @property
    def lives_left(self) -> int:
        return max(MAX_MISSES - self.misses, 0)
