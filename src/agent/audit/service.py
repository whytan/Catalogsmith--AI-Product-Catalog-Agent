from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from agent.db.schema import ApprovalRow, FeedbackEventRow, utcnow


async def log_approval(
    session: AsyncSession,
    *,
    thread_id: str,
    action: str,
    draft_num: int,
    product_id: int | None = None,
    actor: str = "seller",
    first_draft: str = "",
    final_description: str = "",
) -> ApprovalRow:
    row = ApprovalRow(
        product_id=product_id,
        action=action,
        actor=actor,
        draft_num=draft_num,
        created_at=utcnow(),
    )
    session.add(row)
    if first_draft and final_description and product_id:
        session.add(
            FeedbackEventRow(
                product_id=product_id,
                thread_id=thread_id,
                category=None,
                type="publish_snapshot",
                before=first_draft,
                after=final_description,
                comment=f"thread:{thread_id}",
                created_at=utcnow(),
            )
        )
    await session.commit()
    await session.refresh(row)
    return row


async def log_feedback(
    session: AsyncSession,
    *,
    event_type: str,
    before: str,
    after: str,
    comment: str = "",
    product_id: int | None = None,
    thread_id: str | None = None,
    category: str | None = None,
) -> FeedbackEventRow:
    row = FeedbackEventRow(
        product_id=product_id,
        thread_id=thread_id,
        category=category,
        type=event_type,
        before=before,
        after=after,
        comment=comment,
        created_at=utcnow(),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row
