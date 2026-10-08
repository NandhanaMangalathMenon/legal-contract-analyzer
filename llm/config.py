from dataclasses import dataclass

from core.config import Settings, get_settings


@dataclass(frozen=True)
class LLMRuntimeConfig:
    provider: str
    model: str
    temperature: float
    frequency_penalty: float
    presence_penalty: float
    max_output_tokens: int
    embedding_model: str
    api_key: str


def load_llm_runtime(settings: Settings | None = None) -> LLMRuntimeConfig:
    settings = settings or get_settings()
    return LLMRuntimeConfig(
        provider=settings.llm_provider.lower(),
        model=settings.gemini_model,
        temperature=settings.model_temperature,
        frequency_penalty=settings.model_frequency_penalty,
        presence_penalty=settings.model_presence_penalty,
        max_output_tokens=settings.model_max_output_tokens,
        embedding_model=settings.embedding_model,
        api_key=settings.gemini_api_key,
    )
