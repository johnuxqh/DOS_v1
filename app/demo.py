"""Clickable local Streamlit wireframe for the existing Deck of Sweat engine."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.generate_sample_workout import (
    build_workout,
    card_prescription,
    get_progressions,
    get_regressions,
    load_records,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_HISTORY = ROOT / "data/sample/sample_workout_history.json"


def deck_options() -> list[tuple[str, str]]:
    """Return active deck ids and readable labels for demo controls."""
    return sorted(
        [(row["id"], row["name"]) for row in load_records("taxonomy") if row.get("type") == "deck" and row.get("status") == "active"],
        key=lambda item: item[1],
    )


def template_options() -> list[tuple[str, str]]:
    """Return template ids and readable labels for demo controls."""
    return sorted([(row["template_id"], row["template_name"]) for row in load_records("workout_templates")], key=lambda item: item[1])


def equipment_options() -> list[tuple[str, str]]:
    """Return active equipment ids and readable labels, plus template defaults."""
    rows = load_records("equipment")
    return [("", "Use template defaults"), *sorted([(row["id"], row["name"]) for row in rows if row.get("status") == "active"], key=lambda item: item[1])]


def progression_hints(card: dict[str, Any], exercise_names: dict[str, str]) -> list[str]:
    hints = []
    for label, relations in (("Progression", get_progressions(card["id"])), ("Regression", get_regressions(card["id"]))):
        if relations:
            related = relations[0]["related_exercise_id"]
            hints.append(f"{label}: {exercise_names.get(related, related)}")
    return hints


def run_demo() -> None:
    import streamlit as st

    st.set_page_config(page_title="Deck of Sweat Demo", page_icon="🃏", layout="wide")
    st.title("Deck of Sweat")
    st.caption("P4.00 clickable local demo — a wireframe over the existing DOS engine")

    decks, templates, equipment = deck_options(), template_options(), equipment_options()
    deck_labels, template_labels, equipment_labels = dict(decks), dict(templates), dict(equipment)

    st.header("Workout Setup")
    left, right = st.columns(2)
    with left:
        deck_id = st.selectbox("Deck", [item[0] for item in decks], format_func=deck_labels.get)
        template_id = st.selectbox("Workout template", [item[0] for item in templates], format_func=template_labels.get)
        equipment_id = st.selectbox("Equipment (optional)", [item[0] for item in equipment], format_func=equipment_labels.get)
    with right:
        show_progressions = st.toggle("Show progressions / regressions", value=True)
        use_history = st.toggle("Use sample workout history")
        explain_adaptation = st.toggle("Explain adaptation", disabled=not use_history)

    if st.button("Generate Workout", type="primary", use_container_width=True):
        try:
            st.session_state.workout = build_workout(
                equipment=equipment_id or None,
                template_id=template_id,
                deck_id=deck_id,
                history_path=SAMPLE_HISTORY if use_history else None,
            )
            st.session_state.demo_settings = {"show_progressions": show_progressions, "explain_adaptation": explain_adaptation, "used_history": use_history}
        except ValueError as error:
            st.error(str(error))

    workout = st.session_state.get("workout")
    if not workout:
        st.info("Choose your setup and click **Generate Workout**.")
        return
    settings = st.session_state.demo_settings
    protocol, template = workout["protocol"], workout.get("template")
    exercise_names = {row["id"]: row["display_name"] for row in load_records("exercises")}
    slots = {slot["exercise_id"]: slot["slot_name"] for slot in workout.get("composition_slots", [])}

    st.header("Generated Workout")
    st.subheader(protocol["display_name"])
    st.write(f"**Protocol:** {template['protocol_type'].replace('_', ' ').title() if template else protocol['display_name']} · **Deck:** {workout.get('deck_id') or '—'} · **Template:** {template['template_name'] if template else '—'}")
    st.write(f"**Duration:** {protocol['time_minutes']} minutes · **Equipment:** {', '.join(workout['equipment']) if isinstance(workout['equipment'], list) else workout['equipment']}")
    st.info(protocol["instructions_short"])
    for index, card in enumerate(workout["cards"], start=1):
        with st.container(border=True):
            st.markdown(f"### {index}. {card['display_name']}")
            st.write(f"**Prescription:** {card_prescription(card)}" + (f" · **Composition slot:** {slots[card['id']]}" if card["id"] in slots else ""))
            if settings["show_progressions"]:
                for hint in progression_hints(card, exercise_names):
                    st.caption(hint)

    st.header("Why this workout?")
    st.markdown(f"- **Selected template:** {template['template_name']} (`{template['template_id']}`)\n- **Deck:** `{workout.get('deck_id')}`\n- **Equipment filter:** `{workout['equipment']}`")
    if workout.get("composition_slots"):
        st.write("**Composition slots filled:**")
        for slot in workout["composition_slots"]:
            st.write(f"- {slot['slot_name']}: {exercise_names.get(slot['exercise_id'], slot['exercise_id'])}")
    avoided = [note.removeprefix("avoided recent exercise: ") for note in workout.get("adaptation_notes", []) if note.startswith("avoided recent exercise:")]
    if settings["used_history"]:
        st.write("**Recent exercises avoided:** " + (", ".join(avoided) if avoided else "None reported"))
    if settings["show_progressions"]:
        st.write("**Progression/regression hints:** enabled on each card where a relationship exists.")

    st.header("Adaptation Notes")
    if settings["explain_adaptation"]:
        notes = workout.get("adaptation_notes", [])
        if notes:
            for note in notes:
                st.write(f"- {note}")
        else:
            st.write("No history-driven changes were needed.")
    else:
        st.caption("Enable sample history and Explain adaptation during setup to show these notes.")

    st.header("Debug/Data View")
    with st.expander("Raw generated workout JSON"):
        st.json(workout, expanded=False)


if __name__ == "__main__":
    run_demo()
