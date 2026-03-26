from __future__ import annotations

import argparse
import ctypes
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import cv2
import numpy as np

from camera import CameraConfig, CameraManager
from exercise_rules import EXERCISE_ORDER, HOTKEY_TO_EXERCISE
from form_checker import FormChecker
from geometry import compute_joint_metrics
from pose_detector import PoseConfig, PoseDetector
from rep_counter import RepCounter

WINDOW_TITLE = "RepRight Phase 1"


@dataclass
class SessionTracker:
    """Aggregates per-frame form data after warmup for end-of-session insights."""

    scored_frames: int = 0
    good_frames: int = 0
    score_sum: int = 0
    per_exercise: Dict[str, Dict[str, object]] = field(
        default_factory=lambda: defaultdict(
            lambda: {"frames": 0, "good": 0, "score_sum": 0, "errors": Counter()}
        )
    )

    def record(self, exercise: str, evaluation: Dict[str, object]) -> None:
        if str(evaluation.get("stage")) == "warmup":
            return
        status = str(evaluation.get("status", ""))
        score = int(evaluation.get("score", 0))
        self.scored_frames += 1
        if status == "GOOD":
            self.good_frames += 1
        self.score_sum += score
        pe = self.per_exercise[exercise]
        pe["frames"] = int(pe["frames"]) + 1
        if status == "GOOD":
            pe["good"] = int(pe["good"]) + 1
        pe["score_sum"] = int(pe["score_sum"]) + score
        err_counter: Counter = pe["errors"]
        for err in evaluation.get("errors", []) or []:
            err_counter[str(err)] += 1

    def reset(self) -> None:
        self.scored_frames = 0
        self.good_frames = 0
        self.score_sum = 0
        self.per_exercise.clear()


def build_session_insights(
    stats: SessionTracker,
    final_reps: Dict[str, int],
) -> Tuple[List[str], List[str], List[str]]:
    """Return (good_bullets, bad_bullets, headline_lines) for the summary screen."""
    good: List[str] = []
    bad: List[str] = []
    headline: List[str] = []

    if stats.scored_frames == 0:
        headline.append("Session: no scored frames yet (stay visible after warmup).")
        good.append("You started a session — next time, stay in frame for feedback.")
        bad.append("No form data to analyze — ensure lighting and full-body view.")
        return good, bad, headline

    avg = stats.score_sum / stats.scored_frames
    good_pct = 100.0 * stats.good_frames / stats.scored_frames
    headline.append(f"Session: {stats.scored_frames} frames analyzed")
    headline.append(f"Average score: {avg:.0f} / 100")
    headline.append(f"Time in GOOD form: {good_pct:.0f}%")

    if good_pct >= 70:
        good.append("Strong consistency: most frames met your form targets.")
    elif good_pct >= 45:
        good.append("You had solid stretches of good form — build on that rhythm.")
    else:
        bad.append("Form was inconsistent — slow down and prioritize one cue at a time.")

    if avg >= 80:
        good.append(f"Overall movement quality averaged {avg:.0f} — nice work.")
    elif avg < 60:
        bad.append(f"Average score was {avg:.0f} — reduce speed and fix the top cues below.")

    best_ex = None
    best_avg = -1.0
    worst_ex = None
    worst_avg = 101.0
    for ex, pe in stats.per_exercise.items():
        n = int(pe["frames"])
        if n < 8:
            continue
        ex_avg = int(pe["score_sum"]) / n
        if ex_avg > best_avg:
            best_avg = ex_avg
            best_ex = ex
        if ex_avg < worst_avg:
            worst_avg = ex_avg
            worst_ex = ex

    if best_ex is not None:
        good.append(
            f"Strongest exercise: {pretty_exercise_name(best_ex)} (~{best_avg:.0f} avg over {int(stats.per_exercise[best_ex]['frames'])} frames)."
        )
    if worst_ex is not None and worst_avg < 72 and worst_ex != best_ex:
        bad.append(
            f"Needs attention: {pretty_exercise_name(worst_ex)} (~{worst_avg:.0f} avg) — check camera angle and cues."
        )

    global_errors: Counter = Counter()
    for pe in stats.per_exercise.values():
        global_errors.update(pe["errors"])
    for msg, cnt in global_errors.most_common(4):
        if cnt >= 2:
            bad.append(f"Repeated issue ({cnt}x): {msg}")

    total_reps = sum(final_reps.values())
    if total_reps > 0:
        good.append(f"Total reps counted: {total_reps}.")
        top_rep = max(final_reps.items(), key=lambda x: x[1])
        if top_rep[1] > 0:
            good.append(
                f"Most volume: {pretty_exercise_name(top_rep[0])} ({top_rep[1]} reps)."
            )

    if not good:
        good.append("Keep training — small improvements compound.")
    if not bad and good_pct < 88:
        bad.append("Polish the details — minor fixes can push your score higher.")

    return good, bad, headline


