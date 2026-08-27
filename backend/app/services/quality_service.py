from typing import Any

import numpy as np
import pandas as pd

from app.services.stats_service import compute_column_statistics


def _detect_outliers(series: pd.Series) -> int:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if len(values) < 4:
        return 0
    q1 = values.quantile(0.25)
    q3 = values.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return 0
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return int(((values < lower) | (values > upper)).sum())


def analyze_quality(df: pd.DataFrame) -> dict[str, Any]:
    total_rows = len(df)
    total_columns = len(df.columns)
    total_cells = total_rows * total_columns
    missing_cells = int(df.isna().sum().sum())
    missing_percent = round(missing_cells / total_cells * 100, 2) if total_cells else 0.0

    duplicate_rows = int(df.duplicated().sum())

    empty_columns = [str(c) for c in df.columns if df[c].isna().all()]

    columns = compute_column_statistics(df)

    issues: list[dict[str, Any]] = []

    for col_stats in columns:
        name = col_stats["name"]
        if col_stats["missing"] > 0:
            severity = "high" if col_stats["missing_percent"] >= 50 else "medium" if col_stats["missing_percent"] >= 10 else "info"
            issues.append({
                "type": "missing_values",
                "severity": severity,
                "message": (
                    f"Column '{name}' has {col_stats['missing']} missing value(s) "
                    f"({col_stats['missing_percent']}%)."
                ),
                "affected_columns": [name],
            })
        if col_stats["unique"] == 1 and col_stats["count"] > 0:
            issues.append({
                "type": "constant_column",
                "severity": "info",
                "message": f"Column '{name}' contains only a single unique value.",
                "affected_columns": [name],
            })

    for name in empty_columns:
        issues.append({
            "type": "empty_column",
            "severity": "high",
            "message": f"Column '{name}' is completely empty.",
            "affected_columns": [name],
        })

    if duplicate_rows > 0:
        issues.append({
            "type": "duplicate_rows",
            "severity": "medium",
            "message": f"Found {duplicate_rows} fully duplicate row(s) in the dataset.",
            "affected_columns": [],
        })

    for col_stats in columns:
        name = col_stats["name"]
        series = df[name]
        if pd.api.types.is_numeric_dtype(series):
            outliers = _detect_outliers(series)
            if outliers > 0:
                issues.append({
                    "type": "outliers",
                    "severity": "info",
                    "message": f"Column '{name}' contains {outliers} outlier value(s) by the IQR rule.",
                    "affected_columns": [name],
                })

    return {
        "dataset_id": None,
        "total_rows": total_rows,
        "total_columns": total_columns,
        "total_cells": total_cells,
        "missing_cells": missing_cells,
        "missing_percent": missing_percent,
        "duplicate_rows": duplicate_rows,
        "empty_columns": empty_columns,
        "columns": columns,
        "issues": issues,
    }