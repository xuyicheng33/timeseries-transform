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
    is_public: Optional[bool] = None

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
    is_public: bool = False
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
    skipped: List[SkippedResult] = Field(default_factory=list)
    warnings: List[WarningInfo] = Field(default_factory=list)


# ============ 增强可视化 Schemas ============
class ErrorAnalysisRequest(BaseModel):
    """误差分析请求"""
    result_ids: List[int] = Field(default_factory=list)
    start_index: Optional[int] = Field(default=None, ge=0, description="起始索引")
    end_index: Optional[int] = Field(default=None, ge=0, description="结束索引")

    @field_validator('result_ids')
    @classmethod
    def validate_result_ids(cls, v):
        if not v:
            raise ValueError('result_ids 不能为空')
        if len(v) > 10:
            raise ValueError('最多同时分析 10 个结果')
        return v


class HistogramBin(BaseModel):
    """直方图单个 bin"""
    bin_start: float
    bin_end: float
    count: int
    percentage: float


class ErrorDistribution(BaseModel):
    """误差分布统计"""
    min: float
    max: float
    mean: float
    std: float
    median: float
    q1: float  # 25% 分位数
    q3: float  # 75% 分位数
    histogram: List[HistogramBin]


class ResidualData(BaseModel):
    """残差数据"""
    indices: List[int]
    residuals: List[float]  # 预测值 - 真实值
    abs_residuals: List[float]  # 绝对误差
    percentage_errors: List[float]  # 百分比误差


class SingleErrorAnalysis(BaseModel):
    """单个结果的误差分析"""
    result_id: int
    result_name: str
    model_name: str
    metrics: MetricsResponse
    distribution: ErrorDistribution
    residual_data: ResidualData


class RangeInfo(BaseModel):
    """区间信息"""
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    is_full_range: bool = True


class ErrorAnalysisResponse(BaseModel):
    """误差分析响应"""
    analyses: List[SingleErrorAnalysis]
    skipped: List[SkippedResult] = Field(default_factory=list)
    range_info: RangeInfo = Field(default_factory=RangeInfo)
    # 统一的 bin edges，用于前端对齐直方图
    unified_bin_edges: List[float] = Field(default_factory=list)


class RadarMetrics(BaseModel):
    """雷达图指标（归一化后）"""
    result_id: int
    result_name: str
    model_name: str
    # 归一化后的值 (0-1)，方向统一为越大越好
    mse_score: float
    rmse_score: float
    mae_score: float
    r2_score: float
    mape_score: float
    # 原始值
    raw_metrics: MetricsResponse


class MetricRanking(BaseModel):
    """单个指标的排名项"""
    result_id: int
    rank: int
    value: float


class OverallScore(BaseModel):
    """综合得分"""
    result_id: int
    result_name: str
    model_name: str
    score: float
    rank: int


class RadarChartResponse(BaseModel):
    """雷达图响应"""
    results: List[RadarMetrics]
    # 排名信息
    rankings: Dict[str, List[MetricRanking]]  # {metric_name: [排名列表]}
    # 综合得分
    overall_scores: List[OverallScore]


class RangeMetricsRequest(BaseModel):
    """区间指标计算请求"""
    result_ids: List[int]
    start_index: int = Field(..., ge=0)
    end_index: int = Field(..., ge=0)

    @field_validator('result_ids')
    @classmethod
    def validate_result_ids(cls, v):
        if not v:
            raise ValueError('result_ids 不能为空')
        return v


class RangeMetricsResponse(BaseModel):
    """区间指标响应"""
    range_start: int
    range_end: int
    total_points: int
    metrics: Dict[int, MetricsResponse]  # result_id -> metrics
    skipped: List[SkippedResult] = Field(default_factory=list)


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


# ============ 数据质量检测 Schemas ============

class ColumnMissingStats(BaseModel):
    """单列缺失值统计"""
    column: str
    missing_count: int
    missing_ratio: float  # 0-1
    total_count: int


class ColumnOutlierStats(BaseModel):
    """单列异常值统计"""
    column: str
    outlier_count: int
    outlier_ratio: float  # 0-1
    outlier_indices: List[int] = Field(default_factory=list, description="异常值索引（最多返回100个）")
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    min_value: float
    max_value: float
    mean_value: float
    std_value: float


class ColumnTypeInfo(BaseModel):
    """列类型信息"""
    column: str
    inferred_type: str  # numeric / datetime / categorical / text / boolean
    original_dtype: str  # pandas dtype
    unique_count: int
    unique_ratio: float  # 唯一值比例
    sample_values: List[Any] = Field(default_factory=list, description="示例值（最多5个）")


