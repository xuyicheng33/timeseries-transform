/**
 * 主布局组件
 */

import { useState } from 'react'
import { Layout, Menu, Typography, Dropdown, Avatar, Space, message } from 'antd'
import type { MenuProps } from 'antd'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { ROUTES } from '@/constants'
import { useAuth } from '@/contexts/AuthContext'
import { APP_CONFIG } from '@/config/app'
import './MainLayout.css'

const { Header, Sider, Content } = Layout
const { Title, Text } = Typography
const { APP_NAME } = APP_CONFIG

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()
  const [siderCollapsed, setSiderCollapsed] = useState(
    () => localStorage.getItem('layout:siderCollapsed') === '1'
  )

  const menuItems = ROUTES.map((route) => ({
    key: route.path,
    icon: route.icon,
    label: route.name,
  }))

  // 用户下拉菜单
  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人信息',
      disabled: true, // 暂未实现
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '账号设置',
      disabled: true, // 暂未实现
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
    },
  ]

  const handleUserMenuClick: MenuProps['onClick'] = ({ key }) => {
    if (key === 'logout') {
      logout()
      message.success('已退出登录')
      navigate('/login')
    }
  }

  const toggleSider = () => {
    setSiderCollapsed((prev) => {
      const next = !prev
      localStorage.setItem('layout:siderCollapsed', next ? '1' : '0')
      return next
    })
  }

  return (
    <Layout className="main-layout">
      <Header className="main-header">
        <div className="header-content">
          <div className="header-left">
            <button
              type="button"
              className="sider-trigger"
              aria-label={siderCollapsed ? '展开侧边栏' : '收起侧边栏'}
              onClick={toggleSider}
            >
              {siderCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            </button>
            <Title level={3} className="app-title">
              {APP_NAME}
            </Title>
          </div>
          <div className="header-right">
            <Dropdown
              menu={{ items: userMenuItems, onClick: handleUserMenuClick }}
              placement="bottomRight"
              trigger={['click']}
            >
              <Space className="user-dropdown" style={{ cursor: 'pointer' }}>
                <Avatar
                  size="small"
                  icon={<UserOutlined />}
                  style={{ backgroundColor: '#fff', color: 'var(--brand-primary)' }}
                />
                <Text style={{ color: '#fff' }}>{user?.full_name || user?.username || '用户'}</Text>
              </Space>
            </Dropdown>
          </div>
        </div>
      </Header>
      <Layout>
        <Sider
          width={220}
          collapsedWidth={56}
          collapsible
          trigger={null}
          collapsed={siderCollapsed}
          className="main-sider"
        >
          <Menu
            mode="inline"
            inlineCollapsed={siderCollapsed}
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
