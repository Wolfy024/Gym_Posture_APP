# RepRight Phase 1 Architecture

RepRight evaluates movement quality in a deterministic per-frame pipeline. It is designed to be easy to tune without retraining models.

## Runtime pipeline

1. `camera.py` captures a frame from webcam (`auto`/`dshow`/`msmf`/`default` backend).
2. `pose_detector.py` runs MediaPipe Pose and returns 33 normalized landmarks.
3. `geometry.py` converts landmarks into joint/shape metrics:
   - `left_*` and `right_*` elbow, hip, knee angles
   - `spine_angle`
   - torso angle by side (`left_torso_angle`, `right_torso_angle`)
4. `form_checker.py` selects exercise-specific rules from `exercise_rules.py` and computes:
   - stage (e.g., `down`, `up`, `hold`)
   - list of form errors
   - score (0-100)
   - single feedback cue
5. `rep_counter.py` advances stage sequences and increments reps for cyclic exercises.
6. `main.py` draws overlays and handles controls (`1-9`, `0`, `n`, `q`).

## Key metric map

- **Elbow angle:** shoulder-elbow-wrist (used in push-up, shoulder press, bicep curl)
- **Hip angle:** shoulder-hip-knee (used in deadlift, plank, sit-up, burpee, mountain climber)
- **Knee angle:** hip-knee-ankle (used in squat, lunge, deadlift, burpee)
- **Spine angle:** shoulder-center to hip-center against vertical (posture quality)
- **Torso angle:** side shoulder-to-hip against vertical (body-line quality in side view)

## Rule configuration model

Each exercise in `exercise_rules.py` includes:

- `display_name`
- `camera_angle` (`front` or `side`)
- `stage_ranges`: list of threshold windows used for stage detection
- `checks`: constraint rules with `min`, `max`, `penalty`, and feedback message
- `rep_sequence`: ordered stage list used by `RepCounter` (`None` for static hold exercises)
- `primary_angles`: curated metrics shown in the frame overlay

Thresholds are tunable defaults intended for iterative calibration based on lighting, camera placement, and athlete proportions.

## Rep counting behavior

- Counter is exercise-local and persists when switching profiles.
- Reps are counted only when the configured stage sequence is completed in order.
- `plank` has no rep sequence and is treated as hold quality feedback.
- `burpee` and `mountain_climber` use simplified two-stage counting for Phase 1.

## Extension path to web

The pipeline is backend-agnostic. To move to web streaming:

1. Read frames from browser (WebRTC/WebSocket).
2. Feed frame through existing `PoseDetector -> geometry -> FormChecker`.
3. Return JSON `{stage, status, score, errors, feedback, reps}` to frontend.
4. Render browser overlays with the same data contract.
