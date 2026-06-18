from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HitEffect:
    x: float
    y: float
    color: tuple[int, int, int]
    radius: float
    ttl: float
    effect_type: str = "slice"

    def update(self, delta: float) -> None:
        self.ttl -= delta
        self.radius += 180.0 * delta


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    radius: float
    ttl: float

    def update(self, delta: float, gravity: float = 0.0) -> None:
        self.ttl -= delta
        self.x += self.vx * delta
        self.y += self.vy * delta
        self.vy += gravity * delta
        self.radius = max(1.0, self.radius - 8.0 * delta)


@dataclass
class ScorePopup:
    x: float
    y: float
    text: str
    color: tuple[int, int, int]
    ttl: float

    def update(self, delta: float) -> None:
        self.ttl -= delta
        self.y -= 70.0 * delta
