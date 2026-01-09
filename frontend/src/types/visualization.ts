/**
 * 可视化相关类型定义
 */

import type { Metrics } from './result'

// 降采样算法
export type DownsampleAlgorithm = 'lttb' | 'minmax' | 'average'

// 对比请求
export interface CompareRequest {
  result_ids: number[]
  max_points: number
  algorithm: DownsampleAlgorithm
}

// 图表数据系列
export interface ChartSeries {
  name: string
  data: [number, number][]
}

// 图表数据
export interface ChartData {
  series: ChartSeries[]
  total_points: number
  downsampled: boolean
}

// 跳过的结果信息（真正被跳过，未处理）
export interface SkippedResult {
  id: number
  name: string
  reason: string
}

// 警告信息（已处理但有潜在问题）
export interface WarningInfo {
  id: number
  name: string
  message: string
}

// 对比响应
export interface CompareResponse {
  chart_data: ChartData
  metrics: Record<number, Metrics>  // 使用 number 作为索引类型（result_id）
  skipped: SkippedResult[]  // 跳过的结果列表
  warnings: WarningInfo[]   // 警告列表（已处理但有问题）
}

// ============ 误差分析相关 ============

// 误差分析请求
export interface ErrorAnalysisRequest {
  result_ids: number[]
  start_index?: number
  end_index?: number
}

// 误差分布统计
export interface ErrorDistribution {
  min: number
  max: number
  mean: number
  std: number
  median: number
  q1: number
  q3: number
  histogram: Array<{
    bin_start: number
    bin_end: number
    count: number
    percentage: number
  }>
}

// 残差数据
export interface ResidualData {
  indices: number[]
  residuals: number[]
  abs_residuals: number[]
  percentage_errors: number[]
}

// 单个结果的误差分析
export interface SingleErrorAnalysis {
  result_id: number
  result_name: string
  model_name: string
  metrics: Metrics
  distribution: ErrorDistribution
  residual_data: ResidualData
}

// 误差分析响应
export interface ErrorAnalysisResponse {
  analyses: SingleErrorAnalysis[]
  skipped: SkippedResult[]
  range_info: {
    start_index: number | null
    end_index: number | null
    is_full_range: boolean
  }
}

// ============ 雷达图相关 ============

// 雷达图指标（归一化后）
export interface RadarMetrics {
  result_id: number
  result_name: string
  model_name: string
  mse_score: number
  rmse_score: number
  mae_score: number
  r2_score: number
  mape_score: number
  raw_metrics: Metrics
}

// 排名信息
export interface RankingItem {
  result_id: number
  rank: number
  value: number
}

// 综合得分
export interface OverallScore {
  result_id: number
  result_name: string
  model_name: string
  score: number
  rank: number
}

// 雷达图响应
export interface RadarChartResponse {
  results: RadarMetrics[]
  rankings: Record<string, RankingItem[]>
  overall_scores: OverallScore[]
}

// ============ 区间指标相关 ============

// 区间指标请求
export interface RangeMetricsRequest {
  result_ids: number[]
  start_index: number
  end_index: number
}

// 区间指标响应
export interface RangeMetricsResponse {
  range_start: number
  range_end: number
  total_points: number
  metrics: Record<number, Metrics>
  skipped: SkippedResult[]
}

