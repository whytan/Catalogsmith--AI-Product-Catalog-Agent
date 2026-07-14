from __future__ import annotations

from typing import Any

from agent.audit.service import log_feedback
from agent.db.session import SessionLocal
from agent.memory import store_feedback_in_memory


async def capture_node(state: dict[str, Any]) -> dict[str, Any]:
    """Record seller edits or comments before a redraft."""
    before = state.get("description", "")
    comment = state.get("gate_comment", "") or ""
    edited = state.get("edited_description")
    validated = state.get("validated") or {}
    category = validated.get("category", "")
    thread_id = state.get("thread_id")

    is_edit = bool(edited and str(edited).strip() and str(edited).strip() != before.strip())
    if is_edit:
        event_type = "edit"
        after = str(edited).strip()
    else:
        event_type = "comment"
        after = before

    async with SessionLocal() as session:
        await log_feedback(
            session,
            event_type=event_type,
            before=before,
            after=after,
            comment=comment,
            product_id=state.get("product_id"),
            thread_id=thread_id,
            category=category or None,
        )

    store_feedback_in_memory(
        category=category,
        before=before,
        after=after,
        comment=comment,
        thread_id=thread_id,
        product_id=state.get("product_id"),
    )

    updates: dict[str, Any] = {
        "revision_count": state.get("revision_count", 0) + 1,
        "draft_num": state.get("draft_num", 1) + 1,
    }
    if is_edit:
        updates["description"] = after

    return updates
