/**
 * 高级可视化类型定义
 */

// ============ 特征重要性 ============

export type FeatureImportanceMethod = 'correlation' | 'variance' | 'gradient'

export interface FeatureImportanceRequest {
  result_id: number
  method?: FeatureImportanceMethod
  top_k?: number
}

export interface FeatureImportance {
  feature_name: string
  importance: number
  rank: number
}

export interface FeatureImportanceResponse {
  result_id: number
  result_name: string
  method: string
  features: FeatureImportance[]
  total_features: number
}

// ============ 置信区间 ============

export interface ConfidenceIntervalRequest {
  result_id: number
  confidence_level?: number
  window_size?: number
  max_points?: number
}

export interface ConfidenceIntervalPoint {
  index: number
  predicted: number
  lower_bound: number
  upper_bound: number
  true_value?: number
}

export interface ConfidenceIntervalResponse {
  result_id: number
  result_name: string
  confidence_level: number
  data: ConfidenceIntervalPoint[]
  coverage_rate: number
  avg_interval_width: number
  total_points: number
  downsampled: boolean
}

// ============ 误差热力图 ============

export interface ErrorHeatmapRequest {
  result_ids: number[]
  bins?: number
}

export interface HeatmapCell {
  x_bin: number
  y_bin: number
  count: number
  percentage: number
}

export interface ErrorHeatmapData {
  result_id: number
  result_name: string
  model_name: string
  cells: HeatmapCell[]
  x_labels: string[]
  y_labels: string[]
  error_range: [number, number]
}

export interface ErrorHeatmapResponse {
  heatmaps: ErrorHeatmapData[]
  unified_error_range: [number, number]
}

// ============ 预测分解 ============

export type DecompositionType = 'trend_seasonal' | 'residual'

export interface PredictionDecompositionRequest {
  result_id: number
  decomposition_type?: DecompositionType
  period?: number
}

export interface DecompositionComponent {
  name: string
  values: number[]
  indices: number[]
}

export interface PredictionDecompositionResponse {
  result_id: number
  result_name: string
  components: DecompositionComponent[]
  detected_period?: number
}

// ============ 配置常量 ============

export const FEATURE_IMPORTANCE_METHODS = [
  { value: 'correlation', label: '相关性分析', description: '基于与预测值的相关系数' },
  { value: 'variance', label: '方差分析', description: '基于特征的方差大小' },
  { value: 'gradient', label: '梯度分析', description: '基于特征变化与预测变化的关联' },
]

export const CONFIDENCE_LEVELS = [
  { value: 0.9, label: '90%' },
  { value: 0.95, label: '95%' },
  { value: 0.99, label: '99%' },
]

export const DECOMPOSITION_COLORS = {
  trend: '#1890ff',
  seasonal: '#52c41a',
  residual: '#faad14',
  predicted: '#722ed1',
  true: '#eb2f96',
}
