from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from urllib.parse import quote

from fastapi import HTTPException, Request, status

from app.core.config import Settings, get_settings


def verify_api_key(request: Request, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if not settings.api_auth_key:
        return

    provided = request.headers.get("X-API-Key") or request.cookies.get("api_key")
    if not provided or not secrets.compare_digest(provided, settings.api_auth_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или отсутствующий API-ключ.",
        )


def _sign_payload(payload: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_download_token(artifact_name: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    expires_at = int(time.time()) + settings.download_token_ttl_seconds
    payload = f"{artifact_name}:{expires_at}"
    signature = _sign_payload(payload, settings.app_secret_key)
    return f"{quote(artifact_name, safe='')}:{expires_at}:{signature}"


def verify_download_token(token: str, artifact_name: str, settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    try:
        encoded_name, expires_raw, signature = token.split(":", 2)
        if encoded_name != quote(artifact_name, safe=""):
            return False
        expires_at = int(expires_raw)
    except ValueError:
        return False

    if expires_at < int(time.time()):
        return False

    payload = f"{artifact_name}:{expires_at}"
    expected = _sign_payload(payload, settings.app_secret_key)
    return hmac.compare_digest(signature, expected)


def build_download_url(artifact_name: str, settings: Settings | None = None, *, view: bool = False) -> str:
    token = create_download_token(artifact_name, settings)
    route = "artifacts" if view else "download"
    suffix = "/view" if view else ""
    return f"/{route}/{artifact_name}{suffix}?token={token}"
