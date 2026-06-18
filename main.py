from __future__ import annotations

import random
import time
from collections import deque

import cv2
import numpy as np

from camera.webcam import Webcam
from config import (
    CAMERA_INDEX,
    COMBO_POPUP_SECONDS,
    COMBO_RESET_SECONDS,
    FIRE_DURATION_SECONDS,
    FIRE_SCORE_MULTIPLIER,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    FREEZE_DURATION_SECONDS,
    FROZEN_WORLD_SPEED,
    GRAVITY,
    HIT_EFFECT_LIFETIME_SECONDS,
    MAX_MISSES,
    MAX_TRAIL_POINTS,
    POPUP_LIFETIME_SECONDS,
    SPAWN_INTERVAL_SECONDS,
    SHOCK_CHAIN_RADIUS_MULTIPLIER,
    SLICE_SPEED_THRESHOLD,
    TARGET_FPS,
    WINDOW_NAME,
)
from game.collision import segment_hits_object
from game.effects import HitEffect, Particle, ScorePopup
from game.history import GameHistoryEntry, append_history, load_history, now_iso, summarize_history
from game.menu import (
    build_game_over_menu,
    build_history_menu,
    build_main_menu,
    build_mode_menu,
    build_settings_menu,
)
from game.missions import build_default_missions, evaluate_missions
from game.settings import load_settings, save_settings
from game.sound import (
    play_bomb_sound,
    play_freeze_sound,
    play_gold_sound,
    play_miss_sound,
    play_slice_sound,
    play_test_sequence,
    set_sound_enabled,
)
from game.spawner import Spawner
from game.state import GameState
from render.renderer import (
    draw_game_over_screen,
    draw_history_screen,
    draw_hud,
    draw_hit_effects,
    draw_menu_buttons,
    draw_menu_pointer_hint,
    draw_mode_screen,
    draw_objects,
    draw_settings_screen,
    draw_start_screen,
    draw_trail,
)
from tracking.hand_tracker import HandTracker
from utils.math_helpers import euclidean_distance, point_to_segment_distance


def reset_game(state: GameState) -> None:
    state.mode = "playing"
    state.score = 0
    state.misses = 0
    state.combo = 0
    state.objects.clear()
    state.hit_effects.clear()
    state.particles.clear()
    state.score_popups.clear()
    state.trail = deque(maxlen=MAX_TRAIL_POINTS)
    state.last_slice_segment = None
    state.freeze_until = 0.0
    state.fire_until = 0.0
    state.combo_flash_until = 0.0
    state.hovered_button_action = None
    state.hover_started_at = 0.0
    state.session_started_at = time.perf_counter()
    state.fruits_sliced = 0
    state.gold_sliced = 0
    state.freeze_sliced = 0
    state.fire_sliced = 0
    state.shock_sliced = 0
    state.bombs_hit = 0
    state.max_combo = 0
    state.skill_charge = 0.0
    state.blade_rush_until = 0.0
    state.blade_rush_cooldown_until = 0.0
    state.cyclone_cooldown_until = 0.0
    state.completed_missions = []
    state.active_missions = build_default_missions()


def reset_to_main_menu(state: GameState, frame_width: int, frame_height: int) -> None:
    state.mode = "start"
    state.score = 0
    state.misses = 0
    state.combo = 0
    state.objects.clear()
    state.hit_effects.clear()
    state.particles.clear()
    state.score_popups.clear()
    state.trail.clear()
    state.last_slice_segment = None
    state.freeze_until = 0.0
    state.fire_until = 0.0
    state.combo_flash_until = 0.0
    state.menu_buttons = build_main_menu(frame_width, frame_height)
    state.hovered_button_action = None
    state.hover_started_at = 0.0
    state.completed_missions = []


