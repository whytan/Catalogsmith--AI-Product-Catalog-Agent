from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver
from sqlalchemy import update

from agent.audit.service import log_approval, log_feedback
from agent.db.schema import RunRow, utcnow
from agent.db.session import SessionLocal
from agent.llm.cost import total_cost_for_product
from agent.guardrails.sanitize import sanitize_product_facts
from agent.models.product import ProductFacts
from agent.pipeline.nodes.enrich_facts import enrich_facts_from_raw
from agent.pipeline.nodes.sanitize_price import sanitize_parsed_price
from agent.pipeline.nodes.capture import capture_node
from agent.pipeline.nodes.facts_gate import facts_gate_node
from agent.pipeline.nodes.draft import draft_node
from agent.pipeline.nodes.gate import gate_node
from agent.pipeline.nodes.ground_check import ground_check_node
from agent.pipeline.nodes.parse import parse_node
from agent.pipeline.nodes.publish import publish_node
from agent.pipeline.nodes.retrieve import retrieve_state
from agent.pipeline.nodes.sanitize_input import sanitize_input_node
from agent.pipeline.nodes.validate import (
    ValidatedProduct,
    format_validation_issues,
    validate_facts_structural,
)
from agent.pipeline.state import MAX_REVISIONS, PipelineState


async def parse_state(state: PipelineState) -> dict[str, Any]:
    async with SessionLocal() as session:
        facts = await parse_node(state["raw_text"], session)
    facts, _sanitize_meta = sanitize_product_facts(facts)
    facts = enrich_facts_from_raw(facts, state["raw_text"])
    facts = sanitize_parsed_price(facts, state["raw_text"])
    seller_photo = (state.get("seller_photo_filename") or "").strip()
    if seller_photo and not facts.photo_filename.strip():
        facts = facts.model_copy(update={"photo_filename": seller_photo})
    return {
        "facts": facts.model_dump(mode="json"),
        "status": "parsed",
        "messages": [{"role": "assistant", "content": "Parsed product facts from your input."}],
    }


async def validate_state(state: PipelineState) -> dict[str, Any]:
    facts = ProductFacts.model_validate(state["facts"])
    result = validate_facts_structural(facts)
    if not result.ok or result.product is None:
        return {
            "validation_issues": [issue.model_dump() for issue in result.issues],
            "status": "needs_facts",
            "messages": [
                {
                    "role": "assistant",
                    "content": format_validation_issues(result.issues, facts),
                }
            ],
        }

    from agent.adapter.sqlite import SQLiteStorefrontAdapter

    async with SessionLocal() as session:
        adapter = SQLiteStorefrontAdapter(session)
        if await adapter.name_exists(result.product.name):
            raise ValueError(f"A product named '{result.product.name}' already exists.")

    validated = result.product
    return {
        "validated": validated.model_dump(mode="json"),
        "validation_issues": [],
        "status": "validated",
        "messages": [{"role": "assistant", "content": f"Validated: {validated.name} ({validated.category})."}],
    }


def route_after_validate(state: PipelineState) -> str:
    if state.get("validated"):
        return "retrieve"
    return "facts_gate"


async def retrieve_state_node(state: PipelineState) -> dict[str, Any]:
    return await retrieve_state(state)


async def draft_state(state: PipelineState) -> dict[str, Any]:
    product = ValidatedProduct.model_validate(state["validated"])
    draft_num = state.get("draft_num", 1)

    if state.get("rewrite_product_id"):
        description = state.get("description", "")
        comment = (state.get("gate_comment") or "").lower()
        if "shorter" in comment:
            description = " ".join(description.split()[:18])
        if draft_num > 1 and comment:
            description = f"{description} (revised after seller feedback)"
        updates: dict[str, Any] = {
            "description": description.strip(),
            "draft_num": draft_num,
            "status": "awaiting_gate",
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Loop 2 rewrite draft #{draft_num} is ready for your review.",
                }
            ],
        }
        if draft_num == 1:
            updates["first_draft"] = state.get("first_draft") or description
        return updates

    manual_edit = state.get("edited_description")
    if manual_edit and str(manual_edit).strip() and draft_num > 1:
        description = str(manual_edit).strip()
        updates: dict[str, Any] = {
            "description": description,
            "draft_num": draft_num,
            "status": "awaiting_gate",
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Draft #{draft_num} saved your edit and is ready for review.",
                }
            ],
        }
        return updates

    feedback = list(state.get("feedback_memories") or [])
    comment = (state.get("gate_comment") or "").strip()
    if draft_num > 1 and comment:
        if not any(comment.lower() in memory.lower() for memory in feedback):
            feedback = [comment, *feedback]

    previous_description = state.get("description", "") if draft_num > 1 else None
    revision_comment = comment if draft_num > 1 and comment else None

    async with SessionLocal() as session:
        description = await draft_node(
            product,
            session,
            voice_rules=state.get("voice_memories"),
            feedback_memories=feedback,
            previous_description=previous_description,
            revision_comment=revision_comment,
        )
    draft_num = state.get("draft_num", 1)
    updates: dict[str, Any] = {
        "description": description,
        "draft_num": draft_num,
        "status": "awaiting_gate",
        "messages": [
            {
                "role": "assistant",
                "content": f"Draft #{draft_num} is ready for your review at the gate.",
            }
        ],
    }
    if draft_num == 1:
        updates["first_draft"] = description
    return updates


