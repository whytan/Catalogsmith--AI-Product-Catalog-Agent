from __future__ import annotations

from typing import Any

from agent.guardrails.sanitize import sanitize_text
from agent.llm.cost import log_run
from agent.pipeline.state import PipelineState


async def sanitize_input_node(state: PipelineState) -> dict[str, Any]:
    """Strip untrusted instruction-like content before parsing."""
    raw = state.get("raw_text", "")
    result = sanitize_text(raw)

    from agent.db.session import SessionLocal

    async with SessionLocal() as session:
        await log_run(
            session,
            node="sanitizer",
            model="local",
            tokens_in=len(result.stripped),
            tokens_out=len(result.warnings),
            latency_ms=0,
        )

    return {
        "raw_text": result.text,
        "sanitization_stripped": result.stripped,
        "sanitization_warnings": result.warnings,
        "messages": (
            [{"role": "assistant", "content": "Sanitized seller input before parsing."}]
            if result.stripped
            else []
        ),
    }
