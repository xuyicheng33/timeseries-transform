/**
 * 实验报告 API
 */
import { rawRequest } from './request'
import type {
  ExperimentReportRequest,
  MultiResultReportRequest,
  LatexTableResponse,
  ReportFormat,
} from '@/types/report'
import request from './request'

const BASE_URL = '/reports'

/**
 * 生成实验组报告
 * 返回 Blob 用于下载
 * 使用 rawRequest 保留完整响应（包含 Blob 数据）
 */
export async function generateExperimentReport(data: ExperimentReportRequest): Promise<Blob> {
  const response = await rawRequest.post(`${BASE_URL}/experiment`, data, {
    responseType: 'blob',
  })
  // 确保返回的是 Blob 对象
  if (response.data instanceof Blob) {
    return response.data
  }
  // 如果不是 Blob，尝试转换（处理某些浏览器的兼容性问题）
  return new Blob([response.data], {
    type: response.headers['content-type'] || 'application/octet-stream',
  })
}

/**
 * 生成多结果对比报告
 * 返回 Blob 用于下载
 * 使用 rawRequest 保留完整响应（包含 Blob 数据）
 */
export async function generateResultsReport(data: MultiResultReportRequest): Promise<Blob> {
  const response = await rawRequest.post(`${BASE_URL}/results`, data, {
    responseType: 'blob',
  })
  // 确保返回的是 Blob 对象
  if (response.data instanceof Blob) {
    return response.data
  }
  // 如果不是 Blob，尝试转换
  return new Blob([response.data], {
    type: response.headers['content-type'] || 'application/octet-stream',
  })
}

/**
 * 获取 LaTeX 表格代码
 */
export async function getLatexTable(experimentId: number): Promise<LatexTableResponse> {
  return request.get(`${BASE_URL}/latex-table/${experimentId}`)
}

/**
 * 下载报告的辅助函数
 * 增加类型检查，确保 blob 是有效的 Blob 对象
 */
export function downloadReport(blob: Blob, filename: string): void {
  // 确保 blob 是有效的 Blob 对象
  if (!(blob instanceof Blob)) {
    console.error('downloadReport: Invalid blob object', blob)
    throw new Error('无效的文件数据')
  }

  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

/**
 * 获取报告文件扩展名
 */
export function getReportExtension(format: ReportFormat): string {
  switch (format) {
    case 'markdown':
      return 'md'
    case 'html':
      return 'html'
    case 'latex':
      return 'tex'
    default:
      return 'md'
  }
}
