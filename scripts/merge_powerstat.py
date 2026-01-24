"""
按 stationid 分组合并 powerforecast_powerstat 数据集
- 每个 stationid 生成一个独立文件
- 按 statistictime（统计时间）排序
- 不做任何数据清洗
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 配置
SOURCE_DIR = Path(r"E:\待处理数据\powerforecast_powerstat")
OUTPUT_DIR = SOURCE_DIR / "powerforecast_powerstat_merged"

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
    print("按 stationid 分组合并 powerforecast_powerstat 数据集")
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
    
    # 读取数据并按 stationid 分组
    print("读取数据并按 stationid 分组...")
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
    
    # 合并并保存每个 stationid 的数据
    print("合并并保存每个 stationid 的数据...")
    
    for idx, stationid in enumerate(sorted(stationid_data.keys()), 1):
        # 合并该 stationid 的所有数据
        stationid_df = pd.concat(stationid_data[stationid], ignore_index=True)
        
        # 按 statistictime 排序
        try:
            stationid_df['statistictime'] = pd.to_datetime(stationid_df['statistictime'])
            stationid_df = stationid_df.sort_values('statistictime').reset_index(drop=True)
        except Exception as e:
            print(f"  ⚠️  stationid {stationid} 排序失败: {e}")
        
        # 保存文件
        output_file = OUTPUT_DIR / f"powerforecast_powerstat_stationid{stationid}.csv"
        # 确保时间格式完整保存（包含时分秒）
        if 'statistictime' in stationid_df.columns:
            stationid_df['statistictime'] = stationid_df['statistictime'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        stationid_df.to_csv(output_file, index=False, encoding='utf-8')
        
        file_size_kb = output_file.stat().st_size / 1024
        
        # 显示进度
        if idx <= 20 or idx % 10 == 0:
            print(f"  [{idx}/{len(stationid_data)}] stationid {stationid}: {len(stationid_df):,} 行, {file_size_kb:.2f} KB")
            try:
                print(f"      时间范围: {stationid_df['statistictime'].min()} ~ {stationid_df['statistictime'].max()}")
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
    print("  - 按 statistictime（统计时间）字段排序")
    print("  - 每个 stationid 生成独立的 CSV 文件")
    print("="*80)


if __name__ == "__main__":
    try:
        merge_by_stationid()
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()

