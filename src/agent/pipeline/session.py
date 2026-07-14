from __future__ import annotations

import uuid
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Command

from agent.adapter.sqlite import SQLiteStorefrontAdapter
from agent.db.session import SessionLocal
from agent.pipeline.graph import build_graph
from agent.pipeline.messages import serialize_messages
from agent.pipeline.nodes.facts_gate import facts_interrupt_payload
from agent.pipeline.nodes.gate import gate_interrupt_payload
from agent.pipeline.nodes.validate import ValidatedProduct
from agent.pipeline.state import PipelineState


class AgentSession:
    """Runs and resumes the LangGraph catalog pipeline."""

    def __init__(self, checkpointer: BaseCheckpointSaver) -> None:
        self._graph = build_graph(checkpointer)

    def _config(self, thread_id: str) -> dict[str, Any]:
        return {"configurable": {"thread_id": thread_id}}

    async def start(
        self,
        raw_text: str,
        *,
        photo_filename: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        thread_id = str(uuid.uuid4())
        initial: PipelineState = {
            "thread_id": thread_id,
            "raw_text": raw_text,
            "seller_photo_filename": (photo_filename or "").strip(),
            "draft_num": 1,
            "revision_count": 0,
            "status": "starting",
            "validation_issues": [],
            "voice_memories": [],
            "feedback_memories": [],
            "sanitization_stripped": [],
            "sanitization_warnings": [],
            "grounding_violations": [],
            "messages": [{"role": "user", "content": raw_text}],
        }
        await self._graph.ainvoke(initial, self._config(thread_id))
        return thread_id, await self.get_gate_payload(thread_id)

    async def start_rewrite(
        self,
        *,
        product_id: int,
        proposed_description: str,
        reason: str,
    ) -> tuple[str, dict[str, Any]]:
        async with SessionLocal() as session:
            adapter = SQLiteStorefrontAdapter(session)
            product = await adapter.get_product(product_id)
            if product is None:
                raise ValueError(f"Product {product_id} not found.")

        validated = ValidatedProduct(
            name=product.name,
            price=product.price,
            category=product.category,
            features=product.facts.features,
            ingredients=product.facts.ingredients,
            materials=product.facts.materials,
            photo_filename=product.facts.photo_filename,
        )
        thread_id = str(uuid.uuid4())
        initial: PipelineState = {
            "thread_id": thread_id,
            "raw_text": f"loop2-rewrite:{product_id}",
            "validated": validated.model_dump(mode="json"),
            "description": proposed_description,
            "first_draft": product.description,
            "rewrite_product_id": product_id,
            "rewrite_reason": reason,
            "draft_num": 1,
            "revision_count": 0,
            "status": "rewrite_proposed",
            "validation_issues": [],
            "voice_memories": [],
            "feedback_memories": [],
            "sanitization_stripped": [],
            "sanitization_warnings": [],
            "grounding_violations": [],
            "messages": [
                {
                    "role": "assistant",
                    "content": f"SYNTHETIC Loop 2 rewrite proposed: {reason}",
                }
            ],
        }
        await self._graph.ainvoke(initial, self._config(thread_id))
        return thread_id, await self.get_gate_payload(thread_id)

    async def attach_photo(self, thread_id: str, photo_filename: str) -> dict[str, Any]:
        photo_filename = photo_filename.strip()
        if not photo_filename:
            raise ValueError("photo_filename is required.")

        snapshot = await self._graph.aget_state(self._config(thread_id))
        if not snapshot.next:
            raise ValueError("No active session to attach a photo.")

        values = snapshot.values
        validated = dict(values.get("validated") or {})
        facts = dict(values.get("facts") or {})
        validated["photo_filename"] = photo_filename
        facts["photo_filename"] = photo_filename
        await self._graph.aupdate_state(
            self._config(thread_id),
            {"validated": validated, "facts": facts, "seller_photo_filename": photo_filename},
        )
        return await self.get_gate_payload(thread_id)

    async def resume(self, thread_id: str, decision: dict[str, Any]) -> dict[str, Any]:
        await self._graph.ainvoke(Command(resume=decision), self._config(thread_id))
        snapshot = await self._graph.aget_state(self._config(thread_id))

        if snapshot.next:
            return await self.get_gate_payload(thread_id)

        values = snapshot.values
        return {
            "type": "complete",
            "thread_id": thread_id,
            "status": values.get("status"),
            "product_id": values.get("product_id"),
            "description": values.get("description"),
            "messages": serialize_messages(values.get("messages")),
        }

    async def get_gate_payload(self, thread_id: str) -> dict[str, Any]:
        snapshot = await self._graph.aget_state(self._config(thread_id))
        values = snapshot.values
        if not snapshot.next:
            return {
                "type": "complete",
                "thread_id": thread_id,
                "status": values.get("status"),
                "product_id": values.get("product_id"),
                "description": values.get("description"),
                "messages": serialize_messages(values.get("messages")),
            }
        if values.get("status") == "needs_facts" and not values.get("validated"):
            return facts_interrupt_payload({**values, "thread_id": thread_id})
        return gate_interrupt_payload({**values, "thread_id": thread_id})

    async def get_messages(self, thread_id: str) -> list[dict[str, str]]:
        snapshot = await self._graph.aget_state(self._config(thread_id))
        return serialize_messages(snapshot.values.get("messages"))
