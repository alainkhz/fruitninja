from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

_matplotlib_cache_dir = Path(__file__).resolve().parents[1] / "work" / "matplotlib"
_matplotlib_cache_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_matplotlib_cache_dir))

import mediapipe as mp
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode

from config import HAND_LANDMARKER_MODEL_PATH


@dataclass
class HandTrackingResult:
    index_finger_tip: Optional[tuple[int, int]]
    hand_detected: bool
    tracking_confidence: float


class HandTracker:
    def __init__(
        self,
        max_num_hands: int = 1,
        min_detection_confidence: float = 0.6,
        min_tracking_confidence: float = 0.6,
    ) -> None:
        model_path = Path(HAND_LANDMARKER_MODEL_PATH)
        if not model_path.exists():
            raise FileNotFoundError(
                "Hand landmarker model not found. "
                f"Expected: {model_path.resolve()}"
            )

        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path.resolve())),
            running_mode=RunningMode.IMAGE,
            num_hands=max_num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_tracking_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self.landmarker = HandLandmarker.create_from_options(options)
        self.index_tip_landmark = 8

    def process(self, frame) -> HandTrackingResult:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.asarray(rgb_frame))
        results = self.landmarker.detect(mp_image)

        if not results.hand_landmarks:
            return HandTrackingResult(
                index_finger_tip=None,
                hand_detected=False,
                tracking_confidence=0.0,
            )

        hand_landmarks = results.hand_landmarks[0]
        landmark = hand_landmarks[self.index_tip_landmark]
        frame_height, frame_width = frame.shape[:2]
        x = int(landmark.x * frame_width)
        y = int(landmark.y * frame_height)

        return HandTrackingResult(
            index_finger_tip=(x, y),
            hand_detected=True,
            tracking_confidence=1.0,
        )

    def close(self) -> None:
        self.landmarker.close()
