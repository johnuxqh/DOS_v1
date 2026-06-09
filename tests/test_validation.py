from __future__ import annotations

import json
from pathlib import Path

from scripts.export_json import export_all, records_from_csv
from scripts.generate_sample_workout import (
    apply_selection_rules,
    build_workout,
    compose_workout,
    format_workout,
    get_progressions,
    get_regressions,
)
from scripts.validate_data import (
    REQUIRED_COLUMNS,
    validate_enums,
    validate_ids,
    validate_schema,
    validate_workout_template_business_rules,
    validate_exercise_selection_rule_business_rules,
    validate_workout_composition_rule_business_rules,
    validate_exercise_progression_business_rules,
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
        "data/source/exercise_selection_rules.csv",
        "data/source/workout_composition_rules.csv",
        "data/source/exercise_progressions.csv",
        "data/schemas/exercise.schema.json",
        "data/schemas/protocol.schema.json",
        "data/schemas/rule.schema.json",
        "data/schemas/workout_template.schema.json",
        "data/schemas/exercise_selection_rule.schema.json",
        "data/schemas/workout_composition_rule.schema.json",
        "data/schemas/exercise_progression.schema.json",
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
    for export_name in ("exercises", "protocols", "rules", "workout_templates", "exercise_selection_rules", "workout_composition_rules", "exercise_progressions"):
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


def test_exercise_selection_rules_are_valid() -> None:
    selection_rules = records_from_csv("exercise_selection_rules")
    assert selection_rules
    assert validate_schema("exercise_selection_rules", selection_rules) == []


def test_invalid_exercise_selection_rule_template_reference_is_reported() -> None:
    rule = records_from_csv("exercise_selection_rules")[0] | {"applies_to_template_id": "missing_template"}
    template_ids = {template["template_id"] for template in records_from_csv("workout_templates")}
    deck_ids = {"free_beginner"}
    errors = validate_exercise_selection_rule_business_rules([rule], template_ids, deck_ids)
    assert any("unknown template_id" in error for error in errors)


def test_invalid_exercise_selection_rule_deck_reference_is_reported() -> None:
    rule = records_from_csv("exercise_selection_rules")[0] | {"applies_to_deck_id": "missing_deck"}
    template_ids = {"beginner_full_body"}
    deck_ids = {"free_beginner"}
    errors = validate_exercise_selection_rule_business_rules([rule], template_ids, deck_ids)
    assert any("unknown deck_id" in error for error in errors)


def test_exercise_selection_rules_filter_difficulty() -> None:
    exercises = records_from_csv("exercises")
    rule = {"rule_id": "max_easy", "active": True, "priority": 1, "applies_to_template_id": "beginner_full_body", "max_difficulty": 1}
    filtered = apply_selection_rules(exercises, [rule], template_id="beginner_full_body")
    assert filtered
    assert all(exercise["difficulty_level"] <= 1 for exercise in filtered)


def test_exercise_selection_rules_filter_equipment() -> None:
    exercises = records_from_csv("exercises")
    rule = {"rule_id": "bands_only", "active": True, "priority": 1, "applies_to_template_id": "beginner_full_body", "required_equipment": ["resistance_band"]}
    filtered = apply_selection_rules(exercises, [rule], template_id="beginner_full_body")
    assert filtered
    assert all("resistance_band" in exercise["equipment"] for exercise in filtered)


def test_exercise_selection_rules_apply_exclusions() -> None:
    exercises = records_from_csv("exercises")
    rule = {"rule_id": "no_squat", "active": True, "priority": 1, "applies_to_template_id": "beginner_full_body", "excluded_movement_patterns": ["squat"]}
    filtered = apply_selection_rules(exercises, [rule], template_id="beginner_full_body")
    assert filtered
    assert all(exercise["movement_pattern"] != "squat" for exercise in filtered)


def test_exercise_selection_rules_fallback_when_no_rule_matches() -> None:
    exercises = records_from_csv("exercises")
    filtered = apply_selection_rules(exercises, [], template_id="beginner_full_body")
    assert filtered == exercises


def test_workout_composition_rules_are_valid() -> None:
    composition_rules = records_from_csv("workout_composition_rules")
    assert composition_rules
    assert validate_schema("workout_composition_rules", composition_rules) == []


def test_invalid_workout_composition_template_reference_is_reported() -> None:
    rule = records_from_csv("workout_composition_rules")[0] | {"applies_to_template_id": "missing_template"}
    errors = validate_workout_composition_rule_business_rules([rule], {"beginner_full_body"})
    assert any("unknown template_id" in error for error in errors)


def test_invalid_workout_composition_difficulty_range_is_reported() -> None:
    rule = records_from_csv("workout_composition_rules")[0] | {"min_difficulty": 4, "max_difficulty": 2}
    errors = validate_workout_composition_rule_business_rules([rule], {"beginner_full_body"})
    assert any("min_difficulty cannot exceed max_difficulty" in error for error in errors)


def test_template_generator_fills_expected_composition_slots() -> None:
    export_all()
    workout = build_workout(equipment=None, template_id="beginner_full_body")
    assert len(workout["composition_slots"]) == 5
    assert len(workout["cards"]) == 5


def test_composition_avoids_duplicate_exercises() -> None:
    export_all()
    workout = build_workout(equipment=None, template_id="beginner_full_body")
    exercise_ids = [exercise["id"] for exercise in workout["cards"]]
    assert len(exercise_ids) == len(set(exercise_ids))


def test_composition_fallback_fills_strict_slot_failure() -> None:
    exercises = records_from_csv("exercises")[:2]
    rule = {
        "active": True,
        "composition_id": "fallback_test",
        "applies_to_template_id": "fallback_template",
        "applies_to_protocol_type": "circuit",
        "slot_order": 1,
        "slot_name": "impossible_jump",
        "required_movement_pattern": "jump",
        "allowed_movement_patterns": [],
        "required_primary_category": "",
        "allowed_primary_categories": [],
        "min_difficulty": 0,
        "max_difficulty": 0,
        "preferred_equipment": [],
        "fallback_allowed": True,
        "priority": 1,
    }
    cards, slots = compose_workout(exercises, [rule], "fallback_template", "circuit")
    assert len(cards) == 1
    assert slots[0]["used_fallback"] is True


def test_no_composition_rules_preserves_existing_behavior() -> None:
    exercises = records_from_csv("exercises")[:3]
    cards, slots = compose_workout(exercises, [], "unknown_template", "circuit")
    assert cards == []
    assert slots == []


def test_exercise_progression_records_are_valid() -> None:
    progressions = records_from_csv("exercise_progressions")
    assert progressions
    assert validate_schema("exercise_progressions", progressions) == []


def test_invalid_progression_exercise_reference_is_reported() -> None:
    record = records_from_csv("exercise_progressions")[0] | {"exercise_id": "missing_exercise"}
    errors = validate_exercise_progression_business_rules([record], {"air_squat", "dumbbell_goblet_squat"})
    assert any("unknown exercise_id" in error for error in errors)


def test_invalid_progression_related_exercise_reference_is_reported() -> None:
    record = records_from_csv("exercise_progressions")[0] | {"related_exercise_id": "missing_exercise"}
    errors = validate_exercise_progression_business_rules([record], {"air_squat"})
    assert any("unknown related_exercise_id" in error for error in errors)


def test_invalid_progression_relationship_type_is_reported() -> None:
    row = {"relationship_type": "upgrade"}
    errors = validate_enums("exercise_progressions", [row])
    assert any("relationship_type" in error for error in errors)


def test_invalid_progression_type_is_reported() -> None:
    row = {"progression_type": "magic"}
    errors = validate_enums("exercise_progressions", [row])
    assert any("progression_type" in error for error in errors)


def test_progression_self_reference_is_rejected() -> None:
    record = records_from_csv("exercise_progressions")[0] | {"exercise_id": "air_squat", "related_exercise_id": "air_squat"}
    errors = validate_exercise_progression_business_rules([record], {"air_squat"})
    assert any("cannot self-reference" in error for error in errors)


def test_get_progressions_returns_harder_options() -> None:
    records = records_from_csv("exercise_progressions")
    progressions = get_progressions("air_squat", records)
    assert progressions
    assert all(record["relationship_type"] == "progression" and record["difficulty_delta"] > 0 for record in progressions)


def test_get_regressions_returns_easier_options() -> None:
    records = records_from_csv("exercise_progressions")
    regressions = get_regressions("dumbbell_goblet_squat", records)
    assert regressions
    assert all(record["relationship_type"] == "regression" and record["difficulty_delta"] < 0 for record in regressions)


def test_show_progressions_does_not_break_sample_generation() -> None:
    export_all()
    workout = build_workout(equipment=None, template_id="beginner_full_body")
    output = format_workout(workout, show_progressions=True)
    assert "DECK OF SWEAT SAMPLE WORKOUT" in output
    assert "Progression:" in output


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


def test_sample_workout_generation_accepts_deck() -> None:
    export_all()
    workout = build_workout(equipment="bodyweight", time=10, deck_id="free_bodyweight_starter")
    assert workout["deck_id"] == "free_bodyweight_starter"
    assert len(workout["cards"]) >= 1
