#!/usr/bin/env python3
"""Generate a simple readable Deck of Sweat sample workout."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_json import records_from_csv
EXPORT_DIR = ROOT / "data" / "exports"


def load_records(name: str) -> list[dict[str, Any]]:
    export_path = EXPORT_DIR / f"{name}.json"
    if export_path.exists():
        return json.loads(export_path.read_text(encoding="utf-8"))
    return records_from_csv(name)


def equipment_matches(exercise: dict[str, Any], requested: str | list[str]) -> bool:
    requested_items = [requested] if isinstance(requested, str) else requested
    equipment = set(exercise.get("equipment", []))
    if "bodyweight" in requested_items and "bodyweight" in equipment:
        return True
    return "bodyweight" in equipment or any(item in equipment for item in requested_items)


def select_protocol(protocols: list[dict[str, Any]], time: int | None, protocol_id: str | None) -> dict[str, Any]:
    candidates = [protocol for protocol in protocols if protocol.get("status") == "active"]
    if protocol_id:
        candidates = [protocol for protocol in candidates if protocol["id"] == protocol_id]
    if time:
        candidates = [protocol for protocol in candidates if protocol["time_minutes"] == time]
    if not candidates:
        raise ValueError("No active protocol matched the requested filters.")
    return sorted(candidates, key=lambda item: item["id"])[0]


def select_template(templates: list[dict[str, Any]], template_id: str) -> dict[str, Any]:
    matches = [template for template in templates if template["template_id"] == template_id]
    if not matches:
        raise ValueError(f"No workout template matched '{template_id}'.")
    return matches[0]


def protocol_from_template(template: dict[str, Any]) -> dict[str, Any]:
    card_count = min(6, max(4, len(template.get("movement_focus", [])) + 1))
    return {
        "id": template["template_id"],
        "display_name": template["template_name"],
        "time_minutes": template["duration_minutes"],
        "cards_to_draw": card_count,
        "instructions_short": f"{template['protocol_type'].replace('_', ' ').upper()} template: {template['description']}",
    }


def exercise_matches_focus(exercise: dict[str, Any], movement_focus: list[str] | None) -> bool:
    if not movement_focus:
        return True
    categories = {exercise.get("primary_category", ""), *exercise.get("secondary_categories", [])}
    return bool(categories.intersection(movement_focus)) or exercise.get("movement_pattern") in movement_focus


def select_exercises(
    exercises: list[dict[str, Any]],
    equipment: str | list[str],
    count: int,
    movement_focus: list[str] | None = None,
) -> list[dict[str, Any]]:
    equipment_candidates = [
        exercise
        for exercise in exercises
        if exercise.get("status") == "active" and equipment_matches(exercise, equipment)
    ]
    candidates = [exercise for exercise in equipment_candidates if exercise_matches_focus(exercise, movement_focus)]
    if len(candidates) < count:
        candidates.extend(exercise for exercise in equipment_candidates if exercise not in candidates)
    if not candidates:
        raise ValueError(f"No active exercises matched equipment '{equipment}'.")

    selected: list[dict[str, Any]] = []
    used_patterns: set[str] = set()
    for exercise in sorted(candidates, key=lambda item: (item["difficulty_level"], item["id"])):
        if exercise["movement_pattern"] in used_patterns:
            continue
        selected.append(exercise)
        used_patterns.add(exercise["movement_pattern"])
        if len(selected) == count:
            return selected

    for exercise in sorted(candidates, key=lambda item: item["id"]):
        if exercise not in selected:
            selected.append(exercise)
        if len(selected) == count:
            return selected
    return selected


def card_prescription(exercise: dict[str, Any]) -> str:
    if exercise.get("default_reps") and exercise["default_reps"] != "0":
        return str(exercise["default_reps"])
    seconds = exercise.get("default_time_seconds", 0)
    if seconds:
        return f"{seconds} sec"
    return "quality reps"


def build_workout(
    equipment: str | None = "bodyweight",
    time: int | None = 10,
    protocol_id: str | None = None,
    template_id: str | None = None,
) -> dict[str, Any]:
    exercises = load_records("exercises")
    template = None
    movement_focus = None

    if template_id:
        template = select_template(load_records("workout_templates"), template_id)
        protocol = protocol_from_template(template)
        equipment_filter: str | list[str] = equipment or template["equipment_required"]
        movement_focus = template.get("movement_focus", [])
    else:
        protocols = load_records("protocols")
        protocol = select_protocol(protocols, time, protocol_id)
        equipment_filter = equipment or "bodyweight"

    cards = select_exercises(exercises, equipment_filter, protocol["cards_to_draw"], movement_focus)
    if not cards:
        raise ValueError("Could not select any cards for the sample workout.")
    return {"protocol": protocol, "cards": cards, "equipment": equipment_filter, "template": template}


def format_workout(workout: dict[str, Any]) -> str:
    protocol = workout["protocol"]
    lines = [
        "DECK OF SWEAT SAMPLE WORKOUT",
        f"Time: {protocol['time_minutes']} minutes",
        f"Protocol: {protocol['display_name']}",
        *( [f"Template: {workout['template']['template_id']} ({workout['template']['tier']})"] if workout.get("template") else [] ),
        f"Equipment: {workout['equipment']}",
        f"Instructions: {protocol['instructions_short']}",
        "",
        "Cards:",
    ]
    for index, exercise in enumerate(workout["cards"], start=1):
        lines.append(f"{index}. {exercise['display_name']} — {card_prescription(exercise)}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Deck of Sweat sample workout.")
parser.add_argument("--equipment", help="Requested equipment id, e.g. bodyweight or dumbbell.")
parser.add_argument("--time", type=int, default=10, choices=[5, 10, 15], help="Workout duration in minutes.")
parser.add_argument("--protocol", dest="protocol_id", help="Specific protocol id, e.g. amrap_10.")
parser.add_argument("--template", dest="template_id", help="Workout template id, e.g. beginner_full_body or emom_12.")
return parser.parse_args()


def main() -> None:
    args = parse_args()
print(format_workout(build_workout(args.equipment, args.time, args.protocol_id, args.template_id)))


if __name__ == "__main__":
    main()
