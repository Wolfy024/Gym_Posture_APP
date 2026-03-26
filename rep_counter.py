from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from exercise_rules import EXERCISE_RULES


@dataclass
class RepState:
    count: int = 0
    progress_index: int = 0
    last_stage: str = "unknown"


class RepCounter:
    """Counts repetitions using exercise-specific stage sequences."""

    def __init__(self) -> None:
        self._states: Dict[str, RepState] = {}

    def _state(self, exercise: str) -> RepState:
        if exercise not in self._states:
            self._states[exercise] = RepState()
        return self._states[exercise]

    def reset(self, exercise: Optional[str] = None) -> None:
        if exercise is None:
            self._states.clear()
            return
        self._states[exercise] = RepState()

    def update(self, exercise: str, stage: str) -> int:
        state = self._state(exercise)
        sequence: Optional[List[str]] = EXERCISE_RULES[exercise].get("rep_sequence")
        if not sequence:
            state.last_stage = stage
            return state.count

        if stage == state.last_stage or stage == "unknown":
            return state.count

        if stage == sequence[0]:
            state.progress_index = 1
        elif state.progress_index > 0 and state.progress_index < len(sequence) and stage == sequence[state.progress_index]:
            state.progress_index += 1
            if state.progress_index == len(sequence):
                state.count += 1
                state.progress_index = 0
        else:
            state.progress_index = 0

        state.last_stage = stage
        return state.count

    def get_count(self, exercise: str) -> int:
        return self._state(exercise).count

