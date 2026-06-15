# Deck of Sweat Core

Deck of Sweat Core is the data foundation for an evidence-informed micro-workout system built around drawing a small set of exercise cards and following a simple protocol.

This repository is the source of truth for exercise data, protocol data, workout-generation rules, validation rules, and generated exports for future tools.

## Why this repo exists

The first priority is trustworthy, maintainable data. This repo intentionally does **not** include an app, UI, or heavy framework. It provides:

- Human-editable CSV master files in `data/source/`
- Machine-readable JSON exports in `data/exports/`
- JSON Schemas in `data/schemas/`
- Python validation and export scripts in `scripts/`
- Documentation for taxonomy, safety, and governance in `docs/`

## CSV is the editable source

Edit CSV files in `data/source/` when adding or changing content:

- `exercises.csv` — exercise cards and scoring metadata
- `protocols.csv` — workout protocol definitions
- `rules.csv` — workout generation and safety rules
- `workout_templates.csv` — reusable workout-template presets
- `exercise_selection_rules.csv` — data-driven exercise eligibility rules
- `workout_composition_rules.csv` — ordered rules for balanced workout slots
- `exercise_progressions.csv` — progression, regression, and lateral exercise relationships
- `decks.csv` — free/plus/pro packaging for business-model and tracking readiness
- `equipment.csv` — supported equipment IDs and groups
- `taxonomy.csv` — controlled vocabulary for patterns, categories, and groups

Pipe-separated fields, such as `equipment` or `coaching_cues`, are converted to arrays during export.

## JSON exports are generated

Files in `data/exports/` are generated from CSV, including workout templates, and should be refreshed after source changes:

```bash
python scripts/export_json.py
```

The exports are sorted by `id` and pretty-printed with two spaces so downstream consumers can diff them easily.

## Validate data

Run validation before committing any data change:

```bash
python scripts/validate_data.py
```

Validation checks required columns, unique lowercase snake_case IDs, enum values, numeric ranges, JSON Schema compliance, workout-template deck references, exercise-selection, composition-rule, and exercise-progression references, and basic business rules such as beginner safety and protocol card limits.

## Generate a sample workout

Use the sample generator to smoke-test the data model:

```bash
python scripts/generate_sample_workout.py --equipment bodyweight --time 10 --protocol amrap_10
python scripts/generate_sample_workout.py --template beginner_full_body
python scripts/generate_sample_workout.py --template beginner_full_body --show-progressions
python scripts/generate_sample_workout.py --deck free_bodyweight_starter --equipment bodyweight --time 10
```

The script loads generated JSON when available, otherwise it reads the CSV source directly.

## Run tests

```bash
pytest
```

The suite includes real system scenario tests that generate complete Beginner
Full Body, No-Equipment Hotel, EMOM 12, and Mobility Flow workouts and protect
deck, composition, progression-hint, safety, and history-adaptation behaviour.
See [`docs/system_scenario_tests.md`](docs/system_scenario_tests.md).

## Future support

This repository is structured to support later phases without locking the project into an app architecture too early:

- **Google Sheets prototype:** CSV source files can be imported to or exported from Sheets with stable headers.
- **Printable card deck:** JSON exports include short and long card text for future print layouts.
- **Workout generator:** protocol, template, exercise-selection, workout-composition, progression, and business-rule data provide a clear foundation for deterministic or randomized generation.
- **App integration:** JSON exports are stable machine-readable assets for a future mobile or web app.
- **Subscription tracking engine:** deck IDs, entitlement tiers, protocol IDs, exercise IDs, template IDs, and version fields can later support usage history, progression tracking, and content entitlements.

## Workout history and adaptation

P3.00 adds a lightweight, local-first history model without adding accounts or a database:

- `data/schemas/workout_history.schema.json` defines a portable completed-session record.
- `data/sample/sample_workout_history.json` contains realistic, reference-valid sample sessions.
- `scripts/adapt_workout.py` calculates recent exercise use, completion rate, average effort, and deterministic progression/regression signals.
- The sample generator optionally uses history to avoid recent repetition and apply eligible progression or regression swaps.

```bash
python scripts/generate_sample_workout.py --template beginner_full_body --history data/sample/sample_workout_history.json
python scripts/generate_sample_workout.py --template beginner_full_body --history data/sample/sample_workout_history.json --explain-adaptation
```

History is optional; missing or sparse history does not prevent workout generation. See [`docs/workout_history_adaptation.md`](docs/workout_history_adaptation.md) for the model, adaptation thresholds, and future storage options.
