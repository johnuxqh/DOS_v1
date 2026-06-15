"""High-level product-behaviour scenarios for the current workout engine."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.generate_sample_workout import (
    build_workout,
    equipment_from_deck,
    format_workout,
    get_progressions,
    get_regressions,
    load_records,
)

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data/sample/sample_workout_history.json"
LOADED_STRENGTH_EQUIPMENT = {"dumbbell", "kettlebell", "barbell", "bench", "machine"}


def assert_no_duplicate_cards(workout: dict) -> None:
    ids = [card["id"] for card in workout["cards"]]
    assert len(ids) == len(set(ids))


def assert_allowed_equipment(workout: dict, allowed_equipment: set[str]) -> None:
    for card in workout["cards"]:
        assert set(card["equipment"]) <= allowed_equipment, card["id"]


def assert_no_high_impact(workout: dict) -> None:
    assert all(card["impact_level"] != "high" for card in workout["cards"])


def assert_composition_slots_valid(workout: dict) -> None:
    slots = workout["composition_slots"]
    assert len(slots) == len(workout["cards"])
    assert [slot["exercise_id"] for slot in slots] == [card["id"] for card in workout["cards"]]
    assert len({slot["slot_order"] for slot in slots}) == len(slots)


def test_beginner_full_body_product_scenario() -> None:
    workout = build_workout(equipment=None, template_id="beginner_full_body")
    assert workout["template"]["tier"] == "free"
    assert workout["deck_id"] == "free_beginner"
    assert len(workout["cards"]) == 5
    assert_no_duplicate_cards(workout)
    assert_allowed_equipment(workout, {"bodyweight", "resistance_band"})
    assert_no_high_impact(workout)
    assert all(card["beginner_safe"] and card["difficulty_level"] <= 3 for card in workout["cards"])
    patterns = {card["movement_pattern"] for card in workout["cards"]}
    assert {"push", "pull", "anti_rotate"} <= patterns
    assert patterns & {"squat", "hinge"}
    assert patterns & {"hinge", "mobility"}
    assert_composition_slots_valid(workout)


def test_hotel_bodyweight_product_scenario() -> None:
    workout = build_workout(equipment=None, template_id="hotel_no_equipment")
    assert workout["template"]["template_id"] == "hotel_no_equipment"
    assert_allowed_equipment(workout, {"bodyweight"})
    assert all(not (set(card["equipment"]) & (LOADED_STRENGTH_EQUIPMENT | {"resistance_band"})) for card in workout["cards"])
    assert_no_duplicate_cards(workout)
    assert len(workout["cards"]) == len(workout["composition_slots"]) == 4
    assert_composition_slots_valid(workout)


def test_emom_12_product_scenario() -> None:
    workout = build_workout(equipment=None, template_id="emom_12")
    assert workout["template"]["protocol_type"] == "emom"
    assert workout["protocol"]["time_minutes"] == 12
    assert len(workout["cards"]) == 4
    assert_no_duplicate_cards(workout)
    assert_allowed_equipment(workout, {"bodyweight", "dumbbell", "resistance_band"})
    assert_no_high_impact(workout)
    assert all(card["beginner_safe"] and card["difficulty_level"] <= 3 for card in workout["cards"])
    assert all(card["movement_pattern"] in {"squat", "hinge", "push", "pull", "carry", "anti_rotate", "locomotion"} for card in workout["cards"])


def test_mobility_flow_product_scenario() -> None:
    workout = build_workout(equipment=None, template_id="mobility_flow_10")
    assert workout["template"]["protocol_type"] == "mobility_flow"
    assert all(
        {"mobility", "stability", "core"}
        & {card["primary_category"], *card["secondary_categories"]}
        for card in workout["cards"]
    )
    assert_allowed_equipment(workout, {"bodyweight"})
    assert all(not (set(card["equipment"]) & LOADED_STRENGTH_EQUIPMENT) for card in workout["cards"])
    assert_no_high_impact(workout)
    assert all(card["difficulty_level"] <= 2 and card["intensity_level"] in {"low", "moderate"} for card in workout["cards"])


def test_progression_hints_are_valid_and_opt_in() -> None:
    workout = build_workout(equipment=None, template_id="beginner_full_body")
    regression_workout = build_workout(equipment=None, template_id="mobility_flow_10")
    normal = format_workout(workout)
    with_hints = format_workout(workout, show_progressions=True)
    with_regression_hints = format_workout(regression_workout, show_progressions=True)
    valid_ids = {exercise["id"] for exercise in load_records("exercises")}
    progressions = [relation for card in workout["cards"] for relation in get_progressions(card["id"])]
    regressions = [relation for card in regression_workout["cards"] for relation in get_regressions(card["id"])]
    assert progressions and regressions
    assert all(relation["exercise_id"] in valid_ids and relation["related_exercise_id"] in valid_ids for relation in progressions + regressions)
    assert "Progression:" not in normal and "Regression:" not in normal
    assert "Progression:" in with_hints and "Regression:" in with_regression_hints
    assert [card["id"] for card in workout["cards"]] == [card["id"] for card in build_workout(equipment=None, template_id="beginner_full_body")["cards"]]


def test_history_aware_generation_avoids_recent_cards_and_explains_adaptation() -> None:
    normal = build_workout(equipment=None, template_id="beginner_full_body")
    adapted = build_workout(equipment=None, template_id="beginner_full_body", history_path=HISTORY)
    assert len(adapted["cards"]) == len(normal["cards"]) == 5
    assert_no_duplicate_cards(adapted)
    assert adapted["adaptation_notes"]
    assert any(note.startswith("avoided recent exercise:") for note in adapted["adaptation_notes"])
    assert "Adaptation notes:" in format_workout(adapted, explain_adaptation=True)
    assert "Adaptation notes:" not in format_workout(adapted)


def test_ineligible_history_progression_is_hint_only() -> None:
    workout = build_workout(equipment=None, template_id="beginner_full_body", history_path=HISTORY)
    hint = "suggested progression: air_squat -> dumbbell_goblet_squat (hint only; not eligible for this workout)"
    assert hint in workout["adaptation_notes"]
    assert "dumbbell_goblet_squat" not in {card["id"] for card in workout["cards"]}


@pytest.mark.parametrize("history_path", [None, ROOT / "data/sample/missing_history.json"])
def test_missing_or_empty_history_does_not_crash(history_path: Path | None) -> None:
    workout = build_workout(equipment=None, template_id="beginner_full_body", history_path=history_path)
    assert len(workout["cards"]) == 5


def test_free_deck_preserves_id_and_infers_bodyweight() -> None:
    workout = build_workout(equipment=None, time=10, deck_id="free_bodyweight_starter")
    assert workout["deck_id"] == "free_bodyweight_starter"
    assert workout["equipment"] == equipment_from_deck("free_bodyweight_starter") == "bodyweight"
    assert_allowed_equipment(workout, {"bodyweight"})


def test_unknown_deck_has_clear_error() -> None:
    with pytest.raises(ValueError, match="No active deck matched 'unknown_deck'"):
        build_workout(equipment=None, time=10, deck_id="unknown_deck")
