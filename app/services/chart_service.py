from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from app.core.config import Settings, get_settings
from app.core.security import build_download_url
from app.services.file_service import FileReadError, FileService, StoredFile

logger = logging.getLogger(__name__)

SUPPORTED_CHARTS = {"line", "bar", "histogram", "pie", "scatter"}


class ChartService:
    def __init__(self, file_service: FileService, settings: Settings | None = None) -> None:
        self.file_service = file_service
        self.settings = settings or get_settings()

    def suggest_charts(self, stored_file: StoredFile) -> list[dict[str, Any]]:
        if stored_file.kind != "table":
            return [
                {"chart_type": "histogram", "reason": "Распределение яркости пикселей"},
                {"chart_type": "bar", "reason": "Средние значения каналов"},
            ]

        dataframe = self.file_service.read_dataframe(stored_file)
        columns = self.file_service.describe_columns(dataframe)
        numeric = [item["name"] for item in columns if item["kind"] == "numeric"]
        dimensions = [item["name"] for item in columns if item["kind"] in {"categorical", "datetime"}]
        suggestions: list[dict[str, Any]] = []

        if numeric:
            suggestions.append(
                {
                    "chart_type": "histogram",
                    "x_column": numeric[0],
                    "y_column": None,
                    "reason": f"Распределение «{numeric[0]}»",
                }
            )
        if dimensions and numeric:
            suggestions.append(
                {
                    "chart_type": "bar",
                    "x_column": dimensions[0],
                    "y_column": numeric[0],
                    "reason": f"Средние «{numeric[0]}» по «{dimensions[0]}»",
                }
            )
            suggestions.append(
                {
                    "chart_type": "pie",
                    "x_column": dimensions[0],
                    "y_column": numeric[0],
                    "reason": f"Доли «{numeric[0]}» по «{dimensions[0]}»",
                }
            )
        if len(numeric) >= 2:
            suggestions.append(
                {
                    "chart_type": "scatter",
                    "x_column": numeric[0],
                    "y_column": numeric[1],
                    "reason": f"Связь «{numeric[0]}» и «{numeric[1]}»",
                }
            )
        datetime_cols = [item["name"] for item in columns if item["kind"] == "datetime"]
        if datetime_cols and numeric:
            suggestions.append(
                {
                    "chart_type": "line",
                    "x_column": datetime_cols[0],
                    "y_column": numeric[0],
                    "reason": f"Динамика «{numeric[0]}» во времени",
                }
            )
        return suggestions[:5]

    def generate_chart(
        self,
        stored_file: StoredFile,
        chart_type: str,
        x_column: str | None = None,
        y_column: str | None = None,
    ) -> dict[str, Any]:
        chart_type = chart_type.lower()
        if chart_type not in SUPPORTED_CHARTS:
            raise FileReadError("Поддерживаются графики line, bar, histogram, pie и scatter.")

        self.file_service.ensure_storage()
        if stored_file.kind == "table":
            chart = self._generate_table_chart(stored_file, chart_type, x_column, y_column)
        else:
            chart = self._generate_image_chart(stored_file, chart_type)

        logger.info("Generated %s chart for %s", chart_type, stored_file.file_id)
        return chart

    def generate_default_charts(self, stored_file: StoredFile) -> list[dict[str, Any]]:
        charts: list[dict[str, Any]] = []
        for suggestion in self.suggest_charts(stored_file)[:2]:
            try:
                charts.append(
                    self.generate_chart(
                        stored_file,
                        suggestion["chart_type"],
                        x_column=suggestion.get("x_column"),
                        y_column=suggestion.get("y_column"),
                    )
                )
            except FileReadError:
                continue
        return charts

    def _artifact_record(self, chart_type: str, description: str, file_name: str) -> dict[str, Any]:
        return {
            "title": f"{chart_type.title()} chart",
            "description": description,
            "file_name": file_name,
            "relative_path": f"outputs/{file_name}",
            "storage_url": build_download_url(file_name, self.settings, view=True),
            "download_url": build_download_url(file_name, self.settings),
        }

    def _generate_table_chart(
        self,
        stored_file: StoredFile,
        chart_type: str,
        x_column: str | None,
        y_column: str | None,
    ) -> dict[str, Any]:
        dataframe = self.file_service.read_dataframe(stored_file)
        columns = self.file_service.describe_columns(dataframe)
        numeric_columns = [item["name"] for item in columns if item["kind"] == "numeric"]
        dimension_columns = [item["name"] for item in columns if item["kind"] in {"categorical", "datetime"}]

        selected_x = x_column or (dimension_columns or list(dataframe.columns))[0]
        selected_y = y_column or (numeric_columns or list(dataframe.columns))[0]
        file_name = self._build_output_name(stored_file.file_id, chart_type, "png")
        output_path = self.settings.output_dir / file_name

        figure, axis = plt.subplots(figsize=(10, 5.8), dpi=150)
        figure.patch.set_facecolor("#f8f3ea")
        axis.set_facecolor("#fffaf3")

        if chart_type == "histogram":
            if not numeric_columns:
                raise FileReadError("Для histogram нужен хотя бы один числовой столбец.")
            selected_x = x_column or numeric_columns[0]
            series = pd.to_numeric(dataframe[selected_x], errors="coerce").dropna()
            if series.empty:
                raise FileReadError("Недостаточно числовых значений для histogram.")
            bins = min(20, max(8, int(np.sqrt(len(series)))))
            axis.hist(series, bins=bins, color="#d06b4e", edgecolor="#8d3f28")
            axis.set_title(f"Histogram: {selected_x}")
            axis.set_xlabel(selected_x)
            axis.set_ylabel("Frequency")
            description = f"Распределение значений колонки «{selected_x}»."
        elif chart_type == "line":
            if not numeric_columns:
                raise FileReadError("Для line нужен хотя бы один числовой столбец.")
            plot_frame = dataframe[[selected_x, selected_y]].copy()
            plot_frame[selected_y] = pd.to_numeric(plot_frame[selected_y], errors="coerce")
            plot_frame = plot_frame.dropna(subset=[selected_y]).head(50)
            if plot_frame.empty:
                raise FileReadError("Недостаточно данных для line графика.")
            axis.plot(
                plot_frame[selected_x].astype(str),
                plot_frame[selected_y],
                color="#114b5f",
                linewidth=2.5,
                marker="o",
            )
            axis.set_title(f"Line chart: {selected_y} by {selected_x}")
            axis.set_xlabel(selected_x)
            axis.set_ylabel(selected_y)
            axis.tick_params(axis="x", rotation=35)
            description = f"Линейная динамика «{selected_y}» по оси «{selected_x}»."
        elif chart_type == "scatter":
            if len(numeric_columns) < 2:
                raise FileReadError("Для scatter нужны две числовые колонки.")
            x_name = x_column or numeric_columns[0]
            y_name = y_column or numeric_columns[1]
            plot_frame = dataframe[[x_name, y_name]].copy()
            plot_frame[x_name] = pd.to_numeric(plot_frame[x_name], errors="coerce")
            plot_frame[y_name] = pd.to_numeric(plot_frame[y_name], errors="coerce")
            plot_frame = plot_frame.dropna().head(200)
            if plot_frame.empty:
                raise FileReadError("Недостаточно данных для scatter.")
            axis.scatter(plot_frame[x_name], plot_frame[y_name], alpha=0.75, color="#114b5f")
            axis.set_title(f"Scatter: {y_name} vs {x_name}")
            axis.set_xlabel(x_name)
            axis.set_ylabel(y_name)
            description = f"Scatter-plot связи «{x_name}» и «{y_name}»."
        elif chart_type == "pie":
            group_x = x_column or (dimension_columns or list(dataframe.columns))[0]
            group_y = y_column or (numeric_columns or [None])[0]
            if group_y and numeric_columns:
                grouped = (
                    dataframe[[group_x, group_y]]
                    .copy()
                    .dropna(subset=[group_x, group_y])
                    .groupby(group_x, dropna=True)[group_y]
                    .sum()
                    .sort_values(ascending=False)
                    .head(10)
                )
                if grouped.empty:
                    raise FileReadError("Недостаточно данных для pie-графика.")
                labels = grouped.index.astype(str).tolist()
                values = grouped.values.tolist()
                description = f"Доли «{group_y}» по категориям «{group_x}»."
            else:
                counts = dataframe[group_x].astype(str).value_counts().head(10)
                if counts.empty:
                    raise FileReadError("Недостаточно данных для pie-графика.")
                labels = counts.index.tolist()
                values = counts.values.tolist()
                description = f"Распределение частот по колонке «{group_x}»."
            colors = ["#114b5f", "#6c8b6b", "#d06b4e", "#8d3f28", "#f4a261", "#2a9d8f", "#e9c46a", "#264653"]
            axis.pie(
                values,
                labels=labels,
                autopct="%1.1f%%",
                startangle=90,
                colors=colors[: len(labels)],
            )
            axis.set_title(f"Pie chart: {group_x}")
            axis.axis("equal")
        else:
            if numeric_columns:
                group_x = x_column or (dimension_columns or list(dataframe.columns))[0]
                group_y = y_column or numeric_columns[0]
                grouped = (
                    dataframe[[group_x, group_y]]
                    .copy()
                    .dropna(subset=[group_x, group_y])
                    .groupby(group_x, dropna=True)[group_y]
                    .mean()
                    .sort_values(ascending=False)
                    .head(12)
                )
                if grouped.empty:
                    raise FileReadError("Недостаточно данных для bar графика.")
                axis.bar(grouped.index.astype(str), grouped.values, color="#6c8b6b")
                axis.set_ylabel(f"Mean {group_y}")
                axis.set_title(f"Bar chart: {group_x}")
                description = f"Средние значения «{group_y}» по категориям «{group_x}»."
            else:
                counts = dataframe[selected_x].astype(str).value_counts().head(12)
                axis.bar(counts.index, counts.values, color="#6c8b6b")
                axis.set_ylabel("Count")
                axis.set_title(f"Bar chart: {selected_x}")
                description = f"Частоты по колонке «{selected_x}»."
            axis.tick_params(axis="x", rotation=30)

        figure.tight_layout()
        figure.savefig(output_path, bbox_inches="tight")
        plt.close(figure)
        return self._artifact_record(chart_type, description, file_name)

    def _generate_image_chart(self, stored_file: StoredFile, chart_type: str) -> dict[str, Any]:
        image = self.file_service.open_image(stored_file)
        array = np.array(image)
        grayscale = np.array(image.convert("L"))
        file_name = self._build_output_name(stored_file.file_id, chart_type, "png")
        output_path = self.settings.output_dir / file_name

        figure, axis = plt.subplots(figsize=(10, 5.8), dpi=150)
        figure.patch.set_facecolor("#f8f3ea")
        axis.set_facecolor("#fffaf3")

        if chart_type == "histogram":
            axis.hist(grayscale.ravel(), bins=32, color="#d06b4e", edgecolor="#8d3f28")
            axis.set_title("Pixel intensity histogram")
            axis.set_xlabel("Intensity")
            axis.set_ylabel("Pixels")
            description = "Распределение интенсивности пикселей изображения."
        elif chart_type == "bar":
            if array.ndim == 2:
                labels = ["L"]
                values = [grayscale.mean()]
                colors = ["#114b5f"]
            else:
                labels = list(image.getbands())
                values = [array[:, :, index].mean() for index in range(array.shape[2])]
                colors = ["#114b5f", "#6c8b6b", "#d06b4e", "#8d3f28"][: len(labels)]
            axis.bar(labels, values, color=colors)
            axis.set_title("Mean channel values")
            axis.set_ylabel("Average value")
            description = "Средние значения по каналам изображения."
        elif chart_type == "pie":
            if array.ndim == 2:
                labels = ["Dark pixels", "Bright pixels"]
                threshold = grayscale.mean()
                dark_count = int((grayscale < threshold).sum())
                bright_count = int(grayscale.size - dark_count)
                values = [dark_count, bright_count]
            else:
                labels = list(image.getbands())
                values = [float(array[:, :, index].mean()) for index in range(array.shape[2])]
            colors = ["#114b5f", "#6c8b6b", "#d06b4e", "#8d3f28"][: len(labels)]
            axis.pie(values, labels=labels, autopct="%1.1f%%", startangle=90, colors=colors)
            axis.set_title("Channel share")
            axis.axis("equal")
            description = "Доли по каналам или яркости изображения."
        elif chart_type == "scatter":
            sample = grayscale.ravel()[:: max(1, grayscale.size // 500)]
            axis.scatter(np.arange(len(sample)), sample, alpha=0.5, s=8, color="#114b5f")
            axis.set_title("Pixel intensity scatter")
            axis.set_xlabel("Sample index")
            axis.set_ylabel("Intensity")
            description = "Scatter выборки интенсивности пикселей."
        else:
            profile = grayscale.mean(axis=0)
            axis.plot(np.arange(len(profile)), profile, color="#114b5f", linewidth=2.0)
            axis.set_title("Horizontal brightness profile")
            axis.set_xlabel("X coordinate")
            axis.set_ylabel("Average brightness")
            description = "Средняя яркость по горизонтальной оси изображения."

        figure.tight_layout()
        figure.savefig(output_path, bbox_inches="tight")
        plt.close(figure)
        return self._artifact_record(chart_type, description, file_name)

    def _build_output_name(self, file_id: str, artifact_type: str, extension: str) -> str:
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d%H%M%S")
        return f"{file_id}__{artifact_type}__{timestamp}.{extension}"
