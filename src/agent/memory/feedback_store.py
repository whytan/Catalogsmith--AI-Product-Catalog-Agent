from __future__ import annotations

import uuid
from datetime import UTC, datetime

from agent.memory.chroma import FEEDBACK_COLLECTION, get_collection


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def add_feedback_memory(
    *,
    category: str,
    before: str,
    after: str,
    comment: str,
    thread_id: str | None = None,
    product_id: int | None = None,
) -> str:
    collection = get_collection(FEEDBACK_COLLECTION)
    memory_id = f"fb-{uuid.uuid4().hex}"

    document_parts = [
        f"Category: {category}",
        f"Seller comment: {comment}" if comment else "",
        f"Before: {before}" if before else "",
        f"After: {after}" if after else "",
    ]
    document = "\n".join(part for part in document_parts if part)

    collection.add(
        ids=[memory_id],
        documents=[document],
        metadatas=[
            {
                "category": category,
                "comment": comment,
                "thread_id": thread_id or "",
                "product_id": product_id or 0,
                "created_at": _now_iso(),
            }
        ],
    )
    return memory_id


def retrieve_feedback_memories(*, category: str, query: str, limit: int = 5) -> list[str]:
    collection = get_collection(FEEDBACK_COLLECTION)
    if collection.count() == 0:
        return []

    raw = collection.get(where={"category": {"$eq": category}})
    if not raw["ids"]:
        return []

    # Recency-weighted pool, then semantic top-k
    items: list[tuple[str, str, str]] = []
    for doc, meta in zip(raw["documents"], raw["metadatas"], strict=False):
        if not doc or not meta:
            continue
        items.append((doc, meta.get("created_at", ""), meta.get("comment", "")))

    items.sort(key=lambda item: item[1], reverse=True)
    recent_docs = [item[0] for item in items[: max(limit * 3, limit)]]

    if not recent_docs:
        return []

    if len(recent_docs) <= limit:
        return [_summarize_feedback(doc) for doc in recent_docs]

    results = collection.query(
        query_texts=[query],
        n_results=limit,
        where={"category": {"$eq": category}},
    )
    documents = results.get("documents", [[]])[0]
    return [_summarize_feedback(doc) for doc in documents if doc]


def _summarize_feedback(document: str) -> str:
    lines = document.splitlines()
    comment_line = next((line for line in lines if line.startswith("Seller comment:")), "")
    if comment_line:
        return comment_line.replace("Seller comment:", "").strip()
    return document[:200]
