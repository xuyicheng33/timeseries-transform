/**
 * 可视化 API
 */

import api from './index'
import { rawRequest } from './request'
import type {
  CompareRequest,
  CompareResponse,
  Metrics,
  ErrorAnalysisRequest,
  ErrorAnalysisResponse,
  RadarChartResponse,
  RangeMetricsRequest,
  RangeMetricsResponse,
} from '@/types'

/**
 * 对比多个结果
 */
export async function compareResults(data: CompareRequest): Promise<CompareResponse> {
  return api.post('/visualization/compare', data)
}

/**
 * 获取单个结果的指标
 */
export async function getMetrics(id: number): Promise<Metrics> {
  return api.get(`/visualization/metrics/${id}`)
}

/**
 * 误差分析
 */
export async function analyzeErrors(data: ErrorAnalysisRequest): Promise<ErrorAnalysisResponse> {
  return api.post('/visualization/error-analysis', data)
}

/**
 * 获取雷达图数据
 */
export async function getRadarChart(data: CompareRequest): Promise<RadarChartResponse> {
  return api.post('/visualization/radar-chart', data)
}

/**
 * 计算区间指标
 */
export async function calculateRangeMetrics(
  data: RangeMetricsRequest
): Promise<RangeMetricsResponse> {
  return api.post('/visualization/range-metrics', data)
}

/**
 * 导出对比数据为 CSV
 */
export async function exportCompareCSV(data: CompareRequest): Promise<Blob> {
  const response = await rawRequest.post('/visualization/export-csv', data, {
    responseType: 'blob',
  })
  return response.data
}
