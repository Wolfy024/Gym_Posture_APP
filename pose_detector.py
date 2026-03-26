from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import cv2
import mediapipe as mp


@dataclass
class PoseConfig:
    model_complexity: int = 1
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    draw_pose: bool = True
    visibility_threshold: float = 0.5


class PoseDetector:
    def __init__(self, config: PoseConfig) -> None:
        self.config = config
        self._mp_pose = mp.solutions.pose
        self._mp_drawing = mp.solutions.drawing_utils
        self._pose = self._mp_pose.Pose(
            model_complexity=config.model_complexity,
            min_detection_confidence=config.min_detection_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
        )
        self._landmark_names = [landmark.name.lower() for landmark in self._mp_pose.PoseLandmark]

    def process(self, frame_bgr) -> Dict[str, object]:
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self._pose.process(frame_rgb)

        keypoints: Dict[str, Dict[str, float]] = {}
        if results.pose_landmarks:
            for idx, landmark in enumerate(results.pose_landmarks.landmark):
                keypoints[self._landmark_names[idx]] = {
                    "x": float(landmark.x),
                    "y": float(landmark.y),
                    "z": float(landmark.z),
                    "visibility": float(landmark.visibility),
                }

        return {
            "keypoints": keypoints,
            "pose_landmarks": results.pose_landmarks,
            "raw_results": results,
        }

    def draw(self, frame_bgr, pose_landmarks: Optional[object]) -> None:
        if not self.config.draw_pose or pose_landmarks is None:
            return
        self._mp_drawing.draw_landmarks(
            frame_bgr,
            pose_landmarks,
            self._mp_pose.POSE_CONNECTIONS,
        )

    def is_visible(self, keypoints: Dict[str, Dict[str, float]], name: str) -> bool:
        point = keypoints.get(name)
        if not point:
            return False
        return point.get("visibility", 0.0) >= self.config.visibility_threshold

    def close(self) -> None:
        self._pose.close()
