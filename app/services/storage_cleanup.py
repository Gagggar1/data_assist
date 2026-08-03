from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class StorageCleanupService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def cleanup_expired_files(self) -> dict[str, int]:
        if not self.settings.enable_storage_cleanup or self.settings.storage_ttl_days <= 0:
            return {"uploads": 0, "outputs": 0, "cache": 0}

        cutoff = datetime.now(tz=UTC) - timedelta(days=self.settings.storage_ttl_days)
        counts = {
            "uploads": self._cleanup_dir(self.settings.upload_dir, cutoff),
            "outputs": self._cleanup_dir(self.settings.output_dir, cutoff),
            "cache": self._cleanup_dir(self.settings.storage_dir / "cache", cutoff),
        }
        if any(counts.values()):
            logger.info("Storage cleanup removed files: %s", counts)
        return counts

    def _cleanup_dir(self, directory: Path, cutoff: datetime) -> int:
        if not directory.exists():
            return 0

        removed = 0
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
            if modified < cutoff:
                path.unlink(missing_ok=True)
                removed += 1
        return removed
