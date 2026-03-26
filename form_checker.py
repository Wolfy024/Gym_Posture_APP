from __future__ import annotations

from typing import Dict, List, Optional

from exercise_rules import EXERCISE_RULES
from geometry import average_metric, side_metric


class FormChecker:
    """Evaluates pose-derived metrics against per-exercise rule thresholds."""

    def __init__(self) -> None:
        self.exercise_rules = EXERCISE_RULES

    @staticmethod
    def _metric_value(
        metrics: Dict[str, float],
        source: str,
        metric_name: str,
        primary_side: str,
    ) -> Optional[float]:
        if source == "avg":
            return average_metric(metrics, metric_name)
        if source == "side":
            return side_metric(metrics, primary_side, metric_name)
        if source == "value":
            return metrics.get(metric_name)
        raise ValueError(f"Unsupported source: {source}")

    def _detect_stage(self, rule_config: Dict, metrics: Dict[str, float], primary_side: str) -> str:
        for stage_rule in rule_config.get("stage_ranges", []):
            value = self._metric_value(
                metrics,
                stage_rule["source"],
                stage_rule["metric"],
                primary_side,
            )
            if value is None:
                continue
            if stage_rule["min"] <= value <= stage_rule["max"]:
                return stage_rule["name"]
        return "unknown"

    @staticmethod
    def _pick_primary_side(metrics: Dict[str, float]) -> str:
        left_count = len([key for key in metrics if key.startswith("left_")])
        right_count = len([key for key in metrics if key.startswith("right_")])
        return "left" if left_count >= right_count else "right"

    def evaluate(self, exercise: str, metrics: Dict[str, float]) -> Dict[str, object]:
        if exercise not in self.exercise_rules:
            raise ValueError(f"Unsupported exercise '{exercise}'")

        config = self.exercise_rules[exercise]
        primary_side = self._pick_primary_side(metrics)

        stage = self._detect_stage(config, metrics, primary_side)

        errors: List[str] = []
        score = 100

        for check in config.get("checks", []):
            value = self._metric_value(metrics, check["source"], check["metric"], primary_side)
            if value is None:
                errors.append(f"Track {check['metric'].replace('_', ' ')} more clearly.")
                score -= check["penalty"]
                continue

            if value < check["min"] or value > check["max"]:
                errors.append(check["message"])
                score -= check["penalty"]

        score = max(0, min(100, score))
        status = "GOOD" if not errors else "FIX FORM"
        feedback = errors[0] if errors else "Great form. Keep this rhythm."

        angle_overview: Dict[str, float] = {}
        for angle_key in config.get("primary_angles", []):
            if angle_key.startswith("avg_"):
                metric_name = angle_key.replace("avg_", "", 1)
                value = average_metric(metrics, metric_name)
            elif angle_key.startswith("side_"):
                metric_name = angle_key.replace("side_", "", 1)
                value = side_metric(metrics, primary_side, metric_name)
            else:
                value = metrics.get(angle_key)
            if value is not None:
                angle_overview[angle_key] = round(float(value), 1)

        return {
            "exercise_name": config["display_name"],
            "stage": stage,
            "status": status,
            "score": score,
            "errors": errors,
            "feedback": feedback,
            "angles": angle_overview,
            "primary_side": primary_side,
            "has_rep_sequence": config.get("rep_sequence") is not None,
        }

