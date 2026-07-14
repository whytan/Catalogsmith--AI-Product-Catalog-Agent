from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from agent.config import settings
from agent.llm.azure import AzureLLMClient
from agent.memory import format_feedback_for_prompt
from agent.memory.voice import format_voice_rules_for_prompt
from agent.pipeline.nodes.validate import ValidatedProduct

try:
    from eval.rubric import BANNED
except ImportError:
    BANNED = ("best-in-class", "must-have", "game-changer", "game-changing", "revolutionary")

DRAFT_SYSTEM = """You write product descriptions for an online store.
HARD RULE: only claim what is present in the provided facts JSON.
Apply seller feedback memories when they are relevant.
Return ONLY the description text — no markdown, no quotes, no preamble."""


def _facts_block(product: ValidatedProduct) -> str:
    return json.dumps(
        {
            "name": product.name,
            "category": product.category,
            "price_inr": str(product.price),
            "features": product.features,
            "ingredients": product.ingredients,
            "materials": product.materials,
            "photo_filename": product.photo_filename,
        },
        ensure_ascii=True,
        indent=2,
    )


def _apply_rubric_fixes(text: str, combined: str) -> str:
    import re

    if "exclamation" in combined:
        text = text.replace("!", "")
    if "length>" in combined or "shorter" in combined:
        text = " ".join(text.split()[:18])
    if "all_caps" in combined:
        text = re.sub(r"\b[A-Z]{3,}\b", lambda match: match.group().capitalize(), text)
    for phrase in BANNED:
        text = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE)
    return " ".join(text.split())


def _mock_draft_with_memory(
    product: ValidatedProduct,
    voice_rules: list[str],
    feedback_memories: list[str],
    *,
    previous_description: str | None = None,
    revision_comment: str | None = None,
) -> str:
    features = ", ".join(product.features[:2]) if product.features else "thoughtful design"
    text = (
        f"You get reliable everyday use from this {product.category} pick, "
        f"with {features} built in for practical value."
    )
    joined_feedback = " ".join(feedback_memories).lower()
    if revision_comment:
        joined_feedback = f"{revision_comment.lower()} {joined_feedback}"

    if previous_description and revision_comment and "shorter" not in joined_feedback:
        if "checkable style violations" not in revision_comment.lower():
            text = f"{text} Revised per seller feedback: {revision_comment.strip()}"

    if "shorter" in joined_feedback:
        text = " ".join(text.split()[:10])
    if "no exclamation" in joined_feedback or "no exclamation marks" in joined_feedback:
        text = text.replace("!", "")
    if "punchier" in joined_feedback or "punchy" in joined_feedback:
        text = text.replace("reliable everyday use", "solid everyday performance")
    if "battery" in joined_feedback and product.features:
        battery = next((f for f in product.features if "battery" in f.lower()), None)
        if battery:
            text = f"{text} {battery} keeps you going longer."

    if "no exclamation" in " ".join(voice_rules).lower():
        text = text.replace("!", "")

    if "checkable style violations" in joined_feedback or "banned_phrase" in joined_feedback:
        text = _apply_rubric_fixes(text, joined_feedback)

    if "grounding demo" in product.name.lower():
        text = f"{text} Fully waterproof for all conditions."

    return text.strip()


async def draft_node(
    product: ValidatedProduct,
    session: AsyncSession,
    llm: AzureLLMClient | None = None,
    product_id: int | None = None,
    *,
    voice_rules: list[str] | None = None,
    feedback_memories: list[str] | None = None,
    previous_description: str | None = None,
    revision_comment: str | None = None,
) -> str:
    voice = voice_rules or []
    feedback = feedback_memories or []
    rules_text = format_voice_rules_for_prompt(voice)
    feedback_text = format_feedback_for_prompt(feedback)
    facts_text = _facts_block(product)

    revision_block = ""
    if previous_description and revision_comment:
        revision_block = (
            f"\n\nPrevious draft (seller rejected this version):\n{previous_description}\n\n"
            f"Seller revision request (must address this):\n{revision_comment}\n\n"
            "Write a NEW description that clearly changes the draft to satisfy the request. "
            "Do not copy the previous draft verbatim."
        )

    user_prompt = (
        f"Store voice rules:\n{rules_text}\n\n"
        f"Seller feedback memories for this category:\n{feedback_text}\n\n"
        f"Product facts (only source of truth):\n{facts_text}\n\n"
        "Write the product description. Do not mention price unless it is essential to the pitch."
        f"{revision_block}"
    )

    if settings.llm_mock:
        description = _mock_draft_with_memory(
            product,
            voice,
            feedback,
            previous_description=previous_description,
            revision_comment=revision_comment,
        )
        from agent.llm.cost import log_run

        await log_run(
            session,
            node="draft",
            model=f"{settings.azure_openai_deployment_frontier}-mock",
            tokens_in=100,
            tokens_out=50,
            latency_ms=1,
            product_id=product_id,
        )
        return description

    client = llm or AzureLLMClient()
    description, _ = await client.chat(
        session=session,
        node="draft",
        deployment=settings.azure_openai_deployment_frontier,
        messages=[
            {"role": "system", "content": DRAFT_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        product_id=product_id,
        temperature=0.4,
    )
    return description.strip()
