from __future__ import annotations

from game.objects import GameObject
from utils.math_helpers import point_to_segment_distance


def segment_hits_object(
    segment_start: tuple[int, int],
    segment_end: tuple[int, int],
    game_object: GameObject,
) -> bool:
    distance = point_to_segment_distance(
        point=(game_object.x, game_object.y),
        segment_start=segment_start,
        segment_end=segment_end,
    )
    return distance <= game_object.radius
