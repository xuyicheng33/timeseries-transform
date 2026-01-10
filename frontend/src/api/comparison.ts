/**
 * 配置对比分析 API
 */
import request from '@/utils/request'
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
  const response = await request.post<ConfigCompareResponse>('/comparison/analyze', {
    result_ids: resultIds,
  })
  return response.data
}

/**
 * 控制变量对比
 */
export async function controlledComparison(
  resultIds: number[],
  controlParameter: string
): Promise<ControlledCompareResponse> {
  const response = await request.post<ControlledCompareResponse>('/comparison/controlled', {
    result_ids: resultIds,
    control_parameter: controlParameter,
  })
  return response.data
}

/**
 * 参数敏感性分析
 */
export async function analyzeSensitivity(
  resultIds: number[],
  targetMetric: string = 'rmse'
): Promise<SensitivityResponse> {
  const response = await request.post<SensitivityResponse>('/comparison/sensitivity', {
    result_ids: resultIds,
    target_metric: targetMetric,
  })
  return response.data
}

/**
 * 获取可分析的参数列表
 */
export async function getAnalyzableParameters(): Promise<ParametersResponse> {
  const response = await request.get<ParametersResponse>('/comparison/parameters')
  return response.data
}

