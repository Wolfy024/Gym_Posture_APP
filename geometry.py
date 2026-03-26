from __future__ import annotations

from math import acos, degrees, sqrt
from typing import Dict, Optional, Tuple

import numpy as np


Point = Dict[str, float]
Keypoints = Dict[str, Point]


def get_point(keypoints: Keypoints, name: str, min_visibility: float = 0.5) -> Optional[Point]:
    point = keypoints.get(name)
    if not point:
        return None
    if point.get("visibility", 0.0) < min_visibility:
        return None
    return point


def _to_np(point: Point) -> np.ndarray:
    return np.array([point["x"], point["y"]], dtype=np.float64)


def angle_2d(a: Point, b: Point, c: Point) -> float:
    """Returns the angle ABC in degrees."""
    va = _to_np(a) - _to_np(b)
    vc = _to_np(c) - _to_np(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vc)
    if denom == 0:
        return 0.0
    cos_value = np.clip(np.dot(va, vc) / denom, -1.0, 1.0)
    return float(degrees(acos(cos_value)))


def distance_2d(a: Point, b: Point) -> float:
    dx = a["x"] - b["x"]
    dy = a["y"] - b["y"]
    return sqrt(dx * dx + dy * dy)


def torso_angle_from_vertical(shoulder: Point, hip: Point) -> float:
    """
    Returns torso angle in degrees from vertical.
    0 means perfectly upright; larger values indicate forward/backward lean.
    """
    torso = np.array([shoulder["x"] - hip["x"], shoulder["y"] - hip["y"]], dtype=np.float64)
    vertical = np.array([0.0, -1.0], dtype=np.float64)
    denom = np.linalg.norm(torso) * np.linalg.norm(vertical)
    if denom == 0:
        return 0.0
    cos_value = np.clip(np.dot(torso, vertical) / denom, -1.0, 1.0)
    return float(degrees(acos(cos_value)))


def pick_primary_side(keypoints: Keypoints) -> str:
    """Selects side with better landmark visibility for side-view exercises."""
    left_visibility = (
        keypoints.get("left_shoulder", {}).get("visibility", 0.0)
        + keypoints.get("left_hip", {}).get("visibility", 0.0)
        + keypoints.get("left_knee", {}).get("visibility", 0.0)
    )
    right_visibility = (
        keypoints.get("right_shoulder", {}).get("visibility", 0.0)
        + keypoints.get("right_hip", {}).get("visibility", 0.0)
        + keypoints.get("right_knee", {}).get("visibility", 0.0)
    )
    return "left" if left_visibility >= right_visibility else "right"


def compute_joint_metrics(keypoints: Keypoints, min_visibility: float = 0.5) -> Dict[str, float]:
    """
    Computes common joint angles and shape metrics used by exercise rules.
    Missing values are omitted from the returned dictionary.
    """
    metrics: Dict[str, float] = {}

    for side in ("left", "right"):
        shoulder = get_point(keypoints, f"{side}_shoulder", min_visibility)
        elbow = get_point(keypoints, f"{side}_elbow", min_visibility)
        wrist = get_point(keypoints, f"{side}_wrist", min_visibility)
        hip = get_point(keypoints, f"{side}_hip", min_visibility)
        knee = get_point(keypoints, f"{side}_knee", min_visibility)
        ankle = get_point(keypoints, f"{side}_ankle", min_visibility)

        if shoulder and elbow and wrist:
            metrics[f"{side}_elbow_angle"] = angle_2d(shoulder, elbow, wrist)
        if shoulder and hip and knee:
            metrics[f"{side}_hip_angle"] = angle_2d(shoulder, hip, knee)
            metrics[f"{side}_torso_angle"] = torso_angle_from_vertical(shoulder, hip)
        if hip and knee and ankle:
            metrics[f"{side}_knee_angle"] = angle_2d(hip, knee, ankle)

    left_shoulder = get_point(keypoints, "left_shoulder", min_visibility)
    right_shoulder = get_point(keypoints, "right_shoulder", min_visibility)
    left_hip = get_point(keypoints, "left_hip", min_visibility)
    right_hip = get_point(keypoints, "right_hip", min_visibility)

    if left_shoulder and right_shoulder:
        metrics["shoulder_width"] = distance_2d(left_shoulder, right_shoulder)
    if left_hip and right_hip:
        metrics["hip_width"] = distance_2d(left_hip, right_hip)

    if left_shoulder and right_shoulder and left_hip and right_hip:
        shoulder_center = {
            "x": (left_shoulder["x"] + right_shoulder["x"]) / 2.0,
            "y": (left_shoulder["y"] + right_shoulder["y"]) / 2.0,
        }
        hip_center = {
            "x": (left_hip["x"] + right_hip["x"]) / 2.0,
            "y": (left_hip["y"] + right_hip["y"]) / 2.0,
        }
        metrics["spine_angle"] = torso_angle_from_vertical(shoulder_center, hip_center)

    return metrics


def side_metric(metrics: Dict[str, float], side: str, metric_name: str) -> Optional[float]:
    return metrics.get(f"{side}_{metric_name}")


def average_metric(metrics: Dict[str, float], metric_name: str) -> Optional[float]:
    left = metrics.get(f"left_{metric_name}")
    right = metrics.get(f"right_{metric_name}")
    if left is None and right is None:
        return None
    if left is None:
        return right
    if right is None:
        return left
    return (left + right) / 2.0
