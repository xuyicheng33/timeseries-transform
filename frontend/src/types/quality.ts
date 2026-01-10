/**
 * 数据质量相关类型定义
 */

// ============ 枚举类型 ============

/** 异常值检测方法 */
export type OutlierMethod = 'iqr' | 'zscore' | 'mad' | 'percentile' | 'threshold'

/** 异常值处理方式 */
export type OutlierAction = 'keep' | 'remove' | 'clip' | 'replace_mean' | 'replace_median' | 'replace_nan'

/** 缺失值处理策略 */
export type MissingStrategy = 
  | 'keep' 
  | 'drop_row' 
  | 'drop_column' 
  | 'fill_mean' 
  | 'fill_median' 
  | 'fill_mode' 
  | 'fill_forward' 
  | 'fill_backward' 
  | 'fill_linear' 
  | 'fill_value'

/** 数据质量等级 */
export type QualityLevel = 'excellent' | 'good' | 'fair' | 'poor'

/** 列数据类型 */
export type ColumnDataType = 'numeric' | 'integer' | 'float' | 'datetime' | 'categorical' | 'text' | 'boolean' | 'unknown'


// ============ 质量报告相关 ============

/** 单列缺失值统计 */
export interface ColumnMissingStats {
  column: string
  missing_count: number
  missing_ratio: number
  total_count: number
}

/** 单列异常值统计 */
export interface ColumnOutlierStats {
  column: string
  outlier_count: number
  outlier_ratio: number
  outlier_indices: number[]
  lower_bound: number | null
  upper_bound: number | null
  min_value: number
  max_value: number
  mean_value: number
  std_value: number
}

/** 列类型信息 */
export interface ColumnTypeInfo {
  column: string
  inferred_type: ColumnDataType
  original_dtype: string
  unique_count: number
  unique_ratio: number
  sample_values: (string | number | boolean)[]
}

/** 列基础统计信息 */
export interface ColumnBasicStats {
  column: string
  dtype: string
  count: number
  missing_count: number
  missing_ratio: number
  // 数值型统计
  mean?: number
  std?: number
  min?: number
  q1?: number
  median?: number
  q3?: number
  max?: number
  // 分类型统计
  unique_count?: number
  top_value?: string
  top_freq?: number
}

/** 时序特征分析 */
export interface TimeSeriesAnalysis {
  time_column: string | null
  start_time: string | null
  end_time: string | null
  frequency: string | null
  total_duration: string | null
  gaps_count: number
  is_regular: boolean
}

/** 质量改进建议 */
export interface QualitySuggestion {
  level: 'warning' | 'error' | 'info'
  column: string | null
  issue: string
  suggestion: string
  auto_fixable: boolean
}

/** 数据质量报告 */
export interface DataQualityReport {
  // 基础信息
  dataset_id: number
  dataset_name: string
  total_rows: number
  total_columns: number
  
  // 缺失值分析
  missing_stats: ColumnMissingStats[]
  total_missing_cells: number
  total_missing_ratio: number
  
  // 异常值分析
  outlier_method: string
  outlier_stats: ColumnOutlierStats[]
  total_outlier_cells: number
  total_outlier_ratio: number
  
  // 列类型信息
  column_types: ColumnTypeInfo[]
  numeric_columns: string[]
  categorical_columns: string[]
  datetime_columns: string[]
  
  // 列统计信息
  column_stats: ColumnBasicStats[]
  
  // 时序分析
  time_analysis: TimeSeriesAnalysis | null
  
  // 重复值
  duplicate_rows: number
  duplicate_ratio: number
  
  // 质量评分
  quality_score: number
  quality_level: QualityLevel
  
  // 建议
  suggestions: QualitySuggestion[]
  
  // 生成时间
  generated_at: string
}

/** 质量检测请求 */
export interface QualityCheckRequest {
  outlier_method?: OutlierMethod
  outlier_params?: Record<string, number>
  check_columns?: string[]
  include_suggestions?: boolean
}


// ============ 数据清洗相关 ============

/** 单列清洗配置 */
export interface ColumnCleaningConfig {
  column: string
  missing_strategy?: MissingStrategy
  missing_fill_value?: number
  outlier_action?: OutlierAction
  outlier_clip_lower?: number
  outlier_clip_upper?: number
}

/** 数据清洗配置 */
export interface CleaningConfig {
  // 全局缺失值处理
  missing_strategy: MissingStrategy
  missing_fill_value?: number
  missing_drop_threshold: number
  
