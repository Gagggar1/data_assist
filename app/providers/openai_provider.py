from __future__ import annotations

import base64
import json
import logging
from typing import Any

from app.core.config import Settings, get_settings
from app.models.schemas import AIResponseSchema
from app.providers.base import AIPlan
from app.services.file_service import StoredFile

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


class OpenAIProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = None

    @property
    def enabled(self) -> bool:
        return bool(self.settings.openai_api_key) and OpenAI is not None

    @property
    def model_name(self) -> str:
        return self.settings.openai_model

    def plan_response(
        self,
        *,
        conversation_messages: list[dict[str, Any]],
        user_text: str,
        active_file: StoredFile | None,
        active_file_context: dict[str, Any] | None,
        system_prompt: str,
    ) -> AIPlan:
        if OpenAI is None:
            raise RuntimeError("Python-пакет openai не установлен.")
        if not self.settings.openai_api_key:
            raise RuntimeError("Не задан OPENAI_API_KEY.")

        client = self._get_client()
        response = client.responses.create(
            model=self.settings.openai_model,
            instructions=system_prompt,
            input=self._build_input(
                conversation_messages=conversation_messages,
                user_text=user_text,
                active_file=active_file,
                active_file_context=active_file_context,
            ),
        )
        return self._parse_response_text(getattr(response, "output_text", ""))

    def _get_client(self):
        if self._client is None:
            self._client = OpenAI(api_key=self.settings.openai_api_key)
        return self._client

    def _build_input(
        self,
        *,
        conversation_messages: list[dict[str, Any]],
        user_text: str,
        active_file: StoredFile | None,
        active_file_context: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        history = []
        for message in conversation_messages[-self.settings.openai_max_history_messages :]:
            history.append(
                {
                    "role": message.get("role", "assistant"),
                    "text": message.get("text", ""),
                }
            )

        current_request = user_text.strip() or "Пользователь загрузил файл без дополнительного текста."
        prompt_payload = {
            "current_user_message": current_request,
            "recent_messages": history,
            "active_file": active_file_context,
            "available_actions": [
                {"type": "preview"},
                {"type": "analyze"},
                {
                    "type": "generate_chart",
                    "chart_type": "histogram | bar | line | pie | scatter",
                    "x_column": "string | null",
                    "y_column": "string | null",
                },
                {"type": "generate_report"},
                {"type": "save_summary"},
            ],
            "response_contract": {
                "assistant_message": "string",
                "actions": "array",
            },
        }

        content: list[dict[str, Any]] = [
            {
                "type": "input_text",
                "text": (
                    "Верни только JSON без markdown-обёртки. "
                    "Строго следуй схеме из response_contract.\n\n"
                    + json.dumps(prompt_payload, ensure_ascii=False, indent=2)
                ),
            },
        ]

        if active_file and active_file.kind == "image":
            content.append(
                {
                    "type": "input_image",
                    "image_url": self._image_data_url(active_file),
                }
            )

        return [{"role": "user", "content": content}]

    def _parse_response_text(self, raw_text: str) -> AIPlan:
        text = (raw_text or "").strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            text = text.removeprefix("json").strip()

        try:
            payload = json.loads(text)
            schema = AIResponseSchema(
                assistant_message=str(payload.get("assistant_message", "")).strip() or "Готово.",
                actions=AIResponseSchema.normalize_actions(payload.get("actions", [])),
            )
            return AIPlan(assistant_message=schema.assistant_message, actions=schema.actions)
        except (json.JSONDecodeError, ValueError):
            logger.warning("OpenAI returned non-JSON output; falling back to plain text")
            return AIPlan(assistant_message=text or "Не удалось разобрать ответ модели.", actions=[])

    def _image_data_url(self, stored_file: StoredFile) -> str:
        mime_type = stored_file.content_type or "image/png"
        encoded = base64.b64encode(stored_file.path.read_bytes()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"
