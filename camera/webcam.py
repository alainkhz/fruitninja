from __future__ import annotations

import cv2


class Webcam:
    def __init__(self, index: int, width: int, height: int) -> None:
        self.index = index
        self.width = width
        self.height = height
        self.capture = cv2.VideoCapture(self.index)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

    def read(self):
        return self.capture.read()

    def is_opened(self) -> bool:
        return bool(self.capture and self.capture.isOpened())

    def release(self) -> None:
        if self.capture:
            self.capture.release()
