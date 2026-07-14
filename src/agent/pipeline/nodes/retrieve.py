from __future__ import annotations

from typing import Any

from agent.memory.retrieve import retrieve_memories
from agent.pipeline.nodes.validate import ValidatedProduct


async def retrieve_state(state: dict[str, Any]) -> dict[str, Any]:
    product = ValidatedProduct.model_validate(state["validated"])
    voice, feedback = await retrieve_memories(product)
    return {
        "voice_memories": voice,
        "feedback_memories": feedback,
        "status": "retrieved",
        "messages": [
            {
                "role": "assistant",
                "content": (
                    f"Retrieved {len(voice)} voice rules and "
                    f"{len(feedback)} feedback memories for {product.category}."
                ),
            }
        ],
    }
