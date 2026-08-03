from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import Settings, get_settings
from app.providers.base import AIPlan
from app.providers.factory import get_llm_provider

logger = logging.getLogger(__name__)


class AIServiceError(RuntimeError):
    """Base AI service error."""


class AIServiceConfigurationError(AIServiceError):
    """Raised when LLM is not configured."""


class AIServiceRequestError(AIServiceError):
    """Raised when the LLM API request fails."""


class AIService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._provider = get_llm_provider(self.settings)

    @property
    def enabled(self) -> bool:
        return self._provider.enabled

    @property
    def model_name(self) -> str:
        return self._provider.model_name

    def plan_response(
        self,
        *,
        conversation_messages: list,
        user_text: str,
        active_file,
        active_file_context: dict | None,
    ) -> AIPlan:
        if not self.enabled:
            raise AIServiceConfigurationError(
                "LLM не настроен. Добавьте OPENAI_API_KEY и проверьте LLM_PROVIDER."
            )

        try:
            return self._provider.plan_response(
                conversation_messages=conversation_messages,
                user_text=user_text,
                active_file=active_file,
                active_file_context=active_file_context,
                system_prompt=self._system_prompt(),
            )
        except RuntimeError as exc:
            raise AIServiceConfigurationError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover
            logger.exception("LLM request failed")
            raise AIServiceRequestError(str(exc)) from exc

    def _system_prompt(self) -> str:
        prompt_path = Path(__file__).resolve().parents[1] / "prompts" / f"{self.settings.prompt_role}.txt"
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8").strip()
        fallback = Path(__file__).resolve().parents[1] / "prompts" / "financial_analyst.txt"
        return fallback.read_text(encoding="utf-8").strip()
