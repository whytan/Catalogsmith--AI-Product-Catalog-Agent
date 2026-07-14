from __future__ import annotations

from agent.memory.feedback_store import add_feedback_memory
from agent.memory.voice_store import retrieve_voice_rules
from agent.memory.voice import format_voice_rules_for_prompt


def format_feedback_for_prompt(memories: list[str]) -> str:
    if not memories:
        return "No prior seller feedback for this category yet."
    return "\n".join(f"- {memory}" for memory in memories)


def format_retrieved_voice(voice_rules: list[str] | None = None, *, category: str) -> str:
    rules = voice_rules if voice_rules is not None else retrieve_voice_rules(category=category, limit=5)
    return format_voice_rules_for_prompt(rules)


def store_feedback_in_memory(
    *,
    category: str,
    before: str,
    after: str,
    comment: str,
    thread_id: str | None,
    product_id: int | None = None,
) -> None:
    from agent.config import settings

    if not settings.memory_enabled:
        return
    if not comment and before == after:
        return
    add_feedback_memory(
        category=category,
        before=before,
        after=after,
        comment=comment,
        thread_id=thread_id,
        product_id=product_id,
    )
