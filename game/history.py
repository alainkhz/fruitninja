from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


HISTORY_PATH = Path(__file__).resolve().parents[1] / "work" / "history.json"


@dataclass
class GameHistoryEntry:
    played_at: str
    score: int
    duration_seconds: float
    fruits_sliced: int
    gold_sliced: int = 0
    freeze_sliced: int = 0
    fire_sliced: int = 0
    shock_sliced: int = 0
    bombs_hit: int = 0
    misses: int = 0
    max_combo: int = 0
    highest_level: int = 1
    end_reason: str = ""


def _ensure_history_path() -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not HISTORY_PATH.exists():
        HISTORY_PATH.write_text("[]", encoding="utf-8")


def load_history() -> list[GameHistoryEntry]:
    _ensure_history_path()
    try:
        raw = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    history: list[GameHistoryEntry] = []
    for item in raw:
        try:
            history.append(GameHistoryEntry(**item))
        except TypeError:
            continue
    return history


def save_history(entries: list[GameHistoryEntry]) -> None:
    _ensure_history_path()
    payload = [asdict(entry) for entry in entries]
    HISTORY_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def append_history(entry: GameHistoryEntry, limit: int = 25) -> list[GameHistoryEntry]:
    history = load_history()
    history.insert(0, entry)
    history = history[:limit]
    save_history(history)
    return history


def summarize_history(entries: list[GameHistoryEntry]) -> dict[str, float | int]:
    if not entries:
        return {
            "games_played": 0,
            "best_score": 0,
            "average_score": 0,
            "best_combo": 0,
            "best_level": 0,
            "total_fruits": 0,
        }

    total_score = sum(entry.score for entry in entries)
    return {
        "games_played": len(entries),
        "best_score": max(entry.score for entry in entries),
        "average_score": round(total_score / len(entries), 1),
        "best_combo": max(entry.max_combo for entry in entries),
        "best_level": max(entry.highest_level for entry in entries),
        "total_fruits": sum(entry.fruits_sliced for entry in entries),
    }


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
