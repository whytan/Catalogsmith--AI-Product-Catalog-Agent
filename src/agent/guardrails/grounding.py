from __future__ import annotations

from dataclasses import dataclass

from agent.pipeline.nodes.validate import ValidatedProduct

CLAIM_CHECKS: list[tuple[str, list[str]]] = [
    ("waterproof", ["waterproof", "water-resistant", "water resistant"]),
    ("organic", ["organic"]),
    ("vegan", ["vegan"]),
    ("gluten-free", ["gluten-free", "gluten free"]),
    ("lifetime warranty", ["lifetime warranty", "lifetime guarantee"]),
    ("fda approved", ["fda approved", "fda-approved"]),
    ("hypoallergenic", ["hypoallergenic", "hypo-allergenic"]),
]


@dataclass
class GroundingViolation:
    claim: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"claim": self.claim, "message": self.message}


def facts_corpus(product: ValidatedProduct) -> str:
    parts = [product.name, product.category, str(product.price)]
    parts.extend(product.features)
    parts.extend(product.ingredients)
    parts.extend(product.materials)
    return " ".join(parts).lower()


def check_grounding(description: str, product: ValidatedProduct) -> list[GroundingViolation]:
    """Flag claims in the draft that are not supported by product facts."""
    if not description.strip():
        return []

    desc_lower = description.lower()
    corpus = facts_corpus(product)
    violations: list[GroundingViolation] = []

    for claim_id, phrases in CLAIM_CHECKS:
        for phrase in phrases:
            if phrase in desc_lower and phrase not in corpus:
                violations.append(
                    GroundingViolation(
                        claim=claim_id,
                        message=f"Unsupported claim '{phrase}' — not present in product facts",
                    )
                )
                break

    return violations
