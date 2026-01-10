/**
 * 配置对比分析类型定义
 */

// 参数值及其对应的指标
export interface ParameterValue {
  value: string | number | boolean
  result_ids: number[]
  result_names: string[]
  metrics: Record<string, number>
  metrics_std: Record<string, number>
  count: number
}

// 单个参数的分析结果
export interface ParameterAnalysis {
  parameter_name: string
  parameter_label: string
  values: ParameterValue[]
  is_numeric: boolean
  sensitivity_score: number
}

// 结果详情
export interface ResultDetail {
  result_id: number
  result_name: string
  model_name: string
  config_id: number | null
  config_name: string | null
  metrics: Record<string, number>
  parameters: Record<string, string | number | boolean>
}

// 配置对比响应
export interface ConfigCompareResponse {
  total_results: number
  parameters: ParameterAnalysis[]
  result_details: ResultDetail[]
  warnings: string[]
}

// 控制变量对比变体
export interface ControlledVariation {
  parameter_value: string | number | boolean
  result_count: number
  result_ids: number[]
  result_names: string[]
  metrics: Record<string, number>
  metrics_std: Record<string, number>
}

// 图表数据
export interface ChartAxisData {
  name: string
  data: (string | number)[]
  is_numeric: boolean
}

export interface ChartSeriesData {
  name: string
  key: string
  data: (number | null)[]
}

export interface ControlledChartData {
  x_axis: ChartAxisData
  series: ChartSeriesData[]
}

// 控制变量对比响应
export interface ControlledCompareResponse {
  parameter_name: string
  parameter_label: string
  baseline_config: Record<string, string | number | boolean>
  config_consistent: boolean  // 其他参数是否完全一致
  inconsistent_params: string[]  // 不一致的参数列表
  variations: ControlledVariation[]
  chart_data: ControlledChartData
}

// 敏感性分析值-指标对
export interface ValueMetricPair {
  value: string | number | boolean
  metric: number
}

// 敏感性分析项
export interface SensitivityItem {
  parameter: string
  parameter_label: string
  sensitivity_score: number
  value_count: number
  best_value: string | number | boolean
  best_metric: number
  is_numeric: boolean
  value_metrics: ValueMetricPair[]
}

// 敏感性分析响应
export interface SensitivityResponse {
  target_metric: string
  sensitivities: SensitivityItem[]
  recommendations: string[]
}

// 可分析参数
export interface AnalyzableParameter {
  name: string
  label: string
}

// 可分析指标
export interface AnalyzableMetric {
  name: string
  label: string
}

// 参数列表响应
export interface ParametersResponse {
  parameters: AnalyzableParameter[]
  metrics: AnalyzableMetric[]
}

