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

// Folder
export type {
  Folder,
  FolderListResponse,
  FolderCreate,
  FolderUpdate,
  FolderSortOrderItem,
  FolderSortOrderUpdate,
} from './folder'

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

// Experiment (实验组管理)
export type {
  ExperimentStatus,
  Experiment,
  ExperimentResultBrief,
  ExperimentDetail,
  ExperimentCreateRequest,
  ExperimentUpdateRequest,
  ExperimentResultsRequest,
  BestMetricInfo,
  ExperimentSummary,
  ExperimentListParams,
} from './experiment'

// ModelTemplate (模型模板)
export type {
  ModelCategory,
  TaskType,
  ModelTemplateBase,
  ModelTemplateCreate,
  ModelTemplateUpdate,
  ModelTemplate,
  ModelTemplateBrief,
  ModelCategoryOption,
  ModelTemplateListParams,
  InitPresetsResponse,
} from './modelTemplate'

export {
  MODEL_CATEGORY_CONFIG,
  TASK_TYPE_CONFIG,
} from './modelTemplate'

// Report (实验报告)
export type {
  ReportConfig,
  ReportFormat,
  ExperimentReportRequest,
  MultiResultReportRequest,
  LatexTableResponse,
} from './report'

export {
  DEFAULT_REPORT_CONFIG,
  REPORT_FORMAT_OPTIONS,
} from './report'

// Advanced Visualization (高级可视化)
export type {
  FeatureImportanceMethod,
  FeatureImportanceRequest,
  FeatureImportance,
  FeatureImportanceResponse,
  ConfidenceIntervalRequest,
  ConfidenceIntervalPoint,
  ConfidenceIntervalResponse,
  ErrorHeatmapRequest,
  HeatmapCell,
  ErrorHeatmapData,
  ErrorHeatmapResponse,
  DecompositionType,
  PredictionDecompositionRequest,
  DecompositionComponent,
  PredictionDecompositionResponse,
} from './advancedViz'

export {
  FEATURE_IMPORTANCE_METHODS,
  CONFIDENCE_LEVELS,
  DECOMPOSITION_COLORS,
} from './advancedViz'
