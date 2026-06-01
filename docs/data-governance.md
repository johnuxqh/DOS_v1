# Data Governance

Deck of Sweat treats CSV data as product-critical source material.

## Review statuses

- **needs_review:** New or changed content that has not been checked.
- **reviewed:** Content has been reviewed for clarity, formatting, and basic safety.
- **evidence_checked:** Content has received an additional evidence and safety review.

## Adding exercises

1. Add a row to `data/source/exercises.csv`.
2. Use a lowercase snake_case `id` that will remain stable.
3. Fill all required fields, including regression, progression, coaching cues, and safety notes.
4. Use pipe-separated values for multi-value fields.
5. Run validation, export JSON, and tests before committing.

## Retiring exercises

Set `status` to `retired` instead of deleting the row. Stable IDs may be referenced by generated workouts, print exports, app history, or analytics in the future.

## Reviewing science and safety

Safety review should check beginner suitability, contraindications, impact level, difficulty, coaching cues, and whether the exercise is appropriate for its listed protocols. Evidence review should prefer consensus principles from exercise science and strength-and-conditioning practice rather than novelty.

## Committing changes

Data changes should be small and reviewable. Commit the CSV source changes and regenerated JSON exports together so the repository remains internally consistent.
