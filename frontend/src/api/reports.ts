/**
 * 实验报告 API
 */
import request from './request';
import type {
  ExperimentReportRequest,
  MultiResultReportRequest,
  LatexTableResponse,
  ReportFormat,
} from '@/types/report';

const BASE_URL = '/reports';

/**
 * 生成实验组报告
 * 返回 Blob 用于下载
 */
export async function generateExperimentReport(
  data: ExperimentReportRequest
): Promise<Blob> {
  const response = await request.post(`${BASE_URL}/experiment`, data, {
    responseType: 'blob',
  });
  return response.data;
}

/**
 * 生成多结果对比报告
 * 返回 Blob 用于下载
 */
export async function generateResultsReport(
  data: MultiResultReportRequest
): Promise<Blob> {
  const response = await request.post(`${BASE_URL}/results`, data, {
    responseType: 'blob',
  });
  return response.data;
}

/**
 * 获取 LaTeX 表格代码
 */
export async function getLatexTable(
  experimentId: number
): Promise<LatexTableResponse> {
  return request.get(`${BASE_URL}/latex-table/${experimentId}`);
}

/**
 * 下载报告的辅助函数
 */
export function downloadReport(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

/**
 * 获取报告文件扩展名
 */
export function getReportExtension(format: ReportFormat): string {
  switch (format) {
    case 'markdown':
      return 'md';
    case 'html':
      return 'html';
    case 'latex':
      return 'tex';
    default:
      return 'md';
  }
}

