from datetime import datetime
from typing import Optional, List, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field, field_validator, ConfigDict


T = TypeVar('T')


# ============ 分页响应 ============
class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: List[T]
    total: int
    page: int
    page_size: int


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
    file_size: int
    row_count: int
    column_count: int
    columns: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetPreview(BaseModel):
    columns: List[str]
    data: List[Dict[str, Any]]
    total_rows: int


# ============ Configuration Schemas ============
class ConfigurationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    dataset_id: int
    channels: List[str] = Field(default_factory=list)
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

    model_config = ConfigDict(from_attributes=True)


class GenerateFilenameRequest(BaseModel):
    dataset_name: str
    channels: List[str] = Field(default_factory=list)
    normalization: str = "none"
    anomaly_enabled: bool = False
    anomaly_type: Optional[str] = ""
    injection_algorithm: Optional[str] = ""
    sequence_logic: Optional[str] = ""
    window_size: int = 100
    stride: int = 1
    target_type: str = "next"
    target_k: int = 1


# ============ Result Schemas ============
class ResultBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    dataset_id: int
    configuration_id: Optional[int] = None
    algo_name: str = Field(..., min_length=1, max_length=100, alias="model_name")
    algo_version: Optional[str] = Field(default="", alias="model_version")
    description: Optional[str] = ""

    model_config = ConfigDict(populate_by_name=True)


class ResultCreate(ResultBase):
    pass


class ResultUpdate(BaseModel):
    name: Optional[str] = None
    algo_name: Optional[str] = Field(default=None, alias="model_name")
    algo_version: Optional[str] = Field(default=None, alias="model_version")
    description: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class ResultResponse(BaseModel):
    id: int
    name: str
    dataset_id: int
    configuration_id: Optional[int] = None
    filename: str
    row_count: int
    algo_name: str = Field(..., serialization_alias="model_name")
    algo_version: str = Field(default="", serialization_alias="model_version")
    description: str = ""
    metrics: Dict[str, float] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ============ Visualization Schemas ============
class MetricsResponse(BaseModel):
    mse: float
    rmse: float
    mae: float
    r2: float
    mape: float


class CompareRequest(BaseModel):
    result_ids: List[int] = Field(default_factory=list)
    max_points: int = Field(default=2000, ge=10, le=50000)
    algorithm: str = Field(default="lttb", pattern="^(lttb|minmax|average)$")

    @field_validator('result_ids')
    @classmethod
    def validate_result_ids(cls, v):
        if not v:
            raise ValueError('result_ids 不能为空')
        if len(v) > 10:
            raise ValueError('最多同时对比 10 个结果')
        return v


class ChartDataSeries(BaseModel):
    name: str
    data: List[List[float]]


class ChartDataResponse(BaseModel):
    series: List[ChartDataSeries]
    total_points: int
    downsampled: bool


class SkippedResult(BaseModel):
    """跳过的结果信息"""
    id: int
    name: str
    reason: str


class CompareResponse(BaseModel):
    chart_data: ChartDataResponse
    metrics: Dict[int, MetricsResponse]
    skipped: List[SkippedResult] = Field(default_factory=list)  # 跳过的结果列表


# ============ User & Auth Schemas ============
class UserBase(BaseModel):
    """用户基础信息"""
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_]+$')
    email: str = Field(..., max_length=255)
    full_name: Optional[str] = Field(default="", max_length=100)


class UserCreate(UserBase):
    """用户注册"""
    password: str = Field(..., min_length=6, max_length=100)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('密码长度至少 6 位')
        return v


class UserUpdate(BaseModel):
    """用户信息更新"""
    full_name: Optional[str] = Field(default=None, max_length=100)
    email: Optional[str] = Field(default=None, max_length=255)


class UserPasswordUpdate(BaseModel):
    """密码更新"""
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


class UserResponse(BaseModel):
    """用户响应（不包含密码）"""
    id: int
    username: str
    email: str
    full_name: str = ""
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    """用户登录"""
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class Token(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Token 刷新请求"""
    refresh_token: str


class TokenData(BaseModel):
    """Token 数据"""
    user_id: Optional[int] = None
