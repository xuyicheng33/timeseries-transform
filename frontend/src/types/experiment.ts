/**
 * 实验组相关类型定义
 */

// 实验组状态
export type ExperimentStatus = 'draft' | 'running' | 'completed' | 'archived';

// 实验组基础信息
export interface Experiment {
  id: number;
  name: string;
  description: string;
  objective: string;
  status: ExperimentStatus;
  tags: string[];
  conclusion: string;
  user_id: number | null;
  dataset_id: number | null;
  dataset_name: string | null;
  result_count: number;
  created_at: string;
  updated_at: string;
}

// 实验组中的结果简要信息
export interface ExperimentResultBrief {
  id: number;
  name: string;
  model_name: string;
  model_version: string;
  metrics: Record<string, number>;
  created_at: string;
}

// 实验组详情（包含关联结果）
export interface ExperimentDetail extends Experiment {
  results: ExperimentResultBrief[];
}

// 创建实验组请求
export interface ExperimentCreateRequest {
  name: string;
  description?: string;
  objective?: string;
  tags?: string[];
  dataset_id?: number | null;
  result_ids?: number[];
}

// 更新实验组请求
export interface ExperimentUpdateRequest {
  name?: string;
  description?: string;
  objective?: string;
  status?: ExperimentStatus;
  tags?: string[];
  conclusion?: string;
  dataset_id?: number | null;
}

// 添加/移除结果请求
export interface ExperimentResultsRequest {
  result_ids: number[];
}

// 最佳指标信息
export interface BestMetricInfo {
  result_id: number;
  value: number;
  model_name: string;
}

// 实验组汇总统计
export interface ExperimentSummary {
  experiment_id: number;
  experiment_name: string;
  result_count: number;
  model_names: string[];
  best_mse: BestMetricInfo | null;
  best_rmse: BestMetricInfo | null;
  best_mae: BestMetricInfo | null;
  best_r2: BestMetricInfo | null;
  best_mape: BestMetricInfo | null;
  avg_metrics: {
    mse: number;
    rmse: number;
    mae: number;
    r2: number;
    mape: number;
  } | null;
}

// 实验组列表查询参数
export interface ExperimentListParams {
  page?: number;
  page_size?: number;
  status?: ExperimentStatus;
  tag?: string;
  dataset_id?: number;
  search?: string;
}

