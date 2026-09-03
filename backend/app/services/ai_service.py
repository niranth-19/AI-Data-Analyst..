"""Orchestrates a grounded question-answer flow.

1. LLM produces an analysis plan (what to compute).
2. Pandas executes the plan deterministically (source of truth).
3. LLM explains the *computed* results, grounded in real numbers.
"""

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import Analysis, Dataset, User
from app.schemas.analysis import AskResponse
from app.schemas.common import to_serializable
from app.services.ai_plan import (
    PLAN_SYSTEM_PROMPT,
    build_dataset_context,
    build_plan_prompt,
    extract_json,
    validate_plan,
)
from app.services.analysis_engine import execute_plan
from app.services.dataset_service import load_dataframe
from app.services.groq_service import AIServiceError, chat_completion

EXPLAIN_SYSTEM_PROMPT = """You are an AI data analyst explaining results computed from a real dataset. \
The COMPUTED RESULT below was produced by Pandas and is authoritative. \
Follow these rules strictly:
- Explain the result in clear, concise plain English (2-4 sentences).
- NEVER change or invent any numbers. Only reference the numbers given.
- If the computed result is null/empty or contains only an error message, say the question \
cannot be answered from the available data and why.
- If the operation is 'insights', write 3-6 short bullet insights based ONLY on the given facts.
- If the operation is 'quality', summarize the data quality findings factually.
- Do not mention Pandas or code."""


def _build_explain_prompt(question: str, operation: str, result: Any) -> str:
    payload = to_serializable(result)
    try:
        result_json = json.dumps(payload, indent=2, ensure_ascii=False)[:6000]
    except TypeError:
        result_json = str(payload)[:6000]
    return (
        f"USER QUESTION: {question}\n"
        f"OPERATION: {operation}\n\n"
        f"COMPUTED RESULT (authoritative, from the dataset):\n{result_json}"
    )


def _fallback_plan(question: str) -> dict[str, Any]:
    """Best-effort plan when the LLM plan step fails."""
    # Return schema_info to indicate question cannot be answered from dataset
    # rather than giving general "insights" that might reference external knowledge
    return {"operation": "schema_info", "question": question, "group_column": None, "value_column": None}


def ask_question(db: Session, user: User, dataset: Dataset, question: str) -> AskResponse:
    df = load_dataframe(dataset)
    context = build_dataset_context(df)

    plan: dict[str, Any] = {}
    plan_error: str | None = None
    try:
        raw = chat_completion(PLAN_SYSTEM_PROMPT, build_plan_prompt(question, context))
        plan = extract_json(raw) or {}
        plan_error = validate_plan(plan, df)
        if plan_error:
            # One retry, asking explicitly for valid JSON
            retry_prompt = build_plan_prompt(question, context) + (
                f"\n\nPrevious plan was invalid: {plan_error}. Return ONLY valid JSON."
            )
            raw = chat_completion(PLAN_SYSTEM_PROMPT, retry_prompt)
            plan = extract_json(raw) or {}
            plan_error = validate_plan(plan, df)
    except AIServiceError:
        raise
    except Exception:
        plan = _fallback_plan(question)
        plan_error = validate_plan(plan, df)

    if plan_error:
        plan = _fallback_plan(question)

    results, chart_spec = execute_plan(df, plan)
operation = plan.get("operation", "insights")

    # Normalize chart_spec: ensure it's always a dict or None
    if chart_spec is not None:
        try:
            # Validate minimum structure
            if not isinstance(chart_spec, dict):
                chart_spec = None
            elif chart_spec.get("type") is None:
                chart_spec = None
            elif chart_spec.get("labels") is None:
                chart_spec = None
            elif chart_spec.get("datasets") is None:
                chart_spec = None
        except Exception:
            chart_spec = None
    else:
        chart_spec = None
            elif chart_spec.get("type") is None:
                chart_spec = None
            elif chart_spec.get("labels") is None:
                chart_spec = None
            elif chart_spec.get("datasets") is None:
                chart_spec = None
        except Exception:
            chart_spec = None
    else:
        chart_spec = None

    explanation: str
    try:
        explanation = chat_completion(
            EXPLAIN_SYSTEM_PROMPT, _build_explain_prompt(question, operation, results)
        ).strip()
    except AIServiceError:
        if results.get("result") is not None:
            explanation = "The computation succeeded, but the AI explanation service is unavailable."
        else:
            explanation = results.get("message") or "The question could not be answered from the dataset."
    except Exception:
        explanation = results.get("message") or "The question could not be answered from the dataset."

    analysis = Analysis(
        user_id=user.id,
        dataset_id=dataset.id,
        question=question,
        answer=explanation,
        analysis_type=operation,
        results=to_serializable(results),
        chart_spec=to_serializable(chart_spec),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return AskResponse(
        analysis_id=analysis.id,
        question=question,
        answer=explanation,
        analysis_type=operation,
        results=to_serializable(results),
        chart_spec=to_serializable(chart_spec),
        created_at=analysis.created_at,
    )