/**
 * 数据集 API
 */

import api from './index'
import type {
  Dataset,
  DatasetPreview,
  DatasetUpdate,
  DeleteResponse,
} from '@/types'

/**
 * 上传数据集
 */
export async function uploadDataset(
  name: string,
  description: string,
  file: File,
  onProgress?: (percent: number) => void
): Promise<Dataset> {
  const formData = new FormData()
  formData.append('name', name)
  formData.append('description', description)
  formData.append('file', file)

  return api.post('/datasets/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
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
 * 获取数据集列表
 */
export async function getDatasets(): Promise<Dataset[]> {
  return api.get('/datasets')
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

