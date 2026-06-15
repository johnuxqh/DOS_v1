# Clickable local demo

The P4.00 local demo is a simple Streamlit wireframe for clicking through the existing Deck of Sweat engine. It makes deck, template, equipment, composition, progression/regression, and optional history-adaptation output visible without changing the engine.

It is **not** the final app, production mobile UI, an authentication system, a subscription experience, or a new workout-generation layer.

## Install and run

From the repository root, install the demo dependency and launch Streamlit:

```bash
python -m pip install -e '.[demo]'
streamlit run app/demo.py
```

The terminal prints a local URL, normally `http://localhost:8501`.

## How it connects to the engine

`app/demo.py` calls the existing `build_workout` function in `scripts/generate_sample_workout.py`. It reads the same generated exports or CSV source fallback as the command-line sample generator. Selecting sample history passes `data/sample/sample_workout_history.json` to the existing history/adaptation engine. The demo only formats those results for display.

## Manual behaviours to test

- Generate workouts with several deck and template combinations.
- Leave equipment on template defaults, then choose explicit equipment and compare cards.
- Confirm composition slot names appear beside cards and under **Why this workout?**.
- Toggle progression/regression hints and confirm hints only appear when enabled.
- Enable sample history and confirm recent-exercise avoidance appears.
- Enable **Explain adaptation** and inspect adaptation notes.
- Expand **Debug/Data View** and compare its raw JSON with the visible workout.
- Try incompatible deck/template/equipment combinations and confirm the demo shows a readable engine error.
