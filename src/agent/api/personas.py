from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from agent.db.session import get_session
from agent.metrics.loop2 import loop2_summary, persona_dashboard
from agent.personas.conflicts import detect_loop_conflicts
from agent.personas.miner import mine_signal_clusters, propose_rewrite, question_frequency
from agent.personas.orchestrate import Loop2Error, run_loop2_flow
from agent.personas.panel import run_persona_panel

router = APIRouter(prefix="/api/personas", tags=["personas"])


def _agent(request: Request):
    session = getattr(request.app.state, "agent_session", None)
    if session is None:
        raise HTTPException(status_code=503, detail="Agent session not initialized")
    return session


@router.post("/panel/run")
async def api_run_panel(
    session: AsyncSession = Depends(get_session),
    limit: int = 5,
):
    return await run_persona_panel(session, limit=limit)


@router.get("/signals")
async def api_persona_signals(session: AsyncSession = Depends(get_session)):
    return await persona_dashboard(session)


@router.get("/clusters")
async def api_signal_clusters(
    session: AsyncSession = Depends(get_session),
    product_id: int | None = None,
):
    clusters = await mine_signal_clusters(session, product_id=product_id)
    return {"synthetic": True, "clusters": [cluster.to_dict() for cluster in clusters]}


@router.get("/rewrite/{product_id}")
async def api_rewrite_proposal(
    product_id: int,
    theme: str = "battery",
    session: AsyncSession = Depends(get_session),
):
    return await propose_rewrite(session, product_id, theme)


@router.get("/conflicts/{product_id}")
async def api_loop_conflicts(product_id: int, session: AsyncSession = Depends(get_session)):
    return {"synthetic": True, "conflicts": await detect_loop_conflicts(session, product_id=product_id)}


@router.post("/rewrite/{product_id}/start")
async def api_start_rewrite(
    request: Request,
    product_id: int,
    theme: str = "battery",
    session: AsyncSession = Depends(get_session),
):
    proposal = await propose_rewrite(session, product_id, theme)
    agent = _agent(request)
    thread_id, gate = await agent.start_rewrite(
        product_id=product_id,
        proposed_description=proposal["proposed_description"],
        reason=proposal["reason"],
    )
    return {
        "synthetic": True,
        "thread_id": thread_id,
        "gate": gate,
        "gate_url": f"/app?thread={thread_id}",
        "questions_before": await question_frequency(session, product_id=product_id, theme=theme),
    }


@router.get("/loop2/summary")
async def api_loop2_summary(session: AsyncSession = Depends(get_session)):
    return await loop2_summary(session)


@router.post("/loop2/run")
async def api_run_loop2(
    request: Request,
    session: AsyncSession = Depends(get_session),
    limit: int = 5,
    product_id: int | None = None,
    theme: str | None = None,
    run_panel: bool = True,
):
    """Panel → mine → rewrite gate — one call, then open ``gate_url`` in /app."""
    agent = _agent(request)
    try:
        return await run_loop2_flow(
            session,
            agent,
            limit=limit,
            product_id=product_id,
            theme=theme,
            run_panel=run_panel,
        )
    except Loop2Error as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
