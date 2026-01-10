/**
 * 配置对比分析 API
 */
import request from './request'
import type {
  ConfigCompareResponse,
  ControlledCompareResponse,
  SensitivityResponse,
  ParametersResponse,
} from '@/types/comparison'

/**
 * 配置对比分析
 */
export async function analyzeConfigurations(resultIds: number[]): Promise<ConfigCompareResponse> {
  return request.post('/comparison/analyze', {
    result_ids: resultIds,
  })
}

/**
 * 控制变量对比
 */
export async function controlledComparison(
  resultIds: number[],
  controlParameter: string
): Promise<ControlledCompareResponse> {
  return request.post('/comparison/controlled', {
    result_ids: resultIds,
    control_parameter: controlParameter,
  })
}

/**
 * 参数敏感性分析
 */
export async function analyzeSensitivity(
  resultIds: number[],
  targetMetric: string = 'rmse'
): Promise<SensitivityResponse> {
  return request.post('/comparison/sensitivity', {
    result_ids: resultIds,
    target_metric: targetMetric,
  })
}

/**
 * 获取可分析的参数列表
 */
export async function getAnalyzableParameters(): Promise<ParametersResponse> {
  return request.get('/comparison/parameters')
}

