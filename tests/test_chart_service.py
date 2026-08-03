from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

from app.core.config import get_settings
from app.services.chart_service import ChartService
from app.services.file_service import FileService, StoredFile


def test_pie_and_scatter_generation(tmp_path: Path) -> None:
    settings = get_settings()
    upload_dir = tmp_path / "uploads"
    output_dir = tmp_path / "outputs"
    upload_dir.mkdir()
    output_dir.mkdir()

    src = Path("examples/sample_sales.csv")
    file_id = "testfile01"
    dest = upload_dir / f"{file_id}_sample_sales.csv"
    shutil.copy(src, dest)

    stored = StoredFile(
        file_id=file_id,
        original_name="sample_sales.csv",
        saved_name=f"{file_id}_sample_sales.csv",
        extension=".csv",
        content_type="text/csv",
        size_bytes=dest.stat().st_size,
        kind="table",
        created_at="2026-07-27T00:00:00+00:00",
        absolute_path=str(dest.resolve()),
        relative_path=f"uploads/{file_id}_sample_sales.csv",
    )

    file_service = FileService(settings)
    test_settings = replace(settings, upload_dir=upload_dir, output_dir=output_dir, storage_dir=tmp_path)
    object.__setattr__(file_service, "settings", test_settings)

    chart_service = ChartService(file_service, test_settings)
    pie = chart_service.generate_chart(stored, "pie", x_column="region", y_column="revenue")
    scatter = chart_service.generate_chart(stored, "scatter", x_column="revenue", y_column="orders")

    assert pie["file_name"].endswith(".png")
    assert scatter["file_name"].endswith(".png")
    assert (output_dir / pie["file_name"]).exists()
    assert (output_dir / scatter["file_name"]).exists()


def test_suggest_charts() -> None:
    settings = get_settings()
    file_service = FileService(settings)
    file_service.ensure_storage()
    chart_service = ChartService(file_service, settings)

    src = Path("examples/sample_sales.csv")
    file_id = "testsuggest"
    dest = settings.upload_dir / f"{file_id}_sample_sales.csv"
    shutil.copy(src, dest)
    stored = StoredFile(
        file_id=file_id,
        original_name="sample_sales.csv",
        saved_name=f"{file_id}_sample_sales.csv",
        extension=".csv",
        content_type="text/csv",
        size_bytes=dest.stat().st_size,
        kind="table",
        created_at="2026-07-27T00:00:00+00:00",
        absolute_path=str(dest.resolve()),
        relative_path=f"uploads/{file_id}_sample_sales.csv",
    )
    file_service._write_metadata(stored)

    suggestions = chart_service.suggest_charts(stored)
    assert suggestions
    assert any(item["chart_type"] == "pie" for item in suggestions)
