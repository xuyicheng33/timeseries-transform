# 代码审查文档

## 项目名称
**时间序列分析与算法对比评估平台**

## 审查日期
2026年1月7日（更新）

---

## 一、项目概述

### 1.1 项目背景
本项目旨在搭建一个标准化的科研协作平台，用于验证时间序列分析方法与经典算法（Transformer、TCN、RNN等）的效果对比。

### 1.2 核心价值
- **标准统一**：统一输入数据、统一参数配置、统一评估标准
- **结果可视化**：集中展示和对比所有实验结果
- **协作友好**：支持团队成员共享数据和结果

### 1.3 开发阶段

| 阶段 | 模式 | 状态 |
|------|------|------|
| 第一阶段（单机版） | 在线配置 + 离线计算 + 在线展示 | **后端已完成，前端开发中** |
| 第二阶段（部署版） | JWT认证 + PostgreSQL + Docker | 待开发 |
| 第三阶段（算力版） | 后台自动运行算法 | 待开发 |

### 1.4 用户流程（第一阶段）
用户在平台下载数据集 -> 查看参数配置要求 -> 本地运行算法 -> 上传预测结果 -> 平台可视化对比

---

## 二、技术架构

### 2.1 技术栈

| 层级 | 技术选型 | 版本 |
|------|----------|------|
| 后端框架 | FastAPI | 0.109.0 |
| 数据库 | SQLite (异步) | - |
| ORM | SQLAlchemy | 2.0.25 |
| 数据处理 | Pandas + NumPy | 2.1.4 / 1.26.3 |
| 前端框架 | React + TypeScript | 19.x |
| UI组件库 | Ant Design | 6.x |
| 可视化 | ECharts | 6.x |

### 2.2 项目结构

    timeseries-platform/
     backend/                     # 后端项目 [已完成]
        app/
           api/                 # API路由
           models/              # 数据库模型
           schemas/             # Pydantic模型
           services/            # 业务逻辑
           config.py            # 应用配置
           database.py          # 数据库连接
           main.py              # FastAPI入口
        uploads/                 # 文件存储
        requirements.txt         # Python依赖
    
     frontend/                    # 前端项目 [开发中]
        src/
           api/                 # API 封装 [已完成]
           types/               # TypeScript 类型定义 [已完成]
           utils/               # 工具函数 [已完成]
           components/          # 通用组件 [待开发]
           pages/               # 页面组件 [待开发]
           hooks/               # 自定义 Hooks [待开发]
           config/              # 配置文件 [待开发]
           constants/           # 常量定义 [待开发]
        package.json
     README.md

---

## 三、已完成模块（需审查）

### 3.1 数据库模型
文件位置: backend/app/models/models.py

| 模型 | 用途 | 关键字段 |
|------|------|----------|
| Dataset | 存储上传的数据集信息 | name, filepath, columns(JSON), row_count |
| Configuration | 存储参数配置 | channels(JSON), normalization, window_size, generated_filename |
| Result | 存储预测结果 | model_name, metrics(JSON), dataset_id |

### 3.2 API接口清单

#### 数据集接口 /api/datasets
- POST /upload - 上传CSV数据集
- GET / - 获取数据集列表
- GET /{id} - 获取数据集详情
- GET /{id}/preview - 预览前100行数据
- GET /{id}/download - 下载数据集文件
- PUT /{id} - 更新数据集信息
- DELETE /{id} - 删除数据集

#### 配置接口 /api/configurations
- POST / - 创建参数配置
- GET / - 获取配置列表
- GET /{id} - 获取配置详情
- PUT /{id} - 更新配置
- DELETE /{id} - 删除配置
- POST /generate-name - 生成标准文件名

#### 结果接口 /api/results
- POST /upload - 上传预测结果
- GET / - 获取结果列表
- GET /{id} - 获取结果详情
- GET /{id}/download - 下载结果文件
- PUT /{id} - 更新结果信息
- DELETE /{id} - 删除结果

#### 可视化接口 /api/visualization
- POST /compare - 多结果对比（含降采样）
- GET /metrics/{id} - 获取单个结果的指标

### 3.3 核心算法
文件位置: backend/app/services/utils.py

| 函数 | 用途 |
|------|------|
| lttb_downsample() | LTTB降采样算法，用于大数据量可视化 |
| calculate_metrics() | 计算MSE/RMSE/MAE/R2/MAPE |
| generate_standard_filename() | 根据配置生成标准命名 |

评估指标公式:
- MSE  = (1/n) * sum((y - y_pred)^2)
- RMSE = sqrt(MSE)
- MAE  = (1/n) * sum(|y - y_pred|)
- R2   = 1 - SS_res / SS_tot
- MAPE = (100/n) * sum(|(y - y_pred) / y|)

---

## 四、审查重点建议

### 4.1 代码质量
- [ ] 异步数据库操作是否正确
- [ ] 异常处理是否完善
- [ ] 文件操作是否安全

### 4.2 业务逻辑
- [ ] 数据集上传流程是否合理
- [ ] 配置参数是否满足实验需求
- [ ] 指标计算公式是否正确

### 4.3 性能考虑
- [ ] 大文件上传处理
- [ ] 降采样算法效率

---

## 五、数据格式规范

### 输入数据集格式（CSV）
timestamp,feature1,feature2,feature3
2024-01-01 00:00:00,1.23,4.56,7.89

### 预测结果格式（CSV）
index,true_value,predicted_value
0,1.23,1.25

注：必须包含 true_value 和 predicted_value 列

### 标准文件命名规则
{数据集名}_{通道}_{窗口}_{步长}_{归一化}_{异常配置}_{目标}.csv
示例：DatasetA_Ch0-1-2_Win100_Str10_MinMax_PredN.csv

---

## 六、如何运行后端

cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

API文档地址：http://localhost:8000/docs

---

文档生成时间：2026年1月6日
文档更新时间：2026年1月7日
