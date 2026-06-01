#!/usr/bin/env python3
"""Validate Deck of Sweat CSV data, schemas, and business rules."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import csv
import re
from dataclasses import dataclass

try:
    from jsonschema import Draft202012Validator as JsonSchemaValidator
except ModuleNotFoundError:  # pragma: no cover - CI installs jsonschema; local fallback keeps validation runnable.
    JsonSchemaValidator = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_json import records_from_csv
SOURCE_DIR = ROOT / "data" / "source"
SCHEMA_DIR = ROOT / "data" / "schemas"

REQUIRED_COLUMNS = {
    "exercises": [
        "id", "name", "display_name", "equipment", "equipment_group", "movement_pattern", "primary_category",
        "secondary_categories", "difficulty_level", "intensity_level", "impact_level", "space_required", "skill_level",
        "beginner_safe", "athlete_suitability", "protocol_suitability", "default_reps", "default_time_seconds",
        "default_sets", "regression", "progression", "coaching_cues", "safety_notes", "contraindications",
        "strength_score", "mobility_score", "stability_score", "power_score", "conditioning_score", "card_text_short",
        "card_text_long", "status", "version", "review_status", "last_reviewed",
    ],
    "protocols": [
        "id", "name", "display_name", "time_minutes", "protocol_family", "cards_to_draw", "work_structure",
        "rest_structure", "scoring_method", "intensity_target", "recommended_difficulty_min", "recommended_difficulty_max",
        "allows_plyometrics", "max_plyometric_cards", "requires_timer", "instructions_short", "instructions_long",
        "science_rationale", "safety_notes", "status", "version", "review_status", "last_reviewed",
    ],
    "rules": ["id", "rule_type", "name", "description", "applies_to", "value", "severity", "status"],
    "equipment": ["id", "name", "equipment_group", "description", "portable", "status"],
    "taxonomy": ["type", "id", "name", "description", "status"],
}

ENUMS = {
    "exercises": {
        "beginner_safe": {"TRUE", "FALSE"},
        "status": {"draft", "active", "retired"},
        "review_status": {"needs_review", "reviewed", "evidence_checked"},
        "impact_level": {"low", "moderate", "high"},
    },
    "protocols": {
        "time_minutes": {"5", "10", "15"},
        "allows_plyometrics": {"TRUE", "FALSE"},
        "requires_timer": {"TRUE", "FALSE"},
        "status": {"draft", "active", "retired"},
        "review_status": {"needs_review", "reviewed", "evidence_checked"},
    },
    "rules": {"severity": {"warning", "error"}, "status": {"draft", "active", "retired"}},
}

RANGES = {
    "exercises": {
        "difficulty_level": (1, 5),
        "strength_score": (0, 5),
        "mobility_score": (0, 5),
        "stability_score": (0, 5),
        "power_score": (0, 5),
        "conditioning_score": (0, 5),
    },
    "protocols": {
        "cards_to_draw": (1, 99),
        "recommended_difficulty_min": (1, 5),
        "recommended_difficulty_max": (1, 5),
        "max_plyometric_cards": (0, 99),
    },
}


def load_rows(name: str) -> list[dict[str, str]]:
    path = SOURCE_DIR / f"{name}.csv"
    if not path.exists():
        raise ValueError(f"Missing required file: {path.relative_to(ROOT)}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fieldnames(name: str) -> list[str]:
    path = SOURCE_DIR / f"{name}.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        return next(reader)


def validate_required_columns(name: str, columns: list[str]) -> list[str]:
    missing = [column for column in REQUIRED_COLUMNS[name] if column not in columns]
    return [f"{name}: missing required column '{column}'" for column in missing]


def validate_ids(name: str, rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for row in rows:
        item = row.get("id", "")
        unique_key = f"{row.get('type', '')}:{item}" if name == "taxonomy" else item
        if unique_key in seen:
            errors.append(f"{name}: duplicate id '{item}'")
        seen.add(unique_key)
        if not re.match(r"^[a-z][a-z0-9_]*$", item):
            errors.append(f"{name}: id '{item}' must be lowercase snake_case")
    return errors


def validate_enums(name: str, rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for column, allowed in ENUMS.get(name, {}).items():
        bad_values = sorted({row.get(column, "") for row in rows if row.get(column, "") not in allowed})
        errors.extend(f"{name}: column '{column}' has invalid value '{value}'" for value in bad_values)
    return errors


def validate_ranges(name: str, rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for column, (minimum, maximum) in RANGES.get(name, {}).items():
        for index, row in enumerate(rows):
            value = row.get(column, "")
            try:
                numeric = int(value)
            except ValueError:
                errors.append(f"{name}: row {index + 2} column '{column}' must be an integer")
                continue
            if numeric < minimum or numeric > maximum:
                errors.append(f"{name}: row {index + 2} column '{column}' must be between {minimum} and {maximum}")
    return errors


@dataclass
class SimpleSchemaError:
    path: list[str]
    message: str


class SimpleSchemaValidator:
    """Small fallback for the schema subset used by this repository."""

    def __init__(self, schema: dict[str, Any]) -> None:
        self.schema = schema

    def iter_errors(self, record: dict[str, Any]) -> list[SimpleSchemaError]:
        errors: list[SimpleSchemaError] = []
        for field in self.schema.get("required", []):
            if field not in record:
                errors.append(SimpleSchemaError([], f"'{field}' is a required property"))
        for field, rules in self.schema.get("properties", {}).items():
            if field not in record:
                continue
            value = record[field]
            expected_type = rules.get("type")
            if expected_type and not self._type_matches(value, expected_type):
                errors.append(SimpleSchemaError([field], f"{value!r} is not of type '{expected_type}'"))
                continue
            if "enum" in rules and value not in rules["enum"]:
                errors.append(SimpleSchemaError([field], f"{value!r} is not one of {rules['enum']}"))
            if "minimum" in rules and isinstance(value, int) and value < rules["minimum"]:
                errors.append(SimpleSchemaError([field], f"{value!r} is less than the minimum of {rules['minimum']}"))
            if "maximum" in rules and isinstance(value, int) and value > rules["maximum"]:
                errors.append(SimpleSchemaError([field], f"{value!r} is greater than the maximum of {rules['maximum']}"))
            if "pattern" in rules and isinstance(value, str) and not re.match(rules["pattern"], value):
                errors.append(SimpleSchemaError([field], f"{value!r} does not match '{rules['pattern']}'"))
            if "minLength" in rules and isinstance(value, str) and len(value) < rules["minLength"]:
                errors.append(SimpleSchemaError([field], f"{value!r} is too short"))
            if "minItems" in rules and isinstance(value, list) and len(value) < rules["minItems"]:
                errors.append(SimpleSchemaError([field], f"{value!r} is too short"))
        return errors

    @staticmethod
    def _type_matches(value: Any, expected_type: str) -> bool:
        if expected_type == "object":
            return isinstance(value, dict)
        if expected_type == "array":
            return isinstance(value, list)
        if expected_type == "string":
            return isinstance(value, str)
        if expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected_type == "boolean":
            return isinstance(value, bool)
        return True


def validate_schema(name: str, records: list[dict[str, Any]]) -> list[str]:
    schema_path = SCHEMA_DIR / f"{name[:-1] if name.endswith('s') else name}.schema.json"
    if name == "exercises":
        schema_path = SCHEMA_DIR / "exercise.schema.json"
    if name == "protocols":
        schema_path = SCHEMA_DIR / "protocol.schema.json"
    if name == "rules":
        schema_path = SCHEMA_DIR / "rule.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = JsonSchemaValidator(schema) if JsonSchemaValidator else SimpleSchemaValidator(schema)
    errors: list[str] = []
    for record in records:
        for error in sorted(validator.iter_errors(record), key=str):
            path = ".".join(str(part) for part in error.path) or "<root>"
            errors.append(f"{name}: id '{record.get('id', '<missing>')}' schema error at {path}: {error.message}")
    return errors

def validate_exercise_business_rules(records: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for record in records:
        if record["status"] != "active":
            continue
        rid = record["id"]
        if not record.get("regression") or not record.get("progression"):
            errors.append(f"exercises: active exercise '{rid}' must have regression and progression")
        if not record.get("coaching_cues"):
            errors.append(f"exercises: active exercise '{rid}' must have at least one coaching cue")
        if not record.get("protocol_suitability"):
            errors.append(f"exercises: active exercise '{rid}' must have protocol_suitability")
        if record.get("beginner_safe") is True and record.get("difficulty_level", 0) > 3:
            errors.append(f"exercises: beginner_safe exercise '{rid}' must have difficulty_level <= 3")
        if record.get("beginner_safe") is True and record.get("impact_level") == "high":
            errors.append(f"exercises: high impact exercise '{rid}' cannot be beginner_safe TRUE")
    return errors


def validate_protocol_business_rules(records: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    max_cards = {5: 4, 10: 6, 15: 8}
    for record in records:
        rid = record["id"]
        if record["cards_to_draw"] > max_cards[record["time_minutes"]]:
            errors.append(f"protocols: '{rid}' draws too many cards for {record['time_minutes']} minutes")
        if record["allows_plyometrics"] is False and record["max_plyometric_cards"] != 0:
            errors.append(f"protocols: '{rid}' disallows plyometrics but max_plyometric_cards is not 0")
        if record["status"] == "active" and (not record.get("instructions_short") or not record.get("instructions_long")):
            errors.append(f"protocols: active protocol '{rid}' must have short and long instructions")
    return errors


def run_validation() -> list[str]:
    errors: list[str] = []
    for name in REQUIRED_COLUMNS:
        try:
            rows = load_rows(name)
            columns = fieldnames(name)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        errors.extend(validate_required_columns(name, columns))
        errors.extend(validate_ids(name, rows))
        errors.extend(validate_enums(name, rows))
        errors.extend(validate_ranges(name, rows))

    for name in ("exercises", "protocols", "rules"):
        try:
            records = records_from_csv(name)
        except Exception as exc:  # noqa: BLE001 - validation should report conversion failures clearly.
            errors.append(f"{name}: failed to convert CSV to JSON objects: {exc}")
            continue
        errors.extend(validate_schema(name, records))
        if name == "exercises":
            errors.extend(validate_exercise_business_rules(records))
        if name == "protocols":
            errors.extend(validate_protocol_business_rules(records))
    return errors


def main() -> int:
    errors = run_validation()
    if errors:
        print("FAIL: Deck of Sweat data validation failed")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: Deck of Sweat data validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
