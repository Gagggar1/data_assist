from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from app.core.cache import FileCache
from app.services.file_service import FileService, StoredFile

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(self, file_service: FileService, cache: FileCache | None = None) -> None:
        self.file_service = file_service
        self.cache = cache or FileCache()

    def analyze(self, stored_file: StoredFile) -> dict[str, Any]:
        cached = self.cache.get("analysis", stored_file.file_id)
        if cached:
            return cached

        if stored_file.kind == "table":
            result = self._analyze_table(stored_file)
        else:
            result = self._analyze_image(stored_file)

        self.cache.set("analysis", stored_file.file_id, result)
        return result

    def _analyze_table(self, stored_file: StoredFile) -> dict[str, Any]:
        dataframe = self.file_service.read_dataframe(stored_file)
        columns = self.file_service.describe_columns(dataframe)

        numeric_frame = dataframe.select_dtypes(include=[np.number])
        stats_records: list[dict[str, str]] = []
        if not numeric_frame.empty:
            for column in numeric_frame.columns:
                series = numeric_frame[column]
                stats_records.append(
                    {
                        "column": str(column),
                        "mean": self.file_service.format_value(series.mean(skipna=True)),
                        "median": self.file_service.format_value(series.median(skipna=True)),
                        "std": self.file_service.format_value(series.std(skipna=True)),
                        "min": self.file_service.format_value(series.min(skipna=True)),
                        "max": self.file_service.format_value(series.max(skipna=True)),
                    }
                )

        missing_summary = []
        total_rows = max(len(dataframe), 1)
        for column in dataframe.columns:
            missing_count = int(dataframe[column].isna().sum())
            if missing_count:
                missing_summary.append(
                    {
                        "column": str(column),
                        "missing": missing_count,
                        "percent": f"{(missing_count / total_rows) * 100:.1f}%",
                    }
                )

        insights = [
            f"Найдено {len(dataframe):,} строк и {len(dataframe.columns)} колонок.".replace(",", " "),
            "Числовая статистика рассчитана с игнорированием NaN.",
        ]
        if stats_records:
            widest_spread = max(stats_records, key=lambda item: self._to_float(item["std"]))
            insights.append(f"Наибольшая вариативность у колонки «{widest_spread['column']}».")

        top_categories = self._top_categories(dataframe, columns)
        if top_categories:
            top = top_categories[0]
            insights.append(
                f"Топ категория в «{top['column']}»: {top['value']} ({top['share']})."
            )

        trends = self._detect_trends(dataframe, columns)
        insights.extend(trends[:2])

        correlations = self._correlations(numeric_frame)
        anomalies = self._detect_anomalies(numeric_frame)

        category_candidates = [
            item for item in columns if item["kind"] in {"categorical", "text"} and item["missing"] < len(dataframe)
        ]
        if category_candidates:
            insights.append(
                f"Колонка «{category_candidates[0]['name']}» подходит для bar/pie сегментации."
            )

        logger.info("Completed tabular analysis for %s", stored_file.file_id)
        return {
            "kind": "table",
            "summary": {
                "rows": len(dataframe),
                "columns": len(dataframe.columns),
                "numeric_columns": len(numeric_frame.columns),
                "missing_cells": int(dataframe.isna().sum().sum()),
            },
            "column_profile": columns,
            "stats": stats_records,
            "missing_summary": missing_summary,
            "top_categories": top_categories,
            "trends": trends,
            "correlations": correlations,
            "anomalies": anomalies,
            "insights": insights[:10],
        }

    def _analyze_image(self, stored_file: StoredFile) -> dict[str, Any]:
        image = self.file_service.open_image(stored_file)
        array = np.array(image)
        grayscale = np.array(image.convert("L"))

        insights = [
            f"Разрешение изображения: {image.width}×{image.height}.",
            f"Средняя яркость: {grayscale.mean():.2f}.",
            "Доступны histogram, bar, line, pie и scatter по пиксельным данным.",
        ]

        if array.ndim == 3:
            channel_names = list(image.getbands())
            stats = []
            for index, channel_name in enumerate(channel_names):
                channel = array[:, :, index]
                stats.append(
                    {
                        "channel": channel_name,
                        "mean": self.file_service.format_value(float(channel.mean())),
                        "median": self.file_service.format_value(float(np.median(channel))),
                        "std": self.file_service.format_value(float(channel.std())),
                        "min": self.file_service.format_value(int(channel.min())),
                        "max": self.file_service.format_value(int(channel.max())),
                    }
                )
        else:
            stats = [
                {
                    "channel": "L",
                    "mean": self.file_service.format_value(float(grayscale.mean())),
                    "median": self.file_service.format_value(float(np.median(grayscale))),
                    "std": self.file_service.format_value(float(grayscale.std())),
                    "min": self.file_service.format_value(int(grayscale.min())),
                    "max": self.file_service.format_value(int(grayscale.max())),
                }
            ]

        logger.info("Completed image analysis for %s", stored_file.file_id)
        return {
            "kind": "image",
            "summary": {
                "rows": image.height,
                "columns": image.width,
                "numeric_columns": len(stats),
                "missing_cells": 0,
            },
            "column_profile": [],
            "stats": stats,
            "missing_summary": [],
            "top_categories": [],
            "trends": [],
            "correlations": [],
            "anomalies": [],
            "insights": insights,
        }

    def _top_categories(
        self,
        dataframe: pd.DataFrame,
        columns: list[dict[str, Any]],
        limit: int = 3,
    ) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        categorical = [item["name"] for item in columns if item["kind"] in {"categorical", "text"}]
        for column in categorical[:2]:
            counts = dataframe[column].astype(str).value_counts().head(limit)
            total = max(len(dataframe), 1)
            for value, count in counts.items():
                results.append(
                    {
                        "column": column,
                        "value": str(value),
                        "count": str(int(count)),
                        "share": f"{(count / total) * 100:.1f}%",
                    }
                )
        return results[:limit]

    def _detect_trends(
        self,
        dataframe: pd.DataFrame,
        columns: list[dict[str, Any]],
    ) -> list[str]:
        trends: list[str] = []
        datetime_cols = [item["name"] for item in columns if item["kind"] == "datetime"]
        numeric_cols = [item["name"] for item in columns if item["kind"] == "numeric"]

        if not datetime_cols or not numeric_cols:
            return trends

        date_col = datetime_cols[0]
        metric_col = numeric_cols[0]
        frame = dataframe[[date_col, metric_col]].copy()
        frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce")
        frame[metric_col] = pd.to_numeric(frame[metric_col], errors="coerce")
        frame = frame.dropna().sort_values(date_col)
        if len(frame) < 3:
            return trends

        first_half = frame[metric_col].iloc[: len(frame) // 2].mean()
        second_half = frame[metric_col].iloc[len(frame) // 2 :].mean()
        if second_half > first_half * 1.05:
            trends.append(f"«{metric_col}» растёт по «{date_col}» (+{(second_half / max(first_half, 1e-9) - 1) * 100:.1f}%).")
        elif second_half < first_half * 0.95:
            trends.append(f"«{metric_col}» снижается по «{date_col}» ({(second_half / max(first_half, 1e-9) - 1) * 100:.1f}%).")
        else:
            trends.append(f"«{metric_col}» стабилен относительно «{date_col}».")
        return trends

    def _correlations(self, numeric_frame: pd.DataFrame, threshold: float = 0.6) -> list[dict[str, str]]:
        if numeric_frame.shape[1] < 2:
            return []

        corr = numeric_frame.corr(numeric_only=True)
        pairs: list[dict[str, str]] = []
        for left in corr.columns:
            for right in corr.columns:
                if left >= right:
                    continue
                value = corr.loc[left, right]
                if pd.isna(value) or abs(value) < threshold:
                    continue
                pairs.append(
                    {
                        "left": str(left),
                        "right": str(right),
                        "value": f"{value:.2f}",
                    }
                )
        return sorted(pairs, key=lambda item: abs(float(item["value"])), reverse=True)[:5]

    def _detect_anomalies(self, numeric_frame: pd.DataFrame) -> list[dict[str, str]]:
        anomalies: list[dict[str, str]] = []
        for column in numeric_frame.columns:
            series = pd.to_numeric(numeric_frame[column], errors="coerce").dropna()
            if series.empty:
                continue
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outliers = series[(series < lower) | (series > upper)]
            if not outliers.empty:
                anomalies.append(
                    {
                        "column": str(column),
                        "count": str(len(outliers)),
                        "example": self.file_service.format_value(outliers.iloc[0]),
                    }
                )
        return anomalies[:5]

    def _to_float(self, value: str) -> float:
        try:
            return float(str(value).replace(" ", ""))
        except ValueError:
            return 0.0
