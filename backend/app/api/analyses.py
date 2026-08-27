from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_dataset_or_404
from app.core.database import get_db
from app.models import Analysis, User
from app.schemas.analysis import (
    AnalysisListResponse,
    AnalysisOut,
    AskRequest,
    AskResponse,
)
from app.services.ai_service import ask_question
from app.services.groq_service import AIConfigurationError, AIServiceError

router = APIRouter(prefix="/datasets/{dataset_id}", tags=["analyses"])
history_router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post("/ask", response_model=AskResponse)
def ask(
    dataset_id: int,
    payload: AskRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be empty.")
    if len(question) > 1000:
        raise HTTPException(status_code=422, detail="Question is too long (max 1000 characters).")

    dataset = get_owned_dataset_or_404(dataset_id, user, db)
    try:
        return ask_question(db, user, dataset, question)
    except AIConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@history_router.get("", response_model=AnalysisListResponse)
def list_analyses(
    dataset_id: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Analysis).filter(Analysis.user_id == user.id)
    if dataset_id is not None:
        query = query.filter(Analysis.dataset_id == dataset_id)
    analyses = query.order_by(Analysis.created_at.desc()).all()
    return AnalysisListResponse(
        analyses=[AnalysisOut.model_validate(a) for a in analyses],
        total=len(analyses),
    )


@history_router.get("/{analysis_id}", response_model=AnalysisOut)
def get_analysis(
    analysis_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = (
        db.query(Analysis)
        .filter(Analysis.id == analysis_id, Analysis.user_id == user.id)
        .first()
    )
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return AnalysisOut.model_validate(analysis)