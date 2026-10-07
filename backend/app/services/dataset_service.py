import csv
import io
import os
import uuid
from pathlib import Path

import boto3

import pandas as pd
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Dataset, User

settings = get_settings()

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "ai-data-analyst-files")

s3_client = boto3.client(
    "s3",
    endpoint_url=os.getenv("AWS_ENDPOINT_URL_S3"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION", "ap-southeast-1"),
)

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}
MAX_FILE_SIZE = settings.max_upload_size_bytes


def _safe_path(user_id: int, filename: str) -> Path:
    """Resolve a stored filename under the user's storage dir, guarding against traversal."""
    base = settings.STORAGE_DIR / str(user_id)
    resolved = (base / filename).resolve()
    if not str(resolved).startswith(str(base.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file path")
    return resolved


def get_dataset_path(dataset: Dataset) -> Path:
    return _safe_path(dataset.user_id, dataset.stored_filename)


def _detect_delimiter(file_bytes: bytes) -> str:
    sample = file_bytes[:4096].decode("utf-8", errors="ignore")
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return ","


def _read_dataframe(file: UploadFile, extension: str) -> pd.DataFrame:
    contents = file.file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )

    try:
        if extension == "csv":
            delimiter = _detect_delimiter(contents)
            try:
                df = pd.read_csv(
                    io.BytesIO(contents),
                    delimiter=delimiter,
                    encoding="utf-8",
                    on_bad_lines="error",
                )
            except UnicodeDecodeError:
                df = pd.read_csv(
                    io.BytesIO(contents),
                    delimiter=delimiter,
                    encoding="latin-1",
                    on_bad_lines="error",
                )
        else:
            df = pd.read_excel(
                io.BytesIO(contents),
                engine="xlrd" if extension == "xls" else "openpyxl",
            )
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="The file contains no data.")
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read the file as a valid {'CSV' if extension == 'csv' else 'spreadsheet'}: {exc}",
        )

    if df.columns.empty:
        raise HTTPException(status_code=400, detail="The file contains no columns.")
    if df.columns[0] is None or str(df.columns[0]).startswith("Unnamed"):
        df = df.drop(columns=[df.columns[0]])

    df = df.dropna(axis=1, how="all")
    if df.empty:
        raise HTTPException(status_code=400, detail="The file contains no data columns.")

    # Normalize column names
    df.columns = [str(c).strip() if pd.notna(c) else "unnamed_column" for c in df.columns]
    df.columns = _dedupe_column_names(df.columns)

    if len(df) == 0:
        raise HTTPException(status_code=400, detail="The file contains headers but no data rows.")

    if len(df) > settings.MAX_ROWS_PER_DATASET:
        raise HTTPException(
            status_code=400,
            detail=f"Dataset exceeds the limit of {settings.MAX_ROWS_PER_DATASET} rows.",
        )

    return df


def _dedupe_column_names(columns: pd.Index) -> list[str]:
    seen: dict[str, int] = {}
    result: list[str] = []
    for col in columns:
        name = str(col)
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        result.append(name)
    return result


def _normalise_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce common numeric columns to numbers where safe, so stats work."""
    for col in df.columns:
        non_null = df[col].dropna()
        if non_null.empty:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            continue
        if df[col].dtype == object:
            cleaned = non_null.astype(str).str.replace(",", "", regex=False)
            converted = pd.to_numeric(cleaned, errors="coerce")
            if converted.notna().sum() >= max(1, len(non_null) * 0.9):
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "", regex=False), errors="coerce")
    return df


def _infer_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if df[col].dtype == object:
            non_null = df[col].dropna()
            if non_null.empty:
                continue
            try:
                parsed = pd.to_datetime(non_null, errors="coerce", format="mixed")
                if parsed.notna().sum() >= max(1, len(non_null) * 0.9):
                    df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed")
            except (ValueError, TypeError):
                pass
    return df


def column_metadata(df: pd.DataFrame) -> list[dict]:
    meta = []
    for col in df.columns:
        meta.append({"name": str(col), "dtype": str(df[col].dtype)})
    return meta


def process_upload(user: User, db: Session, file: UploadFile) -> Dataset:
    original_filename = file.filename or "uploaded_file"
    extension = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{extension}'. Upload a CSV, XLSX, or XLS file.",
        )

    df = _read_dataframe(file, extension)
    df = _normalise_dtypes(df)
    df = _infer_dtypes(df)

    # Store the original file in Neon Object Storage
    file.file.seek(0)
    contents = file.file.read()

    stored_filename = f"{uuid.uuid4().hex}.{extension}"
    object_key = f"datasets/{user.id}/{stored_filename}"

    try:
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=object_key,
            Body=contents,
            ContentType=file.content_type or "application/octet-stream",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store dataset: {exc}",
        )

    dataset = Dataset(
        user_id=user.id,
        original_filename=original_filename,
        stored_filename=object_key,
        file_format=extension,
        file_size_bytes=len(contents),
        row_count=len(df),
        column_count=len(df.columns),
        columns=column_metadata(df),
        status="ready",
    )

    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def load_dataframe(dataset: Dataset) -> pd.DataFrame:
    try:
        response = s3_client.get_object(
            Bucket=S3_BUCKET_NAME,
            Key=dataset.stored_filename,
        )
        file_bytes = response["Body"].read()

        if dataset.file_format == "csv":
            delimiter = _detect_delimiter(file_bytes)
            try:
                df = pd.read_csv(
                    io.BytesIO(file_bytes),
                    delimiter=delimiter,
                    encoding="utf-8",
                    on_bad_lines="error",
                )
            except UnicodeDecodeError:
                df = pd.read_csv(
                    io.BytesIO(file_bytes),
                    delimiter=delimiter,
                    encoding="latin-1",
                    on_bad_lines="error",
                )
        else:
            df = pd.read_excel(
                io.BytesIO(file_bytes),
                engine="xlrd" if dataset.file_format == "xls" else "openpyxl",
            )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read stored dataset: {exc}",
        )

    df = _normalise_dtypes(df)
    df = _infer_dtypes(df)
    return df


def update_dataset_metadata(dataset: Dataset, df: pd.DataFrame) -> None:
    dataset.row_count = len(df)
    dataset.column_count = len(df.columns)
    dataset.columns = column_metadata(df)


def save_dataframe(dataset: Dataset, df: pd.DataFrame, extension: str | None = None) -> None:
    ext = extension or dataset.file_format
    user_dir = settings.STORAGE_DIR / str(dataset.user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid.uuid4().hex}.{ext}"
    target = user_dir / stored_filename
    if ext == "csv":
        df.to_csv(target, index=False)
    else:
        df.to_excel(target, index=False)
    dataset.stored_filename = stored_filename
    dataset.file_format = ext