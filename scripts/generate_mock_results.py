"""
为每个数据集生成模拟预测结果
每个数据集生成2份结果：一个高质量预测，一个低质量预测
"""
import pandas as pd
import numpy as np
from pathlib import Path

# 配置
TEST_DIR = Path(__file__).parent.parent / "test"
OUTPUT_DIR = TEST_DIR

# 设置随机种子
np.random.seed(42)


def add_noise(values, noise_level):
    """添加噪声到预测值"""
    noise = np.random.normal(0, noise_level * np.std(values), len(values))
    return values + noise


def generate_predictions_for_station50():
    """为 station50_baseinfo 生成预测结果 - 目标列: thopower"""
    print("=" * 60)
    print("生成 station50_baseinfo 的预测结果 (目标: thopower)")
    print("=" * 60)
    
    # 读取原始数据
    df = pd.read_csv(TEST_DIR / "station50_baseinfo_complete.csv")
    print(f"读取数据: {len(df)} 行")
    
    # 使用 thopower 作为真实值（不采样，保持完整）
    true_values = df['thopower'].values
    
    # 高质量预测 (LSTM模型，噪声小)
    pred_high = add_noise(true_values, 0.05)  # 5% 噪声
    pred_high = np.clip(pred_high, 0, None)  # 确保非负
    
    result_high = pd.DataFrame({
        'datetime': df['datetime'],
        'thopower': true_values,
        'predicted_value': pred_high
    })
    
    # 低质量预测 (Baseline模型，噪声大 + 系统偏差)
    pred_low = add_noise(true_values * 0.85, 0.25)  # 系统性低估15% + 25% 噪声
    pred_low = np.clip(pred_low, 0, None)
    
    result_low = pd.DataFrame({
        'datetime': df['datetime'],
        'thopower': true_values,
        'predicted_value': pred_low
    })
    
    # 保存
    file_high = OUTPUT_DIR / "result_station50_LSTM_v1.0_high.csv"
    file_low = OUTPUT_DIR / "result_station50_Baseline_v1.0_low.csv"
    
    result_high.to_csv(file_high, index=False)
    result_low.to_csv(file_low, index=False)
    
    print(f"✅ 高质量结果: {file_high.name} ({len(result_high)} 行)")
    print(f"✅ 低质量结果: {file_low.name} ({len(result_low)} 行)")
    print()


def generate_predictions_for_windturbine55():
    """为 windturbine55_day 生成预测结果 - 目标列: quantity"""
    print("=" * 60)
    print("生成 windturbine55_day 的预测结果 (目标: quantity)")
    print("=" * 60)
    
    # 读取原始数据
    df = pd.read_csv(TEST_DIR / "windturbine55_day_powergeneration_complete.csv")
    print(f"读取数据: {len(df)} 行")
    
    # 使用 quantity 作为真实值（填充缺失值而不是删除）
    df['quantity'] = df['quantity'].fillna(df['quantity'].mean())
    true_values = df['quantity'].values
    
    # 高质量预测 (Transformer模型，噪声小)
    pred_high = add_noise(true_values, 0.08)  # 8% 噪声
    pred_high = np.clip(pred_high, 0, None)
    
    result_high = pd.DataFrame({
        'datetime': df['datetime'],
        'quantity': true_values,
        'predicted_value': pred_high
    })
    
    # 低质量预测 (简单平均模型，噪声大 + 滞后)
    # 使用移动平均模拟滞后效应
    pred_low = np.roll(true_values, 1)  # 滞后1天
    pred_low[0] = true_values[0]  # 第一个值保持不变
    pred_low = add_noise(pred_low, 0.30)  # 30% 噪声
    pred_low = np.clip(pred_low, 0, None)
    
    result_low = pd.DataFrame({
        'datetime': df['datetime'],
        'quantity': true_values,
        'predicted_value': pred_low
    })
    
    # 保存
    file_high = OUTPUT_DIR / "result_windturbine55_Transformer_v1.0_high.csv"
    file_low = OUTPUT_DIR / "result_windturbine55_MovingAvg_v1.0_low.csv"
    
    result_high.to_csv(file_high, index=False)
    result_low.to_csv(file_low, index=False)
    
    print(f"✅ 高质量结果: {file_high.name} ({len(result_high)} 行)")
    print(f"✅ 低质量结果: {file_low.name} ({len(result_low)} 行)")
    print()


def generate_predictions_for_short():
    """为 powerforecast_short 生成预测结果 - 目标列: actualvalue"""
    print("=" * 60)
    print("生成 powerforecast_short 的预测结果 (目标: actualvalue)")
    print("=" * 60)
    
    # 读取原始数据
    df = pd.read_csv(TEST_DIR / "powerforecast_short_station41_actual_complete.csv")
    print(f"读取数据: {len(df)} 行")
    
    # 填充缺失值（用中位数），不删除行
    df['actualvalue'] = df['actualvalue'].fillna(df['actualvalue'].median())
    
    # 使用 actualvalue 作为真实值
    true_values = df['actualvalue'].values
    
    # 高质量预测 (GRU模型，噪声小)
    pred_high = add_noise(true_values, 0.10)  # 10% 噪声
    pred_high = np.clip(pred_high, 0, None)  # 确保非负
    
    result_high = pd.DataFrame({
        'actualvaluetime': df['actualvaluetime'],
        'actualvalue': true_values,
        'predicted_value': pred_high
    })
    
    # 低质量预测 (持续性预测，噪声大)
    # 使用前一个时刻的值作为预测
    pred_low = np.roll(true_values, 1)
    pred_low[0] = true_values[0]
    pred_low = add_noise(pred_low, 0.35)  # 35% 噪声
    pred_low = np.clip(pred_low, 0, None)  # 确保非负
    
    result_low = pd.DataFrame({
        'actualvaluetime': df['actualvaluetime'],
        'actualvalue': true_values,
        'predicted_value': pred_low
    })
    
    # 保存
    file_high = OUTPUT_DIR / "result_short_GRU_v1.0_high.csv"
    file_low = OUTPUT_DIR / "result_short_Persistence_v1.0_low.csv"
    
    result_high.to_csv(file_high, index=False)
    result_low.to_csv(file_low, index=False)
    
    print(f"✅ 高质量结果: {file_high.name} ({len(result_high)} 行)")
    print(f"✅ 低质量结果: {file_low.name} ({len(result_low)} 行)")
    print()


