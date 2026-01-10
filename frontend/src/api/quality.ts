/**
 * 数据质量 API
 */
import request from './request'
import type {
  DataQualityReport,
  QualityCheckRequest,
  CleaningConfig,
  CleaningPreviewResponse,
  CleaningResult,
  OutlierDetailsResponse,
  OutlierMethod,
} from '@/types'

/**
 * 获取数据集质量报告（使用默认参数）
 */
export async function getQualityReport(
  datasetId: number,
  outlierMethod: OutlierMethod = 'iqr'
): Promise<DataQualityReport> {
  return request.get(`/api/quality/${datasetId}/report`, {
    params: { outlier_method: outlierMethod }
  })
}

/**
 * 生成数据集质量报告（带自定义参数）
 */
export async function generateQualityReport(
  datasetId: number,
  config: QualityCheckRequest
): Promise<DataQualityReport> {
  return request.post(`/api/quality/${datasetId}/report`, config)
}

/**
 * 预览数据清洗效果
 */
export async function previewCleaning(
  datasetId: number,
  config: CleaningConfig
): Promise<CleaningPreviewResponse> {
  return request.post(`/api/quality/${datasetId}/clean/preview`, config)
}

/**
 * 执行数据清洗
 */
export async function applyCleaning(
  datasetId: number,
  config: CleaningConfig
): Promise<CleaningResult> {
  return request.post(`/api/quality/${datasetId}/clean/apply`, config)
}

/**
 * 获取指定列的异常值详情
 */
export async function getOutlierDetails(
  datasetId: number,
  column: string,
  options?: {
    method?: OutlierMethod
    multiplier?: number
    threshold?: number
    lower_pct?: number
    upper_pct?: number
  }
): Promise<OutlierDetailsResponse> {
  return request.get(`/api/quality/${datasetId}/outliers`, {
    params: {
      column,
      method: options?.method || 'iqr',
      multiplier: options?.multiplier || 1.5,
      threshold: options?.threshold || 3.0,
      lower_pct: options?.lower_pct || 1,
      upper_pct: options?.upper_pct || 99,
    }
  })
}

