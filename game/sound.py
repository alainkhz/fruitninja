from __future__ import annotations

import math
import random
import wave
from pathlib import Path

import pygame

try:
    import winsound
except ImportError:  # pragma: no cover
    winsound = None


SAMPLE_RATE = 22050
SOUNDS_DIR = Path(__file__).resolve().parents[1] / "work" / "sounds"
SOUNDS_DIR.mkdir(parents=True, exist_ok=True)
KENNEY_AUDIO_DIR = Path(__file__).resolve().parents[1] / "work" / "assets" / "kenney_ui-audio" / "Audio"


def _write_tone_wav(path: Path, frequencies: list[int], duration_ms: int, volume: float = 0.35) -> None:
    frame_count = max(1, int(SAMPLE_RATE * duration_ms / 1000))
    fade_samples = max(1, int(SAMPLE_RATE * 0.01))
    samples = bytearray()

    for index in range(frame_count):
        t = index / SAMPLE_RATE
        amplitude = 0.0
        for frequency in frequencies:
            amplitude += math.sin(2.0 * math.pi * frequency * t)
        amplitude /= max(1, len(frequencies))

        envelope = 1.0
        if index < fade_samples:
            envelope = index / fade_samples
        elif frame_count - index < fade_samples:
            envelope = (frame_count - index) / fade_samples

        value = int(max(-1.0, min(1.0, amplitude * envelope * volume)) * 32767)
        samples.extend(value.to_bytes(2, byteorder="little", signed=True))

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(bytes(samples))


def _ensure_sound_files() -> dict[str, Path]:
    definitions = {
        "slice": ([900, 1200], 55, 0.28),
        "gold": ([1100, 1470], 120, 0.35),
        "freeze": ([520, 700], 180, 0.35),
        "bomb": ([220, 160], 260, 0.40),
        "miss": ([360, 280], 100, 0.30),
    }
    sound_files: dict[str, Path] = {}
    for name, (frequencies, duration_ms, volume) in definitions.items():
        path = SOUNDS_DIR / f"{name}.wav"
        if not path.exists():
            _write_tone_wav(path, frequencies, duration_ms, volume)
        sound_files[name] = path
    return sound_files


SOUND_FILES = _ensure_sound_files()
OGG_SOUND_FILES = {
    "slice": [
        KENNEY_AUDIO_DIR / "click3.ogg",
        KENNEY_AUDIO_DIR / "click5.ogg",
        KENNEY_AUDIO_DIR / "switch7.ogg",
    ],
    "gold": [
        KENNEY_AUDIO_DIR / "switch14.ogg",
        KENNEY_AUDIO_DIR / "switch21.ogg",
        KENNEY_AUDIO_DIR / "switch23.ogg",
    ],
    "freeze": [
        KENNEY_AUDIO_DIR / "rollover3.ogg",
        KENNEY_AUDIO_DIR / "rollover4.ogg",
        KENNEY_AUDIO_DIR / "rollover6.ogg",
    ],
    "bomb": [
        KENNEY_AUDIO_DIR / "switch30.ogg",
        KENNEY_AUDIO_DIR / "switch34.ogg",
        KENNEY_AUDIO_DIR / "switch35.ogg",
    ],
    "miss": [
        KENNEY_AUDIO_DIR / "switch27.ogg",
        KENNEY_AUDIO_DIR / "switch11.ogg",
    ],
}
_mixer_ready = False
_ogg_sounds: dict[str, list[pygame.mixer.Sound]] = {}
_random = random.Random()
_sound_enabled = True


def set_sound_enabled(enabled: bool) -> None:
    global _sound_enabled
    _sound_enabled = enabled


def _ensure_mixer() -> bool:
    global _mixer_ready
    if _mixer_ready:
        return True
    try:
        pygame.mixer.init()
    except pygame.error:
        return False

    pygame.mixer.set_num_channels(12)

    for name, paths in OGG_SOUND_FILES.items():
        loaded_sounds: list[pygame.mixer.Sound] = []
        for path in paths:
            if not path.exists():
                continue
            try:
                sound = pygame.mixer.Sound(str(path))
            except pygame.error:
                continue
            loaded_sounds.append(sound)
        if loaded_sounds:
            _ogg_sounds[name] = loaded_sounds
    _mixer_ready = True
    return True


def _play_ogg(name: str) -> bool:
    if not _ensure_mixer():
        return False
    sounds = _ogg_sounds.get(name)
    if not sounds:
        return False
    try:
        sound = _random.choice(sounds)
        sound.play()
        return True
    except pygame.error:
        return False


def _play_file(name: str) -> None:
    if not _sound_enabled:
        return
    if _play_ogg(name):
        return
    if winsound is None:
        return
    sound_path = SOUND_FILES.get(name)
    if sound_path is None:
        return
    try:
        winsound.PlaySound(
            str(sound_path),
            winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
        )
    except RuntimeError:
        return


def play_slice_sound() -> None:
    _play_file("slice")


def play_gold_sound() -> None:
    _play_file("gold")


def play_freeze_sound() -> None:
    _play_file("freeze")


def play_bomb_sound() -> None:
    _play_file("bomb")


def play_miss_sound() -> None:
    _play_file("miss")


def play_test_sequence() -> None:
    play_slice_sound()
    play_gold_sound()
    play_freeze_sound()
    play_bomb_sound()
    play_miss_sound()
