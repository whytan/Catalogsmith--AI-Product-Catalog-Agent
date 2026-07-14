from __future__ import annotations

import json
import time
from typing import Any

from openai import AsyncAzureOpenAI, AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from agent.config import settings
from agent.llm.cost import LLMUsage, estimate_cost, log_run


class LLMError(Exception):
    pass


def _use_responses_api(deployment: str) -> bool:
    """GPT-5+ hackathon deployments use the Responses API, not chat completions."""
    return "gpt-5" in deployment.lower()


def _responses_client_config() -> tuple[str, dict[str, str] | None]:
    """Return (base_url, default_query) for the Azure Responses API.

    Preview/hackathon resources use ``/openai/responses?api-version=...``.
    GA resources use ``/openai/v1/responses`` with no query param.
    """
    base = settings.azure_openai_endpoint.rstrip("/")
    version = settings.azure_openai_api_version
    if "preview" in version.lower():
        return f"{base}/openai/", {"api-version": version}
    return f"{base}/openai/v1/", None


class AzureLLMClient:
    """Thin Azure OpenAI wrapper — all LLM calls go through here."""

    def __init__(self) -> None:
        if not settings.azure_configured and not settings.llm_mock:
            raise LLMError(
                "Azure OpenAI is not configured. Set AZURE_OPENAI_ENDPOINT and "
                "AZURE_OPENAI_API_KEY in .env, or set LLM_MOCK=1 for offline mode."
            )
        self._chat_client: AsyncAzureOpenAI | None = None
        self._responses_client: AsyncOpenAI | None = None
        if settings.azure_configured:
            self._chat_client = AsyncAzureOpenAI(
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
                azure_endpoint=settings.azure_openai_endpoint,
            )
            responses_base, responses_query = _responses_client_config()
            self._responses_client = AsyncOpenAI(
                api_key=settings.azure_openai_api_key,
                base_url=responses_base,
                default_query=responses_query,
            )

    async def chat(
        self,
        *,
        session: AsyncSession,
        node: str,
        deployment: str,
        messages: list[dict[str, str]],
        product_id: int | None = None,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> tuple[str, LLMUsage]:
        if settings.llm_mock:
            return await self._mock_chat(session, node, deployment, messages, product_id)

        if _use_responses_api(deployment):
            return await self._chat_via_responses(
                session=session,
                node=node,
                deployment=deployment,
                messages=messages,
                product_id=product_id,
                temperature=temperature,
                json_mode=json_mode,
            )

        if self._chat_client is None:
            raise LLMError("Azure client is not initialized.")

        kwargs: dict[str, Any] = {
            "model": deployment,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        started = time.perf_counter()
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self._chat_client.chat.completions.create(**kwargs)
                break
            except Exception as exc:  # noqa: BLE001 — retry wrapper
                last_error = exc
                if attempt == 2:
                    raise LLMError(f"Azure OpenAI call failed after 3 attempts: {exc}") from exc
                time.sleep(0.5 * (attempt + 1))
        else:
            raise LLMError(f"Azure OpenAI call failed: {last_error}")

        latency_ms = int((time.perf_counter() - started) * 1000)
        choice = response.choices[0].message.content or ""
        usage = response.usage
        tokens_in = usage.prompt_tokens if usage else 0
        tokens_out = usage.completion_tokens if usage else 0

        llm_usage = LLMUsage(
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=estimate_cost(deployment, tokens_in, tokens_out),
            latency_ms=latency_ms,
            model=deployment,
        )
        await log_run(
            session,
            node=node,
            model=deployment,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            product_id=product_id,
        )
        return choice, llm_usage

    async def _chat_via_responses(
        self,
        *,
        session: AsyncSession,
        node: str,
        deployment: str,
        messages: list[dict[str, str]],
        product_id: int | None,
        temperature: float,  # unused: GPT-5 Responses API rejects this param
        json_mode: bool,
    ) -> tuple[str, LLMUsage]:
        if self._responses_client is None:
            raise LLMError("Azure Responses client is not initialized.")

        kwargs: dict[str, Any] = {
            "model": deployment,
            "input": messages,
            "max_output_tokens": 4096,
        }
        # GPT-5.x on Azure Responses API does not accept temperature.
        if json_mode:
            kwargs["text"] = {"format": {"type": "json_object"}}

        started = time.perf_counter()
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self._responses_client.responses.create(**kwargs)
                break
            except Exception as exc:  # noqa: BLE001 — retry wrapper
                last_error = exc
                if attempt == 2:
                    hint = (
                        f" Check AZURE_OPENAI_DEPLOYMENT_* in .env matches the exact "
                        f"deployment name in Azure Portal (case-sensitive). "
                        f"Tried deployment: {deployment!r}."
                    )
                    msg = str(exc)
                    if "DeploymentNotFound" in msg:
                        msg += hint
                    raise LLMError(f"Azure OpenAI call failed after 3 attempts: {msg}") from exc
                time.sleep(0.5 * (attempt + 1))
        else:
            raise LLMError(f"Azure OpenAI call failed: {last_error}")

        latency_ms = int((time.perf_counter() - started) * 1000)
        choice = response.output_text or ""
        usage = response.usage
        tokens_in = getattr(usage, "input_tokens", 0) if usage else 0
        tokens_out = getattr(usage, "output_tokens", 0) if usage else 0

        llm_usage = LLMUsage(
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=estimate_cost(deployment, tokens_in, tokens_out),
            latency_ms=latency_ms,
            model=deployment,
        )
        await log_run(
            session,
            node=node,
            model=deployment,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            product_id=product_id,
        )
        return choice, llm_usage

    async def _mock_chat(
        self,
        session: AsyncSession,
        node: str,
        deployment: str,
        messages: list[dict[str, str]],
        product_id: int | None,
    ) -> tuple[str, LLMUsage]:
        user_content = messages[-1]["content"] if messages else ""

        if node == "parse":
            from agent.pipeline.nodes.parse_heuristic import parse_heuristic

            facts = parse_heuristic(user_content)
            content = json.dumps(facts.model_dump(mode="json"))
        elif node == "draft":
            from agent.pipeline.nodes.parse_heuristic import parse_heuristic

            facts = parse_heuristic(user_content.split("---FACTS---")[0])
            features = ", ".join(facts.features[:2]) if facts.features else "quality design"
            content = (
                f"You get reliable everyday use from this {facts.category} pick, "
                f"with {features} built in for practical value."
            )
        else:
            content = "{}"

        llm_usage = LLMUsage(
            tokens_in=100,
            tokens_out=50,
            cost=estimate_cost(deployment, 100, 50),
            latency_ms=1,
            model=deployment,
        )
        await log_run(
            session,
            node=node,
            model=f"{deployment}-mock",
            tokens_in=100,
            tokens_out=50,
            latency_ms=1,
            product_id=product_id,
        )
        return content, llm_usage
