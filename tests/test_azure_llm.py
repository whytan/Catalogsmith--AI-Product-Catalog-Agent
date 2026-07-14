from agent.llm.azure import _responses_client_config, _use_responses_api


def test_use_responses_api_detects_gpt5() -> None:
    assert _use_responses_api("GPT-5.3") is True
    assert _use_responses_api("gpt-4o") is False


def test_responses_client_config_preview(monkeypatch) -> None:
    from agent.config import settings

    monkeypatch.setattr(settings, "azure_openai_endpoint", "https://example.openai.azure.com/")
    monkeypatch.setattr(settings, "azure_openai_api_version", "2025-04-01-preview")

    base, query = _responses_client_config()
    assert base == "https://example.openai.azure.com/openai/"
    assert query == {"api-version": "2025-04-01-preview"}


def test_responses_client_config_v1(monkeypatch) -> None:
    from agent.config import settings

    monkeypatch.setattr(settings, "azure_openai_endpoint", "https://example.openai.azure.com/")
    monkeypatch.setattr(settings, "azure_openai_api_version", "2024-10-21")

    base, query = _responses_client_config()
    assert base == "https://example.openai.azure.com/openai/v1/"
    assert query is None
