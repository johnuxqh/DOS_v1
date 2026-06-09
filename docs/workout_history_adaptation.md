# Workout History and Adaptation

## Why this exists

Deck of Sweat needs a small amount of prior-session context to reduce repetitive workouts and make sensible progression or regression suggestions. P3.00 adds that context as portable JSON data plus deterministic helper functions. It does not introduce a tracking product, account system, or database.

Each workout-history record captures where a workout came from, whether the session was completed, and a compact result for every prescribed exercise. The schema makes those records testable and exportable while leaving storage decisions to future consumers.

## History is not a user account

`user_id` is a caller-provided correlation key. It does not imply authentication, identity management, profiles, permissions, subscriptions, or cloud storage. A future app may use a local anonymous ID, an imported ID, or an authenticated account ID without changing the history record shape.

The sample history is an array of session objects. The adaptation helpers read completed and partial sessions, ignore planned or skipped sessions when calculating exercise outcomes, and return safe defaults for missing or sparse history.

## Lightweight adaptation rules

The current engine is deliberately deterministic and conservative:

- exercises seen in the most recent three completed or partial sessions are deprioritized when alternatives are available;
- progression is suggested after at least three attempts, an 80% or better completion rate, average effort of 6 or lower, and no recorded pain;
- regression is suggested when pain was recorded, completion rate is below 60%, or average effort is 9 or higher;
- swaps use the existing exercise-progression records and must remain eligible for the requested workout;
- generation still succeeds when history is missing, invalid, sparse, or unable to provide an eligible swap.

These rules are transparent starting points, not medical advice. Pain flags trigger conservative regression behavior, but future applications should continue to show the existing safety guidance and encourage users to stop painful movement.

## Supporting future Plus and Pro features

The schema can support future features such as richer session summaries, long-term progression reports, personalized deck rotation, coach review, or tier-specific adaptation policies. Those products can build on stable exercise, deck, template, and protocol references without putting entitlement or billing logic into the core history model.

## Avoiding tracking too early

This phase stores no data automatically and builds no dashboards, streaks, accounts, or analytics pipeline. It only defines the minimum interoperable event shape and pure calculations needed to prove history-aware generation. That keeps DOS focused on workout quality while avoiding premature product and infrastructure decisions.

## Future storage

A local-first app could write session objects to a JSON file, browser storage, SQLite, or an on-device database. A connected app could send the same validated objects to a remote API or synchronize local and remote copies. Because adaptation consumes plain schema-driven records, storage can evolve without rewriting the core rules.

## Command-line usage

```bash
python scripts/generate_sample_workout.py \
  --template beginner_full_body \
  --history data/sample/sample_workout_history.json \
  --explain-adaptation
```

Without `--history`, generation behaves as before. With `--history`, recent exercises are deprioritized where possible and eligible progression/regression swaps may be applied. Add `--explain-adaptation` to print the deterministic adaptation notes.
