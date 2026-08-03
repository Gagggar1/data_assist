from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import build_download_url
from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_endpoint() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert "llm_provider" in payload


def test_index_redirects_to_chat() -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/chat/")


def test_storage_is_not_publicly_mounted() -> None:
    response = client.get("/storage/outputs/anything.txt")
    assert response.status_code == 404


def test_artifact_download_requires_a_valid_signed_link() -> None:
    settings = get_settings()
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    artifact_name = "test__report.txt"
    (settings.output_dir / artifact_name).write_text("private", encoding="utf-8")

    denied = client.get(f"/download/{artifact_name}")
    allowed = client.get(build_download_url(artifact_name, settings))

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert allowed.content == b"private"
