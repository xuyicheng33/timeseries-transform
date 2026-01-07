/**
 * 主布局组件
 */

import { Layout, Menu, Typography } from 'antd'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { ROUTES } from '@/constants'
import './MainLayout.css'

const { Header, Sider, Content } = Layout
const { Title } = Typography

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = ROUTES.map((route) => ({
    key: route.path,
    icon: route.icon,
    label: route.name,
  }))

  return (
    <Layout className="main-layout">
      <Header className="main-header">
        <div className="header-content">
          <Title level={3} className="app-title">
            时间序列分析平台
          </Title>
          <span className="app-subtitle">Time Series Analysis Platform</span>
        </div>
      </Header>
      <Layout>
        <Sider width={220} className="main-sider">
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            className="main-menu"
          />
        </Sider>
        <Content className="main-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

