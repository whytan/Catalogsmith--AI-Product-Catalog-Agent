"""List Azure deployments and probe model name variants.

Run from project root:
  python scripts/probe-azure.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import httpx
from openai import AsyncOpenAI

from agent.config import settings
from agent.llm.azure import _responses_client_config


async def _probe_responses(label: str, base_url: str, query: dict[str, str] | None) -> str | None:
    print(f"--- Responses probe: {label} ---")
    print(f"    base_url={base_url!r}")
    print(f"    query={query!r}")
    client = AsyncOpenAI(
        api_key=settings.azure_openai_api_key,
        base_url=base_url,
        default_query=query,
    )
    candidates = [
        settings.azure_openai_deployment_mini,
        settings.azure_openai_deployment_frontier,
        "GPT-5.3",
        "gpt-5.3",
        "gpt-5.3-chat",
        "gpt-5-chat",
    ]
    seen: set[str] = set()
    for model in candidates:
        if not model or model in seen:
            continue
        seen.add(model)
        try:
            response = await client.responses.create(
                model=model,
                input=[{"role": "user", "content": "Say hello in 3 words"}],
                max_output_tokens=20,
            )
            print(f"SUCCESS model={model!r} -> {response.output_text!r}")
            return model
        except Exception as exc:
            print(f"FAIL model={model!r} -> {type(exc).__name__}: {exc}")
    return None


async def main() -> None:
    if not settings.azure_configured:
        print("Azure is not configured in .env")
        return

    base = settings.azure_openai_endpoint.rstrip("/")
    headers = {"api-key": settings.azure_openai_api_key}
    version = settings.azure_openai_api_version

    print(f"Endpoint: {base}")
    print(f"API version: {version}")
    print(f"Configured deployment: {settings.azure_openai_deployment_mini!r}")
    print()

    async with httpx.AsyncClient(timeout=30) as client:
        for path in ("/openai/deployments", "/openai/models"):
            url = f"{base}{path}?api-version={version}"
            response = await client.get(url, headers=headers)
            print(f"=== GET {path} -> HTTP {response.status_code} ===")
            if response.status_code == 200:
                data = response.json()
                items = data.get("data") or data.get("value") or []
                for item in items[:20]:
                    name = item.get("id") or item.get("name") or item.get("model")
                    print(f"  - {name}")
            else:
                print(response.text[:500])
            print()

    configured_base, configured_query = _responses_client_config()
    working = await _probe_responses("configured (.env)", configured_base, configured_query)
    if working:
        print(f"\nWorking deployment: {working}")
        print(f"Set in .env: AZURE_OPENAI_DEPLOYMENT_MINI={working}")
        print(f"               AZURE_OPENAI_DEPLOYMENT_FRONTIER={working}")
        return

    # Fallback probes when auto-config does not match the resource.
    working = await _probe_responses(
        "v1 (no api-version query)",
        f"{base}/openai/v1/",
        None,
    )
    if working:
        print(f"\nWorking deployment: {working}")
        print("Use AZURE_OPENAI_API_VERSION without 'preview' for v1 routing.")
        return

    working = await _probe_responses(
        "preview (/openai/responses)",
        f"{base}/openai/",
        {"api-version": version},
    )
    if working:
        print(f"\nWorking deployment: {working}")
        return

    print("\nNo candidate worked. Confirm GPT-5.3 is deployed on this resource in Azure Portal.")


if __name__ == "__main__":
    asyncio.run(main())
