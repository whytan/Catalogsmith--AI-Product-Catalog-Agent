from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

from agent.categories import VALID_CATEGORIES

VOICE_RULES_CANDIDATES = (
    Path(__file__).resolve().parents[3] / "config" / "voice_rules.yaml",
    Path.cwd() / "config" / "voice_rules.yaml",
)


def _resolve_voice_rules_path(path: Path | None = None) -> Path | None:
    if path is not None:
        return path if path.exists() else None
    for candidate in VOICE_RULES_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def load_voice_rules(path: Path | None = None) -> list[str]:
    """Load seller voice rules from YAML. Weekend 4 moves this to Chroma retrieval."""
    rules_path = _resolve_voice_rules_path(path)
    if rules_path is None:
        return []
    data = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
    rules = data.get("rules", [])
    return [rule["text"] for rule in rules if isinstance(rule, dict) and rule.get("text")]


def format_voice_rules_for_prompt(rules: list[str]) -> str:
    if not rules:
        return "Write clear, benefit-led product copy."
    return "\n".join(f"- {rule}" for rule in rules)