def show_history_menu(state: GameState, frame_width: int, frame_height: int) -> None:
    state.mode = "history"
    state.objects.clear()
    state.trail.clear()
    state.menu_buttons = build_history_menu(frame_width, frame_height)
    state.hovered_button_action = None
    state.hover_started_at = 0.0
    state.history_entries = load_history()


def show_mode_menu(state: GameState, frame_width: int, frame_height: int) -> None:
    state.mode = "modes"
    state.objects.clear()
    state.trail.clear()
    state.menu_buttons = build_mode_menu(frame_width, frame_height)
    state.hovered_button_action = None
    state.hover_started_at = 0.0


def show_settings_menu(state: GameState, frame_width: int, frame_height: int) -> None:
    state.mode = "settings"
    state.objects.clear()
    state.trail.clear()
    state.menu_buttons = build_settings_menu(frame_width, frame_height)
    state.hovered_button_action = None
    state.hover_started_at = 0.0


def record_game_history(state: GameState, end_reason: str) -> None:
    if state.session_started_at <= 0:
        return
    state.completed_missions = [mission for mission in evaluate_missions(state, end_reason) if mission.completed]
    entry = GameHistoryEntry(
        played_at=now_iso(),
        score=state.score,
        duration_seconds=max(0.0, time.perf_counter() - state.session_started_at),
        fruits_sliced=state.fruits_sliced,
        gold_sliced=state.gold_sliced,
        freeze_sliced=state.freeze_sliced,
        fire_sliced=state.fire_sliced,
        shock_sliced=state.shock_sliced,
        bombs_hit=state.bombs_hit,
        misses=state.misses,
        max_combo=state.max_combo,
        end_reason=end_reason,
    )
    state.history_entries = append_history(entry)
    state.session_started_at = 0.0


def update_menu_hover(state: GameState, finger_tip: tuple[int, int] | None, current_time: float) -> str | None:
    hovered_button = None
    for button in state.menu_buttons:
        if button.contains(finger_tip):
            hovered_button = button
            break

    if hovered_button is None:
        state.hovered_button_action = None
        state.hover_started_at = 0.0
        return None

    if state.hovered_button_action != hovered_button.action:
        state.hovered_button_action = hovered_button.action
        state.hover_started_at = current_time
        return None

    if current_time - state.hover_started_at >= state.settings.hover_seconds:
        state.hovered_button_action = None
        state.hover_started_at = 0.0
        return hovered_button.action
    return None


def get_hover_progress(state: GameState, current_time: float) -> float:
    if not state.hovered_button_action or state.hover_started_at <= 0:
        return 0.0
    return max(0.0, min(1.0, (current_time - state.hover_started_at) / state.settings.hover_seconds))


