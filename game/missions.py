from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.state import GameState


@dataclass
class Mission:
    id: str
    title: str
    description: str
    completed: bool = False


def build_default_missions() -> list[Mission]:
    return [
        Mission("combo_8", "\u9023\u64ca\u9ad8\u624b", "\u55ae\u5c40\u9054\u6210 8 \u9023\u64ca"),
        Mission("gold_2", "\u9ec3\u91d1\u7375\u4eba", "\u55ae\u5c40\u5207\u5230 2 \u9846\u91d1\u8272\u6c34\u679c"),
        Mission("fire_1", "\u706b\u529b\u5168\u958b", "\u55ae\u5c40\u89f8\u767c 1 \u6b21\u706b\u7130\u6c34\u679c"),
        Mission("shock_1", "\u9023\u9396\u555f\u52d5", "\u55ae\u5c40\u89f8\u767c 1 \u6b21\u96fb\u64ca\u9023\u9396"),
        Mission("clean_wave", "\u7a69\u5b9a\u8f38\u51fa", "\u55ae\u5c40\u6f0f\u63a5\u4e0d\u8d85\u904e 1 \u6b21"),
    ]


def evaluate_missions(state: GameState, end_reason: str) -> list[Mission]:
    missions = build_default_missions()
    for mission in missions:
        if mission.id == "combo_8":
            mission.completed = state.max_combo >= 8
        elif mission.id == "gold_2":
            mission.completed = state.gold_sliced >= 2
        elif mission.id == "fire_1":
            mission.completed = state.fire_sliced >= 1
        elif mission.id == "shock_1":
            mission.completed = state.shock_sliced >= 1
        elif mission.id == "clean_wave":
            mission.completed = state.misses <= 1 and end_reason != "\u70b8\u5f48"
    return missions
