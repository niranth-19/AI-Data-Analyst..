"""Deterministic execution of an analysis plan against the dataset.

All numerical answers are computed here with Pandas. The LLM only decides
the operation and columns; it never computes numbers.
"""

from typing import Any

import numpy as np
import pandas as pd

from app.services.ai_plan import validate_plan
from app.services.quality_service import analyze_quality
from app.services.stats_service import compute_column_statistics


def _coerce_value(value: Any, series: pd.Series) -> Any:
    """Try to match a filter literal to the column's dtype."""
    if value is None:
        return None
    if pd.api.types.is_numeric_dtype(series):
        try:
            return float(value)
        except (ValueError, TypeError):
            return value
    return str(value)


def _top_n(items: list[dict], n: int | None, sort: str) -> list[dict]:
    if n is not None and 0 < n < len(items):
        items = items[:n]
    if sort == "asc":
        items = list(reversed(items))
    return items


def _build_category_chart(
    labels: list[str], values: list[float], title: str, chart_type: str = "bar"
) -> dict[str, Any] | None:
    if not labels or not values or len(labels) != len(values):
        return None
    return {
        "type": chart_type,
        "title": title,
        "labels": labels,
        "datasets": [{"label": title, "data": values}],
    }


def _scalar_round(value: Any) -> Any:
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return round(float(value), 4)
    return value


def _execute_aggregate(df: pd.DataFrame, plan: dict) -> dict[str, Any]:
    agg = plan.get("aggregation") or "sum"
    value_col = plan.get("value_column")
    filter_col = plan.get("filter_column")
    filter_val = plan.get("filter_value")

    working = df
    if filter_col is not None and filter_val is not None:
        col_series = df[filter_col]
        fv = _coerce_value(filter_val, col_series)
        mask = col_series.astype(str).str.lower() == str(fv).lower()
        if pd.api.types.is_numeric_dtype(col_series):
            try:
                mask = col_series == float(fv)
            except (ValueError, TypeError):
                pass
        working = df[mask]
        if working.empty:
            return {
                "result": None,
                "rows_matched": 0,
                "message": f"No rows match {filter_col} = {filter_val}.",
            }

    if agg == "count":
        result = len(working) if value_col is None else int(working[value_col].notna().sum())
        return {
            "result": result,
            "aggregation": "count",
            "column": value_col,
            "rows_matched": len(working),
        }

    if value_col is None:
        return {"result": None, "message": "A value column is required for this aggregation."}

    series = pd.to_numeric(working[value_col], errors="coerce").dropna()
    if series.empty:
        return {"result": None, "message": f"Column '{value_col}' has no numeric values to aggregate."}

    if agg == "nunique":
        result = int(working[value_col].nunique(dropna=True))
    elif agg == "sum":
        result = _scalar_round(series.sum())
    elif agg == "mean":
        result = _scalar_round(series.mean())
    elif agg == "median":
        result = _scalar_round(series.median())
    elif agg == "min":
        result = _scalar_round(series.min())
    elif agg == "max":
        result = _scalar_round(series.max())
    elif agg == "std":
        result = _scalar_round(series.std())
    else:
        return {"result": None, "message": f"Unsupported aggregation: {agg}."}

    return {
        "result": result,
        "aggregation": agg,
        "column": value_col,
        "rows_matched": len(working),
        "filter_column": filter_col,
        "filter_value": filter_val,
    }


