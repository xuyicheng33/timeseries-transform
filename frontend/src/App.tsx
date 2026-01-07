import { Suspense, lazy } from 'react'
import { ConfigProvider, Spin } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from '@/components/MainLayout'
import ErrorBoundary from '@/components/ErrorBoundary'
import { ProtectedRoute, GuestRoute } from '@/components/RouteGuard'
import { AuthProvider } from '@/contexts/AuthContext'
import { ROUTES } from '@/constants'

// 懒加载登录/注册页面
const Login = lazy(() => import('@/pages/Login'))
const Register = lazy(() => import('@/pages/Register'))

// Loading 组件
const PageLoading = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
    <Spin size="large" />
  </div>
)

function App() {
  return (
    <ErrorBoundary>
      <ConfigProvider locale={zhCN}>
        <AuthProvider>
          <BrowserRouter>
            <Suspense fallback={<PageLoading />}>
              <Routes>
                {/* 游客路由（未登录可访问） */}
                <Route
                  path="/login"
                  element={
                    <GuestRoute>
                      <Login />
                    </GuestRoute>
                  }
                />
                <Route
                  path="/register"
                  element={
                    <GuestRoute>
                      <Register />
                    </GuestRoute>
                  }
                />

                {/* 受保护的路由（需要登录） */}
                <Route
                  path="/"
                  element={
                    <ProtectedRoute>
                      <MainLayout />
                    </ProtectedRoute>
                  }
                >
                  <Route index element={<Navigate to="/datasets" replace />} />
                  {ROUTES.map((route) => (
                    <Route key={route.path} path={route.path.slice(1)} element={<route.element />} />
                  ))}
                  {/* 404 兜底路由 */}
                  <Route path="*" element={<Navigate to="/datasets" replace />} />
                </Route>
              </Routes>
            </Suspense>
          </BrowserRouter>
        </AuthProvider>
      </ConfigProvider>
    </ErrorBoundary>
  )
}

export default App
