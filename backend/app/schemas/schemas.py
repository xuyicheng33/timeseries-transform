from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============ Dataset Schemas ============
class DatasetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = ""


class DatasetCreate(DatasetBase):
    pass


class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class DatasetResponse(DatasetBase):
    id: int
    filename: str
    filepath: str
    file_size: int
    row_count: int
    column_count: int
    columns: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DatasetPreview(BaseModel):
    columns: List[str]
    data: List[Dict[str, Any]]
    total_rows: int


# ============ Configuration Schemas ============
class ConfigurationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    dataset_id: int
    channels: List[str] = []
    normalization: str = "none"
    anomaly_enabled: bool = False
    anomaly_type: Optional[str] = ""
    injection_algorithm: Optional[str] = ""
    sequence_logic: Optional[str] = ""
    window_size: int = Field(default=100, ge=1)
    stride: int = Field(default=1, ge=1)
    target_type: str = "next"
    target_k: int = Field(default=1, ge=1)


class ConfigurationCreate(ConfigurationBase):
    pass


class ConfigurationUpdate(BaseModel):
    name: Optional[str] = None
    channels: Optional[List[str]] = None
    normalization: Optional[str] = None
    anomaly_enabled: Optional[bool] = None
    anomaly_type: Optional[str] = None
    injection_algorithm: Optional[str] = None
    sequence_logic: Optional[str] = None
    window_size: Optional[int] = None
    stride: Optional[int] = None
    target_type: Optional[str] = None
    target_k: Optional[int] = None


class ConfigurationResponse(ConfigurationBase):
    id: int
    generated_filename: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GenerateFilenameRequest(BaseModel):
    dataset_name: str
    channels: List[str]
    normalization: str
    anomaly_enabled: bool
    anomaly_type: Optional[str] = ""
    injection_algorithm: Optional[str] = ""
    sequence_logic: Optional[str] = ""
    window_size: int
    stride: int
    target_type: str
    target_k: int = 1


# ============ Result Schemas ============
class ResultBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    dataset_id: int
    configuration_id: Optional[int] = None
    model_name: str = Field(..., min_length=1, max_length=100)
    model_version: Optional[str] = ""
    description: Optional[str] = ""


class ResultCreate(ResultBase):
    pass


class ResultUpdate(BaseModel):
    name: Optional[str] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    description: Optional[str] = None


class ResultResponse(ResultBase):
    id: int
    filename: str
    filepath: str
    row_count: int
    metrics: Dict[str, float]
    code_filepath: Optional[str] = ""
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Visualization Schemas ============
class MetricsResponse(BaseModel):
    mse: float
    rmse: float
    mae: float
    r2: float
    mape: float


class CompareRequest(BaseModel):
    result_ids: List[int]
    max_points: int = 2000
    algorithm: str = "lttb"


class ChartDataSeries(BaseModel):
    name: str
    data: List[List[float]]


class ChartDataResponse(BaseModel):
    series: List[ChartDataSeries]
    total_points: int
    downsampled: bool


class CompareResponse(BaseModel):
    chart_data: ChartDataResponse
    metrics: Dict[int, MetricsResponse]
