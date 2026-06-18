from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


SETTINGS_PATH = Path(__file__).resolve().parents[1] / "work" / "settings.json"


@dataclass
class RuntimeSettings:
    sound_enabled: bool = True
    mirror_camera: bool = True
    hover_seconds: float = 1.0
    selected_mode: str = "\u6a19\u6e96\u6a21\u5f0f"


def load_settings() -> RuntimeSettings:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_PATH.exists():
        settings = RuntimeSettings()
        save_settings(settings)
        return settings
    try:
        raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return RuntimeSettings()

    settings = RuntimeSettings()
    for field in asdict(settings).keys():
        if field in raw:
            setattr(settings, field, raw[field])

    mode_map = {
        "Arcade": "\u6a19\u6e96\u6a21\u5f0f",
        "Zen": "\u79aa\u6a21\u5f0f",
        "Challenge": "\u6311\u6230\u6a21\u5f0f",
        "Rush": "\u6a19\u6e96\u6a21\u5f0f",
    }
    settings.selected_mode = mode_map.get(settings.selected_mode, settings.selected_mode)
    return settings


def save_settings(settings: RuntimeSettings) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(asdict(settings), ensure_ascii=True, indent=2), encoding="utf-8")
