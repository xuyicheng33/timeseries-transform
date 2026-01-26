/**
 * 路由守卫组件
 * 用于保护需要登录的路由
 */

import { Navigate, useLocation } from 'react-router-dom'
import { Spin } from 'antd'
import { useAuth } from '@/contexts/AuthContext'
import type { ReactNode } from 'react'

interface ProtectedRouteProps {
  children: ReactNode
  requireAdmin?: boolean
}

/**
 * 需要登录的路由守卫
 */
export function ProtectedRoute({ children, requireAdmin = false }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth()
  const location = useLocation()

  // 加载中显示 loading
  if (isLoading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
        }}
      >
        <Spin size="large" tip="加载中..." />
      </div>
    )
  }

  // 未登录，重定向到登录页
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // 需要管理员权限但不是管理员
  if (requireAdmin && !user?.is_admin) {
    return <Navigate to="/datasets" replace />
  }

  return <>{children}</>
}

interface GuestRouteProps {
  children: ReactNode
}

/**
 * 游客路由守卫（已登录用户不能访问）
 */
export function GuestRoute({ children }: GuestRouteProps) {
  const { isAuthenticated, isLoading } = useAuth()

  // 加载中显示 loading
  if (isLoading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
        }}
      >
        <Spin size="large" tip="加载中..." />
      </div>
    )
  }

  // 已登录，重定向到首页
  if (isAuthenticated) {
    return <Navigate to="/datasets" replace />
  }

  return <>{children}</>
}
