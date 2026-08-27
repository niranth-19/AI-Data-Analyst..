from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    analysis_id: int
    question: str
    answer: str
    analysis_type: str
    results: dict[str, Any] | None
    chart_spec: dict[str, Any] | None
    created_at: datetime


class AnalysisOut(BaseModel):
    id: int
    dataset_id: int
    question: str
    answer: str
    analysis_type: str
    results: dict[str, Any] | None
    chart_spec: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisListResponse(BaseModel):
    analyses: list[AnalysisOut]
    total: int