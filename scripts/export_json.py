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
}
BOOL_FIELDS = {
    "exercises": {"beginner_safe"},
    "protocols": {"allows_plyometrics", "requires_timer"},
    "workout_templates": {"tracking_enabled"},
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
    sort_key = "template_id" if name == "workout_templates" else "id"
    return sorted(records, key=lambda item: item[sort_key])


def write_json(name: str, records: list[dict[str, Any]]) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EXPORT_DIR / f"{name}.json"
    output_path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def export_all() -> list[Path]:
    outputs = []
    for name in ("exercises", "protocols", "rules", "workout_templates"):
        outputs.append(write_json(name, records_from_csv(name)))
    return outputs


def main() -> None:
    for path in export_all():
        print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
