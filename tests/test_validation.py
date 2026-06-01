from __future__ import annotations

import json
from pathlib import Path

from scripts.export_json import export_all, records_from_csv
from scripts.generate_sample_workout import build_workout
from scripts.validate_data import REQUIRED_COLUMNS, run_validation, validate_schema

ROOT = Path(__file__).resolve().parents[1]


def test_required_files_exist() -> None:
    required_files = [
        "data/source/exercises.csv",
        "data/source/protocols.csv",
        "data/source/rules.csv",
        "data/source/equipment.csv",
        "data/source/taxonomy.csv",
        "data/schemas/exercise.schema.json",
        "data/schemas/protocol.schema.json",
        "data/schemas/rule.schema.json",
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
    for export_name in ("exercises", "protocols", "rules"):
        records = json.loads((ROOT / "data" / "exports" / f"{export_name}.json").read_text(encoding="utf-8"))
        assert validate_schema(export_name, records) == []


def test_sample_workout_generation_returns_cards() -> None:
    export_all()
    workout = build_workout(equipment="bodyweight", time=10, protocol_id="amrap_10")
    assert workout["protocol"]["id"] == "amrap_10"
    assert len(workout["cards"]) >= 1