def _execute_group_by(df: pd.DataFrame, plan: dict) -> dict[str, Any]:
    group_col = plan.get("group_column")
    value_col = plan.get("value_column")
    agg = plan.get("aggregation") or "sum"
    top_n = plan.get("top_n") or 10
    sort = plan.get("sort") or "desc"

    if group_col is None:
        return {"result": None, "message": "A group column is required."}

    if agg == "count":
        grouped = df.groupby(group_col, dropna=False).size().reset_index(name="count")
        result_df = grouped.sort_values("count", ascending=(sort != "desc"))
        labels = result_df[group_col].astype(str).tolist()
        values = result_df["count"].tolist()
        result_rows = [
            {"group": str(g), "value": int(v)} for g, v in zip(labels, values)
        ]
    else:
        if value_col is None:
            return {"result": None, "message": "A value column is required for grouping."}
        if agg == "nunique":
            grouped = (
                df.groupby(group_col, dropna=False)[value_col]
                .nunique(dropna=True)
                .reset_index(name="value")
            )
        else:
            grouped = (
                df.groupby(group_col, dropna=False)[value_col]
                .agg(agg)
                .reset_index(name="value")
            )
        grouped["value"] = pd.to_numeric(grouped["value"], errors="coerce")
        grouped = grouped.dropna(subset=["value"])
        grouped = grouped.sort_values("value", ascending=(sort != "desc"))
        result_rows = [
            {"group": str(g), "value": _scalar_round(v)}
            for g, v in zip(grouped[group_col], grouped["value"])
        ]
        values = [r["value"] for r in result_rows]

    result_rows = _top_n(result_rows, top_n, sort)

    # Chart shows full top-N in descending order (clearer)
    chart_values = sorted(values, reverse=True) if sort == "desc" else values
    chart_labels = [r["group"] for r in result_rows]
    chart = _build_category_chart(
        chart_labels, [r["value"] for r in result_rows], f"{agg.capitalize()} by {group_col}"
    )
    chart = None
    if group_col is not None and value_col is not None:
        chart = _build_category_chart(
            chart_labels, [r["value"] for r in result_rows], f"{agg.capitalize()} by {group_col}"
        )
    return {
        "result": result_rows,
        "aggregation": agg,
        "group_column": group_col,
        "value_column": value_col,
        "total_groups": len(result_rows),
        "chart_spec": chart,
    }


def _execute_column_stats(df: pd.DataFrame, plan: dict) -> dict[str, Any]:
    value_col = plan.get("value_column")
    if value_col is None:
        return {"result": None, "message": "A value column is required."}
    series = pd.to_numeric(df[value_col], errors="coerce").dropna()
    if series.empty:
        return {"result": None, "message": f"Column '{value_col}' has no numeric values."}

    labels = ["count", "mean", "median", "min", "max", "sum", "std"]
    values = [series.count(), series.mean(), series.median(), series.min(), series.max(), series.sum(), series.std()]
    stats = {
        "column": value_col,
        "dtype": str(df[value_col].dtype),
        "count": int(series.count()),
        "mean": _scalar_round(series.mean()),
        "median": _scalar_round(series.median()),
        "min": _scalar_round(series.min()),
        "max": _scalar_round(series.max()),
        "sum": _scalar_round(series.sum()),
        "std": _scalar_round(series.std()),
        "missing": int(df[value_col].isna().sum()),
    }
    chart = _build_category_chart(
        labels, [_scalar_round(v) for v in values], f"Statistics for {value_col}"
    )
    return {"result": stats, "chart_spec": chart}


def _execute_distribution(df: pd.DataFrame, plan: dict) -> dict[str, Any]:
    value_col = plan.get("value_column")
    if value_col is None:
        return {"result": None, "message": "A value column is required."}
    series = df[value_col]

    if pd.api.types.is_numeric_dtype(series):
        clean = pd.to_numeric(series, errors="coerce").dropna()
        if clean.empty:
            return {"result": None, "message": f"Column '{value_col}' has no numeric values."}
        counts, edges = np.histogram(clean, bins="auto")
        labels = [f"{edges[i]:.2g}–{edges[i + 1]:.2g}" for i in range(len(counts))]
        chart = _build_category_chart(
            labels, [int(c) for c in counts], f"Distribution of {value_col}"
        )
        return {
            "result": {
                "column": value_col,
                "kind": "histogram",
                "bins": [{"range": lbl, "count": int(c)} for lbl, c in zip(labels, counts)],
            },
            "chart_spec": chart,
        }

    vc = series.dropna().value_counts()
    if vc.empty:
        return {"result": None, "message": f"Column '{value_col}' has no values."}
    total = int(vc.sum())
    rows = [{"group": str(g), "count": int(c), "percent": round(c / total * 100, 2)} for g, c in vc.head(10).items()]
    chart = _build_category_chart(
        [r["group"] for r in rows], [r["count"] for r in rows], f"Distribution of {value_col}", "doughnut"
    )
    return {
        "result": {
            "column": value_col,
            "kind": "value_counts",
            "total_values": total,
            "top": rows,
        },
        "chart_spec": chart,
    }


