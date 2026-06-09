#!/usr/bin/env python3
"""Deterministic, data-first helpers for adapting workouts from local history."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_workout_history(path: str | Path | None) -> list[dict[str, Any]]:
    """Load session records, returning no history when the optional file is unavailable."""
    if not path:
        return []
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return [session for session in data if isinstance(session, dict)]
    if isinstance(data, dict):
        sessions = data.get("sessions", [])
        return [session for session in sessions if isinstance(session, dict)] if isinstance(sessions, list) else []
    return []


def _completed_sessions(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sessions = [session for session in history if session.get("session_status") in {"completed", "partial"}]
    return sorted(sessions, key=lambda session: session.get("completed_at") or session.get("generated_at") or "", reverse=True)


def _exercise_records(history: list[dict[str, Any]], exercise_id: str) -> list[dict[str, Any]]:
    return [
        record
        for session in _completed_sessions(history)
        for record in session.get("completed_exercises", [])
        if record.get("exercise_id") == exercise_id
    ]


def recent_exercise_ids(history: list[dict[str, Any]], lookback_sessions: int = 3) -> set[str]:
    """Return unique exercise IDs from the most recent completed or partial sessions."""
    return {
        record["exercise_id"]
        for session in _completed_sessions(history)[:max(0, lookback_sessions)]
        for record in session.get("completed_exercises", [])
        if record.get("exercise_id")
    }


def exercise_completion_rate(history: list[dict[str, Any]], exercise_id: str) -> float:
    """Return the share of recorded attempts marked completed, or 0.0 with no attempts."""
    records = _exercise_records(history, exercise_id)
    if not records:
        return 0.0
    return sum(record.get("completion_status") == "completed" for record in records) / len(records)


def exercise_average_effort(history: list[dict[str, Any]], exercise_id: str) -> float | None:
    """Return mean perceived effort for attempts that contain a numeric effort value."""
    efforts = [record["perceived_effort"] for record in _exercise_records(history, exercise_id) if isinstance(record.get("perceived_effort"), (int, float))]
    return sum(efforts) / len(efforts) if efforts else None


def should_avoid_exercise(history: list[dict[str, Any]], exercise_id: str, lookback_sessions: int = 3) -> bool:
    return exercise_id in recent_exercise_ids(history, lookback_sessions)


def should_suggest_progression(history: list[dict[str, Any]], exercise_id: str) -> bool:
    records = _exercise_records(history, exercise_id)
    effort = exercise_average_effort(history, exercise_id)
    return (
        len(records) >= 3
        and exercise_completion_rate(history, exercise_id) >= 0.8
        and effort is not None
        and effort <= 6
        and not any(record.get("pain_flag", False) for record in records)
    )


def should_suggest_regression(history: list[dict[str, Any]], exercise_id: str) -> bool:
    records = _exercise_records(history, exercise_id)
    if not records:
        return False
    effort = exercise_average_effort(history, exercise_id)
    return (
        any(record.get("pain_flag", False) for record in records)
        or exercise_completion_rate(history, exercise_id) < 0.6
        or (effort is not None and effort >= 9)
    )