def generate_predictions_for_weather():
    """为 powerforecast_weatherdata 生成预测结果 - 目标列: temperature"""
    print("=" * 60)
    print("生成 powerforecast_weatherdata 的预测结果 (目标: temperature)")
    print("=" * 60)
    
    # 读取原始数据
    df = pd.read_csv(TEST_DIR / "powerforecast_weatherdata_station41_complete.csv")
    print(f"读取数据: {len(df)} 行")
    
    # 使用 temperature 作为真实值（不采样，保持完整）
    true_values = df['temperature'].values
    
    # 高质量预测 (深度学习模型，噪声小)
    pred_high = add_noise(true_values, 0.03)  # 3% 噪声
    
    result_high = pd.DataFrame({
        'datatime': df['datatime'],
        'temperature': true_values,
        'predicted_value': pred_high
    })
    
    # 低质量预测 (线性回归，噪声大 + 趋势偏差)
    # 添加趋势偏差
    trend = np.linspace(0, 2, len(true_values))  # 逐渐增加的偏差
    pred_low = true_values + trend
    pred_low = add_noise(pred_low, 0.15)  # 15% 噪声
    
    result_low = pd.DataFrame({
        'datatime': df['datatime'],
        'temperature': true_values,
        'predicted_value': pred_low
    })
    
    # 保存
    file_high = OUTPUT_DIR / "result_weather_DeepLearning_v1.0_high.csv"
    file_low = OUTPUT_DIR / "result_weather_LinearReg_v1.0_low.csv"
    
    result_high.to_csv(file_high, index=False)
    result_low.to_csv(file_low, index=False)
    
    print(f"✅ 高质量结果: {file_high.name} ({len(result_high)} 行)")
    print(f"✅ 低质量结果: {file_low.name} ({len(result_low)} 行)")
    print()


def calculate_metrics(true_values, pred_values):
    """计算评估指标"""
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    
    mae = mean_absolute_error(true_values, pred_values)
    rmse = np.sqrt(mean_squared_error(true_values, pred_values))
    r2 = r2_score(true_values, pred_values)
    
    # MAPE (处理零值)
    mask = true_values != 0
    if mask.sum() > 0:
        mape = np.mean(np.abs((true_values[mask] - pred_values[mask]) / true_values[mask])) * 100
    else:
        mape = 0
    
    return {
        'MAE': mae,
        'RMSE': rmse,
        'R²': r2,
        'MAPE': mape
    }


def generate_summary():
    """生成所有结果的性能对比"""
    print("=" * 60)
    print("生成性能对比报告")
    print("=" * 60)
    
    results = []
    
    # 读取所有结果文件
    result_files = list(OUTPUT_DIR.glob("result_*.csv"))
    
    for file in result_files:
        df = pd.read_csv(file)
        
        # 第二列是真实值，第三列是预测值
        if len(df.columns) >= 3:
            true_col = df.columns[1]
            pred_col = df.columns[2]
            
            metrics = calculate_metrics(df[true_col].values, df[pred_col].values)
            
            results.append({
                '数据集': file.stem.replace('result_', ''),
                'MAE': f"{metrics['MAE']:.4f}",
                'RMSE': f"{metrics['RMSE']:.4f}",
                'R²': f"{metrics['R²']:.4f}",
                'MAPE': f"{metrics['MAPE']:.2f}%",
                '记录数': len(df)
            })
    
    # 创建对比表
    summary_df = pd.DataFrame(results)
    summary_file = OUTPUT_DIR / "results_performance_summary.csv"
    summary_df.to_csv(summary_file, index=False, encoding='utf-8-sig')
    
    print("\n性能对比:")
    print(summary_df.to_string(index=False))
    print(f"\n✅ 性能对比报告已保存: {summary_file.name}")


if __name__ == "__main__":
    try:
        print("\n" + "=" * 60)
        print("开始生成模拟预测结果")
        print("=" * 60)
        print()
        
        # 生成各数据集的预测结果
        generate_predictions_for_station50()
        generate_predictions_for_windturbine55()
        generate_predictions_for_short()
        generate_predictions_for_weather()
        
        # 生成性能对比
        generate_summary()
        
        print("\n" + "=" * 60)
        print("✅ 所有预测结果生成完成！")
        print("=" * 60)
        print(f"\n共生成 8 个预测结果文件 + 1 个性能对比报告")
        print(f"保存位置: {OUTPUT_DIR}")
        
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()

