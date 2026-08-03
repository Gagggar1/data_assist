import os
import shutil
import tempfile
from pathlib import Path

TEST_STORAGE_DIR = Path(tempfile.mkdtemp(prefix="data-assistant-tests-"))


def pytest_configure() -> None:
    """Keep the test suite independent from a developer's local storage."""
    os.environ["UPLOAD_DIR"] = str(TEST_STORAGE_DIR / "uploads")
    os.environ["OUTPUT_DIR"] = str(TEST_STORAGE_DIR / "outputs")
    os.environ["DATABASE_PATH"] = str(TEST_STORAGE_DIR / "data_assistant.db")


def pytest_unconfigure() -> None:
    shutil.rmtree(TEST_STORAGE_DIR, ignore_errors=True)


def pytest_sessionstart() -> None:
    from app.core.config import get_settings
    from app.db.database import init_db

    get_settings.cache_clear()
    init_db(get_settings())
