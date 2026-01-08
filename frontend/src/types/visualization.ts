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

