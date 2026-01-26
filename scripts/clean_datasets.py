"""
清理 test 文件夹中所有数据集的无效值和异常值
"""
import pandas as pd
import numpy as np
from pathlib import Path

TEST_DIR = Path(__file__).parent.parent / "test"

def clean_dataset(file_path, target_column):
    """清理数据集"""
    print(f"\n处理: {file_path.name}")
    df = pd.read_csv(file_path)
    original_count = len(df)
    print(f"  原始行数: {original_count}")
    
    # 1. 删除目标列的缺失值
    df = df.dropna(subset=[target_column])
    print(f"  删除缺失值后: {len(df)} 行 (删除 {original_count - len(df)} 行)")
    
    # 2. 删除无穷值
    df = df[np.isfinite(df[target_column])]
    print(f"  删除无穷值后: {len(df)} 行")
    
    # 3. 删除极端异常值（超过均值±5倍标准差）
    mean_val = df[target_column].mean()
    std_val = df[target_column].std()
    lower_bound = mean_val - 5 * std_val
    upper_bound = mean_val + 5 * std_val
    
    before_outlier = len(df)
    df = df[(df[target_column] >= lower_bound) & (df[target_column] <= upper_bound)]
    print(f"  删除极端异常值后: {len(df)} 行 (删除 {before_outlier - len(df)} 行)")
    
    # 4. 重置索引
    df = df.reset_index(drop=True)
    
    # 5. 保存清理后的数据
    df.to_csv(file_path, index=False)
    print(f"  ✅ 已保存，最终行数: {len(df)}")
    
    # 6. 统计信息
    print(f"  目标列 '{target_column}' 统计:")
    print(f"    最小值: {df[target_column].min():.4f}")
    print(f"    最大值: {df[target_column].max():.4f}")
    print(f"    平均值: {df[target_column].mean():.4f}")
    print(f"    标准差: {df[target_column].std():.4f}")
    
    return len(df)

print("=" * 60)
print("开始清理 test 文件夹中的数据集")
print("=" * 60)

# 清理各个数据集
datasets = [
    ("station50_baseinfo_complete.csv", "thopower"),
    ("windturbine55_day_powergeneration_complete.csv", "quantity"),
    ("powerforecast_short_station41_actual_complete.csv", "actualvalue"),
    ("powerforecast_weatherdata_station41_complete.csv", "temperature")
]

results = {}
for filename, target_col in datasets:
    file_path = TEST_DIR / filename
    if file_path.exists():
        final_count = clean_dataset(file_path, target_col)
        results[filename] = final_count
    else:
        print(f"\n⚠️  文件不存在: {filename}")

print("\n" + "=" * 60)
print("清理完成汇总")
print("=" * 60)
for filename, count in results.items():
    print(f"  {filename}: {count:,} 行")

print("\n✅ 所有数据集已清理完成！")




