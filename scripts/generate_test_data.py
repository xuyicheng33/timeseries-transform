"""
测试数据集生成脚本
生成用于测试时序预测平台各功能的数据集

数据集类型：
1. 气温预测数据 - 真实感的气温时序
2. 股价预测数据 - 模拟股票价格走势
3. 多变量预测数据 - 工业传感器多通道数据
4. 时序重构数据 - 用于自编码器重构任务
5. 异常检测数据 - 包含异常点的数据
6. 缺失值测试数据 - 包含不同比例缺失值
7. 大规模数据 - 用于性能测试

预测结果数据：
- 不同模型（LSTM, Transformer, TCN, XGBoost）
- 不同精度（高、中、低）
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os

# 设置随机种子以保证可重复性
np.random.seed(42)

# 输出目录
OUTPUT_DIR = "test_datasets"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_temperature_data(n_days=365*2, freq='H'):
    """
    生成气温预测数据
    包含：年周期、日周期、随机波动、极端天气事件
    """
    print("生成气温预测数据...")
    
    # 生成时间索引
    start_date = datetime(2024, 1, 1)
    if freq == 'H':
        n_points = n_days * 24
        dates = [start_date + timedelta(hours=i) for i in range(n_points)]
    else:
        n_points = n_days
        dates = [start_date + timedelta(days=i) for i in range(n_points)]
    
    t = np.arange(n_points)
    
    # 年周期（夏天热，冬天冷）
    year_cycle = 15 * np.sin(2 * np.pi * t / (365 * 24 if freq == 'H' else 365) - np.pi/2)
    
    # 日周期（白天热，晚上冷）
    if freq == 'H':
        day_cycle = 5 * np.sin(2 * np.pi * t / 24 - np.pi/2)
    else:
        day_cycle = 0
    
    # 基础温度
    base_temp = 15
    
    # 随机波动
    noise = np.random.normal(0, 2, n_points)
    
    # 天气系统（低频波动）
    weather_system = 3 * np.sin(2 * np.pi * t / (7 * 24 if freq == 'H' else 7))
    
    # 合成温度
    temperature = base_temp + year_cycle + day_cycle + weather_system + noise
    
    # 添加一些极端天气事件
    n_events = 10
    for _ in range(n_events):
        event_start = np.random.randint(0, n_points - 48)
        event_duration = np.random.randint(12, 48)
        event_magnitude = np.random.choice([-1, 1]) * np.random.uniform(5, 10)
        temperature[event_start:event_start+event_duration] += event_magnitude
    
    # 湿度（与温度负相关）
    humidity = 70 - 0.5 * (temperature - 15) + np.random.normal(0, 5, n_points)
    humidity = np.clip(humidity, 20, 100)
    
    # 气压
    pressure = 1013 + 5 * np.sin(2 * np.pi * t / (3 * 24 if freq == 'H' else 3)) + np.random.normal(0, 3, n_points)
    
    # 风速
    wind_speed = np.abs(5 + 3 * np.sin(2 * np.pi * t / (12 * 24 if freq == 'H' else 12)) + np.random.exponential(2, n_points))
    
    df = pd.DataFrame({
        'datetime': dates,
        'temperature': np.round(temperature, 2),
        'humidity': np.round(humidity, 2),
        'pressure': np.round(pressure, 2),
        'wind_speed': np.round(wind_speed, 2)
    })
    
    return df


def generate_stock_data(n_days=500, n_stocks=1):
    """
    生成股价预测数据
    使用几何布朗运动模拟股价
    """
    print("生成股价预测数据...")
    
    start_date = datetime(2023, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(n_days)]
    
    # 初始价格
    S0 = 100
    
    # 参数
    mu = 0.0002  # 日收益率
    sigma = 0.02  # 波动率
    
    # 生成价格路径
    dt = 1
    returns = np.random.normal(mu, sigma, n_days)
    
    # 添加一些趋势变化
    trend_changes = np.zeros(n_days)
    change_points = [100, 200, 350]
    trends = [0.001, -0.0005, 0.0008]
    for i, cp in enumerate(change_points):
        if cp < n_days:
            trend_changes[cp:] = trends[i]
    
    returns = returns + trend_changes
    
    # 计算价格
    price = S0 * np.exp(np.cumsum(returns))
    
    # 生成成交量（与价格变化相关）
    volume_base = 1000000
    price_change = np.abs(np.diff(price, prepend=price[0]))
    volume = volume_base * (1 + 2 * price_change / price) * np.random.uniform(0.8, 1.2, n_days)
    
    # 生成开盘价、最高价、最低价
    daily_range = price * sigma * np.random.uniform(0.5, 1.5, n_days)
    high = price + daily_range * np.random.uniform(0.3, 0.7, n_days)
    low = price - daily_range * np.random.uniform(0.3, 0.7, n_days)
    open_price = low + (high - low) * np.random.uniform(0.2, 0.8, n_days)
    
    # 技术指标
    # 移动平均
    ma5 = pd.Series(price).rolling(5).mean().fillna(price[0])
    ma20 = pd.Series(price).rolling(20).mean().fillna(price[0])
    
    # RSI
    delta = pd.Series(price).diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50)
    
    df = pd.DataFrame({
        'date': dates,
        'open': np.round(open_price, 2),
        'high': np.round(high, 2),
        'low': np.round(low, 2),
        'close': np.round(price, 2),
        'volume': np.round(volume).astype(int),
        'ma5': np.round(ma5, 2),
        'ma20': np.round(ma20, 2),
        'rsi': np.round(rsi, 2)
    })
    
    return df


def generate_multivariate_sensor_data(n_points=5000, n_sensors=8):
    """
    生成多变量工业传感器数据
    模拟工厂设备的多个传感器读数
    """
    print("生成多变量传感器数据...")
    
    start_date = datetime(2024, 1, 1)
    dates = [start_date + timedelta(minutes=i*5) for i in range(n_points)]
    
    t = np.arange(n_points)
    
    # 基础信号（设备运行周期）
    base_cycle = np.sin(2 * np.pi * t / 288)  # 24小时周期
    
    # 生成相关的传感器数据
    data = {'datetime': dates}
    
    # 温度传感器（多个位置）
    temp_base = 60 + 10 * base_cycle
    data['temp_inlet'] = np.round(temp_base + np.random.normal(0, 1, n_points), 2)
    data['temp_outlet'] = np.round(temp_base + 15 + np.random.normal(0, 1.5, n_points), 2)
    data['temp_ambient'] = np.round(25 + 5 * base_cycle + np.random.normal(0, 0.5, n_points), 2)
    
    # 压力传感器
    pressure_base = 100 + 20 * base_cycle
    data['pressure_1'] = np.round(pressure_base + np.random.normal(0, 2, n_points), 2)
    data['pressure_2'] = np.round(pressure_base * 0.8 + np.random.normal(0, 1.5, n_points), 2)
    
    # 流量传感器
    flow_base = 500 + 100 * base_cycle
    data['flow_rate'] = np.round(np.maximum(0, flow_base + np.random.normal(0, 20, n_points)), 2)
    
    # 振动传感器
    vibration_base = 0.5 + 0.2 * np.abs(base_cycle)
    data['vibration'] = np.round(np.maximum(0, vibration_base + np.random.exponential(0.1, n_points)), 4)
    
    # 功率消耗
    power_base = 1000 + 200 * base_cycle + 50 * data['flow_rate'] / 500
    data['power'] = np.round(np.maximum(0, power_base + np.random.normal(0, 30, n_points)), 2)
    
    df = pd.DataFrame(data)
    return df


def generate_reconstruction_data(n_points=2000, n_features=5):
    """
    生成时序重构数据
    用于自编码器等重构任务
    """
    print("生成时序重构数据...")
    
    t = np.arange(n_points)
    
    data = {}
    
    # 生成多个具有不同特征的信号
    # 信号1：正弦波 + 噪声
    data['signal_1'] = np.sin(2 * np.pi * t / 100) + 0.1 * np.random.randn(n_points)
    
    # 信号2：方波
    data['signal_2'] = np.sign(np.sin(2 * np.pi * t / 50)) + 0.05 * np.random.randn(n_points)
    
    # 信号3：锯齿波
    data['signal_3'] = 2 * (t % 80) / 80 - 1 + 0.1 * np.random.randn(n_points)
    
    # 信号4：复合波
    data['signal_4'] = (np.sin(2 * np.pi * t / 100) + 
                        0.5 * np.sin(2 * np.pi * t / 30) + 
                        0.1 * np.random.randn(n_points))
    
    # 信号5：脉冲信号
    pulse = np.zeros(n_points)
    pulse_positions = np.arange(0, n_points, 100)
    for pos in pulse_positions:
        if pos + 10 < n_points:
            pulse[pos:pos+10] = 1
    data['signal_5'] = pulse + 0.05 * np.random.randn(n_points)
    
    df = pd.DataFrame(data)
    df = df.round(4)
    df.insert(0, 'timestamp', range(n_points))
    
    return df


def generate_anomaly_data(n_points=3000):
    """
    生成包含异常的数据
    用于异常检测任务
    """
    print("生成异常检测数据...")
    
    t = np.arange(n_points)
    
    # 正常信号
    normal_signal = 50 + 10 * np.sin(2 * np.pi * t / 200) + np.random.normal(0, 2, n_points)
    
    # 创建异常标签
    labels = np.zeros(n_points)
    
    # 点异常（突变）
    point_anomalies = np.random.choice(n_points, 30, replace=False)
    normal_signal[point_anomalies] += np.random.choice([-1, 1], 30) * np.random.uniform(15, 25, 30)
    labels[point_anomalies] = 1
    
    # 段异常（持续偏移）
    segment_starts = [500, 1200, 2000, 2500]
    segment_lengths = [50, 80, 60, 40]
    for start, length in zip(segment_starts, segment_lengths):
        if start + length < n_points:
            normal_signal[start:start+length] += np.random.choice([-1, 1]) * 12
            labels[start:start+length] = 1
    
    # 趋势异常
    trend_start = 1800
    trend_length = 100
    if trend_start + trend_length < n_points:
        trend = np.linspace(0, 15, trend_length)
        normal_signal[trend_start:trend_start+trend_length] += trend
        labels[trend_start:trend_start+trend_length] = 1
    
    df = pd.DataFrame({
        'timestamp': range(n_points),
        'value': np.round(normal_signal, 2),
        'is_anomaly': labels.astype(int)
    })
    
    return df


def generate_missing_data(n_points=1000):
    """
    生成包含缺失值的数据
    用于测试数据清洗功能
    """
    print("生成缺失值测试数据...")
    
    t = np.arange(n_points)
    
    # 生成完整数据
    data = {
        'timestamp': range(n_points),
        'col_5pct': 100 + 10 * np.sin(2 * np.pi * t / 100) + np.random.normal(0, 2, n_points),
        'col_10pct': 50 + 5 * np.cos(2 * np.pi * t / 80) + np.random.normal(0, 1, n_points),
        'col_20pct': 200 + 20 * np.sin(2 * np.pi * t / 150) + np.random.normal(0, 5, n_points),
        'col_30pct': 30 + 3 * np.sin(2 * np.pi * t / 50) + np.random.normal(0, 0.5, n_points),
        'col_random': np.random.uniform(0, 100, n_points),
        'col_complete': 1000 + t * 0.1  # 完整列，无缺失
    }
    
    df = pd.DataFrame(data)
    
    # 引入不同比例的缺失值
    missing_rates = {
        'col_5pct': 0.05,
        'col_10pct': 0.10,
        'col_20pct': 0.20,
        'col_30pct': 0.30,
        'col_random': 0.15
    }
    
    for col, rate in missing_rates.items():
        mask = np.random.random(n_points) < rate
        df.loc[mask, col] = np.nan
    
    # 添加连续缺失段
    df.loc[200:220, 'col_10pct'] = np.nan
    df.loc[500:550, 'col_20pct'] = np.nan
    
    df = df.round(2)
    return df


def generate_large_data(n_points=100000, n_features=10):
    """
    生成大规模数据
    用于性能测试
    """
    print("生成大规模测试数据...")
    
    t = np.arange(n_points)
    
    data = {'timestamp': range(n_points)}
    
    for i in range(n_features):
        freq = np.random.uniform(50, 500)
        amplitude = np.random.uniform(10, 100)
        offset = np.random.uniform(0, 50)
        noise_level = np.random.uniform(1, 5)
        
        signal = offset + amplitude * np.sin(2 * np.pi * t / freq) + np.random.normal(0, noise_level, n_points)
        data[f'feature_{i+1}'] = np.round(signal, 2)
    
    df = pd.DataFrame(data)
    return df


def generate_prediction_results(true_values, model_name, accuracy='high'):
    """
    生成模拟的预测结果
    
    accuracy: 'high', 'medium', 'low'
    """
    n = len(true_values)
    
    if accuracy == 'high':
        noise_scale = 0.02
        bias = 0
    elif accuracy == 'medium':
        noise_scale = 0.08
        bias = np.random.uniform(-0.02, 0.02) * np.mean(true_values)
    else:  # low
        noise_scale = 0.15
        bias = np.random.uniform(-0.05, 0.05) * np.mean(true_values)
    
    # 生成预测值
    noise = np.random.normal(0, noise_scale * np.std(true_values), n)
    predictions = true_values + noise + bias
    
    # 添加一些系统性误差
    if accuracy != 'high':
        # 在某些区域预测更差
        bad_regions = np.random.choice(n // 100, 3, replace=False)
        for region in bad_regions:
            start = region * 100
            end = min(start + 100, n)
            predictions[start:end] += np.random.uniform(-1, 1) * 0.1 * np.std(true_values)
    
    return predictions


def save_prediction_results(base_data, output_dir):
    """
    为不同模型生成预测结果文件
    """
    print("生成预测结果数据...")
    
    # 使用气温数据的温度列作为真实值
    true_values = base_data['temperature'].values
    n = len(true_values)
    
    # 只取一部分作为测试集
    test_size = min(1000, n)
    true_test = true_values[-test_size:]
    
    models = [
        ('LSTM', '1.0', 'high'),
        ('LSTM', '1.0', 'medium'),
        ('Transformer', '1.0', 'high'),
        ('Transformer', '2.0', 'medium'),
        ('TCN', '1.0', 'high'),
        ('TCN', '1.0', 'low'),
        ('XGBoost', '1.0', 'medium'),
        ('GRU', '1.0', 'high'),
        ('Autoformer', '1.0', 'medium'),
        ('Prophet', '1.0', 'low'),
    ]
    
    results_dir = os.path.join(output_dir, 'prediction_results')
    os.makedirs(results_dir, exist_ok=True)
    
    for model_name, version, accuracy in models:
        predictions = generate_prediction_results(true_test, model_name, accuracy)
        
        df = pd.DataFrame({
            'true': np.round(true_test, 4),
            'pred': np.round(predictions, 4)
        })
        
        filename = f"result_{model_name}_v{version}_{accuracy}.csv"
        filepath = os.path.join(results_dir, filename)
        df.to_csv(filepath, index=False)
        print(f"  保存: {filename}")
    
    return results_dir


def main():
    """主函数"""
    print("=" * 50)
    print("时序预测平台测试数据集生成器")
    print("=" * 50)
    print()
    
    # 1. 气温预测数据
    temp_data = generate_temperature_data(n_days=365, freq='H')
    temp_data.to_csv(os.path.join(OUTPUT_DIR, 'weather_temperature.csv'), index=False)
    print(f"  保存: weather_temperature.csv ({len(temp_data)} 行)")
    
    # 2. 股价预测数据
    stock_data = generate_stock_data(n_days=500)
    stock_data.to_csv(os.path.join(OUTPUT_DIR, 'stock_price.csv'), index=False)
    print(f"  保存: stock_price.csv ({len(stock_data)} 行)")
    
    # 3. 多变量传感器数据
    sensor_data = generate_multivariate_sensor_data(n_points=5000)
    sensor_data.to_csv(os.path.join(OUTPUT_DIR, 'industrial_sensors.csv'), index=False)
    print(f"  保存: industrial_sensors.csv ({len(sensor_data)} 行)")
    
    # 4. 时序重构数据
    recon_data = generate_reconstruction_data(n_points=2000)
    recon_data.to_csv(os.path.join(OUTPUT_DIR, 'reconstruction_signals.csv'), index=False)
    print(f"  保存: reconstruction_signals.csv ({len(recon_data)} 行)")
    
    # 5. 异常检测数据
    anomaly_data = generate_anomaly_data(n_points=3000)
    anomaly_data.to_csv(os.path.join(OUTPUT_DIR, 'anomaly_detection.csv'), index=False)
    print(f"  保存: anomaly_detection.csv ({len(anomaly_data)} 行)")
    
    # 6. 缺失值测试数据
    missing_data = generate_missing_data(n_points=1000)
    missing_data.to_csv(os.path.join(OUTPUT_DIR, 'missing_values_test.csv'), index=False)
    print(f"  保存: missing_values_test.csv ({len(missing_data)} 行)")
    
    # 7. 大规模数据
    large_data = generate_large_data(n_points=50000, n_features=8)
    large_data.to_csv(os.path.join(OUTPUT_DIR, 'large_scale_test.csv'), index=False)
    print(f"  保存: large_scale_test.csv ({len(large_data)} 行)")
    
    # 8. 生成预测结果
    print()
    results_dir = save_prediction_results(temp_data, OUTPUT_DIR)
    
    print()
    print("=" * 50)
    print("数据集生成完成！")
    print(f"输出目录: {os.path.abspath(OUTPUT_DIR)}")
    print()
    print("数据集列表:")
    print("  原始数据:")
    print("    - weather_temperature.csv  (气温预测，8760行)")
    print("    - stock_price.csv          (股价预测，500行)")
    print("    - industrial_sensors.csv   (多变量传感器，5000行)")
    print("    - reconstruction_signals.csv (时序重构，2000行)")
    print("    - anomaly_detection.csv    (异常检测，3000行)")
    print("    - missing_values_test.csv  (缺失值测试，1000行)")
    print("    - large_scale_test.csv     (大规模测试，50000行)")
    print()
    print("  预测结果:")
    for f in os.listdir(results_dir):
        print(f"    - {f}")
    print("=" * 50)


if __name__ == '__main__':
    main()

