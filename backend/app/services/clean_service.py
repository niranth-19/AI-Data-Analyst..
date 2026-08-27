from typing import Any

import pandas as pd

from app.schemas.dataset import CleanRequest


def clean_dataframe(df: pd.DataFrame, request: CleanRequest) -> tuple[pd.DataFrame, list[str]]:
    df = df.copy()
    operations: list[str] = []

    if request.trim_strings:
        changed = False
        for col in df.columns:
            if df[col].dtype == object:
                non_null = df[col].notna()
                stripped = df[col].astype(str).str.strip()
                if non_null.any() and not (stripped[non_null] == df[col][non_null].astype(str)).all():
                    changed = True
                df[col] = stripped.where(non_null, None)
                df[col] = df[col].replace({"": None, "nan": None, "None": None})
        if changed:
            operations.append("Trimmed leading/trailing whitespace in text columns")

    if request.drop_duplicates:
        before = len(df)
        df = df.drop_duplicates()
        removed = before - len(df)
        if removed > 0:
            operations.append(f"Removed {removed} duplicate row(s)")

    if request.fill_numeric_strategy and request.fill_numeric_strategy != "drop":
        numeric_cols = df.select_dtypes(include="number").columns
        if len(numeric_cols) > 0 and df[numeric_cols].isna().any().any():
            if request.fill_numeric_strategy == "mean":
                df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
                operations.append("Filled missing numeric values with column mean")
            elif request.fill_numeric_strategy == "median":
                df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
                operations.append("Filled missing numeric values with column median")
            elif request.fill_numeric_strategy == "mode":
                for col in numeric_cols:
                    mode_val = df[col].mode()
                    if not mode_val.empty:
                        df[col] = df[col].fillna(mode_val[0])
                operations.append("Filled missing numeric values with column mode")

    if request.fill_categorical_strategy and request.fill_categorical_strategy != "drop":
        cat_cols = [c for c in df.columns if df[c].dtype == object]
        for col in cat_cols:
            if df[col].isna().any():
                if request.fill_categorical_strategy == "mode":
                    mode_val = df[col].mode()
                    if not mode_val.empty:
                        df[col] = df[col].fillna(mode_val[0])
        if any(df[c].isna().any() for c in cat_cols):
            operations.append("Filled missing categorical values with column mode")

    if (request.fill_numeric_strategy == "drop") or (request.fill_categorical_strategy == "drop"):
        before = len(df)
        df = df.dropna()
        removed = before - len(df)
        if removed > 0:
            operations.append(f"Dropped {removed} row(s) containing missing values")

    if request.drop_empty_columns:
        before_cols = list(df.columns)
        df = df.dropna(axis=1, how="all")
        dropped = [c for c in before_cols if c not in df.columns]
        if dropped:
            operations.append(f"Dropped empty column(s): {', '.join(dropped)}")

    if request.convert_date_columns:
        for col in df.columns:
            if df[col].dtype == object:
                non_null = df[col].dropna()
                if non_null.empty:
                    continue
                try:
                    parsed = pd.to_datetime(non_null, errors="coerce", format="mixed")
                    if parsed.notna().sum() >= max(1, len(non_null) * 0.9):
                        df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed")
                        operations.append(f"Converted column '{col}' to datetime")
                except (ValueError, TypeError):
                    pass

    return df, operations