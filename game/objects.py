from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count


_id_counter = count(1)


@dataclass
class GameObject:
    kind: str
    x: float
    y: float
    vx: float
    vy: float
    radius: int
    color: tuple[int, int, int]
    score_value: int = 0
    fruit_name: str = "fruit"
    effect: str = "normal"
    id: int = field(default_factory=lambda: next(_id_counter))
    is_sliced: bool = False
    is_alive: bool = True
    has_entered_screen: bool = False

    def update(self, gravity: float, speed_multiplier: float = 1.0) -> None:
        self.x += self.vx * speed_multiplier
        self.y += self.vy * speed_multiplier
        self.vy += gravity * speed_multiplier
