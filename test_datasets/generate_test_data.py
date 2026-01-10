"""
测试数据生成脚本

生成符合平台要求的测试数据集和预测结果文件
- 数据集：CSV 格式，包含时间戳和多个特征列
- 预测结果：CSV 格式，必须包含 true_value 和 predicted_value 列

使用方法：
    cd test_datasets
    python generate_test_data.py
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# 设置随机种子，确保可重复性
np.random.seed(42)

# 输出目录
OUTPUT_DIR = Path(__file__).parent
RESULTS_DIR = OUTPUT_DIR / "prediction_results_v2"
RESULTS_DIR.mkdir(exist_ok=True)


def generate_sine_wave(n_points: int, freq: float = 0.1, noise_level: float = 0.1) -> np.ndarray:
    """生成带噪声的正弦波"""
    t = np.linspace(0, n_points * freq * 2 * np.pi, n_points)
    signal = np.sin(t) + noise_level * np.random.randn(n_points)
    return signal


def generate_trend(n_points: int, slope: float = 0.001) -> np.ndarray:
    """生成趋势分量"""
    return slope * np.arange(n_points)


def generate_seasonality(n_points: int, period: int = 24) -> np.ndarray:
    """生成季节性分量"""
    t = np.arange(n_points)
    return np.sin(2 * np.pi * t / period)


# ============================================================
# 1. 数据集生成函数
# ============================================================

def generate_weather_dataset(n_points: int = 8760) -> pd.DataFrame:
    """
    生成天气数据集（模拟一年的小时数据）
    
    特征：
    - datetime: 时间戳
    - temperature: 温度 (°C)
    - humidity: 湿度 (%)
    - pressure: 气压 (hPa)
    - wind_speed: 风速 (m/s)
    """
    start_date = datetime(2024, 1, 1)
    dates = [start_date + timedelta(hours=i) for i in range(n_points)]
    
    # 温度：基础温度 + 日周期 + 年周期 + 噪声
    hour_of_day = np.array([d.hour for d in dates])
    day_of_year = np.array([d.timetuple().tm_yday for d in dates])
    
    temp_base = 15  # 基础温度
    temp_daily = 5 * np.sin(2 * np.pi * (hour_of_day - 6) / 24)  # 日周期，6点最低
    temp_yearly = 10 * np.sin(2 * np.pi * (day_of_year - 80) / 365)  # 年周期，3月最低
    temp_noise = np.random.randn(n_points) * 2
    temperature = temp_base + temp_daily + temp_yearly + temp_noise
    
    # 湿度：与温度负相关
    humidity = 70 - 0.5 * (temperature - 15) + np.random.randn(n_points) * 5
    humidity = np.clip(humidity, 30, 100)
    
    # 气压
    pressure = 1013 + 5 * np.sin(2 * np.pi * day_of_year / 365) + np.random.randn(n_points) * 3
    
    # 风速
    wind_speed = 5 + 3 * np.abs(np.sin(2 * np.pi * hour_of_day / 12)) + np.random.exponential(2, n_points)
    wind_speed = np.clip(wind_speed, 0, 30)
    
    return pd.DataFrame({
        'datetime': dates,
        'temperature': np.round(temperature, 2),
        'humidity': np.round(humidity, 2),
        'pressure': np.round(pressure, 2),
        'wind_speed': np.round(wind_speed, 2)
    })


def generate_sensor_dataset(n_points: int = 5000) -> pd.DataFrame:
    """
    生成工业传感器数据集
    
    特征：
    - datetime: 时间戳（5分钟间隔）
    - temp_inlet: 入口温度
    - temp_outlet: 出口温度
    - pressure: 压力
    - flow_rate: 流量
    - vibration: 振动
    - power: 功率
    """
    start_date = datetime(2024, 1, 1)
    dates = [start_date + timedelta(minutes=5*i) for i in range(n_points)]
    
    # 基础信号
    t = np.arange(n_points)
    
    # 入口温度：周期性 + 趋势
    temp_inlet = 60 + 5 * np.sin(2 * np.pi * t / 288) + 0.001 * t + np.random.randn(n_points) * 2
    
    # 出口温度：与入口相关，有延迟
    temp_outlet = temp_inlet + 15 + np.random.randn(n_points) * 1.5
    
    # 压力
    pressure = 100 + 10 * np.sin(2 * np.pi * t / 576) + np.random.randn(n_points) * 3
    
    # 流量
    flow_rate = 500 + 50 * np.sin(2 * np.pi * t / 144) + np.random.randn(n_points) * 20
    
    # 振动：偶尔有异常
    vibration = 0.5 + np.random.exponential(0.2, n_points)
    # 添加一些异常点
    anomaly_idx = np.random.choice(n_points, size=50, replace=False)
    vibration[anomaly_idx] *= 3
    
    # 功率：与流量和温差相关
    power = 1000 + 0.5 * flow_rate + 2 * (temp_outlet - temp_inlet) + np.random.randn(n_points) * 30
    
    return pd.DataFrame({
        'datetime': dates,
        'temp_inlet': np.round(temp_inlet, 2),
        'temp_outlet': np.round(temp_outlet, 2),
        'pressure': np.round(pressure, 2),
        'flow_rate': np.round(flow_rate, 2),
        'vibration': np.round(vibration, 4),
        'power': np.round(power, 2)
    })


def generate_stock_dataset(n_points: int = 500) -> pd.DataFrame:
    """
    生成股票数据集
    
    特征：
    - date: 日期
    - open, high, low, close: OHLC 价格
    - volume: 成交量
    - ma5, ma20: 移动平均
    """
    start_date = datetime(2023, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(n_points)]
    
    # 使用几何布朗运动模拟股价
    returns = np.random.randn(n_points) * 0.02  # 日收益率
    close = 100 * np.exp(np.cumsum(returns))
    
    # OHLC
    daily_range = np.abs(np.random.randn(n_points)) * 0.02 * close
    high = close + daily_range * np.random.rand(n_points)
    low = close - daily_range * np.random.rand(n_points)
    open_price = low + (high - low) * np.random.rand(n_points)
    
    # 成交量
    volume = np.random.randint(800000, 1200000, n_points)
    
    # 移动平均
    close_series = pd.Series(close)
    ma5 = close_series.rolling(5).mean().fillna(close_series)
    ma20 = close_series.rolling(20).mean().fillna(close_series)
    
    return pd.DataFrame({
        'date': dates,
        'open': np.round(open_price, 2),
        'high': np.round(high, 2),
        'low': np.round(low, 2),
        'close': np.round(close, 2),
        'volume': volume,
        'ma5': np.round(ma5, 2),
        'ma20': np.round(ma20, 2)
    })


def generate_anomaly_dataset(n_points: int = 3000) -> pd.DataFrame:
    """
    生成异常检测数据集
    
    特征：
    - timestamp: 时间索引
    - value: 观测值
    - is_anomaly: 异常标签 (0/1)
    """
    # 正常信号
    t = np.arange(n_points)
    value = 50 + 10 * np.sin(2 * np.pi * t / 100) + np.random.randn(n_points) * 2
    
    # 标记异常
    is_anomaly = np.zeros(n_points, dtype=int)
    
    # 点异常（突变）
    point_anomalies = np.random.choice(n_points, size=30, replace=False)
    value[point_anomalies] += np.random.choice([-1, 1], size=30) * np.random.uniform(20, 40, 30)
    is_anomaly[point_anomalies] = 1
    
    # 段异常（持续偏移）
    for _ in range(5):
        start = np.random.randint(0, n_points - 50)
        length = np.random.randint(10, 30)
        value[start:start+length] += np.random.choice([-1, 1]) * 15
        is_anomaly[start:start+length] = 1
    
    return pd.DataFrame({
        'timestamp': t,
        'value': np.round(value, 2),
        'is_anomaly': is_anomaly
    })


def generate_large_dataset(n_points: int = 50000) -> pd.DataFrame:
    """
    生成大规模测试数据集（用于性能测试）
    """
    t = np.arange(n_points)
    
    features = {}
    features['timestamp'] = t
    
    # 生成8个特征
    for i in range(1, 9):
        freq = 0.01 * i
        phase = np.random.rand() * 2 * np.pi
        amplitude = 10 + 5 * i
        noise = np.random.randn(n_points) * (1 + 0.5 * i)
        features[f'feature_{i}'] = np.round(
            amplitude * np.sin(2 * np.pi * freq * t + phase) + 
            0.001 * t + noise + 30, 2
        )
    
    return pd.DataFrame(features)


def generate_missing_values_dataset(n_points: int = 1000) -> pd.DataFrame:
    """
    生成包含缺失值的数据集（用于数据质量测试）
    """
    t = np.arange(n_points)
    
    # 完整列
    col_complete = 1000 + 0.1 * t
    
    # 5% 缺失
    col_5pct = 100 + np.random.randn(n_points) * 5
    mask_5 = np.random.rand(n_points) < 0.05
    col_5pct = np.where(mask_5, np.nan, col_5pct)
    
    # 10% 缺失
    col_10pct = 50 + np.random.randn(n_points) * 3
    mask_10 = np.random.rand(n_points) < 0.10
    col_10pct = np.where(mask_10, np.nan, col_10pct)
    
    # 20% 缺失
    col_20pct = 200 + np.random.randn(n_points) * 10
    mask_20 = np.random.rand(n_points) < 0.20
    col_20pct = np.where(mask_20, np.nan, col_20pct)
    
    # 30% 缺失
    col_30pct = 30 + np.random.randn(n_points) * 2
    mask_30 = np.random.rand(n_points) < 0.30
    col_30pct = np.where(mask_30, np.nan, col_30pct)
    
    # 随机缺失（混合模式）
    col_random = np.random.rand(n_points) * 100
    mask_random = np.random.rand(n_points) < np.random.rand(n_points) * 0.3
    col_random = np.where(mask_random, np.nan, col_random)
    
    return pd.DataFrame({
        'timestamp': t,
        'col_5pct': np.round(col_5pct, 2),
        'col_10pct': np.round(col_10pct, 2),
        'col_20pct': np.round(col_20pct, 2),
        'col_30pct': np.round(col_30pct, 2),
        'col_random': np.round(col_random, 2),
        'col_complete': np.round(col_complete, 1)
    })


# ============================================================
# 2. 预测结果生成函数
# ============================================================

def generate_prediction_result(
    true_values: np.ndarray,
    model_name: str,
    quality: str = 'high',
    n_points: int = None
) -> pd.DataFrame:
    """
    生成预测结果文件
    
    Args:
        true_values: 真实值数组
        model_name: 模型名称
        quality: 预测质量 ('high', 'medium', 'low')
        n_points: 输出点数（默认与 true_values 相同）
    
    Returns:
        包含 true_value 和 predicted_value 列的 DataFrame
    """
    if n_points is None:
        n_points = len(true_values)
    
    # 确保 n_points 不超过 true_values 的长度
    n_points = min(n_points, len(true_values))
    true_values = true_values[:n_points]
    
    # 根据质量级别设置噪声水平
    noise_levels = {
        'high': 0.02,      # 2% 噪声
        'medium': 0.08,    # 8% 噪声
        'low': 0.20        # 20% 噪声
    }
    noise_level = noise_levels.get(quality, 0.05)
    
    # 生成预测值（使用实际的 n_points）
    noise = np.random.randn(n_points) * noise_level * np.std(true_values)
    
    # 添加一些系统性偏差（模拟不同模型的特性）
    if 'LSTM' in model_name:
        bias = 0.01 * np.mean(true_values)  # 轻微正偏差
    elif 'Transformer' in model_name:
        bias = -0.005 * np.mean(true_values)  # 轻微负偏差
    elif 'Prophet' in model_name:
        bias = 0.02 * np.mean(true_values)  # 较大正偏差
    else:
        bias = 0
    
    predicted_values = true_values + noise + bias
    
    return pd.DataFrame({
        'true_value': np.round(true_values, 4),
        'predicted_value': np.round(predicted_values, 4)
    })


def generate_all_prediction_results(base_signal: np.ndarray, dataset_name: str):
    """
    为一个数据集生成多个模型的预测结果
    """
    models = [
        ('LSTM', '1.0', 'high'),
        ('LSTM', '1.0', 'medium'),
        ('GRU', '1.0', 'high'),
        ('Transformer', '1.0', 'high'),
        ('Transformer', '2.0', 'medium'),
        ('TCN', '1.0', 'high'),
        ('TCN', '1.0', 'low'),
        ('Autoformer', '1.0', 'medium'),
        ('Prophet', '1.0', 'low'),
        ('XGBoost', '1.0', 'medium'),
    ]
    
    for model_name, version, quality in models:
        result_df = generate_prediction_result(
            base_signal, 
            model_name, 
            quality,
            n_points=1000  # 统一输出1000个点
        )
        
        filename = f"result_{dataset_name}_{model_name}_v{version}_{quality}.csv"
        filepath = RESULTS_DIR / filename
        result_df.to_csv(filepath, index=False)
        print(f"  ✓ 生成: {filename}")


# ============================================================
# 3. 主函数
# ============================================================

def main():
    print("=" * 60)
    print("时序预测平台 - 测试数据生成脚本")
    print("=" * 60)
    
    # 1. 生成数据集
    print("\n[1/2] 生成数据集文件...")
    
    datasets = {
        'weather_v2.csv': generate_weather_dataset,
        'sensor_v2.csv': generate_sensor_dataset,
        'stock_v2.csv': generate_stock_dataset,
        'anomaly_v2.csv': generate_anomaly_dataset,
        'large_scale_v2.csv': generate_large_dataset,
        'missing_values_v2.csv': generate_missing_values_dataset,
    }
    
    generated_data = {}
    for filename, generator in datasets.items():
        df = generator()
        filepath = OUTPUT_DIR / filename
        df.to_csv(filepath, index=False)
        generated_data[filename] = df
        print(f"  ✓ {filename}: {len(df)} 行, {len(df.columns)} 列")
    
    # 2. 生成预测结果
    print("\n[2/2] 生成预测结果文件...")
    
    # 使用天气数据的温度作为基础信号
    weather_df = generated_data['weather_v2.csv']
    print("\n  >> 天气温度预测结果:")
    generate_all_prediction_results(
        weather_df['temperature'].values, 
        'weather'
    )
    
    # 使用传感器数据的功率作为基础信号
    sensor_df = generated_data['sensor_v2.csv']
    print("\n  >> 传感器功率预测结果:")
    generate_all_prediction_results(
        sensor_df['power'].values, 
        'sensor'
    )
    
    # 使用股票收盘价作为基础信号
    stock_df = generated_data['stock_v2.csv']
    print("\n  >> 股票价格预测结果:")
    generate_all_prediction_results(
        stock_df['close'].values, 
        'stock'
    )
    
    # 3. 生成特殊测试用例
    print("\n[额外] 生成特殊测试用例...")
    
    # 3.1 完美预测（用于验证指标计算）
    perfect_true = np.linspace(0, 100, 500)
    perfect_pred = perfect_true.copy()
    pd.DataFrame({
        'true_value': perfect_true,
        'predicted_value': perfect_pred
    }).to_csv(RESULTS_DIR / 'result_perfect_prediction.csv', index=False)
    print("  ✓ result_perfect_prediction.csv (R²=1.0)")
    
    # 3.2 随机预测（用于验证低质量检测）
    random_true = np.random.randn(500) * 10 + 50
    random_pred = np.random.randn(500) * 10 + 50
    pd.DataFrame({
        'true_value': random_true,
        'predicted_value': random_pred
    }).to_csv(RESULTS_DIR / 'result_random_prediction.csv', index=False)
    print("  ✓ result_random_prediction.csv (R²≈0)")
    
    # 3.3 大规模预测结果（性能测试）
    large_true = generated_data['large_scale_v2.csv']['feature_1'].values
    large_pred = large_true + np.random.randn(len(large_true)) * 2
    pd.DataFrame({
        'true_value': np.round(large_true, 4),
        'predicted_value': np.round(large_pred, 4)
    }).to_csv(RESULTS_DIR / 'result_large_scale.csv', index=False)
    print(f"  ✓ result_large_scale.csv ({len(large_true)} 行)")
    
    # 4. 汇总
    print("\n" + "=" * 60)
    print("生成完成！")
    print(f"  - 数据集目录: {OUTPUT_DIR}")
    print(f"  - 预测结果目录: {RESULTS_DIR}")
    print("=" * 60)
    
    # 5. 生成数据清单
    generate_data_manifest()


def generate_data_manifest():
    """生成数据清单文件"""
    manifest = """# 测试数据清单

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
"""
    
    with open(OUTPUT_DIR / 'DATA_MANIFEST.md', 'w', encoding='utf-8') as f:
        f.write(manifest)
    print("\n  ✓ 生成数据清单: DATA_MANIFEST.md")


if __name__ == '__main__':
    main()

