from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.db.schema import ApprovalRow, FeedbackEventRow, ProductRow


@dataclass
class LearningPoint:
    product_index: int
    product_id: int | None
    product_name: str
    edit_rate: int
    edit_distance: int
    approved_at: datetime


def _edit_distance(first_draft: str, final_text: str) -> int:
    if not first_draft:
        return 0
    return sum(1 for left, right in zip(first_draft, final_text, strict=False) if left != right) + abs(
        len(first_draft) - len(final_text)
    )


async def compute_learning_series(session: AsyncSession) -> list[LearningPoint]:
    approvals = await session.execute(
        select(ApprovalRow)
        .where(ApprovalRow.action == "approve")
        .order_by(ApprovalRow.created_at.asc())
    )
    rows = approvals.scalars().all()
    series: list[LearningPoint] = []

    for index, approval in enumerate(rows, start=1):
        product_name = f"Product #{approval.product_id or index}"
        if approval.product_id:
            product = await session.get(ProductRow, approval.product_id)
            if product:
                product_name = product.name

        snapshot = await session.execute(
            select(FeedbackEventRow)
            .where(
                FeedbackEventRow.product_id == approval.product_id,
                FeedbackEventRow.type == "publish_snapshot",
            )
            .order_by(FeedbackEventRow.created_at.desc())
        )
        snap = snapshot.scalar_one_or_none()
        first_draft = snap.before if snap else ""
        final_text = snap.after if snap else ""

        series.append(
            LearningPoint(
                product_index=index,
                product_id=approval.product_id,
                product_name=product_name,
                edit_rate=max(approval.draft_num - 1, 0),
                edit_distance=_edit_distance(first_draft, final_text),
                approved_at=approval.created_at,
            )
        )

    return series


async def learning_summary(session: AsyncSession) -> dict:
    series = await compute_learning_series(session)
    edit_rates = [point.edit_rate for point in series]
    edit_distances = [point.edit_distance for point in series]
    return {
        "points": [
            {
                "product_index": point.product_index,
                "product_id": point.product_id,
                "product_name": point.product_name,
                "edit_rate": point.edit_rate,
                "edit_distance": point.edit_distance,
                "approved_at": point.approved_at.isoformat(),
            }
            for point in series
        ],
        "summary": {
            "products": len(series),
            "avg_edit_rate": round(sum(edit_rates) / len(edit_rates), 2) if edit_rates else 0,
            "avg_edit_distance": round(sum(edit_distances) / len(edit_distances), 1) if edit_distances else 0,
            "latest_edit_rate": edit_rates[-1] if edit_rates else None,
            "first_edit_rate": edit_rates[0] if edit_rates else None,
        },
    }
