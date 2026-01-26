/**
 * 模型模板 API
 */
import request from './request'
import type { PaginatedResponse } from '@/types/api'
import type {
  ModelTemplate,
  ModelTemplateBrief,
  ModelTemplateCreate,
  ModelTemplateUpdate,
  ModelTemplateListParams,
  ModelCategoryOption,
  InitPresetsResponse,
} from '@/types/modelTemplate'

const BASE_URL = '/model-templates'

/**
 * 初始化预置模型模板（仅管理员）
 */
export async function initPresetTemplates(): Promise<InitPresetsResponse> {
  return request.post(`${BASE_URL}/init-presets`)
}

/**
 * 获取模型模板列表（分页）
 */
export async function getModelTemplates(
  params: ModelTemplateListParams = {}
): Promise<PaginatedResponse<ModelTemplate>> {
  return request.get(BASE_URL, { params })
}

/**
 * 获取所有模型模板（不分页，用于下拉选择）
 */
export async function getAllModelTemplates(category?: string): Promise<ModelTemplateBrief[]> {
  return request.get(`${BASE_URL}/all`, { params: { category } })
}

/**
 * 获取模型类别列表
 */
export async function getModelCategories(): Promise<ModelCategoryOption[]> {
  return request.get(`${BASE_URL}/categories`)
}

/**
 * 获取模型模板详情
 */
export async function getModelTemplate(id: number): Promise<ModelTemplate> {
  return request.get(`${BASE_URL}/${id}`)
}

/**
 * 创建模型模板
 */
export async function createModelTemplate(data: ModelTemplateCreate): Promise<ModelTemplate> {
  return request.post(BASE_URL, data)
}

/**
 * 更新模型模板
 */
export async function updateModelTemplate(
  id: number,
  data: ModelTemplateUpdate
): Promise<ModelTemplate> {
  return request.put(`${BASE_URL}/${id}`, data)
}

/**
 * 删除模型模板
 */
export async function deleteModelTemplate(id: number): Promise<void> {
  return request.delete(`${BASE_URL}/${id}`)
}

/**
 * 复制模型模板
 */
export async function duplicateModelTemplate(id: number): Promise<ModelTemplate> {
  return request.post(`${BASE_URL}/${id}/duplicate`)
}

/**
 * 增加模板使用次数
 */
export async function incrementTemplateUsage(id: number): Promise<void> {
  return request.post(`${BASE_URL}/${id}/increment-usage`)
}
