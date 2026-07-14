from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agent.personas.conflicts import detect_loop_conflicts
from agent.personas.miner import mine_signal_clusters, propose_rewrite, question_frequency
from agent.personas.panel import run_persona_panel
from agent.pipeline.session import AgentSession


class Loop2Error(Exception):
    """Loop 2 orchestration failed — map to HTTP 400 in the API layer."""


async def run_loop2_flow(
    session: AsyncSession,
    agent: AgentSession,
    *,
    limit: int = 5,
    product_id: int | None = None,
    theme: str | None = None,
    run_panel: bool = True,
    panel_seed: int | None = 42,
) -> dict[str, Any]:
    """Run panel → mine top cluster → open rewrite gate in one shot."""
    panel_result: dict[str, Any] | None = None
    if run_panel:
        panel_result = await run_persona_panel(session, limit=limit, seed=panel_seed)
        if panel_result["products"] == 0:
            raise Loop2Error(
                "No published products found. Publish at least one listing via the agent console first."
            )

    clusters = await mine_signal_clusters(session, product_id=product_id)
    if not clusters:
        raise Loop2Error(
            "No persona question clusters yet. Publish products and run the panel, or increase --limit."
        )

    if product_id is not None and theme:
        target_product_id = product_id
        target_theme = theme
    elif product_id is not None:
        match = next((cluster for cluster in clusters if cluster.product_id == product_id), clusters[0])
        target_product_id = match.product_id
        target_theme = match.theme
    else:
        top = clusters[0]
        target_product_id = top.product_id
        target_theme = top.theme

    proposal = await propose_rewrite(session, target_product_id, target_theme)
    thread_id, gate = await agent.start_rewrite(
        product_id=target_product_id,
        proposed_description=proposal["proposed_description"],
        reason=proposal["reason"],
    )
    conflicts = await detect_loop_conflicts(session, product_id=target_product_id)

    return {
        "synthetic": True,
        "panel": panel_result,
        "cluster": {
            "product_id": target_product_id,
            "theme": target_theme,
            "count": next(
                (cluster.count for cluster in clusters if cluster.product_id == target_product_id and cluster.theme == target_theme),
                clusters[0].count,
            ),
        },
        "proposal": proposal,
        "conflicts": conflicts,
        "thread_id": thread_id,
        "gate": gate,
        "gate_url": f"/app?thread={thread_id}",
        "questions_before": await question_frequency(
            session, product_id=target_product_id, theme=target_theme
        ),
    }
