/**
 * 错误边界组件
 * 捕获子组件的 JavaScript 错误，显示友好的错误界面
 */

import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'
import { Result, Button, Typography } from 'antd'

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

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo })
    // 可以在这里上报错误到监控服务
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  handleReload = () => {
    window.location.reload()
  }

  handleGoHome = () => {
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      const isDev = import.meta.env.DEV

      return (
        <div style={{ padding: 24, minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Result
            status="error"
            title="页面出错了"
            subTitle="抱歉，页面发生了一些错误，请尝试刷新页面或返回首页"
            extra={[
              <Button type="primary" key="reload" onClick={this.handleReload}>
                刷新页面
              </Button>,
              <Button key="home" onClick={this.handleGoHome}>
                返回首页
              </Button>,
            ]}
          >
            {isDev && this.state.error && (
              <div style={{ textAlign: 'left', marginTop: 16 }}>
                <Paragraph>
                  <Text strong style={{ color: '#ff4d4f' }}>
                    错误信息：
                  </Text>
                </Paragraph>
                <Paragraph>
                  <Text code>{this.state.error.toString()}</Text>
                </Paragraph>
                {this.state.errorInfo && (
                  <>
                    <Paragraph>
                      <Text strong style={{ color: '#ff4d4f' }}>
                        组件堆栈：
                      </Text>
                    </Paragraph>
                    <pre style={{ 
                      fontSize: 12, 
                      background: '#f5f5f5', 
                      padding: 12, 
                      borderRadius: 4,
                      overflow: 'auto',
                      maxHeight: 200,
                    }}>
                      {this.state.errorInfo.componentStack}
                    </pre>
                  </>
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
