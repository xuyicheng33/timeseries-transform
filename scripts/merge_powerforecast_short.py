"""
合并 powerforecast_short 数据集
只保留实际值相关字段：actualvaluetime, actualvalue, runningcapacity
"""
import pandas as pd
import glob
import os
from pathlib import Path
from datetime import datetime

# 配置
SOURCE_DIR = Path(__file__).parent.parent / "data_for_platform"
OUTPUT_DIR = Path(__file__).parent.parent / "test"
OUTPUT_FILE = OUTPUT_DIR / "powerforecast_short_station41_actual_complete.csv"

# 只保留实际值相关列
KEEP_COLUMNS = ['actualvaluetime', 'actualvalue', 'runningcapacity']
TARGET_STATION_ID = 41


def merge_powerforecast_short():
    """合并所有 powerforecast_short 文件，只保留实际值数据"""
    
    print("=" * 60)
    print("开始合并 powerforecast_short 数据集（仅实际值）")
    print("=" * 60)
    print(f"源目录: {SOURCE_DIR}")
    print(f"目标站点: stationid={TARGET_STATION_ID}")
    print(f"保留列: {', '.join(KEEP_COLUMNS)}")
    print()
    
    # 查找所有文件
    pattern = str(SOURCE_DIR / "powerforecast_short_*.csv")
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
    empty_files = 0
    
    print("开始处理文件...")
    for i, file in enumerate(files, 1):
        filename = Path(file).name
        
        try:
            # 读取文件
            df = pd.read_csv(file, encoding='utf-8')
            total_rows += len(df)
            
            # 检查是否为空文件
            if len(df) == 0:
                empty_files += 1
                if i <= 10 or i % 50 == 0:  # 只显示前10个和每50个
                    print(f"⚠️  [{i}/{len(files)}] {filename} - 空文件")
                continue
            
            # 检查必需列是否存在
            if 'stationid' not in df.columns:
                print(f"⚠️  [{i}/{len(files)}] {filename} - 缺少 stationid 列，跳过")
                error_files.append((filename, "缺少 stationid 列"))
                continue
            
            # 筛选 stationid=41
            df_filtered = df[df['stationid'] == TARGET_STATION_ID].copy()
            
            if len(df_filtered) > 0:
                # 只保留存在的列
                existing_cols = [col for col in KEEP_COLUMNS if col in df_filtered.columns]
                if not existing_cols:
                    print(f"⚠️  [{i}/{len(files)}] {filename} - 缺少所需列，跳过")
                    error_files.append((filename, "缺少所需列"))
                    continue
                
                df_filtered = df_filtered[existing_cols]
                all_data.append(df_filtered)
                filtered_rows += len(df_filtered)
                
                if i <= 10 or i % 50 == 0:  # 只显示前10个和每50个
                    print(f"✅ [{i}/{len(files)}] {filename} - {len(df_filtered):,} 行")
            else:
                if i <= 10:  # 只显示前10个
                    print(f"⚠️  [{i}/{len(files)}] {filename} - 无 stationid={TARGET_STATION_ID} 数据")
            
        except Exception as e:
            print(f"❌ [{i}/{len(files)}] {filename} - 错误: {str(e)}")
            error_files.append((filename, str(e)))
    
    print(f"\n处理完成，共处理 {len(files)} 个文件，其中 {empty_files} 个空文件")
    
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
    
    # 转换 actualvaluetime 列为时间类型
    print("\n处理时间列...")
    try:
        merged_df['actualvaluetime'] = pd.to_datetime(merged_df['actualvaluetime'])
        print("✅ 时间列转换成功")
    except Exception as e:
        print(f"⚠️  时间列转换失败: {e}")
    
    # 按时间排序
    print("\n按时间排序...")
    merged_df = merged_df.sort_values('actualvaluetime').reset_index(drop=True)
    print("✅ 排序完成")
    
    # 去重（保留最后一条记录）
    print("\n检查重复数据...")
    duplicates = merged_df.duplicated(subset=['actualvaluetime'], keep='last').sum()
    if duplicates > 0:
        print(f"⚠️  发现 {duplicates:,} 条重复记录，正在删除...")
        merged_df = merged_df.drop_duplicates(subset=['actualvaluetime'], keep='last')
        print(f"✅ 去重后剩余 {len(merged_df):,} 行")
    else:
        print("✅ 无重复数据")
    
    # 数据质量报告
    print("\n" + "=" * 60)
    print("数据质量报告")
    print("=" * 60)
    print(f"时间范围: {merged_df['actualvaluetime'].min()} 至 {merged_df['actualvaluetime'].max()}")
    print(f"总记录数: {len(merged_df):,} 行")
    print()
    
    print("各列统计信息:")
    print("-" * 60)
    for col in KEEP_COLUMNS:
        if col not in merged_df.columns:
            continue
        if col == 'actualvaluetime':
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
                # 统计负值
                if col == 'actualvalue':
                    negative_count = (valid_data < 0).sum()
                    print(f"    负值数量: {negative_count:,} ({negative_count/len(valid_data)*100:.2f}%)")
    
    # 保存文件
    print("\n" + "=" * 60)
    print("保存文件...")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    merged_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    
    file_size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"✅ 文件已保存: {OUTPUT_FILE}")
    print(f"   文件大小: {file_size_mb:.2f} MB")
    
    # 错误汇总
    if error_files:
        print("\n" + "=" * 60)
        print(f"⚠️  处理失败的文件 ({len(error_files)} 个):")
        print("=" * 60)
        for filename, error in error_files[:10]:  # 只显示前10个
            print(f"  - {filename}: {error}")
        if len(error_files) > 10:
            print(f"  ... 还有 {len(error_files) - 10} 个文件")
    
    # 统计汇总
    print("\n" + "=" * 60)
    print("处理完成！")
    print("=" * 60)
    print(f"✅ 处理文件数: {len(files)}")
    print(f"✅ 空文件数: {empty_files}")
    print(f"✅ 原始总行数: {total_rows:,}")
    print(f"✅ 筛选后行数: {filtered_rows:,}")
    print(f"✅ 最终输出行数: {len(merged_df):,}")
    print(f"✅ 输出文件: {OUTPUT_FILE.name}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        merge_powerforecast_short()
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()

