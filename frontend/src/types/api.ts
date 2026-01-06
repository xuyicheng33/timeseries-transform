/**
 * API 通用类型定义
 */

// 验证错误项
export interface ValidationErrorItem {
  loc: (string | number)[]
  msg: string
  type: string
}

// API 错误响应
export interface ApiError {
  detail: string | object | ValidationErrorItem[]
}

// 删除响应
export interface DeleteResponse {
  message: string
}

// 分页参数
export interface PaginationParams {
  page?: number
  page_size?: number
}

// 分页响应
export interface PaginationResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

