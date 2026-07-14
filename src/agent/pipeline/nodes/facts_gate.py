from __future__ import annotations

from typing import Any

from langgraph.types import interrupt

from agent.models.product import ProductFacts
from agent.pipeline.nodes.validate import apply_facts_completion


def facts_interrupt_payload(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "needs_facts",
        "thread_id": state.get("thread_id"),
        "facts": state.get("facts"),
        "issues": state.get("validation_issues", []),
    }


def facts_gate_node(state: dict[str, Any]) -> dict[str, Any]:
    """Pause for seller to supply missing required fields (e.g. price)."""
    completion = interrupt(facts_interrupt_payload(state))
    if not isinstance(completion, dict):
        completion = {}

    facts = ProductFacts.model_validate(state["facts"])
    facts = apply_facts_completion(facts, completion)
    return {
        "facts": facts.model_dump(mode="json"),
        "validation_issues": [],
        "status": "validating",
        "seller_photo_filename": facts.photo_filename,
    }
