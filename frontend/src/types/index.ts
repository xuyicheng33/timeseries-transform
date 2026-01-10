/**
 * 类型定义统一导出
 */

// Dataset
export type {
  Dataset,
  DatasetPreview,
  DatasetCreate,
  DatasetUpdate,
} from './dataset'

// Configuration
export type {
  NormalizationType,
  TargetType,
  AnomalyType,
  InjectionAlgorithm,
  SequenceLogic,
  Configuration,
  ConfigurationCreate,
  ConfigurationUpdate,
  GenerateFilenameRequest,
  GenerateFilenameResponse,
} from './configuration'

// Result
export type {
  Metrics,
  Result,
  ResultCreate,
  ResultUpdate,
} from './result'

// Visualization
export type {
  DownsampleAlgorithm,
  CompareRequest,
  ChartSeries,
  ChartData,
  SkippedResult,
  WarningInfo,
  CompareResponse,
  // 新增类型
  ErrorAnalysisRequest,
  ErrorDistribution,
  ResidualData,
  SingleErrorAnalysis,
  ErrorAnalysisResponse,
  RadarMetrics,
  RankingItem,
  OverallScore,
  RadarChartResponse,
  RangeMetricsRequest,
  RangeMetricsResponse,
} from './visualization'

// API
export type {
  ValidationErrorItem,
  ApiError,
  DeleteResponse,
  PaginationParams,
  PaginatedResponse,
} from './api'

// Auth
export type {
  User,
  UserRegister,
  UserLogin,
  UserUpdate,
  PasswordUpdate,
  TokenResponse,
  TokenRefresh,
  AuthState,
} from './auth'

// Quality (数据质量)
export type {
  OutlierMethod,
  OutlierAction,
  MissingStrategy,
  QualityLevel,
  ColumnDataType,
  ColumnMissingStats,
  ColumnOutlierStats,
  ColumnTypeInfo,
  ColumnBasicStats,
  TimeSeriesAnalysis,
  QualitySuggestion,
  DataQualityReport,
  QualityCheckRequest,
  ColumnCleaningConfig,
  CleaningConfig,
  CleaningPreviewRow,
  CleaningPreviewStats,
  CleaningPreviewResponse,
  CleaningResult,
  OutlierDetailsResponse,
} from './quality'

export {
  DEFAULT_CLEANING_CONFIG,
  OUTLIER_METHOD_OPTIONS,
  OUTLIER_ACTION_OPTIONS,
  MISSING_STRATEGY_OPTIONS,
  QUALITY_LEVEL_CONFIG,
} from './quality'

// Comparison (配置对比分析)
export type {
  ParameterValue,
  ParameterAnalysis,
  ResultDetail,
  ConfigCompareResponse,
  ControlledVariation,
  ChartAxisData,
  ChartSeriesData,
  ControlledChartData,
  ControlledCompareResponse,
  ValueMetricPair,
  SensitivityItem,
  SensitivityResponse,
  AnalyzableParameter,
  AnalyzableMetric,
  ParametersResponse,
} from './comparison'
