/**
 * 格式化工具函数
 */

import type { Metrics } from '@/types'

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(2)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
}

/**
 * 格式化日期时间
 */
export function formatDateTime(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

/**
 * 格式化日期
 */
export function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

/**
 * 格式化数字（千分位）
 */
export function formatNumber(num: number): string {
  return num.toLocaleString('zh-CN')
}

/**
 * 安全获取指标值
 */
export function getMetricValue(
  metrics: Partial<Metrics> | Record<string, never>,
  key: keyof Metrics
): number | null {
  if (!metrics || Object.keys(metrics).length === 0) return null
  const value = (metrics as Partial<Metrics>)[key]
  return typeof value === 'number' && !isNaN(value) ? value : null
}

/**
 * 格式化指标值
 */
export function formatMetric(value: number | null, type: keyof Metrics): string {
  if (value === null) return '-'

  switch (type) {
    case 'mape':
      return `${value.toFixed(2)}%`
    case 'r2':
      return value.toFixed(4)
    case 'mse':
    case 'rmse':
    case 'mae':
      // 使用科学计数法或固定小数位
      return value < 0.01 ? value.toExponential(4) : value.toFixed(4)
    default:
      return value.toFixed(4)
  }
}

/**
 * 检查 Metrics 是否有效
 */
export function hasMetrics(metrics: Partial<Metrics> | Record<string, never>): boolean {
  return metrics && Object.keys(metrics).length > 0
}
