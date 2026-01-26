/**
 * 批量操作 API
 */
import request from './request'

// ============ 类型定义 ============

export interface BatchDeleteRequest {
  ids: number[]
}

export interface BatchDeleteResult {
  success_count: number
  failed_count: number
  failed_ids: number[]
  errors: string[]
}

export interface BatchExportRequest {
  dataset_ids: number[]
  include_configs?: boolean
  include_results?: boolean
}

export interface ImportPreviewResult {
  metadata: {
    export_time: string
    export_version: string
    datasets_count: number
    configs_count: number
    results_count: number
  } | null
  datasets_count: number
  configurations_count: number
  results_count: number
  datasets: { id: number; name: string }[]
  has_data_files: boolean
  has_result_files: boolean
}

export interface ImportResult {
  success: boolean
  message: string
  imported_datasets: number
  imported_configurations: number
  imported_results: number
  dataset_id_map: Record<number, number>
}

// ============ 批量删除 API ============

/**
 * 批量删除数据集
 */
export async function batchDeleteDatasets(ids: number[]): Promise<BatchDeleteResult> {
  return request.post('/batch/datasets/delete', { ids })
}

/**
 * 批量删除配置
 */
export async function batchDeleteConfigurations(ids: number[]): Promise<BatchDeleteResult> {
  return request.post('/batch/configurations/delete', { ids })
}

/**
 * 批量删除结果
 */
export async function batchDeleteResults(ids: number[]): Promise<BatchDeleteResult> {
  return request.post('/batch/results/delete', { ids })
}

// ============ 导出 API ============

/**
 * 导出数据（返回下载 URL）
 */
export function getExportUrl(params: BatchExportRequest): string {
  const searchParams = new URLSearchParams()
  params.dataset_ids.forEach((id) => searchParams.append('dataset_ids', String(id)))
  if (params.include_configs !== undefined) {
    searchParams.set('include_configs', String(params.include_configs))
  }
  if (params.include_results !== undefined) {
    searchParams.set('include_results', String(params.include_results))
  }
  return `/api/batch/export?${searchParams.toString()}`
}

/**
 * 导出数据（POST 方式，用于大量数据）
 */
export async function exportData(params: BatchExportRequest): Promise<Blob> {
  const response = await request.post('/batch/export', params, {
    responseType: 'blob',
    timeout: 600000, // 10分钟超时
  })
  return response as unknown as Blob
}

// ============ 导入 API ============

/**
 * 预览导入内容
 */
export async function previewImport(file: File): Promise<ImportPreviewResult> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/batch/import/preview', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  })
}

/**
 * 执行导入
 */
export async function importData(file: File): Promise<ImportResult> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/batch/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 600000, // 10分钟超时
  })
}
