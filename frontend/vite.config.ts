import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // 调整 chunk 大小警告阈值
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // 手动分割 chunks
        manualChunks: {
          // React 核心库
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          // Ant Design 组件库
          'vendor-antd': ['antd', '@ant-design/icons'],
          // ECharts 图表库（最大的依赖）
          'vendor-echarts': ['echarts', 'echarts-for-react'],
          // 日期处理
          'vendor-dayjs': ['dayjs'],
        },
      },
    },
  },
})
