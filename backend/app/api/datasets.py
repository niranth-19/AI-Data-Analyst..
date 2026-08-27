from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_dataset_or_404
from app.core.config import get_settings
from app.core.database import get_db
from app.models import Dataset, User
from app.schemas.common import to_serializable
from app.schemas.dataset import (
    CleanRequest,
    CleanResponse,
    DatasetListResponse,
    DatasetOut,
    PreviewOut,
    QualityOut,
    StatisticsOut,
    UploadResponse,
)
from app.services import dataset_service
from app.services.clean_service import clean_dataframe
from app.services.quality_service import analyze_quality
from app.services.stats_service import compute_column_statistics

settings = get_settings()
router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_dataset(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dataset = dataset_service.process_upload(user, db, file)
    return UploadResponse(dataset=DatasetOut.model_validate(dataset))


@router.get("", response_model=DatasetListResponse)
def list_datasets(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    datasets = (
        db.query(Dataset).filter(Dataset.user_id == user.id).order_by(Dataset.created_at.desc()).all()
    )
    return DatasetListResponse(
        datasets=[DatasetOut.model_validate(d) for d in datasets],
        total=len(datasets),
    )


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(
    dataset_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dataset = get_owned_dataset_or_404(dataset_id, user, db)
    return DatasetOut.model_validate(dataset)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
    dataset_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dataset = get_owned_dataset_or_404(dataset_id, user, db)
    try:
        dataset_service.get_dataset_path(dataset).unlink(missing_ok=True)
    except Exception:
        pass
    db.delete(dataset)
    db.commit()
    return None


@router.get("/{dataset_id}/preview", response_model=PreviewOut)
def preview_dataset(
    dataset_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dataset = get_owned_dataset_or_404(dataset_id, user, db)
    df = dataset_service.load_dataframe(dataset)
    rows = df.head(settings.PREVIEW_ROWS).where(df.notna(), None).to_dict(orient="records")
    return PreviewOut(
        dataset=DatasetOut.model_validate(dataset),
        rows=to_serializable(rows),
        total_rows_shown=len(rows),
    )


@router.get("/{dataset_id}/statistics", response_model=StatisticsOut)
def dataset_statistics(
    dataset_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dataset = get_owned_dataset_or_404(dataset_id, user, db)
    df = dataset_service.load_dataframe(dataset)
    stats = compute_column_statistics(df)
    return StatisticsOut(dataset_id=dataset.id, columns=stats)


@router.get("/{dataset_id}/quality", response_model=QualityOut)
def dataset_quality(
    dataset_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dataset = get_owned_dataset_or_404(dataset_id, user, db)
    df = dataset_service.load_dataframe(dataset)
    quality = analyze_quality(df)
    quality["dataset_id"] = dataset.id
    return QualityOut(**quality)


@router.post("/{dataset_id}/clean", response_model=CleanResponse)
def clean_dataset(
    dataset_id: int,
    payload: CleanRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dataset = get_owned_dataset_or_404(dataset_id, user, db)
    df = dataset_service.load_dataframe(dataset)
    rows_before = len(df)
    cols_before = len(df.columns)
    cleaned_df, operations = clean_dataframe(df, payload)

    # Keep original safe: save cleaned version as a new stored file, original untouched
    dataset_service.save_dataframe(dataset, cleaned_df, extension="csv")
    dataset_service.update_dataset_metadata(dataset, cleaned_df)
    dataset.status = "cleaned"
    db.commit()
    db.refresh(dataset)

    return CleanResponse(
        dataset_id=dataset.id,
        message=f"Dataset cleaned successfully. {len(operations)} operation(s) applied.",
        rows_before=rows_before,
        rows_after=len(cleaned_df),
        columns_before=cols_before,
        columns_after=len(cleaned_df.columns),
        operations=operations,
    )