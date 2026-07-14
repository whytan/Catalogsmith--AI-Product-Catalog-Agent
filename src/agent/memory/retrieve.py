from __future__ import annotations

from agent.memory.feedback_store import retrieve_feedback_memories
from agent.memory.voice_store import retrieve_voice_rules
from agent.pipeline.nodes.validate import ValidatedProduct


async def retrieve_memories(
    product: ValidatedProduct,
    *,
    feedback_memory: bool | None = None,
) -> tuple[list[str], list[str]]:
    """Load top voice rules and category-filtered feedback memories."""
    from agent.config import settings

    use_feedback = settings.memory_enabled if feedback_memory is None else feedback_memory
    voice = retrieve_voice_rules(category=product.category, limit=5)
    if not use_feedback:
        return voice, []

    query = f"{product.name} {product.category} {' '.join(product.features[:3])}"
    feedback = retrieve_feedback_memories(category=product.category, query=query, limit=5)
    return voice, feedback
