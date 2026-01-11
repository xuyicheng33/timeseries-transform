"""
生成差异化的预测结果数据
用于测试可视化对比功能，包含不同精度级别的预测结果
"""

import numpy as np
import pandas as pd
import os

# 设置随机种子
np.random.seed(2024)

# 输出目录
OUTPUT_DIR = "test_datasets/prediction_results"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_base_signal(n_points=1000):
    """生成基础真实值信号"""
    t = np.arange(n_points)
    
    # 复合信号：趋势 + 周期 + 噪声
    trend = 100 + 0.05 * t
    seasonal = 20 * np.sin(2 * np.pi * t / 100) + 10 * np.sin(2 * np.pi * t / 30)
    noise = np.random.normal(0, 5, n_points)
    
    # 添加一些突变点
    signal = trend + seasonal + noise
    
    # 添加几个突变
    signal[200:250] += 30
    signal[500:520] -= 25
    signal[700:750] += np.linspace(0, 40, 50)
    signal[800:850] -= np.linspace(0, 35, 50)
    
    return signal


def generate_prediction(true_values, r2_target, model_characteristics=None):
    """
    生成指定 R² 目标的预测值
    
    Args:
        true_values: 真实值数组
        r2_target: 目标 R² 值 (0-1)
        model_characteristics: 模型特性字典，可选
    """
    n = len(true_values)
    true_var = np.var(true_values)
    
    # 根据 R² = 1 - MSE/Var(y) 计算需要的 MSE
    # MSE = Var(y) * (1 - R²)
    target_mse = true_var * (1 - r2_target)
    target_rmse = np.sqrt(target_mse)
    
    # 基础预测 = 真实值 + 噪声
    noise = np.random.normal(0, target_rmse * 0.8, n)
    predictions = true_values.copy() + noise
    
    # 添加模型特性
    if model_characteristics:
        # 滞后效应
        if model_characteristics.get('lag', 0) > 0:
            lag = model_characteristics['lag']
            predictions[lag:] = predictions[lag:] * 0.7 + true_values[:-lag] * 0.3
        
        # 系统性偏差
        if model_characteristics.get('bias', 0) != 0:
            predictions += model_characteristics['bias'] * np.std(true_values)
        
        # 趋势跟踪能力差
        if model_characteristics.get('poor_trend', False):
            trend = np.polyfit(np.arange(n), true_values, 1)
            trend_line = np.polyval(trend, np.arange(n))
            predictions = predictions * 0.8 + trend_line * 0.2
        
        # 对突变反应慢
        if model_characteristics.get('slow_response', False):
            # 平滑预测值
            from scipy.ndimage import uniform_filter1d
            predictions = uniform_filter1d(predictions, size=10)
        
        # 高频噪声
        if model_characteristics.get('noisy', False):
            predictions += np.random.normal(0, target_rmse * 0.3, n)
        
        # 周期性误差
        if model_characteristics.get('periodic_error', False):
            t = np.arange(n)
            predictions += target_rmse * 0.5 * np.sin(2 * np.pi * t / 50)
    
    # 微调以接近目标 R²
    for _ in range(10):
        current_mse = np.mean((predictions - true_values) ** 2)
        current_r2 = 1 - current_mse / true_var
        
        if abs(current_r2 - r2_target) < 0.01:
            break
        
        # 调整噪声幅度
        if current_r2 > r2_target:
            # R² 太高，增加噪声
            extra_noise = np.random.normal(0, target_rmse * 0.1, n)
            predictions += extra_noise
        else:
            # R² 太低，减少误差
            predictions = predictions * 0.95 + true_values * 0.05
    
    return predictions


def calculate_metrics(true_values, predictions):
    """计算评估指标"""
    mse = np.mean((predictions - true_values) ** 2)
    rmse = np.sqrt(mse)
    mae = np.mean(np.abs(predictions - true_values))
    
    ss_res = np.sum((true_values - predictions) ** 2)
    ss_tot = np.sum((true_values - np.mean(true_values)) ** 2)
    r2 = 1 - (ss_res / ss_tot)
    
    # MAPE (避免除零)
    mask = true_values != 0
    mape = np.mean(np.abs((true_values[mask] - predictions[mask]) / true_values[mask])) * 100
    
    return {
        'MSE': mse,
        'RMSE': rmse,
        'MAE': mae,
        'R²': r2,
        'MAPE': mape
    }


