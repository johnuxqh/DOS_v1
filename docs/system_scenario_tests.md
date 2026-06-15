# Real system scenario tests

The real system scenario suite in `tests/test_system_scenarios.py` protects the
product-level behaviour of the existing workout engine. Unlike unit validation,
these tests generate complete workouts and assert outcomes across templates,
decks, selection rules, composition slots, progression relationships, and
history-aware adaptation.

## Behaviours protected before the visual demo

- Beginner Full Body remains a five-card, free, low-impact, beginner-compatible,
  balanced workout with valid composition slots.
- No-Equipment Hotel Workout remains bodyweight-only and fills its four defined
  slots. The current data names this template `hotel_no_equipment`, rather than
  `hotel_bodyweight`.
- EMOM 12 remains a safe four-station, 12-minute EMOM.
- Mobility Flow remains low/moderate difficulty, bodyweight-only, low-impact,
  and focused on mobility, stability, or core work.
- Progression and regression hints reference valid exercises, appear only when
  requested, and do not change normal generation.
- History-aware generation still fills every required card, avoids recent
  exercises where possible, explains adaptation when requested, and leaves
  ineligible progression targets as hint-only suggestions.
- Free deck IDs survive generation, equipment inference remains active, and an
  unknown deck produces a clear error.

## Preventing backend drift

The assertions intentionally avoid exact card ordering. They check stable
product contracts—counts, uniqueness, eligibility, equipment, movement
coverage, safety, slots, IDs, and notes—so data can evolve without silently
changing the experience promised by a template or deck.

Run `pytest` before visual-demo work or any data/engine change. A failing
scenario means the generated product experience has drifted and should be
reviewed before frontend code relies on it.

## Documented fallbacks

Composition rules may permit fallback selection when a strict slot has no
eligible card. Scenario tests accept those data-defined fallbacks while still
requiring every expected slot to be filled. History adaptation similarly
reports an otherwise useful progression as `hint only` when equipment or
selection rules make it ineligible; it must never force that exercise into the
workout.
