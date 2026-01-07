"""
生成测试数据集和预测结果
用于验证时间序列分析平台功能
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# 确保输出目录存在
output_dir = os.path.dirname(os.path.abspath(__file__))

print("=" * 50)
print("生成测试数据集")
print("=" * 50)

# ============ 数据集1：正弦波数据 ============
print("\n[1/4] 生成数据集1：正弦波时间序列...")

np.random.seed(42)
n_points = 1000

# 生成时间戳
start_time = datetime(2024, 1, 1)
timestamps = [start_time + timedelta(hours=i) for i in range(n_points)]

# 生成特征：正弦波 + 噪声
t = np.linspace(0, 10 * np.pi, n_points)
feature1 = np.sin(t) + np.random.normal(0, 0.1, n_points)
feature2 = np.cos(t) + np.random.normal(0, 0.1, n_points)
feature3 = np.sin(2 * t) * 0.5 + np.random.normal(0, 0.05, n_points)

dataset1 = pd.DataFrame({
    'timestamp': timestamps,
    'temperature': (feature1 * 10 + 25).round(2),  # 温度：15-35度
    'humidity': (feature2 * 20 + 60).round(2),     # 湿度：40-80%
    'pressure': (feature3 * 5 + 1013).round(2)     # 气压：1008-1018 hPa
})

dataset1_path = os.path.join(output_dir, 'dataset1_sensor_data.csv')
dataset1.to_csv(dataset1_path, index=False)
print(f"   已保存: {dataset1_path}")
print(f"   行数: {len(dataset1)}, 列: {list(dataset1.columns)}")

# ============ 数据集2：股票模拟数据 ============
print("\n[2/4] 生成数据集2：股票模拟时间序列...")

np.random.seed(123)
n_points = 500

# 生成日期
dates = pd.date_range(start='2023-01-01', periods=n_points, freq='D')

# 生成股票价格（随机游走 + 趋势）
price = 100
prices = [price]
for i in range(1, n_points):
    change = np.random.normal(0.001, 0.02)  # 日收益率
    price = price * (1 + change)
    prices.append(price)

prices = np.array(prices)
volume = np.random.randint(1000000, 5000000, n_points)

dataset2 = pd.DataFrame({
    'date': dates,
    'open': (prices * np.random.uniform(0.99, 1.01, n_points)).round(2),
    'high': (prices * np.random.uniform(1.01, 1.03, n_points)).round(2),
    'low': (prices * np.random.uniform(0.97, 0.99, n_points)).round(2),
    'close': prices.round(2),
    'volume': volume
})

dataset2_path = os.path.join(output_dir, 'dataset2_stock_data.csv')
dataset2.to_csv(dataset2_path, index=False)
print(f"   已保存: {dataset2_path}")
print(f"   行数: {len(dataset2)}, 列: {list(dataset2.columns)}")

# ============ 预测结果1：针对数据集1的温度预测 ============
print("\n[3/4] 生成预测结果1：温度预测（模拟 LSTM 模型）...")

# 取数据集1的温度作为真实值
true_values = dataset1['temperature'].values[100:]  # 跳过前100个作为训练

# 模拟 LSTM 预测（加一些误差）
np.random.seed(456)
predicted_lstm = true_values + np.random.normal(0, 0.5, len(true_values))

result1 = pd.DataFrame({
    'index': range(len(true_values)),
    'true_value': true_values.round(2),
    'predicted_value': predicted_lstm.round(2)
})

result1_path = os.path.join(output_dir, 'result1_lstm_temperature.csv')
result1.to_csv(result1_path, index=False)
print(f"   已保存: {result1_path}")
print(f"   行数: {len(result1)}")

# 计算指标
mse1 = np.mean((true_values - predicted_lstm) ** 2)
print(f"   MSE: {mse1:.4f}")

# ============ 预测结果2：针对数据集1的温度预测（另一个模型）============
print("\n[4/4] 生成预测结果2：温度预测（模拟 Transformer 模型）...")

# 模拟 Transformer 预测（误差更小）
np.random.seed(789)
predicted_transformer = true_values + np.random.normal(0, 0.3, len(true_values))

result2 = pd.DataFrame({
    'index': range(len(true_values)),
    'true_value': true_values.round(2),
    'predicted_value': predicted_transformer.round(2)
})

result2_path = os.path.join(output_dir, 'result2_transformer_temperature.csv')
result2.to_csv(result2_path, index=False)
print(f"   已保存: {result2_path}")
print(f"   行数: {len(result2)}")

# 计算指标
mse2 = np.mean((true_values - predicted_transformer) ** 2)
print(f"   MSE: {mse2:.4f}")

# ============ 总结 ============
print("\n" + "=" * 50)
print("生成完成！文件列表：")
print("=" * 50)
print(f"""
数据集文件（上传到「数据中心」）：
  1. {dataset1_path}
     - 传感器数据，1000行，包含 timestamp, temperature, humidity, pressure
  
  2. {dataset2_path}
     - 股票数据，500行，包含 date, open, high, low, close, volume

预测结果文件（上传到「结果仓库」）：
  3. {result1_path}
     - LSTM 模型预测温度，900行，MSE={mse1:.4f}
  
  4. {result2_path}
     - Transformer 模型预测温度，900行，MSE={mse2:.4f}

使用步骤：
  1. 启动后端和前端
  2. 打开浏览器访问 http://localhost:5173
  3. 在「数据中心」上传 dataset1_sensor_data.csv 和 dataset2_stock_data.csv
  4. 在「配置向导」为 dataset1 创建一个配置
  5. 在「结果仓库」上传 result1 和 result2，关联到 dataset1
  6. 在「可视化对比」选择两个结果进行对比
""")

