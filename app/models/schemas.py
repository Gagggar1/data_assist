from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ChartType = Literal["histogram", "bar", "line", "pie", "scatter"]
ActionType = Literal["preview", "analyze", "generate_chart", "generate_report", "save_summary"]


class ChartAction(BaseModel):
    type: Literal["generate_chart"] = "generate_chart"
    chart_type: ChartType = "bar"
    x_column: str | None = None
    y_column: str | None = None


class SimpleAction(BaseModel):
    type: ActionType

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        allowed = {"preview", "analyze", "generate_report", "save_summary"}
        if value not in allowed:
            raise ValueError(f"Unsupported action type: {value}")
        return value


class AIResponseSchema(BaseModel):
    assistant_message: str = Field(min_length=1)
    actions: list[dict[str, Any]] = Field(default_factory=list, max_length=4)

    @classmethod
    def normalize_actions(cls, actions: list[Any]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        allowed_types = {"preview", "analyze", "generate_chart", "generate_report", "save_summary"}
        allowed_charts = {"histogram", "bar", "line", "pie", "scatter"}

        for item in actions:
            if not isinstance(item, dict):
                continue
            action_type = str(item.get("type", "")).strip()
            if action_type not in allowed_types:
                continue

            if action_type == "generate_chart":
                chart_type = str(item.get("chart_type", "bar")).strip().lower()
                normalized.append(
                    {
                        "type": "generate_chart",
                        "chart_type": chart_type if chart_type in allowed_charts else "bar",
                        "x_column": cls._clean_text(item.get("x_column")),
                        "y_column": cls._clean_text(item.get("y_column")),
                    }
                )
            else:
                normalized.append({"type": action_type})

        return normalized[:4]

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
