# Workout Composition Rules

Workout composition rules define the ordered roles that make a generated workout balanced. They run after exercise eligibility filtering and before final cards are selected.

## Selection rules versus composition rules

- **Exercise selection rules** decide which exercises are eligible for a template/deck combination. They filter by equipment, movement pattern, difficulty, tags, and exclusions.
- **Workout composition rules** decide how eligible exercises are assembled. Each row describes an ordered slot, such as lower body, push, posterior chain, core, or mobility finisher.

Selection rules answer “can this exercise appear?” Composition rules answer “what role should the next exercise fill?”

## How composition creates balanced workouts

When a template has active composition rules, the generator:

1. Applies matching exercise selection rules to build the eligible exercise pool.
2. Loads composition slots matching the template and protocol type.
3. Processes slots in `slot_order` and `priority` order.
4. Selects an unused exercise matching movement, category, difficulty, and preferred-equipment guidance.
5. Uses an unused eligible fallback only when a slot explicitly allows it.
6. Avoids duplicate exercises in the composed workout.

If no composition rules match, the generator keeps the existing non-composition selection behavior.

## Future progression, personalization, and coaching

Composition slots create stable workout roles without hard-coding a single exercise. A future system can preserve a balanced structure while changing exercise difficulty, equipment, coaching emphasis, or progression based on a user's needs. This supports future personalization and coaching logic without adding tracking, subscriptions, UI, or database persistence to the current data foundation.
