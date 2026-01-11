/**
 * 实验组管理 API
 */
import request, { rawRequest } from './request';
import type { PaginatedResponse } from '@/types/api';
import type {
  Experiment,
  ExperimentDetail,
  ExperimentCreateRequest,
  ExperimentUpdateRequest,
  ExperimentResultsRequest,
  ExperimentSummary,
  ExperimentListParams,
} from '@/types/experiment';

const BASE_URL = '/experiments';

/**
 * 获取实验组列表
 */
export async function getExperiments(
  params: ExperimentListParams = {}
): Promise<PaginatedResponse<Experiment>> {
  return request.get(BASE_URL, { params });
}

/**
 * 创建实验组
 */
export async function createExperiment(
  data: ExperimentCreateRequest
): Promise<ExperimentDetail> {
  return request.post(BASE_URL, data);
}

/**
 * 获取实验组详情
 */
export async function getExperiment(id: number): Promise<ExperimentDetail> {
  return request.get(`${BASE_URL}/${id}`);
}

/**
 * 更新实验组
 */
export async function updateExperiment(
  id: number,
  data: ExperimentUpdateRequest
): Promise<Experiment> {
  return request.put(`${BASE_URL}/${id}`, data);
}

/**
 * 删除实验组
 */
export async function deleteExperiment(id: number): Promise<void> {
  return request.delete(`${BASE_URL}/${id}`);
}

/**
 * 添加结果到实验组
 */
export async function addResultsToExperiment(
  experimentId: number,
  data: ExperimentResultsRequest
): Promise<ExperimentDetail> {
  return request.post(`${BASE_URL}/${experimentId}/results`, data);
}

/**
 * 从实验组移除结果
 */
export async function removeResultsFromExperiment(
  experimentId: number,
  data: ExperimentResultsRequest
): Promise<void> {
  return request.delete(`${BASE_URL}/${experimentId}/results`, { data });
}

/**
 * 获取实验组汇总统计
 */
export async function getExperimentSummary(
  experimentId: number
): Promise<ExperimentSummary> {
  return request.get(`${BASE_URL}/${experimentId}/summary`);
}

/**
 * 获取所有标签列表
 */
export async function getAllTags(): Promise<{ tags: string[] }> {
  return request.get(`${BASE_URL}/tags/list`);
}

/**
 * 导出实验组
 * 返回 Blob 用于下载
 */
export async function exportExperiment(
  experimentId: number,
  includeDataFiles: boolean = true
): Promise<Blob> {
  // 使用 rawRequest 保留完整响应（包含 headers），避免被拦截器解包
  const response = await rawRequest.get(`${BASE_URL}/${experimentId}/export`, {
    params: { include_data_files: includeDataFiles },
    responseType: 'blob',
  });
  
  // 校验返回的是否为 Blob
  if (!(response.data instanceof Blob)) {
    throw new Error('导出失败：返回数据格式错误');
  }
  
  return response.data;
}

/**
 * 下载实验组导出文件的辅助函数
 */
export function downloadExperimentExport(blob: Blob, experimentName: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  const safeName = experimentName.replace(/[^a-zA-Z0-9\u4e00-\u9fa5_-]/g, '_');
  const timestamp = new Date().toISOString().slice(0, 10);
  link.download = `experiment_${safeName}_${timestamp}.zip`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

