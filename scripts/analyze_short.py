"""
分析 powerforecast_short 数据结构
"""
import pandas as pd
from pathlib import Path

# 读取一个有数据的文件
file = Path("d:/Desktop/platform/timeseries-platform/data_for_platform/powerforecast_short_20241121.csv")

print("=" * 60)
print("分析 powerforecast_short 数据结构")
print("=" * 60)

# 读取数据
df = pd.read_csv(file, encoding='utf-8')

print(f"\n文件: {file.name}")
print(f"总行数: {len(df)}")
print(f"\n列名:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i}. {col}")

print(f"\n前5行数据:")
print(df.head().to_string())

print(f"\n数据类型:")
print(df.dtypes)

# 检查 stationid 列
if 'stationid' in df.columns:
    print(f"\n唯一的 stationid:")
    print(sorted(df['stationid'].unique()))
    print(f"\nstationid=50 的数据量: {len(df[df['stationid'] == 50])}")

print("\n" + "=" * 60)

