"""
生成简单的性能对比报告（不依赖sklearn）
"""
import pandas as pd
import numpy as np
from pathlib import Path

TEST_DIR = Path(__file__).parent.parent / "test"

def calculate_metrics_simple(true_values, pred_values):
    """计算评估指标（不使用sklearn）"""
    # MAE
    mae = np.mean(np.abs(true_values - pred_values))
    
    # RMSE
    rmse = np.sqrt(np.mean((true_values - pred_values) ** 2))
    
    # R²
    ss_res = np.sum((true_values - pred_values) ** 2)
    ss_tot = np.sum((true_values - np.mean(true_values)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
    
    # MAPE
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

print("=" * 60)
print("生成性能对比报告")
print("=" * 60)

results = []

# 读取所有结果文件
result_files = sorted(TEST_DIR.glob("result_*.csv"))

for file in result_files:
    df = pd.read_csv(file)
    
    # 第二列是真实值，第三列是预测值
    if len(df.columns) >= 3:
        true_col = df.columns[1]
        pred_col = df.columns[2]
        
        metrics = calculate_metrics_simple(df[true_col].values, df[pred_col].values)
        
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
summary_file = TEST_DIR / "results_performance_summary.csv"
summary_df.to_csv(summary_file, index=False, encoding='utf-8-sig')

print("\n性能对比:")
print(summary_df.to_string(index=False))
print(f"\n✅ 性能对比报告已保存: {summary_file.name}")