def _execute_correlation(df: pd.DataFrame, plan: dict) -> dict[str, Any]:
    numeric = df.select_dtypes(include=[np.number])
    if numeric.shape[1] < 2:
        return {"result": None, "message": "At least two numeric columns are needed for correlation analysis."}
    corr = numeric.corr()
    corr_dict = {
        str(a): {str(b): _scalar_round(corr.loc[a, b]) for b in corr.columns}
        for a in corr.index
    }

    best_pair, best_abs = None, 0.0
    for a in corr.columns:
        for b in corr.columns:
            if a == b:
                continue
            val = corr.loc[a, b]
            if not np.isnan(val) and abs(val) > best_abs:
                best_abs = abs(val)
                best_pair = (str(a), str(b), _scalar_round(val))

    chart = None
    if best_pair and not np.isnan(best_pair[2]):
        a, b = best_pair[0], best_pair[1]
        clean = numeric[[a, b]].dropna()
        if len(clean) >= 2:
            chart = {
                "type": "scatter",
                "title": f"{a} vs {b} (r = {best_pair[2]})",
                "labels": [],
                "datasets": [
                    {
                        "label": f"{a} vs {b}",
                        "data": [
                            {"x": float(x), "y": float(y)}
                            for x, y in zip(clean[a], clean[b])
                        ][:500],
                    }
                ],
            }

    return {
        "result": {
            "matrix": corr_dict,
            "strongest_pair": list(best_pair) if best_pair else None,
        },
        "chart_spec": chart,
    }


def _execute_time_series(df: pd.DataFrame, plan: dict) -> dict[str, Any]:
    date_col = plan.get("date_column")
    value_col = plan.get("value_column")
    agg = plan.get("aggregation") or "sum"
    granularity = plan.get("date_granularity") or "month"

    period_freq = {"year": "Y", "month": "M", "day": "D"}.get(granularity, "M")

    if date_col is None:
        return {"result": None, "message": "A date column is required for time-series analysis."}

    date_series = pd.to_datetime(df[date_col], errors="coerce")
    if date_series.isna().all():
        return {"result": None, "message": f"Column '{date_col}' could not be parsed as dates."}
    working = df.copy()
    working["__date__"] = date_series
    working = working.dropna(subset=["__date__"])

    if agg == "count":
        agg_series = working.groupby(working["__date__"].dt.to_period(period_freq)).size()
        values = [int(v) for v in agg_series]
    else:
        if value_col is None:
            return {"result": None, "message": "A value column is required for time-series aggregation."}
        grouped = working.groupby(working["__date__"].dt.to_period(period_freq))[value_col].agg(agg)
        grouped = pd.to_numeric(grouped, errors="coerce").dropna()
        values = [_scalar_round(v) for v in grouped]

    labels = [str(p) for p in grouped.index]
    chart = _build_category_chart(labels, values, f"{agg.capitalize()} of {value_col or 'rows'} by {granularity}", "line")
    return {
        "result": {
            "granularity": granularity,
            "points": [{"period": lbl, "value": v} for lbl, v in zip(labels, values)],
        },
        "chart_spec": chart,
    }


def _execute_quality(df: pd.DataFrame, plan: dict) -> dict[str, Any]:
    quality = analyze_quality(df)
    result = {k: v for k, v in quality.items() if k not in ("columns",)}
    result["columns"] = [
        {"name": c["name"], "dtype": c["dtype"], "missing": c["missing"], "unique": c["unique"]}
        for c in quality["columns"]
    ]
    return {"result": result}


