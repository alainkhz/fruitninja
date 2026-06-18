from __future__ import annotations

import math


def point_to_segment_distance(
    point: tuple[float, float],
    segment_start: tuple[float, float],
    segment_end: tuple[float, float],
) -> float:
    px, py = point
    x1, y1 = segment_start
    x2, y2 = segment_end

    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.dist(point, segment_start)

    projection = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    projection = max(0.0, min(1.0, projection))
    closest_x = x1 + projection * dx
    closest_y = y1 + projection * dy
    return math.dist(point, (closest_x, closest_y))


def euclidean_distance(point_a: tuple[int, int], point_b: tuple[int, int]) -> float:
    return math.dist(point_a, point_b)
