from datetime import datetime

from pydantic import BaseModel


class ReportCreateRequest(BaseModel):
    dataset_id: int
    report_name: str | None = None


class ReportOut(BaseModel):
    id: int
    dataset_id: int
    report_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    reports: list[ReportOut]
    total: int