class ColumnBasicStats(BaseModel):
    """列基础统计信息"""
    column: str
    dtype: str
    count: int
    missing_count: int
    missing_ratio: float
    # 数值型统计
    mean: Optional[float] = None
    std: Optional[float] = None
    min: Optional[float] = None
    q1: Optional[float] = None  # 25%
    median: Optional[float] = None  # 50%
    q3: Optional[float] = None  # 75%
    max: Optional[float] = None
    # 分类型统计
    unique_count: Optional[int] = None
    top_value: Optional[str] = None
    top_freq: Optional[int] = None


class TimeSeriesAnalysis(BaseModel):
    """时序特征分析"""
    time_column: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    frequency: Optional[str] = None  # 推断的频率 (如 "1H", "1D")
    total_duration: Optional[str] = None
    gaps_count: int = 0  # 时间间隔不规则的数量
    is_regular: bool = True  # 是否规则时序


class QualitySuggestion(BaseModel):
    """质量改进建议"""
    level: str  # "warning" / "error" / "info"
    column: Optional[str] = None
    issue: str
    suggestion: str
    auto_fixable: bool = False  # 是否可自动修复


class DataQualityReport(BaseModel):
    """数据质量报告"""
    # 基础信息
    dataset_id: int
    dataset_name: str
    total_rows: int
    total_columns: int
    
    # 缺失值分析
    missing_stats: List[ColumnMissingStats] = Field(default_factory=list)
    total_missing_cells: int = 0
    total_missing_ratio: float = 0.0
    
    # 异常值分析
    outlier_method: str = "iqr"
    outlier_stats: List[ColumnOutlierStats] = Field(default_factory=list)
    total_outlier_cells: int = 0
    total_outlier_ratio: float = 0.0
    
    # 列类型信息
    column_types: List[ColumnTypeInfo] = Field(default_factory=list)
    numeric_columns: List[str] = Field(default_factory=list)
    categorical_columns: List[str] = Field(default_factory=list)
    datetime_columns: List[str] = Field(default_factory=list)
    
    # 列统计信息
    column_stats: List[ColumnBasicStats] = Field(default_factory=list)
    
    # 时序分析（如果检测到时间列）
    time_analysis: Optional[TimeSeriesAnalysis] = None
    
    # 重复值
    duplicate_rows: int = 0
    duplicate_ratio: float = 0.0
    
    # 质量评分
    quality_score: int = Field(ge=0, le=100)
    quality_level: str  # excellent / good / fair / poor
    
    # 建议
    suggestions: List[QualitySuggestion] = Field(default_factory=list)
    
    # 生成时间
    generated_at: datetime = Field(default_factory=lambda: datetime.now())


class QualityCheckRequest(BaseModel):
    """质量检测请求"""
    outlier_method: str = "iqr"  # iqr / zscore / mad / percentile
    outlier_params: Dict[str, Any] = Field(default_factory=dict)
    # IQR: {"multiplier": 1.5}
    # Z-Score: {"threshold": 3.0}
    # MAD: {"threshold": 3.5}
    # Percentile: {"lower": 1, "upper": 99}
    
    check_columns: Optional[List[str]] = None  # None 表示检测所有列
    include_suggestions: bool = True


# ============ 数据清洗 Schemas ============

class ColumnCleaningConfig(BaseModel):
    """单列清洗配置"""
    column: str
    
    # 缺失值处理
    missing_strategy: Optional[str] = None  # 使用枚举值
    missing_fill_value: Optional[float] = None
    
    # 异常值处理
    outlier_action: Optional[str] = None  # 使用枚举值
    outlier_clip_lower: Optional[float] = None
    outlier_clip_upper: Optional[float] = None


class CleaningConfig(BaseModel):
    """数据清洗配置"""
    # 全局缺失值处理
    missing_strategy: str = "keep"  # keep / drop_row / fill_mean / fill_median / fill_forward / fill_backward / fill_value
    missing_fill_value: Optional[float] = None
    missing_drop_threshold: float = Field(default=0.5, ge=0, le=1, description="缺失率超过此值的列将被删除")
    
    # 全局异常值处理
    outlier_method: str = "iqr"  # iqr / zscore / mad / percentile / threshold
    outlier_action: str = "keep"  # keep / remove / clip / replace_mean / replace_median
    outlier_params: Dict[str, Any] = Field(default_factory=lambda: {"multiplier": 1.5})
    
    # 重复值处理
    drop_duplicates: bool = False
    duplicate_keep: str = "first"  # first / last / none
    
    # 列特定配置（覆盖全局配置）
    column_configs: List[ColumnCleaningConfig] = Field(default_factory=list)
    
    # 要处理的列（None 表示所有数值列）
    target_columns: Optional[List[str]] = None
    
    # 输出选项
    create_new_dataset: bool = True  # True: 创建新数据集, False: 覆盖原数据集
    new_dataset_suffix: str = "_cleaned"


class CleaningPreviewRow(BaseModel):
    """清洗预览行"""
    index: int
    column: str
    original_value: Optional[Any] = None
    new_value: Optional[Any] = None
    action: str  # "removed" / "filled" / "clipped" / "replaced"


