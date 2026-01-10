/**
 * 实验组管理 API
 */
import request from './request';
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

