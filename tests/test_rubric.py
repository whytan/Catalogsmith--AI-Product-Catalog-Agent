import os

os.environ["LLM_MOCK"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["CHROMA_EPHEMERAL"] = "1"

import pytest

from eval.rubric import format_rubric_feedback, is_acceptable, rubric_violations


def test_rubric_flags_length_exclamation_and_banned():
    draft = ("WOW!!! This electronics GAME-CHANGER is best-in-class. " * 14).strip()
    violations = rubric_violations(draft)
    assert any(v.startswith("length>") for v in violations)
    assert "exclamation_mark" in violations
    assert "all_caps_word" in violations
    assert any(v.startswith("banned_phrase:") for v in violations)
    assert not is_acceptable(draft)


def test_rubric_accepts_clean_short_draft():
    draft = "You get practical everyday use with thoughtful design built in."
    assert rubric_violations(draft) == []
    assert is_acceptable(draft)


def test_rubric_feedback_is_deterministic():
    violations = ["exclamation_mark", "banned_phrase:game-changer"]
    text = format_rubric_feedback(violations)
    assert "exclamation_mark" in text
    assert "game-changer" in text
