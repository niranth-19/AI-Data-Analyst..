from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_dataset_or_404
from app.core.database import get_db
from app.models import Report, User
from app.schemas.report import (
    ReportCreateRequest,
    ReportListResponse,
    ReportOut,
)
from app.services.pdf_service import generate_report_pdf, get_report_path

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dataset = get_owned_dataset_or_404(payload.dataset_id, user, db)
    report = generate_report_pdf(db, user, dataset, payload.report_name)
    return ReportOut.model_validate(report)


@router.get("", response_model=ReportListResponse)
def list_reports(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reports = (
        db.query(Report).filter(Report.user_id == user.id).order_by(Report.created_at.desc()).all()
    )
    return ReportListResponse(
        reports=[ReportOut.model_validate(r) for r in reports],
        total=len(reports),
    )


@router.get("/{report_id}/download")
def download_report(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.user_id == user.id)
        .first()
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    try:
        path: Path = get_report_path(report)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report path.")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report file not found on disk.")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{report.report_name.replace(' ', '_')}.pdf",
    )