import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column',
        gap: '16px'
      }}>
        <h1 style={{ fontSize: '32px', fontWeight: 600, margin: 0 }}>
          时间序列分析平台
        </h1>
        <p style={{ fontSize: '16px', color: '#666', margin: 0 }}>
          Time Series Analysis Platform
        </p>
        <p style={{ fontSize: '14px', color: '#999', margin: 0 }}>
          正在开发中...
        </p>
      </div>
    </ConfigProvider>
  )
}

export default App
