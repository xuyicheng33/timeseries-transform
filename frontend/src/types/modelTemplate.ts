/**
 * 模型模板类型定义
 */

// 模型类别
export type ModelCategory = 'deep_learning' | 'traditional' | 'ensemble' | 'hybrid' | 'other';

// 任务类型
export type TaskType = 'prediction' | 'reconstruction' | 'anomaly_detection' | 'classification' | 'regression';

// 模型模板基础信息
export interface ModelTemplateBase {
  name: string;
  version: string;
  category: ModelCategory;
  description: string;
  hyperparameters: Record<string, unknown>;
  training_config: Record<string, unknown>;
  task_types: TaskType[];
  recommended_features: string;
}

// 创建模型模板请求
export interface ModelTemplateCreate extends ModelTemplateBase {
  is_public?: boolean;
}

// 更新模型模板请求
export interface ModelTemplateUpdate {
  name?: string;
  version?: string;
  category?: ModelCategory;
  description?: string;
  hyperparameters?: Record<string, unknown>;
  training_config?: Record<string, unknown>;
  task_types?: TaskType[];
  recommended_features?: string;
  is_public?: boolean;
}

// 模型模板响应
export interface ModelTemplate extends ModelTemplateBase {
  id: number;
  is_system: boolean;
  is_public: boolean;
  user_id: number | null;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

// 模型模板简要信息（用于下拉选择）
export interface ModelTemplateBrief {
  id: number;
  name: string;
  version: string;
  category: string;
  description: string;
  is_system: boolean;
}

// 模型类别选项
export interface ModelCategoryOption {
  value: ModelCategory;
  label: string;
  count: number;
}

// 模型模板列表查询参数
export interface ModelTemplateListParams {
  page?: number;
  page_size?: number;
  category?: ModelCategory;
  search?: string;
}

// 预置模型模板初始化响应
export interface InitPresetsResponse {
  message: string;
  created: number;
  skipped: number;
}

// 模型类别配置
export const MODEL_CATEGORY_CONFIG: Record<ModelCategory, { label: string; color: string; icon: string }> = {
  deep_learning: { label: '深度学习', color: 'blue', icon: '🧠' },
  traditional: { label: '传统方法', color: 'green', icon: '📊' },
  ensemble: { label: '集成方法', color: 'purple', icon: '🎯' },
  hybrid: { label: '混合方法', color: 'orange', icon: '🔀' },
  other: { label: '其他', color: 'default', icon: '📦' },
};

// 任务类型配置
export const TASK_TYPE_CONFIG: Record<TaskType, { label: string; color: string }> = {
  prediction: { label: '预测', color: 'blue' },
  reconstruction: { label: '重构', color: 'green' },
  anomaly_detection: { label: '异常检测', color: 'red' },
  classification: { label: '分类', color: 'purple' },
  regression: { label: '回归', color: 'orange' },
};

