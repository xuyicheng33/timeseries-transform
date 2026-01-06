/**
 * 可视化 API
 */

import api from './index'
import type {
  CompareRequest,
  CompareResponse,
  Metrics,
} from '@/types'

/**
 * 对比多个结果
 */
export async function compareResults(
  data: CompareRequest
): Promise<CompareResponse> {
  return api.post('/visualization/compare', data)
}

/**
 * 获取单个结果的指标
 */
export async function getMetrics(id: number): Promise<Metrics> {
  return api.get(`/visualization/metrics/${id}`)
}

