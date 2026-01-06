/**
 * 错误处理工具
 */

import type { ApiError, ValidationErrorItem } from '@/types'

/**
 * 解析 FastAPI 错误 detail
 * detail 可能是：
 * - 字符串: "Dataset not found"
 * - 对象: { msg: "...", type: "..." }
 * - 数组（验证错误）: [{ loc: ["body", "name"], msg: "...", type: "..." }, ...]
 */
export function parseErrorDetail(detail: unknown): string {
  if (!detail) return ''

  // 字符串
  if (typeof detail === 'string') {
    return detail
  }

  // 数组（Pydantic 验证错误）
  if (Array.isArray(detail)) {
    return detail
      .map((err: ValidationErrorItem) => {
        const field = err.loc?.slice(1).join('.') || ''
        return field ? `${field}: ${err.msg}` : err.msg
      })
      .join('; ')
  }

  // 对象
  if (typeof detail === 'object') {
    return (detail as any).msg || JSON.stringify(detail)
  }

  return String(detail)
}

/**
 * 获取错误消息
 */
export function getErrorMessage(error: any): string {
  let message = '请求失败'

  if (error.response) {
    // 服务器返回错误
    const apiError = error.response.data as ApiError
    message = parseErrorDetail(apiError?.detail) || `错误 ${error.response.status}`
  } else if (error.request) {
    // 请求已发出但无响应（断网/超时）
    message = error.code === 'ECONNABORTED' ? '请求超时' : '网络连接失败'
  } else {
    // 请求配置错误
    message = error.message || '请求失败'
  }

  return message
}

