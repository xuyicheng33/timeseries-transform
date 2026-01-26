/**
 * 注册页面
 */

import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Form, Input, Button, Card, Typography, message } from 'antd'
import {
  UserOutlined,
  LockOutlined,
  MailOutlined,
  IdcardOutlined,
  LineChartOutlined,
} from '@ant-design/icons'
import { useAuth } from '@/contexts/AuthContext'
import { APP_CONFIG } from '@/config/app'
import type { UserRegister } from '@/types'

const { Title, Text } = Typography
const { BRAND, APP_NAME } = APP_CONFIG

interface RegisterFormValues extends UserRegister {
  confirmPassword: string
}

export default function Register() {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { register } = useAuth()

  const handleSubmit = async (values: RegisterFormValues) => {
    setLoading(true)
    try {
      await register({
        username: values.username,
        email: values.email,
        password: values.password,
        full_name: values.full_name,
      })
      message.success('注册成功，已自动登录')
      navigate('/datasets', { replace: true })
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
        styles={{ body: { padding: '40px 36px' } }}
      >
        {/* Logo 和标题 */}
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 12,
              background: BRAND.PRIMARY_COLOR,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
            }}
          >
            <LineChartOutlined style={{ fontSize: 28, color: '#fff' }} />
          </div>
          <Title level={3} style={{ margin: 0, color: '#1a1a2e', fontWeight: 600 }}>
            创建账号
          </Title>
          <Text type="secondary" style={{ fontSize: 14 }}>
            注册以开始使用 {APP_NAME}
          </Text>
        </div>

        {/* 注册表单 */}
        <Form form={form} layout="vertical" onFinish={handleSubmit} autoComplete="off" size="large">
          <Form.Item
            name="username"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '用户名至少 3 个字符' },
              { max: 50, message: '用户名最多 50 个字符' },
              { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线' },
            ]}
          >
            <Input
              prefix={<UserOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="用户名"
              disabled={loading}
            />
          </Form.Item>

          <Form.Item
            name="email"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input
              prefix={<MailOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="邮箱"
              disabled={loading}
            />
          </Form.Item>

          <Form.Item name="full_name" rules={[{ max: 100, message: '姓名最多 100 个字符' }]}>
            <Input
              prefix={<IdcardOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="姓名（可选）"
              disabled={loading}
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少 6 个字符' },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="密码"
              disabled={loading}
            />
          </Form.Item>

          <Form.Item
            name="confirmPassword"
            dependencies={['password']}
            rules={[
              { required: true, message: '请确认密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve()
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'))
                },
              }),
            ]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="确认密码"
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
              注册
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: 'center', marginTop: 20 }}>
          <Text type="secondary" style={{ fontSize: 13 }}>
            已有账号？
            <Link
              to="/login"
              style={{ marginLeft: 4, fontWeight: 500, color: BRAND.PRIMARY_COLOR }}
            >
              立即登录
            </Link>
          </Text>
        </div>
      </Card>
    </div>
  )
}
