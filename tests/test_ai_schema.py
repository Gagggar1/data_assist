from __future__ import annotations

from app.models.schemas import AIResponseSchema


def test_ai_response_normalizes_chart_actions() -> None:
    actions = AIResponseSchema.normalize_actions(
        [
            {"type": "generate_chart", "chart_type": "scatter", "x_column": "a", "y_column": "b"},
            {"type": "invalid"},
            {"type": "analyze"},
        ]
    )
    assert len(actions) == 2
    assert actions[0]["chart_type"] == "scatter"
    assert actions[1]["type"] == "analyze"


def test_ai_response_schema_parses_payload() -> None:
    payload = {"assistant_message": "Готово", "actions": [{"type": "preview"}]}
    schema = AIResponseSchema(
        assistant_message=str(payload["assistant_message"]),
        actions=AIResponseSchema.normalize_actions(payload["actions"]),
    )
    assert schema.assistant_message == "Готово"
    assert schema.actions[0]["type"] == "preview"
