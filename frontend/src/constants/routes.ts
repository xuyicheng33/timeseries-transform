/**
 * 路由配置
 */

import {
  DatabaseOutlined,
  SettingOutlined,
  FolderOutlined,
  LineChartOutlined,
} from '@ant-design/icons'

export interface RouteConfig {
  path: string
  name: string
  icon: React.ComponentType
}

export const ROUTES: RouteConfig[] = [
  {
    path: '/datasets',
    name: '数据中心',
    icon: DatabaseOutlined,
  },
  {
    path: '/configurations',
    name: '配置向导',
    icon: SettingOutlined,
  },
  {
    path: '/results',
    name: '结果仓库',
    icon: FolderOutlined,
  },
  {
    path: '/visualization',
    name: '可视化对比',
    icon: LineChartOutlined,
  },
]

