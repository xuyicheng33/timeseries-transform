/**
 * 配置 API
 */

import api from './index'
import type {
  Configuration,
  ConfigurationCreate,
  ConfigurationUpdate,
  GenerateFilenameRequest,
  GenerateFilenameResponse,
  DeleteResponse,
  PaginatedResponse,
} from '@/types'

/**
 * 创建配置
 */
export async function createConfiguration(data: ConfigurationCreate): Promise<Configuration> {
  return api.post('/configurations', data)
}

/**
 * 获取配置列表（分页）
 */
export async function getConfigurations(
  datasetId?: number,
  page: number = 1,
  pageSize: number = 20
): Promise<PaginatedResponse<Configuration>> {
  const params: Record<string, number> = { page, page_size: pageSize }
  if (datasetId !== undefined) params.dataset_id = datasetId

  return api.get('/configurations', { params })
}

/**
 * 获取所有配置（不分页，用于下拉选择等场景）
 */
export async function getAllConfigurations(datasetId?: number): Promise<Configuration[]> {
  const params: Record<string, number> = {}
  if (datasetId !== undefined) params.dataset_id = datasetId

  return api.get('/configurations/all', { params })
}

/**
 * 获取配置详情
 */
export async function getConfiguration(id: number): Promise<Configuration> {
  return api.get(`/configurations/${id}`)
}

/**
 * 更新配置
 */
export async function updateConfiguration(
  id: number,
  data: ConfigurationUpdate
): Promise<Configuration> {
  return api.put(`/configurations/${id}`, data)
}

/**
 * 删除配置
 */
export async function deleteConfiguration(id: number): Promise<DeleteResponse> {
  return api.delete(`/configurations/${id}`)
}

/**
 * 生成标准文件名
 */
export async function generateFilename(
  data: GenerateFilenameRequest
): Promise<GenerateFilenameResponse> {
  return api.post('/configurations/generate-name', data)
}
