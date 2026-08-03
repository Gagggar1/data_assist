from __future__ import annotations

from app.core.config import Settings, get_settings
from app.providers.base import LLMProvider
from app.providers.openai_provider import OpenAIProvider


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    provider_name = settings.llm_provider.lower()
    if provider_name == "openai":
        return OpenAIProvider(settings)
    raise ValueError(
        f"Провайдер '{provider_name}' пока не поддерживается. Доступен: openai."
    )
