"""
按 stationid 分组合并 station_thopower 数据集
- 每个 stationid 生成一个独立文件
- 按 datetime（时间）排序
- 不做任何数据清洗
- 动态列检测（处理多版本表头，部分文件缺少 aevwindspeed 列）
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 配置
SOURCE_DIR = Path(r"E:\待处理数据\station_thopower")
OUTPUT_DIR = SOURCE_DIR / "station_thopower_merged"

def detect_encoding(file_path, sample_size=10240):
    """检测文件编码"""
    import chardet
    try:
        with open(file_path, 'rb') as f:
            raw = f.read(sample_size)
        result = chardet.detect(raw)
        return result.get('encoding', 'utf-8') or 'utf-8'
    except:
        return 'utf-8'


def merge_by_stationid():
    """按 stationid 分组合并数据"""
    print("="*80)
    print("按 stationid 分组合并 station_thopower 数据集")
    print("="*80)
    print(f"源目录: {SOURCE_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print()
    
    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 获取所有CSV文件
    csv_files = sorted(SOURCE_DIR.glob("*.csv"))
    
    if not csv_files:
        print("❌ 未找到CSV文件")
        return
    
    print(f"✅ 找到 {len(csv_files)} 个CSV文件")
    print()
    
    # 第一步：收集所有可能的列
    print("第一步：收集所有列名...")
    all_columns = set()
    
    for i, file_path in enumerate(csv_files, 1):
        file_name = file_path.name
        try:
            encoding = detect_encoding(file_path)
            df = pd.read_csv(file_path, encoding=encoding, nrows=0)  # 只读表头
            columns = df.columns.tolist()
            all_columns.update(columns)
            print(f"  [{i}/{len(csv_files)}] {file_name} - {len(columns)} 列: {columns}")
        except Exception as e:
            print(f"  [{i}/{len(csv_files)}] {file_name} - ❌ 错误: {e}")
    
    all_columns = sorted(all_columns)
    print(f"\n✅ 共发现 {len(all_columns)} 个不同的列")
    print(f"所有列: {all_columns}")
    print()
    
    # 第二步：读取数据并按 stationid 分组
    print("第二步：读取数据并按 stationid 分组...")
    stationid_data = {}  # {stationid: [df1, df2, ...]}
    
    for i, file_path in enumerate(csv_files, 1):
        file_name = file_path.name
        
        try:
            # 检测编码
            encoding = detect_encoding(file_path)
            
            # 读取文件
            df = pd.read_csv(file_path, encoding=encoding)
            
            if len(df) == 0:
                print(f"  [{i}/{len(csv_files)}] {file_name} - 空文件，跳过")
                continue
            
            # 补充缺失的列（填充为 NaN）
            for col in all_columns:
                if col not in df.columns:
                    df[col] = pd.NA
            
            # 按统一顺序排列列
            df = df[all_columns]
            
            # 按 stationid 分组
            for stationid, group in df.groupby('stationid'):
                if stationid not in stationid_data:
                    stationid_data[stationid] = []
                stationid_data[stationid].append(group)
            
            print(f"  [{i}/{len(csv_files)}] {file_name} - {len(df):,} 行, {df['stationid'].nunique()} 个 stationid")
        
        except Exception as e:
            print(f"  [{i}/{len(csv_files)}] {file_name} - ❌ 错误: {e}")
    
    if not stationid_data:
        print("\n❌ 没有可合并的数据")
        return
    
    print(f"\n✅ 读取完成，共 {len(stationid_data)} 个不同的 stationid")
    print()
    
    # 第三步：合并并保存每个 stationid 的数据
    print("第三步：合并并保存每个 stationid 的数据...")
    
    for idx, stationid in enumerate(sorted(stationid_data.keys()), 1):
        # 合并该 stationid 的所有数据
        stationid_df = pd.concat(stationid_data[stationid], ignore_index=True)
        
        # 按时间排序
        try:
            stationid_df['datetime'] = pd.to_datetime(stationid_df['datetime'])
            stationid_df = stationid_df.sort_values('datetime').reset_index(drop=True)
        except Exception as e:
            print(f"  ⚠️  stationid {stationid} 排序失败: {e}")
        
        # 保存文件
        output_file = OUTPUT_DIR / f"station_thopower_stationid{stationid}.csv"
        # 确保时间格式完整保存（包含时分秒）
        if 'datetime' in stationid_df.columns:
            stationid_df['datetime'] = stationid_df['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        stationid_df.to_csv(output_file, index=False, encoding='utf-8')
        
        file_size_kb = output_file.stat().st_size / 1024
        
        # 显示进度
        if idx <= 20 or idx % 5 == 0:
            print(f"  [{idx}/{len(stationid_data)}] stationid {stationid}: {len(stationid_df):,} 行, {file_size_kb:.2f} KB")
            try:
                time_min = pd.to_datetime(stationid_df['datetime']).min()
                time_max = pd.to_datetime(stationid_df['datetime']).max()
                print(f"      时间范围: {time_min} ~ {time_max}")
            except:
                pass
    
    # 统计总结
    print("\n" + "="*80)
    print("合并完成！统计信息：")
    print("="*80)
    print(f"总 stationid 数: {len(stationid_data)}")
    print(f"生成文件数: {len(stationid_data)}")
    print(f"输出目录: {OUTPUT_DIR}")
    
    total_rows = sum(len(pd.concat(data, ignore_index=True)) for data in stationid_data.values())
    print(f"总记录数: {total_rows:,} 行")
    
    print("\nstationid 统计（前20个）:")
    for idx, stationid in enumerate(sorted(stationid_data.keys())[:20], 1):
        row_count = len(pd.concat(stationid_data[stationid], ignore_index=True))
        print(f"  {idx}. stationid {stationid}: {row_count:,} 行")
    
    if len(stationid_data) > 20:
        print(f"  ... 还有 {len(stationid_data) - 20} 个 stationid")
    
    print("="*80)
    print("\n📋 排序说明：")
    print("  - 按 datetime（时间）字段排序")
    print("  - 每个 stationid 生成独立的 CSV 文件")
    print("  - 自动处理多版本表头（部分文件缺少 aevwindspeed 列）")
    print("="*80)


if __name__ == "__main__":
    try:
        merge_by_stationid()
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()

