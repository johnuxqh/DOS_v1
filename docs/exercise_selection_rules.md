# Exercise Selection Rules

Exercise selection rules are a data-driven eligibility layer for workout generation. They control which exercises are allowed before the generator picks cards for a template or deck.

## Why rules exist

Templates describe the workout format, and decks describe the available content pool. Selection rules sit between those systems and the exercise database so each generated workout can respect safety, equipment, difficulty, and movement constraints without hard-coding those decisions into application logic.

Rules can limit exercises by:

- movement pattern
- equipment
- difficulty range
- include or exclude tags
- template scope
- deck scope
- progression/regression policy
- repeat limits for a single workout

If no active rule matches a selected template or deck, the sample generator falls back to the existing exercise-selection behavior.

## Relationship to exercises, decks, and templates

- **Exercises** provide the candidate data: movement pattern, equipment, category tags, difficulty, impact, and card text.
- **Decks** define product/content pools such as Free, Plus, or Pro collections.
- **Workout templates** define the workout structure: duration, protocol type, focus, scoring, and coaching notes.
- **Exercise selection rules** narrow the candidate exercises for a template/deck combination before final card selection.

For example, the `beginner_full_body` rule keeps the beginner template within lower-difficulty, low-impact, bodyweight/band-friendly cards. The `mobility_flow` rule favors mobility and stability tags and excludes power/conditioning emphasis.

## Future personalization

This repository does not implement user accounts, subscriptions, tracking, or persistence. The rule layer still prepares for future personalization by making eligibility decisions explicit data. Later systems can add rules for user experience level, injury constraints, available equipment, goals, subscription tier, or recent workout history while continuing to export deterministic JSON for apps and tools.
