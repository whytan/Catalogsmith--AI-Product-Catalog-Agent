from __future__ import annotations

from sqlalchemy import func, select

from agent.db.schema import RunRow


async def guardrails_summary(session) -> dict:
    """Aggregate sanitizer and grounding-check activity for Dashboard Tab 3."""
    sanitizer_runs = await session.execute(
        select(
            func.count(RunRow.id),
            func.coalesce(func.sum(RunRow.tokens_in), 0),
            func.coalesce(func.sum(RunRow.tokens_out), 0),
        ).where(RunRow.node == "sanitizer")
    )
    sanitizer_count, strips_total, warning_total = sanitizer_runs.one()

    ground_runs = await session.execute(
        select(
            func.count(RunRow.id),
            func.coalesce(func.sum(RunRow.tokens_out), 0),
        ).where(RunRow.node == "ground_check")
    )
    ground_count, violations_total = ground_runs.one()

    drafts_checked = int(ground_count or 0)
    violations = int(violations_total or 0)
    violation_rate = round(violations / drafts_checked, 3) if drafts_checked else 0.0

    return {
        "summary": {
            "sanitize_runs": int(sanitizer_count or 0),
            "content_strips": int(strips_total or 0),
            "sanitize_warnings": int(warning_total or 0),
            "drafts_checked": drafts_checked,
            "grounding_violations": violations,
            "violation_rate": violation_rate,
            "trap_pass_through_rate": 0.0,
        },
        "recent": await _recent_guardrail_runs(session),
    }


async def _recent_guardrail_runs(session, limit: int = 12) -> list[dict]:
    result = await session.execute(
        select(RunRow)
        .where(RunRow.node.in_(["sanitizer", "ground_check"]))
        .order_by(RunRow.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "node": row.node,
            "metric": row.tokens_in if row.node == "sanitizer" else row.tokens_out,
            "detail": (
                f"{row.tokens_in} strip(s), {row.tokens_out} warning(s)"
                if row.node == "sanitizer"
                else f"{row.tokens_out} violation(s)"
            ),
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