async def publish_state(state: PipelineState) -> dict[str, Any]:
    product = ValidatedProduct.model_validate(state["validated"])
    final_description = state.get("edited_description") or state.get("description", "")
    started_at = utcnow()

    async with SessionLocal() as session:
        if state.get("edited_description") and state["edited_description"] != state.get("description"):
            await log_feedback(
                session,
                event_type="edit",
                before=state.get("description", ""),
                after=final_description,
                comment=state.get("gate_comment", "") or "Manual edit at gate",
                thread_id=state.get("thread_id"),
                category=product.category,
            )

        if state.get("rewrite_product_id"):
            from agent.pipeline.nodes.publish import publish_rewrite_node

            published = await publish_rewrite_node(
                product_id=state["rewrite_product_id"],
                description=final_description,
            )
        else:
            published = await publish_node(product, final_description, session)
        await session.execute(
            update(RunRow)
            .where(RunRow.product_id.is_(None), RunRow.created_at >= started_at)
            .values(product_id=published.id)
        )
        await log_approval(
            session,
            thread_id=state.get("thread_id", ""),
            action="approve",
            draft_num=state.get("draft_num", 1),
            product_id=published.id,
            first_draft=state.get("first_draft", "") or state.get("description", ""),
            final_description=final_description,
        )
        await session.commit()
        cost = await total_cost_for_product(session, published.id)

    return {
        "product_id": published.id,
        "description": final_description,
        "status": "published",
        "messages": [
            {
                "role": "assistant",
                "content": (
                    f"Published {product.name} (ID {published.id}). "
                    f"Estimated LLM cost: ${cost:.6f}"
                ),
            }
        ],
    }


async def park_state(state: PipelineState) -> dict[str, Any]:
    async with SessionLocal() as session:
        await log_approval(
            session,
            thread_id=state.get("thread_id", ""),
            action="parked",
            draft_num=state.get("draft_num", 1),
        )
    return {
        "status": "parked",
        "messages": [
            {
                "role": "assistant",
                "content": "Reached the 5-round revision limit. Product parked as draft.",
            }
        ],
    }


def route_after_gate(state: PipelineState) -> str:
    if state.get("gate_action") == "approve":
        return "publish"
    if state.get("revision_count", 0) >= MAX_REVISIONS:
        return "park"
    return "capture"


def route_start(state: PipelineState) -> str:
    if state.get("rewrite_product_id"):
        return "ground_check"
    return "sanitize"


def build_graph(checkpointer: BaseCheckpointSaver):
    builder = StateGraph(PipelineState)

    builder.add_node("sanitize", sanitize_input_node)
    builder.add_node("parse", parse_state)
    builder.add_node("validate", validate_state)
    builder.add_node("facts_gate", facts_gate_node)
    builder.add_node("retrieve", retrieve_state_node)
    builder.add_node("draft", draft_state)
    builder.add_node("ground_check", ground_check_node)
    builder.add_node("gate", gate_node)
    builder.add_node("capture", capture_node)
    builder.add_node("publish", publish_state)
    builder.add_node("park", park_state)

    builder.add_conditional_edges(START, route_start, {
        "sanitize": "sanitize",
        "ground_check": "ground_check",
    })
    builder.add_edge("sanitize", "parse")
    builder.add_edge("parse", "validate")
    builder.add_conditional_edges("validate", route_after_validate, {
        "retrieve": "retrieve",
        "facts_gate": "facts_gate",
    })
    builder.add_edge("facts_gate", "validate")
    builder.add_edge("retrieve", "draft")
    builder.add_edge("draft", "ground_check")
    builder.add_edge("ground_check", "gate")
    builder.add_conditional_edges("gate", route_after_gate, {
        "publish": "publish",
        "capture": "capture",
        "park": "park",
    })
    builder.add_edge("capture", "retrieve")
    builder.add_edge("publish", END)
    builder.add_edge("park", END)

    return builder.compile(checkpointer=checkpointer)
