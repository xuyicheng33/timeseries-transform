# 时间序列分析平台 - 前端

基于 React 19 + TypeScript + Vite + Ant Design 6 的现代化前端应用。

## 技术栈

- **构建工具**: Vite 7
- **框架**: React 19 (函数组件 + Hooks)
- **语言**: TypeScript 5
- **UI 组件库**: Ant Design 6
- **图表库**: ECharts 6 + echarts-for-react
- **路由**: React Router 7
- **HTTP**: Axios

## 项目结构

```
src/
├── api/                # API 封装（待实现）
├── components/         # 通用组件（待实现）
├── pages/              # 页面组件（待实现）
├── hooks/              # 自定义 Hooks（待实现）
├── types/              # TypeScript 类型定义（待实现）
├── utils/              # 工具函数（待实现）
├── config/             # 配置文件（待实现）
└── constants/          # 常量定义（待实现）
```

**注意**: 当前为初始化阶段，上述目录结构已创建但内容待后续步骤实现。

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

- `.env.example` - 环境变量模板（提交到仓库）
- `.env.development` - 开发环境（使用 Vite proxy，不提交）
- `.env.production` - 生产环境（不提交）

**首次使用**: 复制 `.env.example` 为 `.env.development` 和 `.env.production`，根据需要修改。

## 开发规范

- 使用函数组件 + Hooks
- 严格的 TypeScript 类型检查
- 统一的代码风格（ESLint）
- 模块化的 API 封装
- 响应式设计
- 外部链接必须添加 `rel="noopener noreferrer"`

## 当前状态

- ✅ 项目初始化完成
- ✅ 依赖安装完成
- ✅ 开发环境配置完成
- ⏳ 类型定义待实现
- ⏳ API 封装待实现
- ⏳ 页面组件待实现

## 浏览器支持

- Chrome >= 90
- Firefox >= 88
- Safari >= 14
- Edge >= 90
