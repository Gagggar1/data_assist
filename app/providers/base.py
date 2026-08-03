from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.services.file_service import StoredFile


@dataclass
class AIPlan:
    assistant_message: str
    actions: list[dict[str, Any]]


class LLMProvider(Protocol):
    @property
    def enabled(self) -> bool: ...

    @property
    def model_name(self) -> str: ...

    def plan_response(
        self,
        *,
        conversation_messages: list[dict[str, Any]],
        user_text: str,
        active_file: StoredFile | None,
        active_file_context: dict[str, Any] | None,
        system_prompt: str,
    ) -> AIPlan: ...