def main():
    print("=" * 60)
    print("生成差异化预测结果数据")
    print("=" * 60)
    
    # 生成三种不同的基础数据（对应三个数据集）
    datasets = {
        'weather': generate_base_signal(1000),
        'stock': generate_base_signal(800),
        'sensor': generate_base_signal(1200),
    }
    
    # 定义不同模型的配置
    # (模型名, 版本, 目标R², 精度标签, 模型特性)
    model_configs = [
        # 高精度模型
        ('LSTM', '1.0', 0.95, 'high', {'lag': 1}),
        ('Transformer', '1.0', 0.92, 'high', {'noisy': True}),
        ('TCN', '1.0', 0.90, 'high', {'periodic_error': True}),
        ('GRU', '1.0', 0.88, 'high', {'lag': 2}),
        
        # 中等精度模型
        ('LSTM', '1.0', 0.75, 'medium', {'lag': 3, 'bias': 0.1}),
        ('Transformer', '2.0', 0.70, 'medium', {'poor_trend': True}),
        ('XGBoost', '1.0', 0.65, 'medium', {'slow_response': True}),
        ('Autoformer', '1.0', 0.60, 'medium', {'periodic_error': True, 'lag': 2}),
        
        # 低精度模型
        ('TCN', '1.0', 0.45, 'low', {'noisy': True, 'bias': -0.2}),
        ('Prophet', '1.0', 0.35, 'low', {'poor_trend': True, 'slow_response': True}),
    ]
    
    # 特殊测试数据
    special_configs = [
        # 完美预测（用于测试边界情况）
        ('perfect_prediction', None, 0.999, 'perfect', {}),
        # 随机预测（很差的模型）
        ('random_prediction', None, 0.10, 'random', {'noisy': True, 'bias': 0.5}),
        # 大规模数据
        ('large_scale', None, 0.80, 'large', {}),
    ]
    
    print("\n生成标准预测结果...")
    print("-" * 60)
    
    results_summary = []
    
    for dataset_name, true_values in datasets.items():
        print(f"\n数据集: {dataset_name}")
        
        for model_name, version, r2_target, accuracy, characteristics in model_configs:
            # 生成预测
            predictions = generate_prediction(true_values, r2_target, characteristics)
            
            # 计算实际指标
            metrics = calculate_metrics(true_values, predictions)
            
            # 保存文件
            df = pd.DataFrame({
                'true_value': np.round(true_values, 4),
                'predicted_value': np.round(predictions, 4)
            })
            
            filename = f"result_{dataset_name}_{model_name}_v{version}_{accuracy}.csv"
            filepath = os.path.join(OUTPUT_DIR, filename)
            df.to_csv(filepath, index=False)
            
            results_summary.append({
                'dataset': dataset_name,
                'model': model_name,
                'version': version,
                'accuracy': accuracy,
                'R²': metrics['R²'],
                'RMSE': metrics['RMSE'],
                'filename': filename
            })
            
            print(f"  {model_name} v{version} ({accuracy}): R²={metrics['R²']:.4f}, RMSE={metrics['RMSE']:.2f}")
    
    # 生成特殊测试数据
    print("\n生成特殊测试数据...")
    print("-" * 60)
    
    # 完美预测
    true_values = datasets['weather']
    perfect_pred = true_values + np.random.normal(0, 0.01, len(true_values))
    df = pd.DataFrame({
        'true_value': np.round(true_values, 4),
        'predicted_value': np.round(perfect_pred, 4)
    })
    df.to_csv(os.path.join(OUTPUT_DIR, 'result_perfect_prediction.csv'), index=False)
    metrics = calculate_metrics(true_values, perfect_pred)
    print(f"  完美预测: R²={metrics['R²']:.4f}")
    
    # 随机预测
    random_pred = np.random.normal(np.mean(true_values), np.std(true_values) * 1.5, len(true_values))
    df = pd.DataFrame({
        'true_value': np.round(true_values, 4),
        'predicted_value': np.round(random_pred, 4)
    })
    df.to_csv(os.path.join(OUTPUT_DIR, 'result_random_prediction.csv'), index=False)
    metrics = calculate_metrics(true_values, random_pred)
    print(f"  随机预测: R²={metrics['R²']:.4f}")
    
    # 大规模数据
    large_true = generate_base_signal(10000)
    large_pred = generate_prediction(large_true, 0.80, {'lag': 2})
    df = pd.DataFrame({
        'true_value': np.round(large_true, 4),
        'predicted_value': np.round(large_pred, 4)
    })
    df.to_csv(os.path.join(OUTPUT_DIR, 'result_large_scale.csv'), index=False)
    metrics = calculate_metrics(large_true, large_pred)
    print(f"  大规模数据 (10000点): R²={metrics['R²']:.4f}")
    
    # 打印汇总
    print("\n" + "=" * 60)
    print("生成完成！文件保存在:", os.path.abspath(OUTPUT_DIR))
    print("=" * 60)
    
    print("\nR² 分布统计:")
    r2_values = [r['R²'] for r in results_summary]
    print(f"  最小值: {min(r2_values):.4f}")
    print(f"  最大值: {max(r2_values):.4f}")
    print(f"  平均值: {np.mean(r2_values):.4f}")
    print(f"  标准差: {np.std(r2_values):.4f}")
    
    print("\n按精度级别分布:")
    for accuracy in ['high', 'medium', 'low']:
        r2_acc = [r['R²'] for r in results_summary if r['accuracy'] == accuracy]
        if r2_acc:
            print(f"  {accuracy}: R² 范围 [{min(r2_acc):.2f}, {max(r2_acc):.2f}]")


if __name__ == '__main__':
    main()

