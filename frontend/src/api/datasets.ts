/**
 * 数据集 API
 */

import api from './index'
import type {
  Dataset,
  DatasetPreview,
  DatasetUpdate,
  DeleteResponse,
  PaginatedResponse,
} from '@/types'

/**
 * 上传数据集
 */
export async function uploadDataset(
  name: string,
  description: string,
  file: File,
  isPublic: boolean = false,
  onProgress?: (percent: number) => void
): Promise<Dataset> {
  const formData = new FormData()
  formData.append('name', name)
  formData.append('description', description)
  formData.append('file', file)
  formData.append('is_public', String(isPublic))

  return api.post('/datasets/upload', formData, {
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
 * 获取数据集列表（分页）
 */
export async function getDatasets(
  page: number = 1,
  pageSize: number = 20
): Promise<PaginatedResponse<Dataset>> {
  return api.get('/datasets', {
    params: { page, page_size: pageSize },
  })
}

/**
 * 获取所有数据集（不分页，用于下拉选择等场景）
 */
export async function getAllDatasets(): Promise<Dataset[]> {
  return api.get('/datasets/all')
}

/**
 * 获取数据集详情
 */
export async function getDataset(id: number): Promise<Dataset> {
  return api.get(`/datasets/${id}`)
}

/**
 * 预览数据集
 */
export async function previewDataset(
  id: number,
  rows: number = 100
): Promise<DatasetPreview> {
  return api.get(`/datasets/${id}/preview`, {
    params: { rows },
  })
}

/**
 * 获取数据集下载路径
 */
export function getDatasetDownloadPath(id: number): string {
  return `/datasets/${id}/download`
}

/**
 * 更新数据集
 */
export async function updateDataset(
  id: number,
  data: DatasetUpdate
): Promise<Dataset> {
  return api.put(`/datasets/${id}`, data)
}

/**
 * 删除数据集
 */
export async function deleteDataset(id: number): Promise<DeleteResponse> {
  return api.delete(`/datasets/${id}`)
}

/**
 * 批量更新数据集排序（仅管理员）
 */
export interface DatasetSortOrderItem {
  id: number
  sort_order: number
}

export interface DatasetSortOrderUpdate {
  orders: DatasetSortOrderItem[]
}

export async function updateDatasetSortOrder(
  data: DatasetSortOrderUpdate
): Promise<{ message: string }> {
  return api.put('/datasets/sort-order/batch', data)
}

