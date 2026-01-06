# 时间序列分析平台 - 前端

基于 React 18 + TypeScript + Vite + Ant Design 5 的现代化前端应用。

## 技术栈

- **构建工具**: Vite 5
- **框架**: React 18 (函数组件 + Hooks)
- **语言**: TypeScript 5
- **UI 组件库**: Ant Design 5
- **图表库**: ECharts 5 + echarts-for-react
- **路由**: React Router 6
- **HTTP**: Axios

## 项目结构

```
src/
├── api/                # API 封装
├── components/         # 通用组件
├── pages/              # 页面组件
├── hooks/              # 自定义 Hooks
├── types/              # TypeScript 类型定义
├── utils/              # 工具函数
├── config/             # 配置文件
└── constants/          # 常量定义
```

## 开发

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 环境变量

- `.env.development` - 开发环境（使用 Vite proxy）
- `.env.production` - 生产环境

## 开发规范

- 使用函数组件 + Hooks
- 严格的 TypeScript 类型检查
- 统一的代码风格（ESLint）
- 模块化的 API 封装
- 响应式设计

## 浏览器支持

- Chrome >= 90
- Firefox >= 88
- Safari >= 14
- Edge >= 90
