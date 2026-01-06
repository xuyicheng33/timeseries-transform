/**
 * 配置相关类型定义
 */

// 归一化类型
export type NormalizationType = 'none' | 'minmax' | 'zscore' | 'head' | 'decimal'

// 目标类型
export type TargetType = 'next' | 'kstep' | 'reconstruct'

// 异常类型
export type AnomalyType = 'point' | 'segment' | 'trend' | 'seasonal' | 'noise'

// 注入算法
export type InjectionAlgorithm = 'random' | 'rule' | 'pattern'

// 序列逻辑
export type SequenceLogic = 'anomaly_first' | 'window_first'

// 配置信息
export interface Configuration {
  id: number
  name: string
  dataset_id: number
  channels: string[]
  normalization: NormalizationType
  anomaly_enabled: boolean
  anomaly_type: AnomalyType | ''
  injection_algorithm: InjectionAlgorithm | ''
  sequence_logic: SequenceLogic | ''
  window_size: number
  stride: number
  target_type: TargetType
  target_k: number
  generated_filename: string
  created_at: string
  updated_at: string
}

// 创建配置
export interface ConfigurationCreate {
  name: string
  dataset_id: number
  channels: string[]
  normalization: NormalizationType
  anomaly_enabled: boolean
  anomaly_type?: string
  injection_algorithm?: string
  sequence_logic?: string
  window_size: number
  stride: number
  target_type: TargetType
  target_k?: number
}

// 更新配置
export interface ConfigurationUpdate {
  name?: string
  channels?: string[]
  normalization?: NormalizationType
  anomaly_enabled?: boolean
  anomaly_type?: string
  injection_algorithm?: string
  sequence_logic?: string
  window_size?: number
  stride?: number
  target_type?: TargetType
  target_k?: number
}

// 生成文件名请求
export interface GenerateFilenameRequest {
  dataset_name: string
  channels: string[]
  normalization: NormalizationType
  anomaly_enabled: boolean
  anomaly_type?: string
  injection_algorithm?: string
  sequence_logic?: string
  window_size: number
  stride: number
  target_type: TargetType
  target_k?: number
}

// 生成文件名响应
export interface GenerateFilenameResponse {
  filename: string
}

