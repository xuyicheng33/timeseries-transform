/**
 * 路由配置
 */

import type { ReactNode, LazyExoticComponent, ComponentType } from 'react'
import {
  DatabaseOutlined,
  SettingOutlined,
  FolderOutlined,
  LineChartOutlined,
  ExperimentOutlined,
  RocketOutlined,
} from '@ant-design/icons'

// 懒加载页面组件
import { lazy } from 'react'

const DataHub = lazy(() => import('@/pages/DataHub'))
const ConfigWizard = lazy(() => import('@/pages/ConfigWizard'))
const ResultRepo = lazy(() => import('@/pages/ResultRepo'))
const Visualization = lazy(() => import('@/pages/Visualization'))
const ExperimentManager = lazy(() => import('@/pages/ExperimentManager'))
const ModelTemplateManager = lazy(() => import('@/pages/ModelTemplateManager'))

export interface RouteConfig {
  path: string
  name: string
  icon: ReactNode
  element: LazyExoticComponent<ComponentType>
}

export const ROUTES: RouteConfig[] = [
  {
    path: '/datasets',
    name: '数据中心',
    icon: <DatabaseOutlined />,
    element: DataHub,
  },
  {
    path: '/configurations',
    name: '配置向导',
    icon: <SettingOutlined />,
    element: ConfigWizard,
  },
  {
    path: '/model-templates',
    name: '模型模板',
    icon: <RocketOutlined />,
    element: ModelTemplateManager,
  },
  {
    path: '/results',
    name: '结果仓库',
    icon: <FolderOutlined />,
    element: ResultRepo,
  },
  {
    path: '/visualization',
    name: '可视化对比',
    icon: <LineChartOutlined />,
    element: Visualization,
  },
  {
    path: '/experiments',
    name: '实验管理',
    icon: <ExperimentOutlined />,
    element: ExperimentManager,
  },
]
