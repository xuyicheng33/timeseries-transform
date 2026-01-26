/**
 * 高级可视化 API
 */
import request from './request'
import type {
  FeatureImportanceRequest,
  FeatureImportanceResponse,
  ConfidenceIntervalRequest,
  ConfidenceIntervalResponse,
  ErrorHeatmapRequest,
  ErrorHeatmapResponse,
  PredictionDecompositionRequest,
  PredictionDecompositionResponse,
} from '@/types/advancedViz'

const BASE_URL = '/advanced-viz'

/**
 * 特征重要性分析
 */
export async function analyzeFeatureImportance(
  data: FeatureImportanceRequest
): Promise<FeatureImportanceResponse> {
  return request.post(`${BASE_URL}/feature-importance`, data)
}

/**
 * 计算预测置信区间
 */
export async function calculateConfidenceInterval(
  data: ConfidenceIntervalRequest
): Promise<ConfidenceIntervalResponse> {
  return request.post(`${BASE_URL}/confidence-interval`, data)
}

/**
 * 生成误差热力图数据
 */
export async function generateErrorHeatmap(
  data: ErrorHeatmapRequest
): Promise<ErrorHeatmapResponse> {
  return request.post(`${BASE_URL}/error-heatmap`, data)
}

/**
 * 预测分解
 */
export async function decomposePrediction(
  data: PredictionDecompositionRequest
): Promise<PredictionDecompositionResponse> {
  return request.post(`${BASE_URL}/prediction-decomposition`, data)
}
