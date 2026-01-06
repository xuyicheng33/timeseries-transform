/**
 * 数据集相关类型定义
 */

// 数据集基础信息
export interface Dataset {
  id: number
  name: string
  filename: string
  file_size: number
  row_count: number
  column_count: number
  columns: string[]
  description: string
  created_at: string
  updated_at: string
}

// 数据集预览
export interface DatasetPreview {
  columns: string[]
  data: Record<string, unknown>[]
  total_rows: number
}

// 创建数据集
export interface DatasetCreate {
  name: string
  description?: string
  file: File
}

// 更新数据集
export interface DatasetUpdate {
  name?: string
  description?: string
}

