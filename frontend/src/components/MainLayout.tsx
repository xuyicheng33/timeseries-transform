/**
 * 主布局组件
 */

import { Layout, Menu, Typography, Dropdown, Avatar, Space, message } from 'antd'
import type { MenuProps } from 'antd'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import {
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { ROUTES } from '@/constants'
import { useAuth } from '@/contexts/AuthContext'
import './MainLayout.css'

const { Header, Sider, Content } = Layout
const { Title, Text } = Typography

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()

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

  return (
    <Layout className="main-layout">
      <Header className="main-header">
        <div className="header-content">
          <div className="header-left">
            <Title level={3} className="app-title">
              时序分析平台
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
                  style={{ backgroundColor: '#1890ff' }}
                />
                <Text style={{ color: '#fff' }}>
                  {user?.full_name || user?.username || '用户'}
                </Text>
              </Space>
            </Dropdown>
          </div>
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

