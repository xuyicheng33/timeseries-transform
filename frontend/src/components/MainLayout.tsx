/**
 * 主布局组件
 * 支持响应式侧边栏折叠
 */

import { useState, useEffect } from 'react'
import { Layout, Menu, Typography, Button, Drawer } from 'antd'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { MenuOutlined, MenuFoldOutlined, MenuUnfoldOutlined } from '@ant-design/icons'
import { ROUTES } from '@/constants'
import './MainLayout.css'

const { Header, Sider, Content } = Layout
const { Title } = Typography

// 响应式断点
const MOBILE_BREAKPOINT = 768

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  
  // 侧边栏状态
  const [collapsed, setCollapsed] = useState(false)
  const [isMobile, setIsMobile] = useState(window.innerWidth < MOBILE_BREAKPOINT)
  const [drawerOpen, setDrawerOpen] = useState(false)

  // 监听窗口大小变化
  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < MOBILE_BREAKPOINT
      setIsMobile(mobile)
      if (!mobile) {
        setDrawerOpen(false)
      }
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const menuItems = ROUTES.map((route) => ({
    key: route.path,
    icon: route.icon,
    label: route.name,
  }))

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
    if (isMobile) {
      setDrawerOpen(false)
    }
  }

  const menuContent = (
    <Menu
      mode="inline"
      selectedKeys={[location.pathname]}
      items={menuItems}
      onClick={handleMenuClick}
      className="main-menu"
    />
  )

  return (
    <Layout className="main-layout">
      <Header className="main-header">
        <div className="header-content">
          {isMobile && (
            <Button
              type="text"
              icon={<MenuOutlined />}
              onClick={() => setDrawerOpen(true)}
              className="mobile-menu-btn"
            />
          )}
          <Title level={3} className="app-title">
            {isMobile ? 'TSAP' : '时间序列分析平台'}
          </Title>
          {!isMobile && <span className="app-subtitle">Time Series Analysis Platform</span>}
        </div>
      </Header>
      <Layout>
        {/* 桌面端侧边栏 */}
        {!isMobile && (
          <Sider 
            width={220} 
            collapsedWidth={80}
            collapsed={collapsed}
            className="main-sider"
          >
            {menuContent}
            <div className="sider-collapse-btn">
              <Button
                type="text"
                icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                onClick={() => setCollapsed(!collapsed)}
                style={{ width: '100%' }}
              />
            </div>
          </Sider>
        )}
        
        {/* 移动端抽屉菜单 */}
        {isMobile && (
          <Drawer
            title="导航菜单"
            placement="left"
            onClose={() => setDrawerOpen(false)}
            open={drawerOpen}
            width={250}
            styles={{ body: { padding: 0 } }}
          >
            {menuContent}
          </Drawer>
        )}
        
        <Content className="main-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
