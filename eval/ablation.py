"""Learning ablation — feedback memory ON vs OFF with a deterministic rubric gate."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from agent.config import settings
from agent.memory import store_feedback_in_memory
from agent.memory.chroma import reset_client, use_fresh_persistent_path
from agent.memory.retrieve import retrieve_memories
from agent.memory.voice_store import seed_voice_collection
from agent.pipeline.nodes.draft import draft_node
from agent.pipeline.nodes.validate import ValidatedProduct
from eval.fixtures import ABLATION_PRODUCTS
from eval.rubric import format_rubric_feedback, is_acceptable, rubric_violations

MAX_DRAFT_CYCLES = 5

Mode = Literal["mock", "azure"]


@dataclass
class ProductAblationResult:
    product_name: str
    category: str
    memory_on: bool
    edit_rate: int
    draft_cycles: int
    accepted: bool
    final_violations: list[str]
    violation_history: list[list[str]]


@dataclass
class ArmResult:
    memory_on: bool
    products: list[ProductAblationResult]

    @property
    def mean_edit_rate(self) -> float:
        if not self.products:
            return 0.0
        return sum(item.edit_rate for item in self.products) / len(self.products)


@dataclass
class AblationReport:
    run_id: str
    mode: Mode
    claim: str
    memory_on: ArmResult
    memory_off: ArmResult
    delta_mean_edit_rate: float
    memory_reduced_edits: bool
    n_products: int
    products_improved: int
    products_unchanged: int
    products_regressed: int
    note: str

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "claim": self.claim,
            "n_products": self.n_products,
            "products_improved": self.products_improved,
            "products_unchanged": self.products_unchanged,
            "products_regressed": self.products_regressed,
            "memory_on": {
                "mean_edit_rate": round(self.memory_on.mean_edit_rate, 3),
                "products": [asdict(p) for p in self.memory_on.products],
            },
            "memory_off": {
                "mean_edit_rate": round(self.memory_off.mean_edit_rate, 3),
                "products": [asdict(p) for p in self.memory_off.products],
            },
            "delta_mean_edit_rate": round(self.delta_mean_edit_rate, 3),
            "memory_reduced_edits": self.memory_reduced_edits,
            "note": self.note,
            "deployment": {
                "mini": settings.azure_openai_deployment_mini,
                "frontier": settings.azure_openai_deployment_frontier,
                "llm_mock": settings.llm_mock,
                "chroma_ephemeral": settings.chroma_ephemeral,
            },
        }


def _violating_probe_draft(product: ValidatedProduct) -> str:
    """First-pass draft that reliably trips the rubric (deterministic, not LLM)."""
    feature = product.features[0] if product.features else "everyday use"
    return (
        f"WOW!!! This {product.category} GAME-CHANGER is best-in-class and a must-have! "
        f"It delivers {feature} and more {feature} and even more {feature} for buyers who "
        f"want the absolute best premium experience every single day without compromise."
    )


async def _draft_cycle(
    session: AsyncSession,
    product: ValidatedProduct,
    *,
    memory_on: bool,
    draft_num: int,
    previous_description: str | None,
    revision_comment: str | None,
    probe_first_draft: bool,
) -> str:
    voice, feedback = await retrieve_memories(product, feedback_memory=memory_on)

    if probe_first_draft and draft_num == 1 and not revision_comment and not feedback:
        return _violating_probe_draft(product)

    return await draft_node(
        product,
        session,
        voice_rules=voice,
        feedback_memories=feedback,
        previous_description=previous_description,
        revision_comment=revision_comment,
    )


async def run_product_ablation(
    session: AsyncSession,
    product: ValidatedProduct,
    *,
    memory_on: bool,
    probe_first_draft: bool = True,
) -> ProductAblationResult:
    draft_num = 0
    revision_count = 0
    description = ""
    previous_description: str | None = None
    revision_comment: str | None = None
    violation_history: list[list[str]] = []

    while draft_num < MAX_DRAFT_CYCLES:
        draft_num += 1
        description = await _draft_cycle(
            session,
            product,
            memory_on=memory_on,
            draft_num=draft_num,
            previous_description=previous_description,
            revision_comment=revision_comment,
            probe_first_draft=probe_first_draft,
        )
        violations = rubric_violations(description)
        violation_history.append(violations)

        if is_acceptable(description):
            break

        if revision_count >= MAX_DRAFT_CYCLES - 1:
            break

        comment = format_rubric_feedback(violations)
        if memory_on:
            store_feedback_in_memory(
                category=product.category,
                before=description,
                after=description,
                comment=comment,
                thread_id=f"ablation-{uuid.uuid4().hex[:8]}",
            )

        previous_description = description
        revision_comment = comment
        revision_count += 1

    final_violations = rubric_violations(description)
    accepted = is_acceptable(description)
    edit_rate = max(draft_num - 1, 0) if accepted else MAX_DRAFT_CYCLES - 1

    return ProductAblationResult(
        product_name=product.name,
        category=product.category,
        memory_on=memory_on,
        edit_rate=edit_rate,
        draft_cycles=draft_num,
        accepted=accepted,
        final_violations=final_violations,
        violation_history=violation_history,
    )


async def run_arm(
    session: AsyncSession,
    products: list[ValidatedProduct],
    *,
    memory_on: bool,
    probe_first_draft: bool = True,
    arm_tag: str = "arm",
) -> ArmResult:
    if settings.chroma_ephemeral:
        reset_client()
    else:
        # Fresh on-disk path per arm — avoids delete_collection corrupting HNSW.
        use_fresh_persistent_path(f"data/chroma_ablation/{arm_tag}-{uuid.uuid4().hex[:8]}")
    seed_voice_collection()

    results: list[ProductAblationResult] = []
    for product in products:
        results.append(
            await run_product_ablation(
                session,
                product,
                memory_on=memory_on,
                probe_first_draft=probe_first_draft,
            )
        )
    return ArmResult(memory_on=memory_on, products=results)


def _distribution(off_arm: ArmResult, on_arm: ArmResult) -> tuple[int, int, int]:
    improved = unchanged = regressed = 0
    by_name_off = {p.product_name: p.edit_rate for p in off_arm.products}
    for on in on_arm.products:
        off_rate = by_name_off.get(on.product_name)
        if off_rate is None:
            continue
        if on.edit_rate < off_rate:
            improved += 1
        elif on.edit_rate == off_rate:
            unchanged += 1
        else:
            regressed += 1
    return improved, unchanged, regressed


async def run_ablation(
    session: AsyncSession,
    products: list[ValidatedProduct] | None = None,
    *,
    probe_first_draft: bool = True,
    mode: Mode | None = None,
) -> AblationReport:
    """Run OFF then ON arms on the same product list (fresh Chroma per arm)."""
    catalog = products or ABLATION_PRODUCTS
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    resolved_mode: Mode = mode or ("mock" if settings.llm_mock else "azure")
    claim = (
        "plumbing_regression_only"
        if resolved_mode == "mock"
        else "learning_proof_checkable_style_rules"
    )

    off_arm = await run_arm(
        session, catalog, memory_on=False, probe_first_draft=probe_first_draft, arm_tag=f"{run_id}-off"
    )
    on_arm = await run_arm(
        session, catalog, memory_on=True, probe_first_draft=probe_first_draft, arm_tag=f"{run_id}-on"
    )

    delta = off_arm.mean_edit_rate - on_arm.mean_edit_rate
    improved, unchanged, regressed = _distribution(off_arm, on_arm)
    note = (
        "Deterministic rubric gate — measures checkable style rules only "
        "(length, punctuation, banned phrases). Not fuzzy taste or grounding. "
        + (
            "mode=mock — plumbing check, not proof."
            if resolved_mode == "mock"
            else "mode=azure — real deployment drafts."
        )
    )

    return AblationReport(
        run_id=run_id,
        mode=resolved_mode,
        claim=claim,
        memory_on=on_arm,
        memory_off=off_arm,
        delta_mean_edit_rate=delta,
        memory_reduced_edits=delta > 0,
        n_products=len(catalog),
        products_improved=improved,
        products_unchanged=unchanged,
        products_regressed=regressed,
        note=note,
    )


def write_report(report: AblationReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
