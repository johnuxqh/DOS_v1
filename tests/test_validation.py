from __future__ import annotations

import json
from pathlib import Path

from scripts.export_json import export_all, records_from_csv
from scripts.generate_sample_workout import build_workout
from scripts.validate_data import (
    REQUIRED_COLUMNS,
    validate_enums,
    validate_ids,
    validate_schema,
    validate_workout_template_business_rules,
    run_validation,
)

ROOT = Path(__file__).resolve().parents[1]


def test_required_files_exist() -> None:
    required_files = [
        "data/source/exercises.csv",
        "data/source/protocols.csv",
        "data/source/rules.csv",
        "data/source/equipment.csv",
        "data/source/taxonomy.csv",
"data/source/workout_templates.csv",
"data/schemas/exercise.schema.json",
"data/schemas/protocol.schema.json",
"data/schemas/rule.schema.json",
"data/schemas/workout_template.schema.json",
    ]
    for file_path in required_files:
        assert (ROOT / file_path).exists(), file_path


def test_csv_files_load_with_required_columns() -> None:
    for name, columns in REQUIRED_COLUMNS.items():
        records = records_from_csv(name) if name in {"exercises", "protocols", "rules"} else None
        if records is not None:
            assert records
        source_text = (ROOT / "data" / "source" / f"{name}.csv").read_text(encoding="utf-8")
        header = source_text.splitlines()[0].split(",")
        for column in columns:
            assert column in header


def test_validation_passes() -> None:
    assert run_validation() == []


def test_export_json_creates_json_files() -> None:
    outputs = export_all()
    for output in outputs:
        assert output.exists()
        data = json.loads(output.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert data


def test_generated_json_is_schema_valid() -> None:
    export_all()
for export_name in ("exercises", "protocols", "rules", "workout_templates"):
        records = json.loads((ROOT / "data" / "exports" / f"{export_name}.json").read_text(encoding="utf-8"))
        assert validate_schema(export_name, records) == []


def test_workout_templates_are_valid() -> None:
    templates = records_from_csv("workout_templates")
    assert templates
    assert validate_schema("workout_templates", templates) == []


def test_invalid_workout_template_deck_reference_is_reported() -> None:
    template = records_from_csv("workout_templates")[0] | {"deck_id": "missing_deck"}
    errors = validate_workout_template_business_rules([template], {"free_bodyweight"})
    assert any("references unknown deck_id" in error for error in errors)


def test_invalid_workout_template_protocol_type_is_reported() -> None:
    row = {"template_id": "bad_protocol", "protocol_type": "randomizer"}
    errors = validate_enums("workout_templates", [row])
    assert any("protocol_type" in error for error in errors)


def test_duplicate_workout_template_id_is_reported() -> None:
    rows = [{"template_id": "duplicate_template"}, {"template_id": "duplicate_template"}]
    errors = validate_ids("workout_templates", rows)
    assert any("duplicate template_id" in error for error in errors)


def test_sample_workout_generation_returns_cards() -> None:
    export_all()
    workout = build_workout(equipment="bodyweight", time=10, protocol_id="amrap_10")
    assert workout["protocol"]["id"] == "amrap_10"
    assert len(workout["cards"]) >= 1


def test_sample_workout_generation_uses_template() -> None:
    export_all()
    workout = build_workout(equipment=None, template_id="beginner_full_body")
    assert workout["template"]["template_id"] == "beginner_full_body"
    assert workout["protocol"]["id"] == "beginner_full_body"
    assert len(workout["cards"]) >= 1
