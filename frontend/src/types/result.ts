/**
 * 结果相关类型定义
 */

// 评估指标
export interface Metrics {
  mse: number
  rmse: number
  mae: number
  r2: number
  mape: number
}

// 结果信息
export interface Result {
  id: number
  name: string
  dataset_id: number
  configuration_id: number | null
  filename: string
  model_name: string
  model_version: string
  description: string
  row_count: number
  metrics: Partial<Metrics> | Record<string, never>  // 可能为空对象或部分指标
  created_at: string
  updated_at: string
}

// 创建结果
export interface ResultCreate {
  name: string
  dataset_id: number
  configuration_id?: number
  model_name: string
  model_version?: string
  description?: string
  file: File
}

// 更新结果
export interface ResultUpdate {
  name?: string
  model_name?: string
  model_version?: string
  description?: string
}

