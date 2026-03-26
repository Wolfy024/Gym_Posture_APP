from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2


@dataclass
class CameraConfig:
    camera_index: int = 0
    backend: str = "auto"
    width: int = 1280
    height: int = 720
    read_retries: int = 3


class CameraManager:
    """Simple webcam manager with backend selection and read retry support."""

    def __init__(self, config: CameraConfig) -> None:
        self.config = config
        self.capture: Optional[cv2.VideoCapture] = None
        self.backend_name: str = "auto"

    @staticmethod
    def _backend_flag(name: str) -> int:
        if name == "dshow":
            return cv2.CAP_DSHOW
        if name == "msmf":
            return cv2.CAP_MSMF
        if name == "default":
            return cv2.CAP_ANY
        if name == "auto":
            return cv2.CAP_ANY
        raise ValueError(f"Unsupported camera backend: {name}")

    def _apply_resolution(self) -> None:
        if not self.capture:
            return
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, float(self.config.width))
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, float(self.config.height))

    def open(self) -> None:
        backend_order = [self.config.backend]
        if self.config.backend == "auto":
            backend_order = ["default", "dshow", "msmf"]

        last_error = "Unknown camera initialization failure."
        for backend_name in backend_order:
            flag = self._backend_flag(backend_name)
            capture = cv2.VideoCapture(self.config.camera_index, flag)
            if capture and capture.isOpened():
                self.capture = capture
                self.backend_name = backend_name
                self._apply_resolution()
                return

            if capture:
                capture.release()
            last_error = (
                f"Unable to open camera index {self.config.camera_index} "
                f"with backend '{backend_name}'."
            )

        raise RuntimeError(last_error)

    def read(self):
        if not self.capture:
            raise RuntimeError("Camera is not open. Call open() first.")

        attempts = max(1, self.config.read_retries)
        for _ in range(attempts):
            ok, frame = self.capture.read()
            if ok and frame is not None:
                return frame
        return None

    def release(self) -> None:
        if self.capture:
            self.capture.release()
            self.capture = None
