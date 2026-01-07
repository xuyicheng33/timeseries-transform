/**
 * 页面加载组件
 * 用于路由懒加载时的 loading 状态展示
 */

import { Spin } from 'antd'

interface PageLoadingProps {
  tip?: string
}

export default function PageLoading({ tip = '加载中...' }: PageLoadingProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100%',
        minHeight: 400,
        gap: 16,
      }}
    >
      <Spin size="large" />
      <span style={{ color: '#666' }}>{tip}</span>
    </div>
  )
}

