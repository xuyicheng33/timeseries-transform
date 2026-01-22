"""
合并 windturbine_day_powergeneration 数据集
筛选 devid=55 的数据
"""
import pandas as pd
import glob
import os
from pathlib import Path
from datetime import datetime

# 配置
SOURCE_DIR = Path(__file__).parent.parent / "data_for_platform"
OUTPUT_DIR = Path(__file__).parent.parent / "test_datasets"
OUTPUT_FILE = OUTPUT_DIR / "windturbine55_day_powergeneration_complete.csv"

# 所有列
ALL_COLUMNS = ['datetime', 'devid', 'accumulatorid', 'quantity', 'performquantity', 'effecthour', 'lostquant']
TARGET_DEV_ID = 55


def merge_windturbine_day():
    """合并所有 windturbine_day_powergeneration 文件，筛选 devid=55"""
    
    print("=" * 60)
    print("开始合并 windturbine_day_powergeneration 数据集")
    print("=" * 60)
    print(f"源目录: {SOURCE_DIR}")
    print(f"目标设备: devid={TARGET_DEV_ID}")
    print(f"保留列: {', '.join(ALL_COLUMNS)}")
    print()
    
    # 查找所有文件
    pattern = str(SOURCE_DIR / "windturbine_day_powergeneration_*.csv")
    files = sorted(glob.glob(pattern))
    
    if not files:
        print(f"❌ 未找到文件: {pattern}")
        return
    
    print(f"✅ 找到 {len(files)} 个文件")
    print(f"   时间范围: {Path(files[0]).stem.split('_')[-1]} - {Path(files[-1]).stem.split('_')[-1]}")
    print()
    
    # 逐个读取并合并
    all_data = []
    total_rows = 0
    filtered_rows = 0
    error_files = []
    
    print("开始处理文件...")
    for i, file in enumerate(files, 1):
        filename = Path(file).name
        
        try:
            # 读取文件
            df = pd.read_csv(file, encoding='utf-8')
            total_rows += len(df)
            
            # 检查必需列是否存在
            if 'datetime' not in df.columns or 'devid' not in df.columns:
                print(f"⚠️  [{i}/{len(files)}] {filename} - 缺少必需列，跳过")
                error_files.append((filename, "缺少必需列"))
                continue
            
            # 筛选 devid=55
            df_filtered = df[df['devid'] == TARGET_DEV_ID].copy()
            
            if len(df_filtered) > 0:
                # 只保留存在的列
                existing_cols = [col for col in ALL_COLUMNS if col in df_filtered.columns]
                df_filtered = df_filtered[existing_cols]
                
                all_data.append(df_filtered)
                filtered_rows += len(df_filtered)
                print(f"✅ [{i}/{len(files)}] {filename} - {len(df_filtered):,} 行")
            else:
                print(f"⚠️  [{i}/{len(files)}] {filename} - 无 devid={TARGET_DEV_ID} 数据")
            
        except Exception as e:
            print(f"❌ [{i}/{len(files)}] {filename} - 错误: {str(e)}")
            error_files.append((filename, str(e)))
    
    print()
    print("=" * 60)
    print("数据合并中...")
    print("=" * 60)
    
    if not all_data:
        print("❌ 没有可合并的数据")
        return
    
    # 合并所有数据
    merged_df = pd.concat(all_data, ignore_index=True)
    print(f"✅ 合并完成，共 {len(merged_df):,} 行")
    
    # 转换 datetime 列为时间类型
    print("\n处理时间列...")
    try:
        merged_df['datetime'] = pd.to_datetime(merged_df['datetime'])
        print("✅ 时间列转换成功")
    except Exception as e:
        print(f"⚠️  时间列转换失败: {e}")
    
    # 按时间排序
    print("\n按时间排序...")
    merged_df = merged_df.sort_values('datetime').reset_index(drop=True)
    print("✅ 排序完成")
    
    # 去重
    print("\n检查重复数据...")
    duplicates = merged_df.duplicated(subset=['datetime'], keep='first').sum()
    if duplicates > 0:
        print(f"⚠️  发现 {duplicates:,} 条重复记录，正在删除...")
        merged_df = merged_df.drop_duplicates(subset=['datetime'], keep='first')
        print(f"✅ 去重后剩余 {len(merged_df):,} 行")
    else:
        print("✅ 无重复数据")
    
    # 数据质量报告
    print("\n" + "=" * 60)
    print("数据质量报告")
    print("=" * 60)
    print(f"时间范围: {merged_df['datetime'].min()} 至 {merged_df['datetime'].max()}")
    print(f"总记录数: {len(merged_df):,} 行（{len(merged_df)} 天）")
    print(f"设备ID: {merged_df['devid'].unique()}")
    print()
    
    # 检查日期连续性
    date_range = pd.date_range(start=merged_df['datetime'].min(), 
                                end=merged_df['datetime'].max(), 
                                freq='D')
    missing_dates = set(date_range) - set(merged_df['datetime'])
    if missing_dates:
        print(f"⚠️  缺失日期: {len(missing_dates)} 天")
        if len(missing_dates) <= 10:
            for date in sorted(missing_dates):
                print(f"    - {date.date()}")
    else:
        print("✅ 日期连续，无缺失")
    
    print()
    print("各列统计信息:")
    print("-" * 60)
    for col in merged_df.columns:
        if col in ['datetime', 'devid', 'accumulatorid']:
            continue
        missing = merged_df[col].isna().sum()
        missing_pct = (missing / len(merged_df)) * 100
        print(f"  {col}:")
        print(f"    缺失值: {missing:,} ({missing_pct:.2f}%)")
        if merged_df[col].dtype in ['float64', 'int64']:
            valid_data = merged_df[col].dropna()
            if len(valid_data) > 0:
                print(f"    最小值: {valid_data.min():.4f}")
                print(f"    最大值: {valid_data.max():.4f}")
                print(f"    平均值: {valid_data.mean():.4f}")
                print(f"    总和: {valid_data.sum():.2f}")
    
    # 月度统计
    print("\n" + "=" * 60)
    print("月度统计")
    print("=" * 60)
    merged_df['year_month'] = merged_df['datetime'].dt.to_period('M')
    monthly_stats = merged_df.groupby('year_month').agg({
        'datetime': 'count',
        'quantity': ['sum', 'mean'],
        'effecthour': 'sum'
    }).round(2)
    print(monthly_stats.to_string())
    merged_df = merged_df.drop('year_month', axis=1)
    
    # 保存文件
    print("\n" + "=" * 60)
    print("保存文件...")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    merged_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    
    file_size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"✅ 文件已保存: {OUTPUT_FILE}")
    print(f"   文件大小: {file_size_kb:.2f} KB")
    
    # 错误汇总
    if error_files:
        print("\n" + "=" * 60)
        print(f"⚠️  处理失败的文件 ({len(error_files)} 个):")
        print("=" * 60)
        for filename, error in error_files:
            print(f"  - {filename}: {error}")
    
    # 统计汇总
    print("\n" + "=" * 60)
    print("处理完成！")
    print("=" * 60)
    print(f"✅ 处理文件数: {len(files)}")
    print(f"✅ 原始总行数: {total_rows:,}")
    print(f"✅ 筛选后行数: {filtered_rows:,}")
    print(f"✅ 最终输出行数: {len(merged_df):,}")
    print(f"✅ 输出文件: {OUTPUT_FILE.name}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        merge_windturbine_day()
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()

