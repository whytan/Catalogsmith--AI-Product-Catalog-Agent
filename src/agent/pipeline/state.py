from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class PipelineState(TypedDict, total=False):
    thread_id: str
    raw_text: str
    facts: dict[str, Any] | None
    validated: dict[str, Any] | None
    validation_issues: list[dict[str, str]]
    description: str
    draft_num: int
    revision_count: int
    gate_action: str | None
    gate_comment: str | None
    edited_description: str | None
    product_id: int | None
    first_draft: str | None
    voice_memories: list[str]
    feedback_memories: list[str]
    sanitization_stripped: list[str]
    sanitization_warnings: list[str]
    grounding_violations: list[dict[str, str]]
    rewrite_product_id: int | None
    rewrite_reason: str | None
    seller_photo_filename: str
    status: str
    error: str | None
    messages: Annotated[list[dict[str, str]], add_messages]


MAX_REVISIONS = 5
