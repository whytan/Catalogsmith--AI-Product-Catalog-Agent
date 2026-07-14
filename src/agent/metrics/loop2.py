from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.db.schema import PersonaRow, SignalRow, loads_json
from agent.personas.miner import mine_signal_clusters


async def persona_dashboard(session: AsyncSession, *, limit: int = 50) -> dict[str, Any]:
    signal_counts = await session.execute(
        select(SignalRow.kind, func.count(SignalRow.id)).group_by(SignalRow.kind)
    )
    by_kind = {kind: count for kind, count in signal_counts.all()}

    recent = await session.execute(
        select(SignalRow, PersonaRow)
        .outerjoin(PersonaRow, PersonaRow.id == SignalRow.persona_id)
        .order_by(SignalRow.created_at.desc())
        .limit(limit)
    )

    rows: list[dict[str, Any]] = []
    for signal, persona in recent.all():
        payload = loads_json(signal.payload)
        rows.append(
            {
                "product_id": signal.product_id,
                "persona": persona.name if persona else "unknown",
                "kind": signal.kind,
                "synthetic": payload.get("synthetic", True),
                "text": payload.get("text") or payload.get("note") or payload.get("action", ""),
                "theme": payload.get("theme"),
                "created_at": signal.created_at.isoformat(),
            }
        )

    clusters = [cluster.to_dict() for cluster in await mine_signal_clusters(session)]

    return {
        "synthetic": True,
        "summary": {
            "total_signals": sum(by_kind.values()),
            "questions": by_kind.get("question", 0),
            "reviews": by_kind.get("review", 0),
            "views": by_kind.get("view", 0),
            "cart": by_kind.get("cart", 0),
            "clusters": len(clusters),
        },
        "recent": rows,
        "clusters": clusters[:12],
    }


async def loop2_summary(session: AsyncSession) -> dict[str, Any]:
    persona_data = await persona_dashboard(session, limit=20)
    return {
        "synthetic": True,
        "personas": persona_data,
        "note": "Loop 2 metrics are SYNTHETIC and never used for resume numbers.",
    }
