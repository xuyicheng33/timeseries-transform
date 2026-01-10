# 测试数据清单

## 数据集文件

| 文件名 | 描述 | 行数 | 推荐测试场景 |
|--------|------|------|--------------|
| weather_v2.csv | 天气数据（一年小时数据） | 8760 | 温度预测、多变量预测 |
| sensor_v2.csv | 工业传感器数据 | 5000 | 设备监控、异常检测 |
| stock_v2.csv | 股票价格数据 | 500 | 金融预测、趋势分析 |
| anomaly_v2.csv | 异常检测数据 | 3000 | 异常检测评估 |
| large_scale_v2.csv | 大规模数据 | 50000 | 性能测试、降采样测试 |
| missing_values_v2.csv | 缺失值数据 | 1000 | 数据质量检测 |

## 预测结果文件 (prediction_results_v2/)

### 列格式
- `true_value`: 真实值
- `predicted_value`: 预测值

### 文件命名规则
`result_{数据集}_{模型}_v{版本}_{质量}.csv`

### 质量级别
- `high`: 高质量预测 (噪声 ~2%)
- `medium`: 中等质量预测 (噪声 ~8%)
- `low`: 低质量预测 (噪声 ~20%)

### 特殊测试文件
- `result_perfect_prediction.csv`: 完美预测 (R²=1.0)
- `result_random_prediction.csv`: 随机预测 (R²≈0)
- `result_large_scale.csv`: 大规模预测结果 (50000行)

## 使用说明

1. **上传数据集**: 选择 `*_v2.csv` 文件上传到平台
2. **上传预测结果**: 选择 `prediction_results_v2/` 目录下的文件
3. **可视化对比**: 选择同一数据集的多个预测结果进行对比

## 测试场景

### 场景1: 基础功能测试
- 上传 `weather_v2.csv`
- 上传 `result_weather_LSTM_v1.0_high.csv`
- 验证指标计算正确

### 场景2: 多模型对比
- 上传 `weather_v2.csv`
- 上传多个 `result_weather_*.csv`
- 使用可视化对比功能

### 场景3: 性能测试
- 上传 `large_scale_v2.csv`
- 上传 `result_large_scale.csv`
- 测试降采样和渲染性能

### 场景4: 数据质量测试
- 上传 `missing_values_v2.csv`
- 使用数据质量检测功能
