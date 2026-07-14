from __future__ import annotations

from typing import Any

from langgraph.types import interrupt


def gate_interrupt_payload(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "gate",
        "thread_id": state.get("thread_id"),
        "description": state.get("description", ""),
        "facts": state.get("validated"),
        "draft_num": state.get("draft_num", 1),
        "revision_count": state.get("revision_count", 0),
        "status": state.get("status"),
        "sanitization_warnings": state.get("sanitization_warnings", []),
        "grounding_violations": state.get("grounding_violations", []),
        "rewrite_reason": state.get("rewrite_reason"),
        "rewrite_product_id": state.get("rewrite_product_id"),
    }


def gate_node(state: dict[str, Any]) -> dict[str, Any]:
    """Human approval gate — pauses the graph until resumed."""
    decision = interrupt(gate_interrupt_payload(state))
    if not isinstance(decision, dict):
        decision = {"action": "approve"}

    return {
        "gate_action": decision.get("action", "approve"),
        "gate_comment": decision.get("comment", ""),
        "edited_description": decision.get("edited_description"),
    }
