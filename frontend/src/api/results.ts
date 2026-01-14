/**
 * 结果 API
 */

import api from './index'
import type {
  Result,
  ResultUpdate,
  DeleteResponse,
  PaginatedResponse,
} from '@/types'

/**
 * 上传结果
 * 
 * 支持两种上传模式：
 * 1. 完整模式：CSV 包含 true_value 和 predicted_value 两列
 * 2. 仅预测值模式：CSV 只包含 predicted_value 列，需要指定 targetColumn 参数
 */
export async function uploadResult(
  name: string,
  datasetId: number,
  modelName: string,
  file: File,
  configurationId?: number,
  modelVersion?: string,
  description?: string,
  onProgress?: (percent: number) => void,
  targetColumn?: string  // 新增：数据集中的目标列名（用于只上传预测值的情况）
): Promise<Result> {
  const formData = new FormData()
  formData.append('name', name)
  formData.append('dataset_id', String(datasetId))
  formData.append('model_name', modelName)
  formData.append('file', file)
  
  if (configurationId) {
    formData.append('configuration_id', String(configurationId))
  }
  if (modelVersion) {
    formData.append('model_version', modelVersion)
  }
  if (description) {
    formData.append('description', description)
  }
  if (targetColumn) {
    formData.append('target_column', targetColumn)
  }

  return api.post('/results/upload', formData, {
    timeout: 300000, // 5分钟
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        onProgress(percent)
      }
    },
  })
}

/**
 * 获取所有不重复的模型名称（用于筛选下拉框）
 */
export async function getModelNames(datasetId?: number): Promise<string[]> {
  const params: Record<string, number> = {}
  if (datasetId !== undefined) params.dataset_id = datasetId
  
  return api.get('/results/model-names', { params })
}

/**
 * 获取结果列表（分页）
 */
export async function getResults(
  datasetId?: number,
  modelName?: string,
  page: number = 1,
  pageSize: number = 20,
  configurationId?: number
): Promise<PaginatedResponse<Result>> {
  const params: Record<string, number | string> = { page, page_size: pageSize }
  if (datasetId !== undefined) params.dataset_id = datasetId
  if (modelName !== undefined) params.algo_name = modelName
  if (configurationId !== undefined) params.configuration_id = configurationId
  
  return api.get('/results', { params })
}

/**
 * 获取所有结果（不分页，用于下拉选择等场景）
 */
export async function getAllResults(
  datasetId?: number,
  modelName?: string
): Promise<Result[]> {
  const params: Record<string, number | string> = {}
  if (datasetId !== undefined) params.dataset_id = datasetId
  if (modelName !== undefined) params.algo_name = modelName
  
  return api.get('/results/all', { params })
}

/**
 * 获取结果详情
 */
export async function getResult(id: number): Promise<Result> {
  return api.get(`/results/${id}`)
}

/**
 * 预览结果数据
 */
export async function previewResult(
  id: number,
  rows: number = 100
): Promise<{ columns: string[]; data: Record<string, unknown>[]; total_rows: number }> {
  return api.get(`/results/${id}/preview`, { params: { rows } })
}

/**
 * 获取结果下载路径
 */
export function getResultDownloadPath(id: number): string {
  return `/results/${id}/download`
}

/**
 * 更新结果
 */
export async function updateResult(
  id: number,
  data: ResultUpdate
): Promise<Result> {
  return api.put(`/results/${id}`, data)
}

/**
 * 删除结果
 */
export async function deleteResult(id: number): Promise<DeleteResponse> {
  return api.delete(`/results/${id}`)
}

