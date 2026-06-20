from __future__ import annotations

import time

import cv2
import numpy as np


class Webcam:
    def __init__(self, index: int, width: int, height: int) -> None:
        self.index = index
        self.width = width
        self.height = height
        self.capture = None
        self.backend_name = "uninitialized"
        self.capture = self._open_best_capture()

    def _candidate_backends(self) -> list[tuple[str, int | None]]:
        candidates: list[tuple[str, int | None]] = []
        if hasattr(cv2, "CAP_DSHOW"):
            candidates.append(("DirectShow", cv2.CAP_DSHOW))
        if hasattr(cv2, "CAP_MSMF"):
            candidates.append(("Media Foundation", cv2.CAP_MSMF))
        candidates.append(("Default", None))
        return candidates

    def _configure_capture(self, capture) -> None:
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if hasattr(cv2, "VideoWriter_fourcc"):
            capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

    def _looks_valid_frame(self, frame) -> bool:
        if frame is None or frame.size == 0:
            return False
        if frame.ndim < 2:
            return False
        mean_luma = float(np.mean(frame))
        max_value = int(np.max(frame))
        return mean_luma > 8.0 or max_value > 24

    def _warmup_and_validate(self, capture) -> bool:
        last_good = False
        for _ in range(12):
            ok, frame = capture.read()
            if ok and self._looks_valid_frame(frame):
                last_good = True
                break
            time.sleep(0.03)
        return last_good

    def _open_best_capture(self):
        for backend_name, backend in self._candidate_backends():
            capture = cv2.VideoCapture(self.index, backend) if backend is not None else cv2.VideoCapture(self.index)
            if not capture or not capture.isOpened():
                if capture:
                    capture.release()
                continue

            self._configure_capture(capture)
            if self._warmup_and_validate(capture):
                self.backend_name = backend_name
                return capture

            capture.release()

        self.backend_name = "unavailable"
        fallback = cv2.VideoCapture(self.index)
        if fallback and fallback.isOpened():
            self._configure_capture(fallback)
            return fallback
        return fallback

    def read(self):
        if not self.capture:
            return False, None
        return self.capture.read()

    def is_opened(self) -> bool:
        return bool(self.capture and self.capture.isOpened())

    def release(self) -> None:
        if self.capture:
            self.capture.release()
