# Workout Templates

Workout templates are reusable protocol presets that connect a deck, a tier, and a workout structure. They do not generate a full app experience yet; they provide a data layer that future generators, printable products, and apps can rely on.

## What templates contain

Each row in `data/source/workout_templates.csv` defines a repeatable format with:

- a stable `template_id`
- a user-facing name and description
- a Free, Plus, or Pro `tier`
- a `deck_id` that references an active deck in taxonomy data
- a controlled `protocol_type`, such as `amrap`, `emom`, `circuit`, `ladder`, or `mobility_flow`
- timing fields such as duration, rounds, work seconds, and rest seconds
- required equipment and movement focus tags
- scoring, tracking, coaching, and safety metadata

## How templates connect decks to workout generation

A deck describes the content pool. A workout template describes how to use that content pool. The template layer lets a future workout engine ask questions such as:

1. Which deck is available to this user?
2. Which template matches the user's tier, time, equipment, and goal?
3. Which exercises fit the template's equipment and movement focus?
4. Which scoring and tracking rules should be displayed or recorded?

This keeps deck content separate from workout structure while still making both machine-readable.

## Free / Plus / Pro support

Templates include a `tier` field so product packaging can be managed in data rather than hard-coded in an app. For example:

- **Free:** bodyweight, beginner, hotel, and mobility templates.
- **Plus:** mixed-equipment and dumbbell templates.
- **Pro:** more advanced loaded strength templates.

The tier field is validated so future exports can safely power cards, Google Sheets prototypes, or app gating.

## Subscription tracking support

The current repository does not implement login, payment, subscriptions, or persistence. The template data still prepares for subscription tracking by providing stable IDs for:

- template availability by tier
- deck access by tier
- workout history references
- usage analytics
- repeatable progression comparisons

A future subscription or tracking engine can record `template_id`, `deck_id`, and versioned exercise IDs without changing the data foundation.
