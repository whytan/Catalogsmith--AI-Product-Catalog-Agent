"""Quick probe for Azure Responses API (GPT-5.x). Run: python scripts/probe-responses.py"""
from __future__ import annotations

import asyncio

from agent.config import settings
from openai import AsyncOpenAI


async def main() -> None:
    client = AsyncOpenAI(
        api_key=settings.azure_openai_api_key,
        base_url=f"{settings.azure_openai_endpoint.rstrip('/')}/openai/v1/",
    )
    response = await client.responses.create(
        model=settings.azure_openai_deployment_mini,
        input=[{"role": "user", "content": "Say hello in 3 words"}],
        max_output_tokens=50,
    )
    print("OK:", response.output_text)


if __name__ == "__main__":
    asyncio.run(main())