def show_camera_error() -> None:
    frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype="uint8")
    cv2.putText(frame, "Camera could not be opened", (160, 260), 0, 1.0, (0, 0, 255), 2)
    cv2.putText(frame, "Check camera permission or whether another app is using it.", (70, 320), 0, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, "Press any key to exit.", (230, 380), 0, 0.8, (200, 200, 200), 2)
    cv2.imshow(WINDOW_NAME, frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def build_spawn_profile(state: GameState, base_request: dict[str, float]) -> dict[str, float]:
    profile = dict(base_request)
    mode = state.settings.selected_mode
    if mode == "禪模式":
        profile["bomb_chance_multiplier"] = 0.0
        profile["gold_weight"] = profile.get("gold_weight", 1.0) * 1.2
        profile["freeze_weight"] = profile.get("freeze_weight", 1.0) * 1.2
    elif mode == "挑戰模式":
        profile["bomb_chance_multiplier"] = profile.get("bomb_chance_multiplier", 1.0) * 1.3
        profile["velocity_multiplier"] = profile.get("velocity_multiplier", 1.0) * 1.16
        profile["shock_weight"] = profile.get("shock_weight", 1.0) * 1.2
    return profile


def detect_blade_rush(trail: deque[tuple[int, int]], frame_scale: float) -> bool:
    if len(trail) < 8:
        return False
    recent = list(trail)[-8:]
    dx = recent[-1][0] - recent[0][0]
    dy = recent[-1][1] - recent[0][1]
    required_dx = max(120.0, 220.0 * frame_scale)
    max_dy = max(45.0, 70.0 * frame_scale)
    if abs(dx) < required_dx or abs(dy) > max_dy:
        return False

    segment_dx = [recent[index][0] - recent[index - 1][0] for index in range(1, len(recent))]
    segment_dy = [recent[index][1] - recent[index - 1][1] for index in range(1, len(recent))]
    horizontal_total = sum(abs(value) for value in segment_dx)
    vertical_total = sum(abs(value) for value in segment_dy)
    if horizontal_total < required_dx * 1.2 or vertical_total > max_dy * 1.5:
        return False

    direction = 1 if dx > 0 else -1
    aligned_segments = sum(1 for value in segment_dx if value * direction > 0)
    end_burst = abs(segment_dx[-1]) + abs(segment_dx[-2])
    return aligned_segments >= 6 and end_burst >= max(28.0, 42.0 * frame_scale)


def detect_cyclone(trail: deque[tuple[int, int]]) -> bool:
    if len(trail) < 10:
        return False
    recent = list(trail)[-10:]
    xs = [point[0] for point in recent]
    ys = [point[1] for point in recent]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    start_end_distance = euclidean_distance(recent[0], recent[-1])
    return width > 80 and height > 80 and start_end_distance < 45


def get_spawn_interval_seconds(state: GameState) -> float:
    mode = state.settings.selected_mode
    if mode == "禪模式":
        return SPAWN_INTERVAL_SECONDS * 0.9
    if mode == "挑戰模式":
        return SPAWN_INTERVAL_SECONDS * 0.72
    return SPAWN_INTERVAL_SECONDS


def get_max_active_fruits(state: GameState) -> int:
    mode = state.settings.selected_mode
    if mode == "挑戰模式":
        return 4
    if mode == "禪模式":
        return 3
    return 3


def main() -> None:
    runtime_settings = load_settings()
    set_sound_enabled(runtime_settings.sound_enabled)

    webcam = Webcam(index=CAMERA_INDEX, width=FRAME_WIDTH, height=FRAME_HEIGHT)
    if not webcam.is_opened():
        print("Camera could not be opened. Check permission or device availability.")
        show_camera_error()
        webcam.release()
        return

    tracker = HandTracker()
    spawner = Spawner()
    state = GameState(trail=deque(maxlen=MAX_TRAIL_POINTS), settings=runtime_settings)
    state.history_entries = load_history()

    last_frame_time = time.perf_counter()
    last_score_time = 0.0
    next_spawn_at = last_frame_time + 0.6
    random_generator = random.Random()

    def slice_object(game_object) -> None:
        nonlocal last_score_time, current_time
        if not game_object.is_alive or game_object.is_sliced or game_object.kind != "fruit":
            return

        game_object.is_sliced = True
        game_object.is_alive = False
        if current_time - last_score_time > COMBO_RESET_SECONDS:
            state.combo = 0
        state.combo += 1
        state.max_combo = max(state.max_combo, state.combo)
        state.fruits_sliced += 1
        state.skill_charge = min(1.0, state.skill_charge + 0.12)
        combo_multiplier = max(1, state.combo)
        fire_multiplier = FIRE_SCORE_MULTIPLIER if current_time < state.fire_until else 1.0
        awarded_score = int(game_object.score_value * combo_multiplier * fire_multiplier)
        state.score += awarded_score
        last_score_time = current_time
        state.combo_flash_until = current_time + COMBO_POPUP_SECONDS

        state.hit_effects.append(HitEffect(x=game_object.x, y=game_object.y, color=game_object.color, radius=game_object.radius * 0.7, ttl=HIT_EFFECT_LIFETIME_SECONDS, effect_type=game_object.effect))
        popup_color = (255, 230, 120) if game_object.effect == "gold" else (255, 255, 255)
        if current_time < state.fire_until:
            popup_color = (120, 220, 255)
        state.score_popups.append(ScorePopup(x=game_object.x - game_object.radius * 0.6, y=game_object.y, text=f"+{awarded_score}", color=popup_color, ttl=POPUP_LIFETIME_SECONDS))

        for _ in range(10):
            state.particles.append(
                Particle(
                    x=game_object.x,
                    y=game_object.y,
                    vx=random_generator.uniform(-140.0, 140.0),
                    vy=random_generator.uniform(-160.0, -20.0),
                    color=game_object.color,
                    radius=max(2.0, game_object.radius / 7.0),
                    ttl=0.45 + random_generator.uniform(0.0, 0.18),
                )
            )

        if game_object.effect == "gold":
            state.gold_sliced += 1
            play_gold_sound()
        elif game_object.effect == "freeze":
            state.freeze_sliced += 1
            state.freeze_until = current_time + FREEZE_DURATION_SECONDS
            state.score_popups.append(ScorePopup(x=game_object.x - game_object.radius, y=game_object.y - game_object.radius, text="冰凍！", color=(255, 240, 140), ttl=POPUP_LIFETIME_SECONDS))
            play_freeze_sound()
        elif game_object.effect == "fire":
            state.fire_sliced += 1
            state.fire_until = current_time + FIRE_DURATION_SECONDS
            state.score_popups.append(ScorePopup(x=game_object.x - game_object.radius, y=game_object.y - game_object.radius, text="火焰 x2！", color=(120, 220, 255), ttl=POPUP_LIFETIME_SECONDS))
            play_gold_sound()
        elif game_object.effect == "shock":
            state.shock_sliced += 1
            state.score_popups.append(ScorePopup(x=game_object.x - game_object.radius, y=game_object.y - game_object.radius, text="連鎖！", color=(255, 250, 140), ttl=POPUP_LIFETIME_SECONDS))
            play_freeze_sound()
            chain_radius = game_object.radius * SHOCK_CHAIN_RADIUS_MULTIPLIER
            nearby_targets = []
            for target in state.objects:
                if target.id == game_object.id or not target.is_alive or target.kind != "fruit":
                    continue
                if euclidean_distance((int(game_object.x), int(game_object.y)), (int(target.x), int(target.y))) <= chain_radius:
                    nearby_targets.append(target)
            for target in nearby_targets[:3]:
                if target.effect != "shock":
                    slice_object(target)
        else:
            play_slice_sound()

    try:
        while True:
            ok, frame = webcam.read()
            if not ok:
                break

            frame_height, frame_width = frame.shape[:2]
            if state.settings.mirror_camera:
                frame = cv2.flip(frame, 1)

            current_time = time.perf_counter()
            delta = current_time - last_frame_time
            fps = 1.0 / delta if delta > 0 else 0.0
            last_frame_time = current_time
            frame_scale = min(frame_width / 1280.0, frame_height / 720.0)
            world_speed = FROZEN_WORLD_SPEED if current_time < state.freeze_until else 1.0

            tracking_result = tracker.process(frame)
            if tracking_result.index_finger_tip:
                state.trail.append(tracking_result.index_finger_tip)
            else:
                state.trail.clear()
                state.last_slice_segment = None

            if state.mode == "start" and not state.menu_buttons:
                state.menu_buttons = build_main_menu(frame_width, frame_height)
            elif state.mode == "game_over" and not state.menu_buttons:
                state.menu_buttons = build_game_over_menu(frame_width, frame_height)
            elif state.mode == "history" and not state.menu_buttons:
                state.menu_buttons = build_history_menu(frame_width, frame_height)
            elif state.mode == "modes" and not state.menu_buttons:
                state.menu_buttons = build_mode_menu(frame_width, frame_height)
            elif state.mode == "settings" and not state.menu_buttons:
                state.menu_buttons = build_settings_menu(frame_width, frame_height)

            if state.mode in {"start", "game_over", "history", "modes", "settings"}:
                triggered_action = update_menu_hover(state, tracking_result.index_finger_tip, current_time)
                if triggered_action == "start_game":
                    reset_game(state)
                    state.menu_buttons.clear()
                    next_spawn_at = current_time + 0.45
                elif triggered_action == "show_modes":
                    show_mode_menu(state, frame_width, frame_height)
                elif triggered_action == "show_settings":
                    show_settings_menu(state, frame_width, frame_height)
                elif triggered_action == "restart_game":
                    reset_game(state)
                    state.menu_buttons.clear()
                    next_spawn_at = current_time + 0.45
                elif triggered_action == "go_to_menu":
                    reset_to_main_menu(state, frame_width, frame_height)
                elif triggered_action == "show_history":
                    show_history_menu(state, frame_width, frame_height)
                elif triggered_action == "mode_arcade":
                    state.settings.selected_mode = "標準模式"
                    save_settings(state.settings)
                    show_mode_menu(state, frame_width, frame_height)
                elif triggered_action == "mode_zen":
                    state.settings.selected_mode = "禪模式"
                    save_settings(state.settings)
                    show_mode_menu(state, frame_width, frame_height)
                elif triggered_action == "mode_challenge":
                    state.settings.selected_mode = "挑戰模式"
                    save_settings(state.settings)
                    show_mode_menu(state, frame_width, frame_height)
                elif triggered_action == "toggle_sound":
                    state.settings.sound_enabled = not state.settings.sound_enabled
                    set_sound_enabled(state.settings.sound_enabled)
                    save_settings(state.settings)
                    show_settings_menu(state, frame_width, frame_height)
                elif triggered_action == "toggle_mirror":
                    state.settings.mirror_camera = not state.settings.mirror_camera
                    save_settings(state.settings)
                    show_settings_menu(state, frame_width, frame_height)
                elif triggered_action == "cycle_hover_speed":
                    state.settings.hover_seconds = 1.4 if state.settings.hover_seconds <= 0.8 else 0.6 if state.settings.hover_seconds >= 1.4 else 1.0
                    save_settings(state.settings)
                    show_settings_menu(state, frame_width, frame_height)
                elif triggered_action == "exit_game":
                    break

            if state.mode == "playing":
                active_fruits = sum(1 for game_object in state.objects if game_object.is_alive and game_object.kind == "fruit")
                if current_time >= next_spawn_at and active_fruits < get_max_active_fruits(state):
                    state.objects.append(spawner.spawn(frame_width, frame_height, build_spawn_profile(state, {})))
                    next_spawn_at = current_time + get_spawn_interval_seconds(state)

                for game_object in state.objects:
                    if game_object.is_alive:
                        game_object.update(gravity=GRAVITY, speed_multiplier=world_speed)
                        if game_object.y + game_object.radius >= 0 and game_object.y - game_object.radius <= frame_height:
                            game_object.has_entered_screen = True
                        if game_object.has_entered_screen and game_object.y - game_object.radius > frame_height:
                            game_object.is_alive = False
                            if game_object.kind == "fruit" and not game_object.is_sliced:
                                state.misses += 1
                                play_miss_sound()

                if len(state.trail) >= 2:
                    slice_start = state.trail[-2]
                    slice_end = state.trail[-1]
                    speed = euclidean_distance(slice_start, slice_end)

                    if (
                        detect_blade_rush(state.trail, frame_scale)
                        and state.skill_charge >= 1.0
                        and current_time >= state.blade_rush_cooldown_until
                        and current_time >= state.blade_rush_until
                    ):
                        state.blade_rush_until = current_time + 4.8
                        state.blade_rush_cooldown_until = current_time + 1.6
                        state.skill_charge = 0.0
                        state.score_popups.append(ScorePopup(x=frame_width * 0.5 - 90, y=frame_height * 0.20, text="?????", color=(255, 220, 120), ttl=POPUP_LIFETIME_SECONDS + 0.4))
                        state.hit_effects.append(HitEffect(x=frame_width * 0.5, y=frame_height * 0.5, color=(120, 200, 255), radius=min(frame_width, frame_height) * 0.22, ttl=0.55, effect_type="blade_rush"))
                        for _ in range(26):
                            state.particles.append(
                                Particle(
                                    x=frame_width * 0.5,
                                    y=frame_height * 0.5,
                                    vx=random_generator.uniform(-260.0, 260.0),
                                    vy=random_generator.uniform(-220.0, 220.0),
                                    color=(120, 210, 255),
                                    radius=random_generator.uniform(3.0, 7.0),
                                    ttl=0.55 + random_generator.uniform(0.0, 0.2),
                                )
                            )
                        play_gold_sound()

                    if detect_cyclone(state.trail) and state.skill_charge >= 0.75 and current_time >= state.cyclone_cooldown_until and tracking_result.index_finger_tip:
                        state.skill_charge = max(0.0, state.skill_charge - 0.75)
                        state.cyclone_cooldown_until = current_time + 4.0
                        cyclone_center = tracking_result.index_finger_tip
                        state.hit_effects.append(HitEffect(x=cyclone_center[0], y=cyclone_center[1], color=(120, 240, 255), radius=max(110, int(160 * frame_scale)), ttl=0.5, effect_type="cyclone"))
                        for _ in range(24):
                            state.particles.append(
                                Particle(
                                    x=cyclone_center[0],
                                    y=cyclone_center[1],
                                    vx=random_generator.uniform(-240.0, 240.0),
                                    vy=random_generator.uniform(-240.0, 240.0),
                                    color=(120, 240, 255),
                                    radius=random_generator.uniform(3.0, 6.0),
                                    ttl=0.5 + random_generator.uniform(0.0, 0.25),
                                )
                            )
                        for target in list(state.objects):
                            if target.kind == "fruit" and target.is_alive and euclidean_distance(cyclone_center, (int(target.x), int(target.y))) <= max(150, int(240 * frame_scale)):
                                slice_object(target)
                        state.score_popups.append(ScorePopup(x=cyclone_center[0] - 45, y=cyclone_center[1] - 20, text="????", color=(120, 240, 255), ttl=POPUP_LIFETIME_SECONDS + 0.35))
                        play_freeze_sound()
                    if speed >= SLICE_SPEED_THRESHOLD * frame_scale:
                        state.last_slice_segment = (slice_start, slice_end)
                        for game_object in state.objects:
                            if not game_object.is_alive or game_object.is_sliced:
                                continue
                            extra_radius = 60 if current_time < state.blade_rush_until and game_object.kind == "fruit" else 0
                            hit = segment_hits_object(slice_start, slice_end, game_object)
                            if not hit and extra_radius > 0:
                                hit = point_to_segment_distance((game_object.x, game_object.y), slice_start, slice_end) <= game_object.radius + extra_radius
                            if hit:
                                if game_object.kind == "bomb":
                                    if state.settings.selected_mode == "禪模式":
                                        continue
                                    game_object.is_sliced = True
                                    game_object.is_alive = False
                                    play_bomb_sound()
                                    state.bombs_hit += 1
                                    record_game_history(state, "炸彈")
                                    state.mode = "game_over"
                                    state.menu_buttons = build_game_over_menu(frame_width, frame_height)
                                else:
                                    slice_object(game_object)
                    else:
                        state.last_slice_segment = None

                if current_time - last_score_time > COMBO_RESET_SECONDS:
                    state.combo = 0

                for effect in state.hit_effects:
                    effect.update(delta)
                state.hit_effects = [effect for effect in state.hit_effects if effect.ttl > 0]

                for particle in state.particles:
                    particle.update(delta, gravity=180.0 * world_speed)
                state.particles = [particle for particle in state.particles if particle.ttl > 0]

                for popup in state.score_popups:
                    popup.update(delta)
                state.score_popups = [popup for popup in state.score_popups if popup.ttl > 0]

                state.objects = [game_object for game_object in state.objects if game_object.is_alive]
                if state.misses >= MAX_MISSES:
                    record_game_history(state, "失誤")
                    state.mode = "game_over"
                    state.menu_buttons = build_game_over_menu(frame_width, frame_height)

            draw_objects(frame, state.objects)
            draw_hit_effects(frame, state.hit_effects, state.particles, state.score_popups)
            draw_trail(frame, state.trail)

            if state.mode == "playing":
                draw_hud(
                    frame,
                    score=state.score,
                    misses=state.misses,
                    fps=fps,
                    tracking_active=tracking_result.hand_detected,
                    combo=state.combo if current_time < state.combo_flash_until else 0,
                    freeze_seconds_left=max(0.0, state.freeze_until - current_time),
                    fire_seconds_left=max(0.0, state.fire_until - current_time),
                    combo_progress=max(0.0, min(1.0, 1.0 - ((current_time - last_score_time) / COMBO_RESET_SECONDS))) if state.combo > 0 else 0.0,
                    skill_charge=state.skill_charge,
                    blade_rush_seconds_left=max(0.0, state.blade_rush_until - current_time),
                    active_missions=state.active_missions,
                )

            if tracking_result.index_finger_tip:
                cv2.circle(frame, tracking_result.index_finger_tip, 10, (255, 255, 255), -1)

            if state.mode == "start":
                draw_start_screen(frame, state.settings.selected_mode)
                draw_menu_buttons(frame, state.menu_buttons, state.hovered_button_action, get_hover_progress(state, current_time))
                draw_menu_pointer_hint(frame, tracking_result.index_finger_tip)
            elif state.mode == "game_over":
                draw_game_over_screen(frame, state.score, state.completed_missions)
                draw_menu_buttons(frame, state.menu_buttons, state.hovered_button_action, get_hover_progress(state, current_time))
                draw_menu_pointer_hint(frame, tracking_result.index_finger_tip)
            elif state.mode == "history":
                draw_history_screen(frame, state.history_entries, summarize_history(state.history_entries))
                draw_menu_buttons(frame, state.menu_buttons, state.hovered_button_action, get_hover_progress(state, current_time))
                draw_menu_pointer_hint(frame, tracking_result.index_finger_tip)
            elif state.mode == "modes":
                draw_mode_screen(frame, state.settings.selected_mode)
                draw_menu_buttons(frame, state.menu_buttons, state.hovered_button_action, get_hover_progress(state, current_time))
                draw_menu_pointer_hint(frame, tracking_result.index_finger_tip)
            elif state.mode == "settings":
                draw_settings_screen(frame, state.settings)
                draw_menu_buttons(frame, state.menu_buttons, state.hovered_button_action, get_hover_progress(state, current_time))
                draw_menu_pointer_hint(frame, tracking_result.index_finger_tip)

            cv2.imshow(WINDOW_NAME, frame)
            key = cv2.waitKey(max(1, int(1000 / TARGET_FPS))) & 0xFF
            if key == 27 or key == ord("q"):
                break
            if key == ord("t"):
                play_test_sequence()
            if key == ord(" "):
                reset_game(state)
                state.menu_buttons.clear()
                next_spawn_at = current_time + 0.45
            if key == ord("m"):
                reset_to_main_menu(state, frame_width, frame_height)
            if key == ord("h"):
                show_history_menu(state, frame_width, frame_height)
            if key == ord("r") and state.mode == "game_over":
                reset_game(state)
                state.menu_buttons.clear()
                next_spawn_at = current_time + 0.45

    finally:
        tracker.close()
        webcam.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
