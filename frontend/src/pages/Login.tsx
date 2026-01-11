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
  Space,
  Divider,
  message,
} from 'antd'
import {
  UserOutlined,
  LockOutlined,
  LoginOutlined,
  LineChartOutlined,
} from '@ant-design/icons'
import { useAuth } from '@/contexts/AuthContext'
import type { UserLogin } from '@/types'

const { Title, Text } = Typography

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
        background: '#f0f2f5',
        padding: 24,
      }}
    >
      <Card
        style={{
          width: '100%',
          maxWidth: 420,
          borderRadius: 8,
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
        }}
        styles={{ body: { padding: '40px 32px' } }}
      >
        {/* Logo 和标题 */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Space align="center" size={12}>
            <LineChartOutlined style={{ fontSize: 32, color: '#1890ff' }} />
            <Title level={3} style={{ margin: 0, color: '#333' }}>
              Demo
            </Title>
          </Space>
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

          <Form.Item style={{ marginBottom: 16 }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              icon={<LoginOutlined />}
              block
              style={{
                height: 44,
                borderRadius: 6,
              }}
            >
              登录
            </Button>
          </Form.Item>
        </Form>

        <Divider plain>
          <Text type="secondary" style={{ fontSize: 12 }}>
            还没有账号？
          </Text>
        </Divider>

        <Link to="/register">
          <Button
            block
            style={{
              height: 44,
              borderRadius: 6,
            }}
          >
            注册新账号
          </Button>
        </Link>
      </Card>
    </div>
  )
}

