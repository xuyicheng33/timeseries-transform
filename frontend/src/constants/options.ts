/**
 * 常量定义
 */

// 归一化选项
export const NORMALIZATION_OPTIONS = [
  { label: '无归一化', value: 'none', description: '保持原始数据不变' },
  { label: 'MinMax', value: 'minmax', description: '缩放到 [0, 1] 区间' },
  { label: 'Z-Score', value: 'zscore', description: '标准化为均值0、标准差1' },
  { label: 'Head', value: 'head', description: '使用头部数据归一化' },
  { label: 'Decimal', value: 'decimal', description: '小数定标归一化' },
  // 新增归一化方法
  { label: 'Robust', value: 'robust', description: '使用中位数和IQR，对异常值鲁棒' },
  { label: 'MaxAbs', value: 'maxabs', description: '除以最大绝对值，保留稀疏性' },
  { label: 'Log', value: 'log', description: '对数变换，适合长尾分布' },
  { label: 'Log1p', value: 'log1p', description: 'log(1+x)，处理含零值数据' },
  { label: 'Sqrt', value: 'sqrt', description: '平方根变换，温和压缩' },
  { label: 'Box-Cox', value: 'boxcox', description: '自动选择最佳幂次变换' },
  { label: 'Yeo-Johnson', value: 'yeojohnson', description: '支持负值的Box-Cox变换' },
  { label: 'Quantile', value: 'quantile', description: '映射到均匀/正态分布' },
  { label: 'Rank', value: 'rank', description: '转换为排名百分比' },
]

// 归一化方法分组（用于更好的UI展示）
export const NORMALIZATION_GROUPS = [
  {
    label: '基础方法',
    options: [
      { label: '无归一化', value: 'none' },
      { label: 'MinMax [0,1]', value: 'minmax' },
      { label: 'Z-Score 标准化', value: 'zscore' },
    ],
  },
  {
    label: '鲁棒方法',
    options: [
      { label: 'Robust (中位数/IQR)', value: 'robust' },
      { label: 'MaxAbs (最大绝对值)', value: 'maxabs' },
    ],
  },
  {
    label: '变换方法',
    options: [
      { label: 'Log 对数', value: 'log' },
      { label: 'Log1p log(1+x)', value: 'log1p' },
      { label: 'Sqrt 平方根', value: 'sqrt' },
      { label: 'Box-Cox', value: 'boxcox' },
      { label: 'Yeo-Johnson', value: 'yeojohnson' },
    ],
  },
  {
    label: '分布变换',
    options: [
      { label: 'Quantile 分位数', value: 'quantile' },
      { label: 'Rank 排名', value: 'rank' },
    ],
  },
  {
    label: '其他',
    options: [
      { label: 'Head', value: 'head' },
      { label: 'Decimal', value: 'decimal' },
    ],
  },
]

// 目标类型选项
export const TARGET_TYPE_OPTIONS = [
  { label: '下一步预测', value: 'next' },
  { label: 'K步预测', value: 'kstep' },
  { label: '重构', value: 'reconstruct' },
]

// 异常类型选项
export const ANOMALY_TYPE_OPTIONS = [
  { label: '软替换', value: 'point' },
  { label: '均匀替换', value: 'segment' },
  { label: '峰值噪声', value: 'noise' },
  { label: '长度调整', value: 'trend' },
]

// 注入算法选项
export const INJECTION_ALGORITHM_OPTIONS = [
  { label: '按窗口', value: 'random' },
  { label: '按序列', value: 'rule' },
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

// 降采样算法详细说明
export const DOWNSAMPLE_ALGORITHM_DESCRIPTIONS: Record<
  string,
  { name: string; description: string; pros: string; cons: string; useCase: string }
> = {
  lttb: {
    name: 'LTTB (Largest Triangle Three Buckets)',
    description:
      '基于三角形面积的降采样算法，通过选择能形成最大三角形面积的点来保留数据的视觉特征。',
    pros: '保留数据的整体形状和趋势，视觉效果最佳',
    cons: '计算复杂度略高',
    useCase: '适合大多数时序数据可视化场景，特别是需要保持曲线形状的情况',
  },
  minmax: {
    name: 'MinMax (最大最小值)',
    description: '在每个采样区间内保留最大值和最小值点，确保极值不丢失。',
    pros: '保留极值点，不会丢失峰值和谷值',
    cons: '可能产生锯齿状的视觉效果',
    useCase: '适合需要关注极端值的场景，如异常检测、峰值分析',
  },
  average: {
    name: 'Average (平均值)',
    description: '在每个采样区间内计算平均值作为代表点。',
    pros: '计算简单快速，平滑噪声',
    cons: '可能丢失极值和细节特征',
    useCase: '适合数据噪声较大、关注整体趋势的场景',
  },
}

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
