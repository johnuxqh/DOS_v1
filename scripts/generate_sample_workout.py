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

from scripts.adapt_workout import (
    load_workout_history,
    recent_exercise_ids,
    should_suggest_progression,
    should_suggest_regression,
)
from scripts.export_json import records_from_csv
EXPORT_DIR = ROOT / "data" / "exports"


def load_records(name: str) -> list[dict[str, Any]]:
    export_path = EXPORT_DIR / f"{name}.json"
    if export_path.exists():
        return json.loads(export_path.read_text(encoding="utf-8"))
    return records_from_csv(name)


def get_related_exercises(
    exercise_id: str,
    relationship_type: str,
    progression_records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    records = progression_records if progression_records is not None else load_records("exercise_progressions")
    return sorted(
        [
            record
            for record in records
            if record.get("active", False)
            and record.get("exercise_id") == exercise_id
            and record.get("relationship_type") == relationship_type
        ],
        key=lambda item: (item["difficulty_delta"], item["related_exercise_id"]),
    )


def get_progressions(
    exercise_id: str,
    progression_records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    return get_related_exercises(exercise_id, "progression", progression_records)


def get_regressions(
    exercise_id: str,
    progression_records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    return get_related_exercises(exercise_id, "regression", progression_records)


def suggest_related_exercise(
    exercise_id: str,
    relationship_type: str,
    progression_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    related = get_related_exercises(exercise_id, relationship_type, progression_records)
    return related[0] if related else None


def active_deck_ids() -> set[str]:
    return {
        row["id"]
        for row in load_records("taxonomy")
        if row.get("type") == "deck" and row.get("status") == "active"
    }


def validate_deck(deck_id: str | None) -> None:
    if deck_id is None:
        return
    if deck_id not in active_deck_ids():
        raise ValueError(f"No active deck matched '{deck_id}'.")


def equipment_from_deck(deck_id: str | None) -> str | None:
    if deck_id is None:
        return None
    if "dumbbell" in deck_id:
        return "dumbbell"
    if "kettlebell" in deck_id:
        return "kettlebell"
    if "barbell" in deck_id or "strength" in deck_id:
        return "barbell"
    if "band" in deck_id:
        return "resistance_band"
    return "bodyweight"


def matching_selection_rules(
    rules: list[dict[str, Any]],
    template_id: str | None,
    deck_id: str | None,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for rule in rules:
        if not rule.get("active", False):
            continue
        rule_template_id = rule.get("applies_to_template_id", "")
        rule_deck_id = rule.get("applies_to_deck_id", "")
        if rule_template_id and rule_template_id != template_id:
            continue
        if rule_deck_id and rule_deck_id != deck_id:
            continue
        if rule_template_id or rule_deck_id:
            matches.append(rule)
    return sorted(matches, key=lambda item: item["priority"])


def exercise_tags(exercise: dict[str, Any]) -> set[str]:
    return {
        exercise.get("movement_pattern", ""),
        exercise.get("primary_category", ""),
        exercise.get("equipment_group", ""),
        exercise.get("impact_level", ""),
        f"{exercise.get('impact_level', '')}_impact",
        *exercise.get("secondary_categories", []),
        *exercise.get("equipment", []),
    } - {""}


def exercise_passes_selection_rule(exercise: dict[str, Any], rule: dict[str, Any]) -> bool:
    movement_pattern = exercise.get("movement_pattern", "")
    equipment = set(exercise.get("equipment", []))
    tags = exercise_tags(exercise)
    difficulty = exercise.get("difficulty_level", 0)

    allowed_patterns = set(rule.get("allowed_movement_patterns", []))
    if allowed_patterns and movement_pattern not in allowed_patterns:
        return False

    excluded_patterns = set(rule.get("excluded_movement_patterns", []))
    if excluded_patterns and movement_pattern in excluded_patterns:
        return False

    required_equipment = set(rule.get("required_equipment", []))
    if required_equipment and not equipment.intersection(required_equipment):
        return False

    excluded_equipment = set(rule.get("excluded_equipment", []))
    if excluded_equipment and equipment.intersection(excluded_equipment):
        return False

    min_difficulty = rule.get("min_difficulty", 0)
    max_difficulty = rule.get("max_difficulty", 0)
    if min_difficulty and difficulty < min_difficulty:
        return False
    if max_difficulty and difficulty > max_difficulty:
        return False

    include_tags = set(rule.get("include_tags", []))
    if include_tags and not tags.intersection(include_tags):
        return False

    exclude_tags = set(rule.get("exclude_tags", []))
    if exclude_tags and tags.intersection(exclude_tags):
        return False

    return True


def apply_selection_rules(
    exercises: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    template_id: str | None = None,
    deck_id: str | None = None,
) -> list[dict[str, Any]]:
    matching_rules = matching_selection_rules(rules, template_id, deck_id)
    if not matching_rules:
        return exercises
    return [
        exercise
        for exercise in exercises
        if all(exercise_passes_selection_rule(exercise, rule) for rule in matching_rules)
    ]


def matching_composition_rules(
    rules: list[dict[str, Any]],
    template_id: str | None,
    protocol_type: str | None,
) -> list[dict[str, Any]]:
    matches = [
        rule
        for rule in rules
        if rule.get("active", False)
        and (not rule.get("applies_to_template_id") or rule["applies_to_template_id"] == template_id)
        and (not rule.get("applies_to_protocol_type") or rule["applies_to_protocol_type"] == protocol_type)
    ]
    return sorted(matches, key=lambda item: (item["slot_order"], item["priority"]))


def exercise_matches_composition_slot(exercise: dict[str, Any], slot: dict[str, Any]) -> bool:
    movement_pattern = exercise.get("movement_pattern", "")
    primary_category = exercise.get("primary_category", "")
    difficulty = exercise.get("difficulty_level", 0)

    if slot.get("required_movement_pattern") and movement_pattern != slot["required_movement_pattern"]:
        return False
    allowed_patterns = set(slot.get("allowed_movement_patterns", []))
    if allowed_patterns and movement_pattern not in allowed_patterns:
        return False
    if slot.get("required_primary_category") and primary_category != slot["required_primary_category"]:
        return False
    allowed_categories = set(slot.get("allowed_primary_categories", []))
    if allowed_categories and primary_category not in allowed_categories:
        return False
    if slot.get("min_difficulty", 0) and difficulty < slot["min_difficulty"]:
        return False
    if slot.get("max_difficulty", 0) and difficulty > slot["max_difficulty"]:
        return False
    return True


def composition_candidate_sort_key(exercise: dict[str, Any], slot: dict[str, Any], avoided_ids: set[str] | None = None) -> tuple[int, int, int, str]:
    preferred_equipment = set(slot.get("preferred_equipment", []))
    has_preferred_equipment = bool(set(exercise.get("equipment", [])).intersection(preferred_equipment))
    return (1 if exercise["id"] in (avoided_ids or set()) else 0, 0 if has_preferred_equipment else 1, exercise.get("difficulty_level", 0), exercise["id"])


def compose_workout(
    eligible_exercises: list[dict[str, Any]],
    composition_rules: list[dict[str, Any]],
    template_id: str | None,
    protocol_type: str | None,
    avoided_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    slots = matching_composition_rules(composition_rules, template_id, protocol_type)
    if not slots:
        return [], []

    selected: list[dict[str, Any]] = []
    filled_slots: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for slot in slots:
        remaining = [exercise for exercise in eligible_exercises if exercise["id"] not in selected_ids]
        strict_matches = [exercise for exercise in remaining if exercise_matches_composition_slot(exercise, slot)]
        candidates = strict_matches
        used_fallback = False
        if not candidates and slot.get("fallback_allowed", False):
            candidates = remaining
            used_fallback = True
        if not candidates:
            continue
        choice = sorted(candidates, key=lambda exercise: composition_candidate_sort_key(exercise, slot, avoided_ids))[0]
        selected.append(choice)
        selected_ids.add(choice["id"])
        filled_slots.append({"slot_order": slot["slot_order"], "slot_name": slot["slot_name"], "exercise_id": choice["id"], "used_fallback": used_fallback})
    return selected, filled_slots


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


def eligible_exercises(
    exercises: list[dict[str, Any]],
    equipment: str | list[str],
    selection_rules: list[dict[str, Any]] | None = None,
    template_id: str | None = None,
    deck_id: str | None = None,
) -> list[dict[str, Any]]:
    equipment_candidates = [
        exercise
        for exercise in exercises
        if exercise.get("status") == "active" and equipment_matches(exercise, equipment)
    ]
    return apply_selection_rules(equipment_candidates, selection_rules or [], template_id, deck_id)


def select_exercises(
    exercises: list[dict[str, Any]],
    equipment: str | list[str],
    count: int,
    movement_focus: list[str] | None = None,
    selection_rules: list[dict[str, Any]] | None = None,
    template_id: str | None = None,
    deck_id: str | None = None,
    avoided_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    rule_filtered_candidates = eligible_exercises(exercises, equipment, selection_rules, template_id, deck_id)
    candidates = [exercise for exercise in rule_filtered_candidates if exercise_matches_focus(exercise, movement_focus)]
    if len(candidates) < count:
        candidates.extend(exercise for exercise in rule_filtered_candidates if exercise not in candidates)
    if not candidates:
        raise ValueError(f"No active exercises matched equipment '{equipment}'.")

    selected: list[dict[str, Any]] = []
    used_patterns: set[str] = set()
    for exercise in sorted(candidates, key=lambda item: (item["id"] in (avoided_ids or set()), item["difficulty_level"], item["id"])):
        if exercise["movement_pattern"] in used_patterns:
            continue
        selected.append(exercise)
        used_patterns.add(exercise["movement_pattern"])
        if len(selected) == count:
            return selected

    for exercise in sorted(candidates, key=lambda item: (item["id"] in (avoided_ids or set()), item["id"])):
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


def apply_history_adaptation(
    cards: list[dict[str, Any]],
    eligible: list[dict[str, Any]],
    history: list[dict[str, Any]],
    progression_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Apply safe deterministic progression/regression swaps to selected cards."""
    if not history:
        return cards, []
    eligible_by_id = {exercise["id"]: exercise for exercise in eligible}
    selected_ids = {exercise["id"] for exercise in cards}
    adapted = list(cards)
    notes: list[str] = []
    for index, exercise in enumerate(adapted):
        relationship_type = None
        if should_suggest_regression(history, exercise["id"]):
            relationship_type = "regression"
        elif should_suggest_progression(history, exercise["id"]):
            relationship_type = "progression"
        if not relationship_type:
            continue
        relations = get_related_exercises(exercise["id"], relationship_type, progression_records)
        suggestion_recorded = False
        for relation in relations:
            related_id = relation["related_exercise_id"]
            if related_id not in eligible_by_id or related_id in selected_ids:
                continue
            if relationship_type == "progression" and should_suggest_regression(history, related_id):
                continue
            selected_ids.remove(exercise["id"])
            selected_ids.add(related_id)
            adapted[index] = eligible_by_id[related_id]
            notes.append(f"suggested {relationship_type}: {exercise['id']} -> {related_id}")
            suggestion_recorded = True
            break
        if relations and not suggestion_recorded:
            notes.append(
                f"suggested {relationship_type}: {exercise['id']} -> "
                f"{relations[0]['related_exercise_id']} (hint only; not eligible for this workout)"
            )
    return adapted, notes


def build_workout(
    equipment: str | None = "bodyweight",
    time: int | None = 10,
    protocol_id: str | None = None,
    template_id: str | None = None,
    deck_id: str | None = None,
    history_path: str | Path | None = None,
) -> dict[str, Any]:
    exercises = load_records("exercises")
    history = load_workout_history(history_path)
    avoided_ids = recent_exercise_ids(history)
    template = None
    movement_focus = None
    validate_deck(deck_id)

    selection_rules: list[dict[str, Any]] = []
    composition_rules: list[dict[str, Any]] = []
    if template_id:
        template = select_template(load_records("workout_templates"), template_id)
        protocol = protocol_from_template(template)
        deck_id = deck_id or template.get("deck_id")
        equipment_filter: str | list[str] = equipment or template["equipment_required"]
        movement_focus = template.get("movement_focus", [])
        selection_rules = load_records("exercise_selection_rules")
        composition_rules = load_records("workout_composition_rules")
    else:
        protocols = load_records("protocols")
        protocol = select_protocol(protocols, time, protocol_id)
        equipment_filter = equipment or equipment_from_deck(deck_id) or "bodyweight"

    composition_slots: list[dict[str, Any]] = []
    eligible = eligible_exercises(exercises, equipment_filter, selection_rules, template_id, deck_id)
    if template:
        cards, composition_slots = compose_workout(eligible, composition_rules, template_id, template["protocol_type"], avoided_ids)
    else:
        cards = []

    if not cards:
        cards = select_exercises(
            exercises,
            equipment_filter,
            protocol["cards_to_draw"],
            movement_focus,
            selection_rules,
            template_id,
            deck_id,
            avoided_ids,
        )
    if not cards:
        raise ValueError("Could not select any cards for the sample workout.")
    cards, adaptation_notes = apply_history_adaptation(cards, eligible, history, load_records("exercise_progressions"))
    for slot, card in zip(composition_slots, cards):
        slot["exercise_id"] = card["id"]
    selected_ids = {exercise["id"] for exercise in cards}
    adaptation_notes = [
        *[f"avoided recent exercise: {exercise_id}" for exercise_id in sorted(avoided_ids - selected_ids) if exercise_id in {exercise["id"] for exercise in eligible}],
        *adaptation_notes,
    ]
    return {
        "protocol": protocol,
        "cards": cards,
        "equipment": equipment_filter,
        "template": template,
        "deck_id": deck_id,
        "composition_slots": composition_slots,
        "adaptation_notes": adaptation_notes,
    }


def format_workout(workout: dict[str, Any], show_progressions: bool = False, explain_adaptation: bool = False) -> str:
    protocol = workout["protocol"]
    exercise_names = {exercise["id"]: exercise["display_name"] for exercise in load_records("exercises")}
    progression_records = load_records("exercise_progressions") if show_progressions else []
    lines = [
        "DECK OF SWEAT SAMPLE WORKOUT",
        f"Time: {protocol['time_minutes']} minutes",
        f"Protocol: {protocol['display_name']}",
        *( [f"Template: {workout['template']['template_id']} ({workout['template']['tier']})"] if workout.get("template") else [] ),
        *( [f"Deck: {workout['deck_id']}"] if workout.get("deck_id") else [] ),
        f"Equipment: {workout['equipment']}",
        f"Instructions: {protocol['instructions_short']}",
        "",
        "Cards:",
    ]
    for index, exercise in enumerate(workout["cards"], start=1):
        lines.append(f"{index}. {exercise['display_name']} — {card_prescription(exercise)}")
        if show_progressions:
            progression = suggest_related_exercise(exercise["id"], "progression", progression_records)
            regression = suggest_related_exercise(exercise["id"], "regression", progression_records)
            if progression:
                name = exercise_names.get(progression["related_exercise_id"], progression["related_exercise_id"])
                lines.append(f"   Progression: {name} ({progression['progression_type']})")
            if regression:
                name = exercise_names.get(regression["related_exercise_id"], regression["related_exercise_id"])
                lines.append(f"   Regression: {name} ({regression['progression_type']})")
    if explain_adaptation and workout.get("adaptation_notes"):
        lines.extend(["", "Adaptation notes:", *[f"- {note}" for note in workout["adaptation_notes"]]])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Deck of Sweat sample workout.")
    parser.add_argument("--equipment", help="Requested equipment id, e.g. bodyweight or dumbbell.")
    parser.add_argument("--time", type=int, default=10, choices=[5, 10, 15], help="Workout duration in minutes.")
    parser.add_argument("--protocol", dest="protocol_id", help="Specific protocol id, e.g. amrap_10.")
    parser.add_argument("--template", dest="template_id", help="Workout template id, e.g. beginner_full_body or emom_12.")
    parser.add_argument("--deck", dest="deck_id", help="Deck id, e.g. free_bodyweight_starter.")
    parser.add_argument("--show-progressions", action="store_true", help="Show deterministic progression and regression hints.")
    parser.add_argument("--history", help="Optional local workout history JSON file.")
    parser.add_argument("--explain-adaptation", action="store_true", help="Explain history-aware exercise choices and swaps.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workout = build_workout(args.equipment, args.time, args.protocol_id, args.template_id, args.deck_id, args.history)
    print(format_workout(workout, show_progressions=args.show_progressions, explain_adaptation=args.explain_adaptation))


if __name__ == "__main__":
    main()
