import { Suspense, lazy } from 'react'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout, ErrorBoundary, PageLoading } from '@/components'

// 路由懒加载
const DataHub = lazy(() => import('@/pages/DataHub'))
const ConfigWizard = lazy(() => import('@/pages/ConfigWizard'))
const ResultRepo = lazy(() => import('@/pages/ResultRepo'))
const Visualization = lazy(() => import('@/pages/Visualization'))

function App() {
  return (
    <ErrorBoundary>
      <ConfigProvider locale={zhCN}>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<MainLayout />}>
              <Route index element={<Navigate to="/datasets" replace />} />
              <Route
                path="datasets"
                element={
                  <Suspense fallback={<PageLoading tip="加载数据中心..." />}>
                    <DataHub />
                  </Suspense>
                }
              />
              <Route
                path="configurations"
                element={
                  <Suspense fallback={<PageLoading tip="加载配置向导..." />}>
                    <ConfigWizard />
                  </Suspense>
                }
              />
              <Route
                path="results"
                element={
                  <Suspense fallback={<PageLoading tip="加载结果仓库..." />}>
                    <ResultRepo />
                  </Suspense>
                }
              />
              <Route
                path="visualization"
                element={
                  <Suspense fallback={<PageLoading tip="加载可视化..." />}>
                    <Visualization />
                  </Suspense>
                }
              />
              {/* 404 兜底路由 */}
              <Route path="*" element={<Navigate to="/datasets" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ConfigProvider>
    </ErrorBoundary>
  )
}

export default App