  // 全局异常值处理
  outlier_method: OutlierMethod
  outlier_action: OutlierAction
  outlier_params: Record<string, number>
  
  // 重复值处理
  drop_duplicates: boolean
  duplicate_keep: 'first' | 'last' | 'none'
  
  // 列特定配置
  column_configs: ColumnCleaningConfig[]
  
  // 要处理的列
  target_columns?: string[]
  
  // 输出选项
  create_new_dataset: boolean
  new_dataset_suffix: string
}

/** 清洗预览行 */
export interface CleaningPreviewRow {
  index: number
  column: string
  original_value: string | number | null
  new_value: string | number | null
  action: 'removed' | 'filled' | 'clipped' | 'replaced'
}

/** 清洗预览统计 */
export interface CleaningPreviewStats {
  column: string
  original_missing: number
  after_missing: number
  original_outliers: number
  after_outliers: number
  rows_affected: number
}

/** 清洗预览响应 */
export interface CleaningPreviewResponse {
  preview_changes: CleaningPreviewRow[]
  stats: CleaningPreviewStats[]
  total_rows_before: number
  total_rows_after: number
  rows_removed: number
  cells_modified: number
  columns_removed: string[]
  quality_score_before: number
  quality_score_after: number
}

/** 清洗执行结果 */
export interface CleaningResult {
  success: boolean
  message: string
  new_dataset_id?: number
  new_dataset_name?: string
  rows_before: number
  rows_after: number
  rows_removed: number
  cells_modified: number
  columns_removed: string[]
  quality_score_after: number
}

/** 异常值详情响应 */
export interface OutlierDetailsResponse {
  column: string
  method: OutlierMethod
  params: Record<string, number>
  lower_bound: number | null
  upper_bound: number | null
  outlier_count: number
  outlier_ratio: number
  outliers: Array<{
    index: number
    value: number | null
  }>
  stats: {
    min: number
    max: number
    mean: number
    std: number
  }
}


// ============ 默认配置 ============

/** 默认清洗配置 */
export const DEFAULT_CLEANING_CONFIG: CleaningConfig = {
  missing_strategy: 'keep',
  missing_drop_threshold: 0.5,
  outlier_method: 'iqr',
  outlier_action: 'keep',
  outlier_params: { multiplier: 1.5 },
  drop_duplicates: false,
  duplicate_keep: 'first',
  column_configs: [],
  create_new_dataset: true,
  new_dataset_suffix: '_cleaned',
}

/** 异常值方法选项 */
export const OUTLIER_METHOD_OPTIONS = [
  { value: 'iqr', label: 'IQR (四分位距法)', description: '适用于大多数数据分布' },
  { value: 'zscore', label: 'Z-Score', description: '适用于正态分布数据' },
  { value: 'mad', label: 'MAD (中位数绝对偏差)', description: '对异常值更鲁棒' },
  { value: 'percentile', label: '百分位截断', description: '按百分位数截断' },
  { value: 'threshold', label: '自定义阈值', description: '手动设置上下界' },
]

/** 异常值处理选项 */
export const OUTLIER_ACTION_OPTIONS = [
  { value: 'keep', label: '保留不处理' },
  { value: 'remove', label: '删除整行' },
  { value: 'clip', label: '裁剪到边界值' },
  { value: 'replace_mean', label: '替换为均值' },
  { value: 'replace_median', label: '替换为中位数' },
  { value: 'replace_nan', label: '替换为空值' },
]

/** 缺失值处理选项 */
export const MISSING_STRATEGY_OPTIONS = [
  { value: 'keep', label: '保留不处理' },
  { value: 'drop_row', label: '删除包含缺失值的行' },
  { value: 'fill_mean', label: '均值填充' },
  { value: 'fill_median', label: '中位数填充' },
  { value: 'fill_mode', label: '众数填充' },
  { value: 'fill_forward', label: '前向填充' },
  { value: 'fill_backward', label: '后向填充' },
  { value: 'fill_linear', label: '线性插值' },
  { value: 'fill_value', label: '自定义值填充' },
]

/** 质量等级配置 */
export const QUALITY_LEVEL_CONFIG: Record<QualityLevel, { color: string; label: string }> = {
  excellent: { color: '#52c41a', label: '优秀' },
  good: { color: '#1890ff', label: '良好' },
  fair: { color: '#faad14', label: '一般' },
  poor: { color: '#ff4d4f', label: '较差' },
}

