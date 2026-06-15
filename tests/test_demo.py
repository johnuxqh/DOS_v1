"""Small non-rendering checks for the local demo helpers."""

from app.demo import deck_options, equipment_options, template_options


def test_demo_options_are_available_and_readable() -> None:
    assert ("free_beginner", "Free Beginner") in deck_options()
    assert ("beginner_full_body", "Beginner Full Body") in template_options()
    assert equipment_options()[0] == ("", "Use template defaults")