class CleaningPreviewStats(BaseModel):
    """清洗预览统计"""
    column: str
    original_missing: int
    after_missing: int
    original_outliers: int
    after_outliers: int
    rows_affected: int


class CleaningPreviewResponse(BaseModel):
    """清洗预览响应"""
    # 预览变更
    preview_changes: List[CleaningPreviewRow] = Field(default_factory=list, description="变更预览（最多100条）")
    
    # 统计信息
    stats: List[CleaningPreviewStats] = Field(default_factory=list)
    
    # 汇总
    total_rows_before: int
    total_rows_after: int
    rows_removed: int
    cells_modified: int
    columns_removed: List[str] = Field(default_factory=list)
    
    # 预估质量提升
    quality_score_before: int
    quality_score_after: int


class CleaningResult(BaseModel):
    """清洗执行结果"""
    success: bool
    message: str
    
    # 新数据集信息（如果创建了新数据集）
    new_dataset_id: Optional[int] = None
    new_dataset_name: Optional[str] = None
    
    # 清洗统计
    rows_before: int
    rows_after: int
    rows_removed: int
    cells_modified: int
    columns_removed: List[str] = Field(default_factory=list)
    
    # 清洗后的质量评分
    quality_score_after: int


# ============ 实验组 Schemas ============

class ExperimentBase(BaseModel):
    """实验组基础信息"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default="", max_length=2000)
    objective: Optional[str] = Field(default="", max_length=2000, description="实验目标/假设")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    dataset_id: Optional[int] = Field(default=None, description="关联的数据集ID")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('名称不能为空')
        return v

    @field_validator('description', 'objective')
    @classmethod
    def validate_optional_text(cls, v: Optional[str]) -> str:
        if v is None:
            return ""
        return v.strip()

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        # 去除空白标签，去重
        cleaned = list(set(tag.strip() for tag in v if tag.strip()))
        return cleaned


class ExperimentCreate(ExperimentBase):
    """创建实验组"""
    result_ids: List[int] = Field(default_factory=list, description="初始关联的结果ID列表")


class ExperimentUpdate(BaseModel):
    """更新实验组"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    objective: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[str] = Field(default=None, pattern=r'^(draft|running|completed|archived)$')
    tags: Optional[List[str]] = None
    conclusion: Optional[str] = Field(default=None, max_length=5000, description="实验结论")
    dataset_id: Optional[int] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('名称不能为空')
        return v

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            return list(set(tag.strip() for tag in v if tag.strip()))
        return v


class ExperimentResultBrief(BaseModel):
    """实验组中的结果简要信息"""
    id: int
    name: str
    algo_name: str = Field(..., serialization_alias="model_name")
    algo_version: str = Field(default="", serialization_alias="model_version")
    metrics: Dict[str, float] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ExperimentResponse(BaseModel):
    """实验组响应"""
    id: int
    name: str
    description: str = ""
    objective: str = ""
    status: str = "draft"
    tags: List[str] = Field(default_factory=list)
    conclusion: str = ""
    user_id: Optional[int] = None
    dataset_id: Optional[int] = None
    dataset_name: Optional[str] = None  # 关联数据集名称
    result_count: int = 0  # 关联结果数量
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExperimentDetailResponse(ExperimentResponse):
    """实验组详情响应（包含关联结果）"""
    results: List[ExperimentResultBrief] = Field(default_factory=list)


class ExperimentAddResults(BaseModel):
    """添加结果到实验组"""
    result_ids: List[int] = Field(..., min_length=1, description="要添加的结果ID列表")

    @field_validator('result_ids')
    @classmethod
    def validate_result_ids(cls, v: List[int]) -> List[int]:
        if not v:
            raise ValueError('result_ids 不能为空')
        return list(set(v))  # 去重


class ExperimentRemoveResults(BaseModel):
    """从实验组移除结果"""
    result_ids: List[int] = Field(..., min_length=1, description="要移除的结果ID列表")


class ExperimentCompareRequest(BaseModel):
    """实验组内结果对比请求"""
    max_points: int = Field(default=2000, ge=10, le=50000)
    algorithm: DownsampleAlgorithm = DownsampleAlgorithm.LTTB


class ExperimentSummary(BaseModel):
    """实验组汇总统计"""
    experiment_id: int
    experiment_name: str
    result_count: int
    model_names: List[str] = Field(default_factory=list)
    # 最佳指标
    best_mse: Optional[Dict[str, Any]] = None  # {"result_id": x, "value": y, "model_name": z}
    best_rmse: Optional[Dict[str, Any]] = None
    best_mae: Optional[Dict[str, Any]] = None
    best_r2: Optional[Dict[str, Any]] = None
    best_mape: Optional[Dict[str, Any]] = None
    # 平均指标
    avg_metrics: Optional[MetricsResponse] = None
