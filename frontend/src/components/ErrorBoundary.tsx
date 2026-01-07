/**
 * 错误边界组件
 * 捕获子组件的 JavaScript 错误，防止整个应用崩溃
 */

import { Component, ErrorInfo, ReactNode } from 'react'
import { Result, Button, Typography, Space } from 'antd'
import { ReloadOutlined, HomeOutlined, BugOutlined } from '@ant-design/icons'

const { Paragraph, Text } = Typography

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // 更新 state 使下一次渲染能够显示降级后的 UI
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // 记录错误信息
    this.setState({ errorInfo })
    
    // 可以在这里上报错误到日志服务
    console.error('ErrorBoundary caught an error:', error)
    console.error('Error info:', errorInfo)
    
    // TODO: 未来可以集成错误上报服务
    // reportErrorToService(error, errorInfo)
  }

  handleReload = (): void => {
    window.location.reload()
  }

  handleGoHome = (): void => {
    window.location.href = '/'
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })
  }

  render(): ReactNode {
    if (this.state.hasError) {
      // 如果提供了自定义 fallback，使用它
      if (this.props.fallback) {
        return this.props.fallback
      }

      // 默认错误 UI
      const isDev = import.meta.env.DEV

      return (
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            minHeight: '100vh',
            padding: 24,
            background: '#f5f5f5',
          }}
        >
          <Result
            status="error"
            title="页面出错了"
            subTitle="抱歉，页面遇到了一些问题。请尝试刷新页面或返回首页。"
            extra={
              <Space>
                <Button type="primary" icon={<ReloadOutlined />} onClick={this.handleReload}>
                  刷新页面
                </Button>
                <Button icon={<HomeOutlined />} onClick={this.handleGoHome}>
                  返回首页
                </Button>
                <Button onClick={this.handleReset}>
                  重试
                </Button>
              </Space>
            }
          >
            {isDev && this.state.error && (
              <div
                style={{
                  textAlign: 'left',
                  background: '#fff1f0',
                  border: '1px solid #ffa39e',
                  borderRadius: 8,
                  padding: 16,
                  marginTop: 16,
                  maxWidth: 800,
                  overflow: 'auto',
                }}
              >
                <Paragraph>
                  <Space>
                    <BugOutlined style={{ color: '#ff4d4f' }} />
                    <Text strong style={{ color: '#ff4d4f' }}>
                      开发模式 - 错误详情
                    </Text>
                  </Space>
                </Paragraph>
                <Paragraph>
                  <Text strong>错误信息：</Text>
                  <br />
                  <Text code style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                    {this.state.error.message}
                  </Text>
                </Paragraph>
                {this.state.error.stack && (
                  <Paragraph>
                    <Text strong>堆栈跟踪：</Text>
                    <br />
                    <Text
                      code
                      style={{
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-all',
                        fontSize: 12,
                        display: 'block',
                        maxHeight: 200,
                        overflow: 'auto',
                      }}
                    >
                      {this.state.error.stack}
                    </Text>
                  </Paragraph>
                )}
                {this.state.errorInfo?.componentStack && (
                  <Paragraph>
                    <Text strong>组件堆栈：</Text>
                    <br />
                    <Text
                      code
                      style={{
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-all',
                        fontSize: 12,
                        display: 'block',
                        maxHeight: 200,
                        overflow: 'auto',
                      }}
                    >
                      {this.state.errorInfo.componentStack}
                    </Text>
                  </Paragraph>
                )}
              </div>
            )}
          </Result>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary

