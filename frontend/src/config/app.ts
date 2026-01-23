/**
 * 应用配置
 */
export const APP_CONFIG = {
  APP_NAME: 'Time Series Analysis Platform',
  APP_NAME_EN: 'Time Series Analysis Platform',
  APP_VERSION: '1.0.0',
  BRAND: {
    PRIMARY_COLOR: '#4f46e5',
    PRIMARY_HOVER: '#4338ca',
    PRIMARY_LIGHT: '#e0e7ff',
    PRIMARY_BG: '#eef2ff',
  },
  UPLOAD: {
    MAX_SIZE: 500 * 1024 * 1024,
    ALLOWED_TYPES: ['.csv'],
  },
  PREVIEW: {
    DEFAULT_ROWS: 100,
  },
  VISUALIZATION: {
    DEFAULT_POINTS: 2000,
    MIN_POINTS: 10,
    MAX_POINTS: 50000,
    MAX_RESULTS: 10,
  },
}
