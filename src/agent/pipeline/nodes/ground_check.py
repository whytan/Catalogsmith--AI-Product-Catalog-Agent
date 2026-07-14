from __future__ import annotations

from typing import Any

from agent.guardrails.grounding import check_grounding
from agent.llm.cost import log_run
from agent.pipeline.nodes.validate import ValidatedProduct
from agent.pipeline.state import PipelineState


async def ground_check_node(state: PipelineState) -> dict[str, Any]:
    """Flag unsupported claims in the draft before the human gate."""
    product = ValidatedProduct.model_validate(state["validated"])
    description = state.get("description", "")
    violations = check_grounding(description, product)
    serialized = [item.to_dict() for item in violations]

    from agent.db.session import SessionLocal

    async with SessionLocal() as session:
        await log_run(
            session,
            node="ground_check",
            model="local",
            tokens_in=len(description),
            tokens_out=len(violations),
            latency_ms=0,
        )

    messages: list[dict[str, str]] = []
    if violations:
        summary = "; ".join(item.message for item in violations)
        messages.append(
            {
                "role": "assistant",
                "content": f"Grounding check flagged {len(violations)} issue(s): {summary}",
            }
        )

    return {
        "grounding_violations": serialized,
        "messages": messages,
    }
