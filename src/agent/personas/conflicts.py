from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.db.schema import FeedbackEventRow, SignalRow, loads_json
from agent.personas.miner import SignalCluster


async def detect_loop_conflicts(session: AsyncSession, *, product_id: int) -> list[dict[str, Any]]:
    """Surface tension between seller feedback style and persona preferences."""
    feedback = await session.execute(
        select(FeedbackEventRow)
        .where(FeedbackEventRow.product_id == product_id)
        .order_by(FeedbackEventRow.created_at.desc())
        .limit(10)
    )
    seller_comments = " ".join(row.comment.lower() for row in feedback.scalars().all() if row.comment)

    signals = await session.execute(
        select(SignalRow).where(SignalRow.product_id == product_id, SignalRow.kind.in_(["question", "review"]))
    )
    persona_text = " ".join(
        loads_json(row.payload).get("text", "").lower() for row in signals.scalars().all()
    )

    conflicts: list[dict[str, Any]] = []

    if "shorter" in seller_comments and ("detail" in persona_text or "spec" in persona_text):
        conflicts.append(
            {
                "type": "length",
                "seller_preference": "shorter copy",
                "persona_preference": "more specs and detail",
                "message": "Seller wants shorter text, but spec-reader personas ask for more detail.",
            }
        )

    if "no exclamation" in seller_comments and "gift" in persona_text:
        conflicts.append(
            {
                "type": "tone",
                "seller_preference": "no exclamation marks",
                "persona_preference": "warmer gift-oriented tone",
                "message": "Seller tone is restrained; gift personas want warmer reassurance.",
            }
        )

    if "price" in persona_text and "punch" in seller_comments:
        conflicts.append(
            {
                "type": "value_framing",
                "seller_preference": "punchier marketing",
                "persona_preference": "price transparency",
                "message": "Seller asked for punchier copy; bargain personas focus on price clarity.",
            }
        )

    if not conflicts and persona_text:
        conflicts.append(
            {
                "type": "none",
                "message": "No major Loop 1 vs Loop 2 style conflict detected for this product.",
            }
        )

    return conflicts


def top_cluster(clusters: list[SignalCluster]) -> SignalCluster | None:
    return clusters[0] if clusters else None
