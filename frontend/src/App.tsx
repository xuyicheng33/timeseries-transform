import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from '@/components/MainLayout'
import DataHub from '@/pages/DataHub'
import ConfigWizard from '@/pages/ConfigWizard'
import ResultRepo from '@/pages/ResultRepo'
import Visualization from '@/pages/Visualization'

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Navigate to="/datasets" replace />} />
            <Route path="datasets" element={<DataHub />} />
            <Route path="configurations" element={<ConfigWizard />} />
            <Route path="results" element={<ResultRepo />} />
            <Route path="visualization" element={<Visualization />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  )
}

export default App
