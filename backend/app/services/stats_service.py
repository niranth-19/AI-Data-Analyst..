from typing import Any

import numpy as np
import pandas as pd

from app.schemas.common import to_serializable


def _numeric_stats(series: pd.Series) -> dict[str, Any]:
    if pd.api.types.is_datetime64_any_dtype(series) or pd.api.types.is_timedelta64_dtype(series):
        return {}
    try:
        values = pd.to_numeric(series, errors="coerce").dropna()
    except (ValueError, TypeError):
        return {}
    if values.empty:
        return {}
    return {
        "count": int(values.count()),
        "mean": round(float(values.mean()), 4),
        "median": round(float(values.median()), 4),
        "min": round(float(values.min()), 4),
        "max": round(float(values.max()), 4),
        "sum": round(float(values.sum()), 4),
        "std": round(float(values.std()), 4),
    }


def compute_column_statistics(df: pd.DataFrame) -> list[dict[str, Any]]:
    stats = []
    for col in df.columns:
        series = df[col]
        missing = int(series.isna().sum())
        missing_pct = round(missing / len(df) * 100, 2) if len(df) else 0.0
        unique = int(series.nunique(dropna=True))
        base = {
            "name": str(col),
            "dtype": str(series.dtype),
            "count": int(series.count()),
            "missing": missing,
            "missing_percent": missing_pct,
            "unique": unique,
        }
        numeric = _numeric_stats(series)
        base["numeric"] = numeric if numeric else None
        stats.append(base)
    return stats


def safe_jsonable(obj: Any) -> Any:
    return to_serializable(obj)


def describe_numeric_columns(df: pd.DataFrame) -> dict[str, Any]:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        return {}
    return df[numeric_cols].describe().to_dict()