def _draw_text_block(
    img: np.ndarray,
    lines: List[str],
    x: int,
    y_start: int,
    color: Tuple[int, int, int],
    font_scale: float,
    line_height: int,
    max_width_px: int,
) -> int:
    """Draw wrapped lines; returns next y below block."""
    y = y_start
    approx_chars = max(20, int(max_width_px / (font_scale * 9)))
    for raw in lines:
        for wl in _wrap_text(raw, max_len=approx_chars):
            if y > img.shape[0] - 30:
                break
            cv2.putText(
                img,
                wl,
                (x, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                color,
                1,
                cv2.LINE_AA,
            )
            y += line_height
    return y


def run_session_summary_loop(
    stats: SessionTracker,
    final_reps: Dict[str, int],
    frame_shape: Tuple[int, ...],
) -> str:
    """
    Full-screen summary until user chooses an action.
    Returns: 'quit' | 'continue' | 'new_session'
    """
    good_lines, bad_lines, headline = build_session_insights(stats, final_reps)
    h, w = int(frame_shape[0]), int(frame_shape[1])
    footer = [
        "q: quit app",
        "c: continue session (same stats)",
        "r: new session (reset reps & stats)",
    ]

    while True:
        img = np.zeros((h, w, 3), dtype=np.uint8)
        cv2.putText(
            img,
            "Session summary",
            (40, 55),
            cv2.FONT_HERSHEY_DUPLEX,
            1.0,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        y = 100
        y = _draw_text_block(img, headline, 40, y, (200, 200, 200), 0.55, 24, w - 80)

        cv2.putText(
            img,
            "What you did well",
            (40, y + 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (80, 220, 80),
            2,
            cv2.LINE_AA,
        )
        y = _draw_text_block(img, good_lines, 50, y + 40, (180, 255, 180), 0.5, 22, w - 100)

        cv2.putText(
            img,
            "Focus next time",
            (40, y + 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (60, 120, 255),
            2,
            cv2.LINE_AA,
        )
        y = _draw_text_block(img, bad_lines, 50, y + 45, (180, 200, 255), 0.5, 22, w - 100)

        fy = h - 110
        for i, ft in enumerate(footer):
            cv2.putText(
                img,
                ft,
                (40, fy + i * 26),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                (255, 255, 200),
                1,
                cv2.LINE_AA,
            )

        cv2.imshow(WINDOW_TITLE, img)
        key_code = cv2.waitKey(0) & 0xFF
        if key_code == ord("q"):
            return "quit"
        if key_code == ord("c"):
            return "continue"
        if key_code == ord("r"):
            return "new_session"


def next_exercise(current_exercise: str) -> str:
    idx = EXERCISE_ORDER.index(current_exercise)
    return EXERCISE_ORDER[(idx + 1) % len(EXERCISE_ORDER)]


def previous_exercise(current_exercise: str) -> str:
    idx = EXERCISE_ORDER.index(current_exercise)
    return EXERCISE_ORDER[(idx - 1) % len(EXERCISE_ORDER)]


def pretty_exercise_name(exercise_key: str) -> str:
    return exercise_key.replace("_", " ").title()


def _wrap_text(text: str, max_len: int = 36):
    words = text.split()
    if not words:
        return [""]
    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_len:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _set_window_state_windows(title: str, state: str) -> None:
    """Set native window state on Windows: fullscreen, maximize, minimize, restore."""
    if sys.platform != "win32":
        return
    hwnd = ctypes.windll.user32.FindWindowW(None, title)
    if not hwnd:
        return
    if state == "maximize":
        ctypes.windll.user32.ShowWindow(hwnd, 3)
    elif state == "minimize":
        ctypes.windll.user32.ShowWindow(hwnd, 6)
    elif state == "restore":
        ctypes.windll.user32.ShowWindow(hwnd, 9)


def configure_window(fullscreen: bool) -> None:
    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    if fullscreen:
        cv2.setWindowProperty(WINDOW_TITLE, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)


def draw_overlay(
    frame,
    active_exercise: str,
    evaluation: Dict[str, object],
    reps: int,
    warmup_left: int,
) -> None:
    frame_h, frame_w = frame.shape[:2]
    panel_width = min(430, max(320, frame_w // 3))
    panel_x1 = frame_w - panel_width

    # Opaque black side panel for readable workout information.
    cv2.rectangle(frame, (panel_x1, 0), (frame_w, frame_h), (0, 0, 0), thickness=-1)

    lines = [
        f"Exercise: {evaluation['exercise_name']}",
        f"Key: {active_exercise}",
        f"Stage: {evaluation['stage']}",
        f"Status: {evaluation['status']}",
        f"Score: {evaluation['score']}",
        f"Reps: {reps}",
    ]

    if warmup_left > 0:
        lines.append(f"Warmup Frames Left: {warmup_left}")

    angles = evaluation.get("angles", {})
    if angles:
        lines.append("Angles:")
        for key, value in angles.items():
            lines.append(f"  - {key}: {value}")

    errors = evaluation.get("errors", [])
    if errors:
        lines.append("Errors:")
        for err in errors[:2]:
            lines.extend(_wrap_text(f"  - {err}"))
    else:
        lines.append("Errors: none")

    lines.append("Feedback:")
    lines.extend(_wrap_text(str(evaluation["feedback"])))
    lines.append("")
    lines.append("Exercises:")
    for idx, key in enumerate(EXERCISE_ORDER, start=1):
        hotkey = str(idx % 10)
        marker = ">" if key == active_exercise else " "
        lines.append(f"{marker} {hotkey}: {pretty_exercise_name(key)}")

    lines.append("")
    lines.append("Controls: 1-9/0 switch")
    lines.append("n: next  p: previous  e: end session")
    lines.append("q: quit  f: fullscreen  m: maximize")
    lines.append("r: restore  z: minimize")

    base_color = (0, 255, 0) if evaluation["status"] == "GOOD" else (0, 165, 255)
    y = 30
    for line in lines:
        cv2.putText(
            frame,
            line,
            (panel_x1 + 12, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            base_color if line.startswith("Status:") else (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        y += 21
        if y > frame_h - 10:
            break


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RepRight Phase 1 rule-based form analyzer")
    parser.add_argument(
        "--exercise",
        default="squat",
        choices=EXERCISE_ORDER,
        help="Active exercise profile.",
    )
    parser.add_argument("--camera-index", type=int, default=0, help="Webcam index.")
    parser.add_argument(
        "--camera-backend",
        default="auto",
        choices=["auto", "dshow", "msmf", "default"],
        help="Camera backend selection.",
    )
    parser.add_argument("--width", type=int, default=1280, help="Capture width.")
    parser.add_argument("--height", type=int, default=720, help="Capture height.")
    parser.add_argument(
        "--model-complexity",
        type=int,
        default=1,
        choices=[0, 1, 2],
        help="MediaPipe model complexity.",
    )
    parser.add_argument("--warmup-frames", type=int, default=5, help="Frames to skip before scoring.")
    parser.add_argument("--read-retries", type=int, default=3, help="Frame read retry attempts.")
    parser.add_argument("--no-draw-pose", action="store_true", help="Disable pose skeleton overlay.")
    parser.add_argument(
        "--windowed",
        action="store_true",
        help="Start in windowed mode instead of fullscreen.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    camera = CameraManager(
        CameraConfig(
            camera_index=args.camera_index,
            backend=args.camera_backend,
            width=args.width,
            height=args.height,
            read_retries=args.read_retries,
        )
    )
    pose = PoseDetector(
        PoseConfig(
            model_complexity=args.model_complexity,
            draw_pose=not args.no_draw_pose,
        )
    )
    checker = FormChecker()
    rep_counter = RepCounter()
    session = SessionTracker()
    active_exercise = args.exercise
    warmup_left = max(0, args.warmup_frames)
    is_fullscreen = not args.windowed

    camera.open()
    configure_window(fullscreen=is_fullscreen)
    print(
        f"Camera opened on index={args.camera_index}, backend={camera.backend_name}. "
        "Press q to exit, e for session summary."
    )

    try:
        while True:
            frame = camera.read()
            if frame is None:
                print("Warning: failed to read frame from camera.")
                continue

            pose_data = pose.process(frame)
            keypoints = pose_data["keypoints"]
            metrics = compute_joint_metrics(keypoints)

            if warmup_left > 0:
                warmup_left -= 1
                evaluation = {
                    "exercise_name": pretty_exercise_name(active_exercise),
                    "stage": "warmup",
                    "status": "GOOD",
                    "score": 100,
                    "errors": [],
                    "feedback": "Warming up pose tracking...",
                    "angles": {},
                }
            else:
                evaluation = checker.evaluate(active_exercise, metrics)
                session.record(active_exercise, evaluation)

            reps = rep_counter.update(active_exercise, str(evaluation["stage"]))
            pose.draw(frame, pose_data["pose_landmarks"])
            draw_overlay(frame, active_exercise, evaluation, reps, warmup_left)

            cv2.imshow(WINDOW_TITLE, frame)
            key_code = cv2.waitKey(1) & 0xFF

            if key_code == ord("e"):
                final_reps = {ex: rep_counter.get_count(ex) for ex in EXERCISE_ORDER}
                action = run_session_summary_loop(session, final_reps, frame.shape)
                if action == "quit":
                    break
                if action == "new_session":
                    session.reset()
                    rep_counter.reset()
                    warmup_left = max(0, args.warmup_frames)
                continue

            if key_code == ord("q"):
                break
            if key_code == ord("n"):
                active_exercise = next_exercise(active_exercise)
                print(f"Switched exercise: {active_exercise}")
                continue
            if key_code == ord("p"):
                active_exercise = previous_exercise(active_exercise)
                print(f"Switched exercise: {active_exercise}")
                continue
            if key_code == ord("f"):
                is_fullscreen = not is_fullscreen
                mode = cv2.WINDOW_FULLSCREEN if is_fullscreen else cv2.WINDOW_NORMAL
                cv2.setWindowProperty(WINDOW_TITLE, cv2.WND_PROP_FULLSCREEN, mode)
                if not is_fullscreen:
                    _set_window_state_windows(WINDOW_TITLE, "restore")
                continue
            if key_code == ord("m"):
                cv2.setWindowProperty(WINDOW_TITLE, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
                is_fullscreen = False
                _set_window_state_windows(WINDOW_TITLE, "maximize")
                continue
            if key_code == ord("r"):
                cv2.setWindowProperty(WINDOW_TITLE, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
                is_fullscreen = False
                _set_window_state_windows(WINDOW_TITLE, "restore")
                continue
            if key_code == ord("z"):
                cv2.setWindowProperty(WINDOW_TITLE, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
                is_fullscreen = False
                _set_window_state_windows(WINDOW_TITLE, "minimize")
                continue

            key_char = chr(key_code) if 0 <= key_code < 256 else ""
            if key_char in HOTKEY_TO_EXERCISE:
                active_exercise = HOTKEY_TO_EXERCISE[key_char]
                print(f"Switched exercise: {active_exercise}")

    finally:
        pose.close()
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

