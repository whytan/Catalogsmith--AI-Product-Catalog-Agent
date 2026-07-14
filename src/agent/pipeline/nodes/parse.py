from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from agent.config import settings
from agent.llm.azure import AzureLLMClient
from agent.models.product import ProductFacts

PARSE_SYSTEM = """You extract product facts from raw seller input.
Return ONLY valid JSON with this schema:
{
  "name": "string",
  "price": number or null,
  "category": "electronics|kitchen|beauty|",
  "features": ["string"],
  "ingredients": ["string"],
  "materials": ["string"],
  "photo_filename": "string"
}
Rules:
- price must be a positive number in INR if present (no currency symbol in JSON); use null if price is not in the input
- category must be one of: electronics, kitchen, beauty — infer electronics for phones/tablets/smartphones
- extract name from "Model Name" or product title when present
- for long spec sheets, put the most important highlights in features (storage, camera, battery, display, OS)
- do not invent facts not present in the input
- photo_filename only if a photo/image/filename is mentioned
"""


async def parse_node(
    raw_text: str,
    session: AsyncSession,
    llm: AzureLLMClient | None = None,
) -> ProductFacts:
    raw_text = raw_text.strip()
    if not raw_text:
        raise ValueError("Input is empty.")

    if settings.llm_mock:
        client = llm or AzureLLMClient()
        content, _usage = await client.chat(
            session=session,
            node="parse",
            deployment=settings.azure_openai_deployment_mini,
            messages=[
                {"role": "system", "content": PARSE_SYSTEM},
                {"role": "user", "content": raw_text},
            ],
            json_mode=True,
            temperature=0.0,
        )
        return parse_llm_json(content)

    client = llm or AzureLLMClient()
    content, _usage = await client.chat(
        session=session,
        node="parse",
        deployment=settings.azure_openai_deployment_mini,
        messages=[
            {"role": "system", "content": PARSE_SYSTEM},
            {"role": "user", "content": raw_text},
        ],
        json_mode=True,
        temperature=0.0,
    )
    return parse_llm_json(content)


def parse_llm_json(content: str) -> ProductFacts:
    """Parse and normalize LLM JSON output into ProductFacts."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Parser returned invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Parser JSON must be an object.")

    return ProductFacts.model_validate(data)
