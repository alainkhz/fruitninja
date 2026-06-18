from __future__ import annotations

import random
from typing import Any, Optional

from config import (
    BOMB_CHANCE,
    BOMB_RADIUS,
    FIRE_FRUIT_CHANCE,
    FIRE_FRUIT_SCORE,
    FREEZE_FRUIT_CHANCE,
    FREEZE_FRUIT_SCORE,
    FRUIT_RADIUS,
    FRUIT_SCORE,
    GOLD_FRUIT_CHANCE,
    GOLD_FRUIT_SCORE,
    SHOCK_FRUIT_CHANCE,
    SHOCK_FRUIT_SCORE,
)
from game.objects import GameObject


class Spawner:
    def __init__(self, random_seed: Optional[int] = None) -> None:
        self.random = random.Random(random_seed)

    def spawn(self, frame_width: int, frame_height: int, profile: Optional[dict[str, Any]] = None) -> GameObject:
        profile = profile or {}
        scale = min(frame_width / 1280.0, frame_height / 720.0)
        scale = max(0.55, scale)
        horizontal_margin = max(40, int(80 * scale))
        spawn_offset_min = max(10, int(18 * scale))
        spawn_offset_max = max(spawn_offset_min + 10, int(60 * scale))
        fruit_radius = max(20, int(FRUIT_RADIUS * scale))
        bomb_radius = max(18, int(BOMB_RADIUS * scale))
        target_apex_y = frame_height * self.random.uniform(0.22, 0.45)
        gravity = 0.42

        x = self.random.randint(horizontal_margin, max(horizontal_margin + 1, frame_width - horizontal_margin))
        y = frame_height + self.random.randint(spawn_offset_min, spawn_offset_max)
        velocity_multiplier = float(profile.get("velocity_multiplier", 1.0))
        vx = self.random.uniform(-4.0, 4.0) * scale * velocity_multiplier
        vy = -((max(y - target_apex_y, 1.0) * 2.0 * gravity) ** 0.5)
        vy *= self.random.uniform(0.98, 1.06) * velocity_multiplier

        bomb_chance = BOMB_CHANCE * float(profile.get("bomb_chance_multiplier", 1.0))
        bomb_chance = max(0.0, min(0.8, bomb_chance))
        if self.random.random() < bomb_chance:
            return GameObject(
                kind="bomb",
                x=x,
                y=y,
                vx=vx,
                vy=vy,
                radius=bomb_radius,
                color=(30, 30, 30),
            )

        fruit_styles = [
            ("orange", (0, 170, 255)),
            ("lime", (80, 210, 80)),
            ("apple", (40, 40, 220)),
            ("peach", (100, 170, 255)),
        ]
        fruit_name, fruit_color = self.random.choice(fruit_styles)
        effect_roll = self.random.random()
        effect = "normal"
        score_value = FRUIT_SCORE
        gold_chance = GOLD_FRUIT_CHANCE * float(profile.get("gold_weight", 1.0))
        freeze_chance = FREEZE_FRUIT_CHANCE * float(profile.get("freeze_weight", 1.0))
        fire_chance = FIRE_FRUIT_CHANCE * float(profile.get("fire_weight", 1.0))
        shock_chance = SHOCK_FRUIT_CHANCE * float(profile.get("shock_weight", 1.0))

        if effect_roll < gold_chance:
            effect = "gold"
            fruit_name = "gold"
            fruit_color = (60, 215, 255)
            score_value = GOLD_FRUIT_SCORE
        elif effect_roll < gold_chance + freeze_chance:
            effect = "freeze"
            fruit_name = "ice"
            fruit_color = (255, 190, 90)
            score_value = FREEZE_FRUIT_SCORE
        elif effect_roll < gold_chance + freeze_chance + fire_chance:
            effect = "fire"
            fruit_name = "fire"
            fruit_color = (70, 115, 255)
            score_value = FIRE_FRUIT_SCORE
        elif effect_roll < gold_chance + freeze_chance + fire_chance + shock_chance:
            effect = "shock"
            fruit_name = "shock"
            fruit_color = (80, 230, 255)
            score_value = SHOCK_FRUIT_SCORE

        return GameObject(
            kind="fruit",
            x=x,
            y=y,
            vx=vx,
            vy=vy,
            radius=fruit_radius,
            color=fruit_color,
            score_value=score_value,
            fruit_name=fruit_name,
            effect=effect,
        )
