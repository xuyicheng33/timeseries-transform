/**
 * 应用配置
 */

export const APP_CONFIG = {
  // 应用信息
  APP_NAME: 'Demo',
  APP_NAME_EN: 'Demo',
  APP_VERSION: '1.0.0',

  // 品牌主题配置（单色，无渐变）
  BRAND: {
    PRIMARY_COLOR: '#4f46e5', // Indigo-600，主品牌色
    PRIMARY_HOVER: '#4338ca', // Indigo-700，悬停色
    PRIMARY_LIGHT: '#e0e7ff', // Indigo-100，浅色背景
    PRIMARY_BG: '#eef2ff', // Indigo-50，页面背景
  },

  // 上传配置
  UPLOAD: {
    MAX_SIZE: 500 * 1024 * 1024, // 100MB
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

