from datetime import datetime
from typing import Optional, List, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.schemas.enums import (
    NormalizationType, TargetType, AnomalyType, 
    InjectionAlgorithm, SequenceLogic, DownsampleAlgorithm
)


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

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('名称不能为空')
        return v

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> str:
        if v is None:
            return ""
        return v.strip()


class DatasetCreate(DatasetBase):
    pass


class DatasetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('名称不能为空')
        return v


class DatasetResponse(DatasetBase):
    id: int
    filename: str
    file_size: int
    row_count: int
    column_count: int
    columns: List[str]
    user_id: Optional[int] = None
    is_public: bool = True
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
    normalization: NormalizationType = NormalizationType.NONE
    anomaly_enabled: bool = False
    anomaly_type: Optional[AnomalyType] = None
    injection_algorithm: Optional[InjectionAlgorithm] = None
    sequence_logic: Optional[SequenceLogic] = None
    window_size: int = Field(default=100, ge=1, le=10000)
    stride: int = Field(default=1, ge=1, le=1000)
    target_type: TargetType = TargetType.NEXT
    target_k: int = Field(default=1, ge=1, le=100)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('名称不能为空')
        return v

    @field_validator('channels')
    @classmethod
    def validate_channels(cls, v: List[str]) -> List[str]:
        # 去除空白通道名
        return [ch.strip() for ch in v if ch.strip()]

    @field_validator('anomaly_type', 'injection_algorithm', 'sequence_logic', mode='before')
    @classmethod
    def convert_empty_string_to_none(cls, v):
        """将空字符串转换为 None，兼容前端提交的 '' 值"""
        if v == '' or v is None:
            return None
        return v


class ConfigurationCreate(ConfigurationBase):
    pass


class ConfigurationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    channels: Optional[List[str]] = None
    normalization: Optional[NormalizationType] = None
    anomaly_enabled: Optional[bool] = None
    anomaly_type: Optional[AnomalyType] = None
    injection_algorithm: Optional[InjectionAlgorithm] = None
    sequence_logic: Optional[SequenceLogic] = None
    window_size: Optional[int] = Field(default=None, ge=1, le=10000)
    stride: Optional[int] = Field(default=None, ge=1, le=1000)
    target_type: Optional[TargetType] = None
    target_k: Optional[int] = Field(default=None, ge=1, le=100)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('名称不能为空')
        return v

    @field_validator('anomaly_type', 'injection_algorithm', 'sequence_logic', mode='before')
    @classmethod
    def convert_empty_string_to_none(cls, v):
        """将空字符串转换为 None，兼容前端提交的 '' 值"""
        if v == '' or v is None:
            return None
        return v


class ConfigurationResponse(BaseModel):
    id: int
    name: str
    dataset_id: int
    channels: List[str]
    normalization: str  # 返回字符串以兼容前端
    anomaly_enabled: bool
    anomaly_type: Optional[str] = ""
    injection_algorithm: Optional[str] = ""
    sequence_logic: Optional[str] = ""
    window_size: int
    stride: int
    target_type: str
    target_k: int
    generated_filename: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator('anomaly_type', 'injection_algorithm', 'sequence_logic', mode='before')
    @classmethod
    def convert_none_to_empty(cls, v):
        return v if v is not None else ""


class GenerateFilenameRequest(BaseModel):
    dataset_name: str
    channels: List[str] = Field(default_factory=list)
    normalization: NormalizationType = NormalizationType.NONE
    anomaly_enabled: bool = False
    anomaly_type: Optional[str] = ""
    injection_algorithm: Optional[str] = ""
    sequence_logic: Optional[str] = ""
    window_size: int = Field(default=100, ge=1)
    stride: int = Field(default=1, ge=1)
    target_type: TargetType = TargetType.NEXT
    target_k: int = Field(default=1, ge=1)


# ============ Result Schemas ============
class ResultBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    dataset_id: int
    configuration_id: Optional[int] = None
    algo_name: str = Field(..., min_length=1, max_length=100, alias="model_name")
    algo_version: Optional[str] = Field(default="", max_length=50, alias="model_version")
    description: Optional[str] = Field(default="", max_length=1000)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator('name', 'algo_name')
    @classmethod
    def validate_required_string(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('字段不能为空')
        return v

    @field_validator('algo_version', 'description')
    @classmethod
    def validate_optional_string(cls, v: Optional[str]) -> str:
        if v is None:
            return ""
        return v.strip()


class ResultCreate(ResultBase):
    pass


class ResultUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    algo_name: Optional[str] = Field(default=None, min_length=1, max_length=100, alias="model_name")
    algo_version: Optional[str] = Field(default=None, max_length=50, alias="model_version")
    description: Optional[str] = Field(default=None, max_length=1000)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator('name', 'algo_name')
    @classmethod
    def validate_required_string(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('字段不能为空')
        return v


class ResultResponse(BaseModel):
    id: int
    name: str
    dataset_id: int
    configuration_id: Optional[int] = None
    user_id: Optional[int] = None
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
    algorithm: DownsampleAlgorithm = DownsampleAlgorithm.LTTB

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


class WarningInfo(BaseModel):
    """警告信息（结果已处理但有潜在问题）"""
    id: int
    name: str
    message: str


class CompareResponse(BaseModel):
    chart_data: ChartDataResponse
    metrics: Dict[int, MetricsResponse]
    skipped: List[SkippedResult] = Field(default_factory=list)  # 真正被跳过的结果
    warnings: List[WarningInfo] = Field(default_factory=list)   # 已处理但有警告的结果


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
