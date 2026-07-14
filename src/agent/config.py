from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./data/catalog.db"
    store_name: str = "Catalogsmith"
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_ephemeral: bool = False

    @field_validator("chroma_ephemeral", mode="before")
    @classmethod
    def parse_chroma_ephemeral(cls, value: object) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @property
    def chroma_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"

    # Azure OpenAI (Weekend 2+)
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_deployment_frontier: str = "gpt-4o"
    azure_openai_deployment_mini: str = "gpt-4o-mini"

    # Offline / test mode — uses heuristic parser, mock draft
    llm_mock: bool = False

    # Planted regression — disables sanitizer so injection trap tests fail (CI proof)
    sanitizer_weak: bool = False

    # MCP storefront transport for publish path
    mcp_mode: str = "inline"

    # Disable feedback memory retrieval + storage (ablation OFF arm / A/B control)
    memory_off: bool = False

    @field_validator("memory_off", mode="before")
    @classmethod
    def parse_memory_off(cls, value: object) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @property
    def memory_enabled(self) -> bool:
        return not self.memory_off

    @field_validator("llm_mock", mode="before")
    @classmethod
    def parse_llm_mock(cls, value: object) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @field_validator("sanitizer_weak", mode="before")
    @classmethod
    def parse_sanitizer_weak(cls, value: object) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    # Pricing per 1M tokens (USD) for cost estimates
    frontier_input_cost_per_1m: float = 2.50
    frontier_output_cost_per_1m: float = 10.00
    mini_input_cost_per_1m: float = 0.15
    mini_output_cost_per_1m: float = 0.60

    @property
    def azure_configured(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)


settings = Settings()
