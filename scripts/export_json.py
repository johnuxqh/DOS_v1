#!/usr/bin/env python3
"""Export Deck of Sweat source CSV files to JSON."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "source"
EXPORT_DIR = ROOT / "data" / "exports"

ARRAY_FIELDS = {
    "exercises": {
        "equipment",
        "secondary_categories",
        "athlete_suitability",
        "protocol_suitability",
        "coaching_cues",
        "safety_notes",
        "contraindications",
    },
    "workout_templates": {
        "equipment_required",
        "movement_focus",
        "coaching_notes",
        "safety_notes",
    },
    "exercise_selection_rules": {
        "allowed_movement_patterns",
        "excluded_movement_patterns",
        "required_equipment",
        "excluded_equipment",
        "include_tags",
        "exclude_tags",
    },
    "workout_composition_rules": {
        "allowed_movement_patterns",
        "allowed_primary_categories",
        "preferred_equipment",
    },
}
BOOL_FIELDS = {
    "exercises": {"beginner_safe"},
    "protocols": {"allows_plyometrics", "requires_timer"},
    "workout_templates": {"tracking_enabled"},
    "exercise_selection_rules": {"active", "allow_progressions", "allow_regressions"},
    "workout_composition_rules": {"active", "fallback_allowed"},
    "exercise_progressions": {"active"},
}
INT_FIELDS = {
    "exercises": {
        "difficulty_level",
        "default_time_seconds",
        "default_sets",
        "strength_score",
        "mobility_score",
        "stability_score",
        "power_score",
        "conditioning_score",
    },
    "protocols": {
        "time_minutes",
        "cards_to_draw",
        "recommended_difficulty_min",
        "recommended_difficulty_max",
        "max_plyometric_cards",
    },
    "workout_templates": {
        "duration_minutes",
        "rounds",
        "work_seconds",
        "rest_seconds",
    },
    "exercise_selection_rules": {
        "priority",
        "min_difficulty",
        "max_difficulty",
        "max_repeats_per_workout",
    },
    "workout_composition_rules": {
        "slot_order",
        "min_difficulty",
        "max_difficulty",
        "priority",
    },
    "exercise_progressions": {"difficulty_delta"},
}


def split_pipe(value: Any) -> list[str]:
    if value is None or str(value).strip() == "":
        return []
    return [part.strip() for part in str(value).split("|") if part.strip()]


def parse_bool(value: Any) -> bool:
    text = str(value).strip().upper()
    if text == "TRUE":
        return True
    if text == "FALSE":
        return False
    raise ValueError(f"Expected TRUE/FALSE, got {value!r}")


def parse_int(value: Any) -> int:
    if value is None or str(value).strip() == "":
        return 0
    return int(value)


def clean_scalar(value: Any) -> Any:
    if value is None:
        return ""
    return value


def load_csv_rows(name: str) -> list[dict[str, str]]:
    with (SOURCE_DIR / f"{name}.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def records_from_csv(name: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in load_csv_rows(name):
        record: dict[str, Any] = {}
        for key, value in row.items():
            if key in ARRAY_FIELDS.get(name, set()):
                record[key] = split_pipe(value)
            elif key in BOOL_FIELDS.get(name, set()):
                record[key] = parse_bool(value)
            elif key in INT_FIELDS.get(name, set()):
                record[key] = parse_int(value)
            else:
                record[key] = clean_scalar(value)
        records.append(record)
    if name == "workout_composition_rules":
        return sorted(records, key=lambda item: (item["composition_id"], item["slot_order"]))
    sort_keys = {"workout_templates": "template_id", "exercise_selection_rules": "rule_id", "exercise_progressions": "progression_id"}
    sort_key = sort_keys.get(name, "id")
    return sorted(records, key=lambda item: item[sort_key])


def write_json(name: str, records: list[dict[str, Any]]) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EXPORT_DIR / f"{name}.json"
    output_path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def export_all() -> list[Path]:
    outputs = []
    for name in ("exercises", "protocols", "rules", "workout_templates", "exercise_selection_rules", "workout_composition_rules", "exercise_progressions"):
        outputs.append(write_json(name, records_from_csv(name)))
    return outputs


def main() -> None:
    for path in export_all():
        print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
