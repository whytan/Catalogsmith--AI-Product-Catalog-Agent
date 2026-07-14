"""Deterministic acceptance rubric for learning ablation.

Measures the mechanically-checkable subset of seller style — not fuzzy taste
or grounding (those stay separate guardrail metrics).

Rules are frozen before ablation runs. Populate BANNED from voice_rules.yaml
and real reject comments in feedback_events.
"""

from __future__ import annotations

import re

# From config/voice_rules.yaml (plain-language, no-exclamation) plus common hype.
# Real gate comment on #15 was "highlight camera" — directive, not a ban phrase.
BANNED = (
    "best-in-class",
    "must-have",
    "game-changer",
    "game-changing",
    "revolutionary",
)

MAX_WORDS = 80


def rubric_violations(draft: str) -> list[str]:
    """Return machine-readable violation codes for a draft."""
    violations: list[str] = []
    words = draft.split()
    word_count = len(words)
    if word_count > MAX_WORDS:
        violations.append(f"length>{MAX_WORDS} ({word_count} words)")
    if "!" in draft:
        violations.append("exclamation_mark")
    if re.search(r"\b[A-Z]{3,}\b", draft):
        violations.append("all_caps_word")
    lowered = draft.lower()
    for phrase in BANNED:
        if phrase.lower() in lowered:
            violations.append(f"banned_phrase:{phrase}")
    return violations


def is_acceptable(draft: str) -> bool:
    return not rubric_violations(draft)


def format_rubric_feedback(violations: list[str]) -> str:
    """Reject comment fed back to the drafter on the next cycle."""
    if not violations:
        return ""
    return "Fix these checkable style violations before approval: " + "; ".join(violations)
