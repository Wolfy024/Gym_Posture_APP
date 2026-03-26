from __future__ import annotations

from typing import Dict, List


EXERCISE_ORDER: List[str] = [
    "squat",
    "push_up",
    "deadlift",
    "lunge",
    "plank",
    "shoulder_press",
    "bicep_curl",
    "sit_up",
    "burpee",
    "mountain_climber",
]


HOTKEY_TO_EXERCISE: Dict[str, str] = {
    "1": "squat",
    "2": "push_up",
    "3": "deadlift",
    "4": "lunge",
    "5": "plank",
    "6": "shoulder_press",
    "7": "bicep_curl",
    "8": "sit_up",
    "9": "burpee",
    "0": "mountain_climber",
}


EXERCISE_RULES: Dict[str, Dict] = {
    "squat": {
        "display_name": "Squat",
        "camera_angle": "front",
        "stage_ranges": [
            {"name": "down", "metric": "knee_angle", "source": "avg", "min": 65, "max": 105},
            {"name": "up", "metric": "knee_angle", "source": "avg", "min": 150, "max": 190},
        ],
        "checks": [
            {"metric": "knee_angle", "source": "avg", "min": 65, "max": 190, "penalty": 12, "message": "Control depth; avoid knee collapse."},
            {"metric": "spine_angle", "source": "value", "min": 0, "max": 35, "penalty": 10, "message": "Keep chest up and spine neutral."},
        ],
        "rep_sequence": ["down", "up"],
        "primary_angles": ["avg_knee_angle", "spine_angle"],
    },
    "push_up": {
        "display_name": "Push-up",
        "camera_angle": "side",
        "stage_ranges": [
            {"name": "down", "metric": "elbow_angle", "source": "side", "min": 45, "max": 100},
            {"name": "up", "metric": "elbow_angle", "source": "side", "min": 150, "max": 190},
        ],
        "checks": [
            {"metric": "elbow_angle", "source": "side", "min": 45, "max": 190, "penalty": 10, "message": "Use full elbow range of motion."},
            {"metric": "hip_angle", "source": "side", "min": 150, "max": 190, "penalty": 10, "message": "Keep hips aligned with shoulders."},
            {"metric": "torso_angle", "source": "side", "min": 65, "max": 125, "penalty": 8, "message": "Maintain a stable body line."},
        ],
        "rep_sequence": ["down", "up"],
        "primary_angles": ["side_elbow_angle", "side_hip_angle"],
    },
    "deadlift": {
        "display_name": "Deadlift",
        "camera_angle": "side",
        "stage_ranges": [
            {"name": "down", "metric": "hip_angle", "source": "side", "min": 45, "max": 120},
            {"name": "up", "metric": "hip_angle", "source": "side", "min": 150, "max": 190},
        ],
        "checks": [
            {"metric": "hip_angle", "source": "side", "min": 45, "max": 190, "penalty": 10, "message": "Hinge at hips through full range."},
            {"metric": "knee_angle", "source": "side", "min": 95, "max": 190, "penalty": 8, "message": "Avoid excessive knee bend."},
            {"metric": "torso_angle", "source": "side", "min": 5, "max": 70, "penalty": 10, "message": "Keep torso controlled and neutral."},
        ],
        "rep_sequence": ["down", "up"],
        "primary_angles": ["side_hip_angle", "side_knee_angle"],
    },
    "lunge": {
        "display_name": "Lunge",
        "camera_angle": "front",
        "stage_ranges": [
            {"name": "down", "metric": "knee_angle", "source": "avg", "min": 70, "max": 110},
            {"name": "up", "metric": "knee_angle", "source": "avg", "min": 145, "max": 190},
        ],
        "checks": [
            {"metric": "knee_angle", "source": "avg", "min": 70, "max": 190, "penalty": 10, "message": "Keep front knee tracking over toes."},
            {"metric": "spine_angle", "source": "value", "min": 0, "max": 30, "penalty": 8, "message": "Stay upright through the movement."},
        ],
        "rep_sequence": ["down", "up"],
        "primary_angles": ["avg_knee_angle", "spine_angle"],
    },
    "plank": {
        "display_name": "Plank",
        "camera_angle": "side",
        "stage_ranges": [
            {"name": "hold", "metric": "hip_angle", "source": "side", "min": 155, "max": 190},
        ],
        "checks": [
            {"metric": "hip_angle", "source": "side", "min": 155, "max": 190, "penalty": 12, "message": "Lift or lower hips to form a straight line."},
            {"metric": "torso_angle", "source": "side", "min": 70, "max": 120, "penalty": 10, "message": "Brace core and keep shoulders stacked."},
        ],
        "rep_sequence": None,
        "primary_angles": ["side_hip_angle", "side_torso_angle"],
    },
    "shoulder_press": {
        "display_name": "Shoulder Press",
        "camera_angle": "front",
        "stage_ranges": [
            {"name": "down", "metric": "elbow_angle", "source": "avg", "min": 55, "max": 110},
            {"name": "up", "metric": "elbow_angle", "source": "avg", "min": 145, "max": 190},
        ],
        "checks": [
            {"metric": "elbow_angle", "source": "avg", "min": 55, "max": 190, "penalty": 10, "message": "Press through full elbow extension."},
            {"metric": "spine_angle", "source": "value", "min": 0, "max": 25, "penalty": 8, "message": "Avoid over-arching the lower back."},
        ],
        "rep_sequence": ["down", "up"],
        "primary_angles": ["avg_elbow_angle", "spine_angle"],
    },
    "bicep_curl": {
        "display_name": "Bicep Curl",
        "camera_angle": "front",
        "stage_ranges": [
            {"name": "up", "metric": "elbow_angle", "source": "avg", "min": 35, "max": 80},
            {"name": "down", "metric": "elbow_angle", "source": "avg", "min": 145, "max": 190},
        ],
        "checks": [
            {"metric": "elbow_angle", "source": "avg", "min": 35, "max": 190, "penalty": 10, "message": "Use controlled elbow flexion and extension."},
            {"metric": "spine_angle", "source": "value", "min": 0, "max": 25, "penalty": 8, "message": "Avoid swinging torso to lift."},
        ],
        "rep_sequence": ["up", "down"],
        "primary_angles": ["avg_elbow_angle", "spine_angle"],
    },
    "sit_up": {
        "display_name": "Sit-up / Crunch",
        "camera_angle": "side",
        "stage_ranges": [
            {"name": "up", "metric": "hip_angle", "source": "side", "min": 55, "max": 120},
            {"name": "down", "metric": "hip_angle", "source": "side", "min": 130, "max": 190},
        ],
        "checks": [
            {"metric": "hip_angle", "source": "side", "min": 55, "max": 190, "penalty": 10, "message": "Curl trunk through a full range."},
            {"metric": "torso_angle", "source": "side", "min": 20, "max": 140, "penalty": 8, "message": "Keep movement smooth and controlled."},
        ],
        "rep_sequence": ["up", "down"],
        "primary_angles": ["side_hip_angle", "side_torso_angle"],
    },
    "burpee": {
        "display_name": "Burpee",
        "camera_angle": "side",
        "stage_ranges": [
            {"name": "floor", "metric": "hip_angle", "source": "side", "min": 120, "max": 190},
            {"name": "stand", "metric": "torso_angle", "source": "side", "min": 0, "max": 35},
        ],
        "checks": [
            {"metric": "spine_angle", "source": "value", "min": 0, "max": 45, "penalty": 10, "message": "Keep torso stable during transitions."},
            {"metric": "knee_angle", "source": "side", "min": 70, "max": 190, "penalty": 8, "message": "Land softly with controlled knees."},
        ],
        "rep_sequence": ["floor", "stand"],
        "primary_angles": ["side_hip_angle", "side_knee_angle"],
    },
    "mountain_climber": {
        "display_name": "Mountain Climber",
        "camera_angle": "side",
        "stage_ranges": [
            {"name": "drive", "metric": "hip_angle", "source": "side", "min": 65, "max": 130},
            {"name": "extend", "metric": "hip_angle", "source": "side", "min": 135, "max": 190},
        ],
        "checks": [
            {"metric": "hip_angle", "source": "side", "min": 65, "max": 190, "penalty": 10, "message": "Drive knees without piking hips."},
            {"metric": "torso_angle", "source": "side", "min": 65, "max": 125, "penalty": 8, "message": "Keep shoulders over wrists."},
        ],
        "rep_sequence": ["drive", "extend"],
        "primary_angles": ["side_hip_angle", "side_torso_angle"],
    },
}

