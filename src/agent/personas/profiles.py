from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "personas.yaml"


@dataclass(frozen=True)
class PersonaProfile:
    persona_id: str
    name: str
    focus: str
    question_templates: list[str]
    review_tone: str
    cart_threshold: int


def load_persona_profiles() -> list[PersonaProfile]:
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    personas = {item["id"]: item["name"] for item in data["personas"]}
    profiles: list[PersonaProfile] = []
    for persona_id, profile in data["profiles"].items():
        profiles.append(
            PersonaProfile(
                persona_id=persona_id,
                name=personas[persona_id],
                focus=profile["focus"],
                question_templates=profile["question_templates"],
                review_tone=profile["review_tone"],
                cart_threshold=int(profile["cart_threshold"]),
            )
        )
    return profiles
