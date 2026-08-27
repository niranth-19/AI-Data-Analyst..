"""Build prompts and parse the LLM's analysis plan.

The LLM only decides WHAT to compute (operation + columns). All actual
numerical work is done deterministically by Pandas.
"""

import json
import re
from typing import Any

import pandas as pd

PLAN_SYSTEM_PROMPT = """You are the query-planner for an AI data analyst. The user asks a natural-language \
question about an uploaded dataset. You must respond with ONLY a JSON object describing what \
Pandas computation should be run. Never invent columns: use only the column names given in the \
dataset context. Never provide computed numbers in your JSON.

Choose exactly one "operation" from:
- "aggregate": compute a single aggregate (sum/mean/median/min/max/count/std) of one numeric column, optionally filtered.
- "group_by": group rows by a categorical column and aggregate a numeric column per group (e.g. sales by category, employees per department).
- "column_stats": descriptive statistics of one numeric column (mean, median, min, max, std, sum).
- "distribution": value distribution of a column (categorical counts, or histogram for numeric).
- "correlation": correlation between numeric columns.
- "quality": data quality summary (missing values, duplicates, empty columns). Set all columns to null.
- "time_series": group a numeric column by a date column (year/month/day granularity).
- "insights": general analysis/trends/insights over the whole dataset. Set all columns to null.
- "schema_info": describe the columns/types/sample of the dataset. Set all columns to null.

JSON schema:
{
  "operation": "aggregate|group_by|column_stats|distribution|correlation|quality|time_series|insights|schema_info",
  "question": "<the user's question, rephrased>",
  "group_column": "<column name or null>",
  "value_column": "<numeric column name or null>",
  "aggregation": "sum|count|mean|median|min|max|std|nunique",
  "top_n": <integer or null>,
  "sort": "desc|asc",
  "filter_column": "<column name or null>",
  "filter_value": "<literal value to filter on or null>",
  "date_column": "<date column name or null>",
  "date_granularity": "year|month|day|none",
  "explanation": "<one sentence describing the computation>"
}

Rules:
- "count" aggregation counts rows (value_column may be null).
- For "group_by", set group_column, value_column, aggregation; set top_n (e.g. 10) and sort.
- For "aggregate" or "column_stats", set value_column; aggregation only for "aggregate".
- If the question asks about missing values, duplicates or data quality, use "quality".
- If the question asks for general trends/insights/overview, use "insights".
- If a date column exists and the question mentions time, month, year, or trend over time, use "time_series".
- For "time_series", set date_column, date_granularity, value_column, aggregation.
- For filter questions (e.g. "sales in 2023"), set filter_column/filter_value AND the operation for the rest.
- Use "nunique" aggregation for counting distinct values of value_column.
- top_n must be between 1 and 50, default 10 for group_by.
- "insights" operation should ONLY reference facts computed from the dataset context provided below.
- If the question is NOT about the dataset (e.g., asking for code tutorials, general knowledge, or external information), choose "schema_info" with all columns set to null, and set the question to a rephrased version acknowledging it cannot be answered from the dataset.
- Aggregation semantics:
  * "highest/lowest/top-selling product or category by sales/revenue/amount" -> aggregate "sum" over a numeric value column.
  * "highest/lowest single sale / transaction / record value" -> "max" or "min".
  * "average/typical" -> "mean" or "median".
  * "how many / number of / count" -> "count".
- Never answer the question in prose; return only the JSON object."""


def build_dataset_context(df: pd.DataFrame) -> str:
    lines: list[str] = []
    lines.append(f"Row count: {len(df)}")
    lines.append(f"Columns ({len(df.columns)}):")
    for col in df.columns:
        series = df[col]
        missing = int(series.isna().sum())
        unique = int(series.nunique(dropna=True))
        sample = series.dropna().head(3).tolist()
        sample_txt = ", ".join(str(v) for v in sample)
        lines.append(
            f"- {col!r} | dtype={series.dtype} | missing={missing} | unique={unique} | sample=[{sample_txt}]"
        )
    return "\n".join(lines)


def build_plan_prompt(question: str, context: str) -> str:
    return f"""DATASET CONTEXT:
{context}

USER QUESTION: {question}

Return the JSON plan for this question."""


def extract_json(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


ALLOWED_OPERATIONS = {
    "aggregate", "group_by", "column_stats", "distribution",
    "correlation", "quality", "time_series", "insights", "schema_info",
}
ALLOWED_AGGREGATIONS = {"sum", "count", "mean", "median", "min", "max", "std", "nunique"}
ALLOWED_GRANULARITIES = {"year", "month", "day", "none"}


def validate_plan(plan: dict[str, Any], df: pd.DataFrame) -> str | None:
    """Return an error string if the plan is invalid, else None."""
    op = plan.get("operation")
    if op not in ALLOWED_OPERATIONS:
        return f"Unknown operation: {op!r}"
    columns = {str(c) for c in df.columns}
    for key in ("group_column", "value_column", "filter_column", "date_column"):
        val = plan.get(key)
        if val is not None and str(val) not in columns:
            return f"Column {val!r} does not exist in the dataset."
    agg = plan.get("aggregation")
    if agg is not None and agg not in ALLOWED_AGGREGATIONS:
        return f"Unsupported aggregation: {agg!r}"
    gran = plan.get("date_granularity")
    if gran is not None and gran not in ALLOWED_GRANULARITIES:
        return f"Unsupported granularity: {gran!r}"
    top_n = plan.get("top_n")
    if top_n is not None:
        try:
            if not (1 <= int(top_n) <= 50):
                return "top_n must be between 1 and 50."
        except (TypeError, ValueError):
            return "top_n must be an integer."
    return None