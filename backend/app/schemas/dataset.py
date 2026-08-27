from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ColumnInfo(BaseModel):
    name: str
    dtype: str


class DatasetOut(BaseModel):
    id: int
    original_filename: str
    file_format: str
    file_size_bytes: int
    row_count: int
    column_count: int
    columns: list[ColumnInfo]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DatasetListResponse(BaseModel):
    datasets: list[DatasetOut]
    total: int


class UploadResponse(BaseModel):
    dataset: DatasetOut


class PreviewOut(BaseModel):
    dataset: DatasetOut
    rows: list[dict[str, Any]]
    total_rows_shown: int


class NumericStats(BaseModel):
    count: int | None = None
    mean: float | None = None
    median: float | None = None
    min: float | None = None
    max: float | None = None
    sum: float | None = None
    std: float | None = None


class ColumnStatistics(BaseModel):
    name: str
    dtype: str
    count: int
    missing: int
    missing_percent: float
    unique: int
    numeric: NumericStats | None = None


class StatisticsOut(BaseModel):
    dataset_id: int
    columns: list[ColumnStatistics]


class QualityIssue(BaseModel):
    type: str
    severity: str
    message: str
    affected_columns: list[str]


class QualityOut(BaseModel):
    dataset_id: int
    total_rows: int
    total_columns: int
    total_cells: int
    missing_cells: int
    missing_percent: float
    duplicate_rows: int
    empty_columns: list[str]
    columns: list[ColumnStatistics]
    issues: list[QualityIssue]


class CleanRequest(BaseModel):
    drop_duplicates: bool = False
    fill_numeric_strategy: str | None = None  # mean | median | mode | drop
    fill_categorical_strategy: str | None = None  # mode | drop
    drop_empty_columns: bool = False
    trim_strings: bool = True
    convert_date_columns: bool = True


class CleanResponse(BaseModel):
    dataset_id: int
    message: str
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    operations: list[str]