/**
 * 应用配置
 */

export const APP_CONFIG = {
  // 应用信息
  APP_NAME: '时间序列分析平台',
  APP_NAME_EN: 'Time Series Analysis Platform',
  APP_VERSION: '1.0.0',

  // 上传配置
  UPLOAD: {
    MAX_SIZE: 100 * 1024 * 1024, // 100MB
    ALLOWED_TYPES: ['.csv'],
    TIMEOUT: 300000, // 5分钟
  },

  // 可视化配置
  VISUALIZATION: {
    MAX_RESULTS: 10, // 最多对比10个结果
    MAX_POINTS: 50000, // 最大点数
    MIN_POINTS: 10, // 最小点数
    DEFAULT_POINTS: 2000, // 默认点数
  },

  // 预览配置
  PREVIEW: {
    DEFAULT_ROWS: 100, // 默认预览行数
  },
}

