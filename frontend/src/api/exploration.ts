/**
 * 数据探索 API
 */
import request from './request'

// ============ 类型定义 ============

export interface HistogramBin {
  bin_start: number
  bin_end: number
  count: number
  ratio: number
}

export interface NumericStats {
  min: number
  max: number
  mean: number
  std: number
  median: number
  q1: number
  q3: number
  skewness?: number
  kurtosis?: number
}

export interface BoxplotData {
  min: number
  q1: number
  median: number
  q3: number
  max: number
  outliers: number[]
}

export interface NumericDistribution {
  type: 'numeric'
  column: string
  total_count: number
  valid_count: number
  missing_count: number
  histogram: HistogramBin[]
  stats: NumericStats
  boxplot: BoxplotData
}

export interface ValueCount {
  value: string
  count: number
  ratio: number
}

export interface CategoricalDistribution {
  type: 'categorical'
  column: string
  total_count: number
  unique_count: number
  missing_count: number
  value_counts: ValueCount[]
}

export type DistributionResponse = NumericDistribution | CategoricalDistribution

export interface StrongCorrelation {
  column1: string
  column2: string
  correlation: number
  strength: 'strong' | 'moderate'
}

export interface CorrelationResponse {
  columns: string[]
  matrix: (number | null)[][]
  method: string
  strong_correlations: StrongCorrelation[]
}

export interface TrendStats {
  min: number
  max: number
  mean: number
  std: number
  trend_slope: number
  trend_direction: 'increasing' | 'decreasing' | 'stable'
  total_points: number
  sampled_points: number
}

export interface TrendResponse {
  raw_data: [number, number][]
  moving_avg: [number, number][]
  trend_line: [number, number][]
  stats: TrendStats
}

export interface SeriesData {
  name: string
  data: [number, number | null][]
}

export interface ColumnStats {
  column: string
  min: number
  max: number
  mean: number
  std: number
  valid_count: number
}

export interface CompareResponse {
  series: SeriesData[]
  stats: ColumnStats[]
  correlation: {
    columns: string[]
    matrix: number[][]
  }
  normalized: boolean
  total_points: number
  sampled_points: number
}

export interface ColumnSummary {
  name: string
  dtype: string
  inferred_type: 'numeric' | 'datetime' | 'boolean' | 'categorical' | 'text'
  missing: number
  missing_ratio: number
  unique: number
}

export interface NumericColumnStats {
  count: number
  mean: number
  std: number
  min: number
  q1: number
  median: number
  q3: number
  max: number
}

export interface OverviewResponse {
  basic_info: {
    name: string
    rows: number
    columns: number
    memory_mb: number
  }
  column_summary: ColumnSummary[]
  numeric_summary: Record<string, NumericColumnStats>
  numeric_columns: string[]
  categorical_columns: string[]
}

// ============ API 函数 ============

/**
 * 获取列分布数据
 */
export async function getColumnDistribution(
  datasetId: number,
  column: string,
  bins: number = 30
): Promise<DistributionResponse> {
  return request.get(`/exploration/${datasetId}/distribution/${encodeURIComponent(column)}`, {
    params: { bins },
    timeout: 300000
  })
}

/**
 * 获取相关性矩阵
 */
export async function getCorrelationMatrix(
  datasetId: number,
  columns?: string[],
  method: 'pearson' | 'spearman' | 'kendall' = 'pearson'
): Promise<CorrelationResponse> {
  return request.get(`/exploration/${datasetId}/correlation`, {
    params: {
      columns: columns?.join(','),
      method
    },
    timeout: 300000
  })
}

/**
 * 获取趋势分析数据
 */
export async function getTrendAnalysis(
  datasetId: number,
  column: string,
  options?: {
    time_column?: string
    window?: number
    max_points?: number
  }
): Promise<TrendResponse> {
  return request.get(`/exploration/${datasetId}/trend/${encodeURIComponent(column)}`, {
    params: {
      time_column: options?.time_column,
      window: options?.window || 10,
      max_points: options?.max_points || 2000
    },
    timeout: 300000
  })
}

/**
 * 多列对比
 */
export async function compareColumns(
  datasetId: number,
  columns: string[],
  options?: {
    normalize?: boolean
    max_points?: number
  }
): Promise<CompareResponse> {
  return request.get(`/exploration/${datasetId}/compare`, {
    params: {
      columns: columns.join(','),
      normalize: options?.normalize ?? true,
      max_points: options?.max_points || 2000
    },
    timeout: 300000
  })
}

/**
 * 获取数据概览
 */
export async function getDataOverview(datasetId: number): Promise<OverviewResponse> {
  return request.get(`/exploration/${datasetId}/overview`, {
    timeout: 300000
  })
}

