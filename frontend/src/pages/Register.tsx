/**
 * 注册页面
 */

import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
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
  MailOutlined,
  IdcardOutlined,
  UserAddOutlined,
  LineChartOutlined,
} from '@ant-design/icons'
import { useAuth } from '@/contexts/AuthContext'
import type { UserRegister } from '@/types'

const { Title, Text } = Typography

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
              注册账号
            </Title>
          </Space>
        </div>

        {/* 注册表单 */}
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          autoComplete="off"
          size="large"
        >
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

          <Form.Item
            name="full_name"
            rules={[{ max: 100, message: '姓名最多 100 个字符' }]}
          >
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

          <Form.Item style={{ marginBottom: 16 }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              icon={<UserAddOutlined />}
              block
              style={{
                height: 44,
                borderRadius: 6,
              }}
            >
              注册
            </Button>
          </Form.Item>
        </Form>

        <Divider plain>
          <Text type="secondary" style={{ fontSize: 12 }}>
            已有账号？
          </Text>
        </Divider>

        <Link to="/login">
          <Button
            block
            style={{
              height: 44,
              borderRadius: 6,
            }}
          >
            返回登录
          </Button>
        </Link>
      </Card>
    </div>
  )
}

