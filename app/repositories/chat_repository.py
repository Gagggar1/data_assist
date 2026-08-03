from __future__ import annotations

import json
from typing import Any

from app.db.database import get_connection


class ChatRepository:
    def save(self, conversation: dict[str, Any]) -> None:
        conversation_id = conversation["conversation_id"]
        created_at = conversation.get("created_at", conversation.get("updated_at", ""))
        updated_at = conversation.get("updated_at", created_at)
        payload = json.dumps(conversation, ensure_ascii=False)

        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO conversations (conversation_id, data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(conversation_id) DO UPDATE SET
                    data = excluded.data,
                    updated_at = excluded.updated_at
                """,
                (conversation_id, payload, created_at, updated_at),
            )
            connection.commit()

    def get(self, conversation_id: str) -> dict[str, Any] | None:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT data FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
        if not row:
            return None
        return json.loads(row["data"])

    def delete(self, conversation_id: str) -> None:
        with get_connection() as connection:
            connection.execute(
                "DELETE FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            )
            connection.commit()
