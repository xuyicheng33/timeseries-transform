/**
 * 登录页面
 */

import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import {
  Form,
  Input,
  Button,
  Card,
  Typography,
  message,
} from 'antd'
import {
  UserOutlined,
  LockOutlined,
  LineChartOutlined,
} from '@ant-design/icons'
import { useAuth } from '@/contexts/AuthContext'
import { APP_CONFIG } from '@/config/app'
import type { UserLogin } from '@/types'

const { Title, Text } = Typography
const { BRAND, APP_NAME } = APP_CONFIG

export default function Login() {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()

  // 获取重定向地址
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/datasets'

  const handleSubmit = async (values: UserLogin) => {
    setLoading(true)
    try {
      await login(values)
      message.success('登录成功')
      navigate(from, { replace: true })
    } catch (error) {
      // 错误已在 API 层处理
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        background: BRAND.PRIMARY_BG,
        padding: 24,
      }}
    >
      <Card
        style={{
          width: '100%',
          maxWidth: 400,
          borderRadius: 12,
          boxShadow: '0 4px 24px rgba(0, 0, 0, 0.08)',
          border: `1px solid ${BRAND.PRIMARY_LIGHT}`,
        }}
        styles={{ body: { padding: '48px 36px' } }}
      >
        {/* Logo 和标题 */}
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div style={{ 
            width: 56, 
            height: 56, 
            borderRadius: 12, 
            background: BRAND.PRIMARY_COLOR,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px'
          }}>
            <LineChartOutlined style={{ fontSize: 28, color: '#fff' }} />
          </div>
          <Title level={3} style={{ margin: 0, color: '#1a1a2e', fontWeight: 600 }}>
            {APP_NAME}
          </Title>
          <Text type="secondary" style={{ fontSize: 14 }}>登录以继续</Text>
        </div>

        {/* 登录表单 */}
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          autoComplete="off"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名或邮箱' }]}
          >
            <Input
              prefix={<UserOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="用户名或邮箱"
              disabled={loading}
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="密码"
              disabled={loading}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 20 }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{
                height: 46,
                borderRadius: 8,
                background: BRAND.PRIMARY_COLOR,
                border: 'none',
                fontWeight: 500,
                fontSize: 15,
              }}
            >
              登录
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: 'center', marginTop: 24 }}>
          <Text type="secondary" style={{ fontSize: 13 }}>
            还没有账号？
            <Link to="/register" style={{ marginLeft: 4, fontWeight: 500, color: BRAND.PRIMARY_COLOR }}>
              立即注册
            </Link>
          </Text>
        </div>
      </Card>
    </div>
  )
}

