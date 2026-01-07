/**
 * 常量定义
 */

// 归一化选项
export const NORMALIZATION_OPTIONS = [
  { label: '无归一化', value: 'none' },
  { label: 'MinMax', value: 'minmax' },
  { label: 'Z-Score', value: 'zscore' },
  { label: 'Head', value: 'head' },
  { label: 'Decimal', value: 'decimal' },
]

// 目标类型选项
export const TARGET_TYPE_OPTIONS = [
  { label: '下一步预测', value: 'next' },
  { label: 'K步预测', value: 'kstep' },
  { label: '重构', value: 'reconstruct' },
]

// 异常类型选项
export const ANOMALY_TYPE_OPTIONS = [
  { label: '点异常', value: 'point' },
  { label: '段异常', value: 'segment' },
  { label: '趋势异常', value: 'trend' },
  { label: '季节异常', value: 'seasonal' },
  { label: '噪声异常', value: 'noise' },
]

// 注入算法选项
export const INJECTION_ALGORITHM_OPTIONS = [
  { label: '随机', value: 'random' },
  { label: '规则', value: 'rule' },
  { label: '模式', value: 'pattern' },
]

// 序列逻辑选项
export const SEQUENCE_LOGIC_OPTIONS = [
  { label: '异常优先', value: 'anomaly_first' },
  { label: '窗口优先', value: 'window_first' },
]

// 降采样算法选项
export const DOWNSAMPLE_ALGORITHM_OPTIONS = [
  { label: 'LTTB（推荐）', value: 'lttb' },
  { label: 'MinMax', value: 'minmax' },
  { label: 'Average', value: 'average' },
]

// 指标名称映射
export const METRIC_NAMES = {
  mse: 'MSE',
  rmse: 'RMSE',
  mae: 'MAE',
  r2: 'R²',
  mape: 'MAPE',
}

// 指标描述
export const METRIC_DESCRIPTIONS = {
  mse: '均方误差',
  rmse: '均方根误差',
  mae: '平均绝对误差',
  r2: '决定系数',
  mape: '平均绝对百分比误差',
}