def _execute_schema_info(df: pd.DataFrame, plan: dict) -> dict[str, Any]:
    return {
        "result": {
            "rows": len(df),
            "columns": [
                {
                    "name": str(c),
                    "dtype": str(df[c].dtype),
                    "missing": int(df[c].isna().sum()),
                    "unique": int(df[c].nunique(dropna=True)),
                }
                for c in df.columns
            ],
            "sample_rows": df.head(5).where(pd.notna(df), None).to_dict(orient="records"),
        }
    }


def _execute_insights(df: pd.DataFrame, plan: dict) -> dict[str, Any]:
    """Deterministic facts the LLM will interpret (never inventing numbers)."""
    facts: dict[str, Any] = {"rows": len(df)}

    numeric = df.select_dtypes(include=[np.number])
    if numeric.shape[1] >= 2:
        corr = numeric.corr()
        strongest = []
        for a in corr.columns:
            for b in corr.columns:
                if a == b:
                    continue
                val = corr.loc[a, b]
                if not np.isnan(val):
                    strongest.append((str(a), str(b), round(float(val), 3)))
        strongest = sorted(strongest, key=lambda t: abs(t[2]), reverse=True)
        facts["strongest_correlations"] = strongest[:3]

    # Most correlated numeric column (for chart)
    chart_col = None
    if facts.get("strongest_correlations"):
        a, b, _ = strongest[0]
        chart_col = b if a else None
        if chart_col:
            clean = numeric[[a, chart_col]].dropna()
            if len(clean) >= 2:
                facts["_chart"] = {
                    "type": "scatter",
                    "title": f"{a} vs {chart_col} (r = {strongest[0][2]})",
                    "labels": [],
                    "datasets": [{"label": f"{a} vs {chart_col}",
                                  "data": [{"x": float(x), "y": float(y)}
                                           for x, y in zip(clean[a], clean[chart_col])][:500]}],
                }

    categorical = df.select_dtypes(exclude=[np.number])
    cat_summary = []
    for col in categorical.columns:
        vc = df[col].dropna().value_counts()
        if vc.empty:
            continue
        top = vc.head(1).index[0]
        cat_summary.append({
            "column": str(col),
            "top_value": str(top),
            "top_count": int(vc.iloc[0]),
            "top_percent": round(float(vc.iloc[0] / vc.sum() * 100), 1),
            "unique_values": int(vc.size),
        })
    facts["categorical_summary"] = cat_summary[:5]

    quality = analyze_quality(df)
    facts["missing_cells"] = quality["missing_cells"]
    facts["missing_percent"] = quality["missing_percent"]
    facts["duplicate_rows"] = quality["duplicate_rows"]

    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            s = pd.to_numeric(df[col], errors="coerce").dropna()
            if not s.empty:
                facts.setdefault("numeric_highlights", []).append({
                    "column": str(col),
                    "max": _scalar_round(s.max()),
                    "min": _scalar_round(s.min()),
                    "mean": _scalar_round(s.mean()),
                })

    chart = facts.pop("_chart", None)
    return {"result": facts, "chart_spec": chart}


def execute_plan(df: pd.DataFrame, plan: dict) -> tuple[dict[str, Any], str | None]:
    """Execute a validated plan. Returns (results, chart_spec)."""
    error = validate_plan(plan, df)
    if error:
        return {"result": None, "message": error}, None

    operation = plan.get("operation")
    handlers = {
        "aggregate": _execute_aggregate,
        "group_by": _execute_group_by,
        "column_stats": _execute_column_stats,
        "distribution": _execute_distribution,
        "correlation": _execute_correlation,
        "time_series": _execute_time_series,
        "quality": _execute_quality,
        "schema_info": _execute_schema_info,
        "insights": _execute_insights,
    }
    handler = handlers.get(operation)
    if handler is None:
        return {"result": None, "message": f"Unsupported operation: {operation}"}, None

    try:
        outcome = handler(df, plan)
    except Exception as exc:  # noqa: BLE001 - deterministic fallback
        return {"result": None, "message": f"Analysis failed: {exc}"}, None

    chart = outcome.pop("chart_spec", None)
    return outcome, chart


def compute_quality_summary(df: pd.DataFrame) -> dict[str, Any]:
    return analyze_quality(df)