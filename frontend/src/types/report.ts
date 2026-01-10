/**
 * 实验报告类型定义
 */

// 报告配置
export interface ReportConfig {
  include_summary?: boolean;
  include_metrics_table?: boolean;
  include_best_model?: boolean;
  include_config_details?: boolean;
  include_dataset_info?: boolean;
  include_conclusion?: boolean;
  custom_title?: string;
  custom_author?: string;
}

// 报告格式
export type ReportFormat = 'markdown' | 'html' | 'latex';

// 实验报告请求
export interface ExperimentReportRequest {
  experiment_id: number;
  config?: ReportConfig;
  format?: ReportFormat;
}

// 多结果报告请求
export interface MultiResultReportRequest {
  result_ids: number[];
  title?: string;
  config?: ReportConfig;
  format?: ReportFormat;
}

// LaTeX 表格响应
export interface LatexTableResponse {
  latex: string;
  experiment_name: string;
  result_count: number;
}

// 默认报告配置
export const DEFAULT_REPORT_CONFIG: ReportConfig = {
  include_summary: true,
  include_metrics_table: true,
  include_best_model: true,
  include_config_details: false,
  include_dataset_info: true,
  include_conclusion: true,
};

// 报告格式选项
export const REPORT_FORMAT_OPTIONS = [
  { value: 'markdown', label: 'Markdown (.md)', icon: '📝' },
  { value: 'html', label: 'HTML 网页 (.html)', icon: '🌐' },
  { value: 'latex', label: 'LaTeX 表格 (.tex)', icon: '📄' },
];

