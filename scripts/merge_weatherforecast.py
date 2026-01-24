"""
全量合并 powerforecast_fd_weatherforecast 数据集
- 只按时间排序
- 不做任何数据清洗
- 生成一个完整文件
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 配置
SOURCE_DIR = Path(r"E:\待处理数据\powerforecast_fd_weatherforecast")
OUTPUT_DIR = SOURCE_DIR / "powerforecast_fd_weatherforecast_merged"
OUTPUT_FILE = OUTPUT_DIR / "powerforecast_fd_weatherforecast_full.csv"

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


def merge_all():
    """全量合并数据"""
    print("="*80)
    print("开始全量合并 powerforecast_fd_weatherforecast 数据集")
    print("="*80)
    print(f"源目录: {SOURCE_DIR}")
    print(f"输出文件: {OUTPUT_FILE}")
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
    
    # 读取并合并数据
    print("开始读取并合并数据...")
    all_data = []
    error_count = 0
    
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
            
            all_data.append(df)
            
            # 每10个文件或最后一个文件显示进度
            if i % 10 == 0 or i == len(csv_files):
                print(f"  [{i}/{len(csv_files)}] {file_name} - {len(df):,} 行")
        
        except Exception as e:
            print(f"  [{i}/{len(csv_files)}] {file_name} - ❌ 错误: {e}")
            error_count += 1
    
    if not all_data:
        print("\n❌ 没有可合并的数据")
        return
    
    print(f"\n✅ 读取完成，成功读取 {len(all_data)} 个文件")
    if error_count > 0:
        print(f"⚠️  {error_count} 个文件读取失败")
    print()
    
    # 合并所有数据
    print("合并所有数据...")
    merged_df = pd.concat(all_data, ignore_index=True)
    print(f"  合并后: {len(merged_df):,} 行")
    
    # 显示列信息
    print(f"  列数: {len(merged_df.columns)}")
    print(f"  列名: {merged_df.columns.tolist()}")
    
    # 按时间排序
    print("\n按时间排序...")
    try:
        merged_df['datatime'] = pd.to_datetime(merged_df['datatime'])
        merged_df = merged_df.sort_values('datatime').reset_index(drop=True)
        print(f"  排序完成: {len(merged_df):,} 行")
        print(f"  时间范围: {merged_df['datatime'].min()} ~ {merged_df['datatime'].max()}")
    except Exception as e:
        print(f"  ⚠️  排序时出现问题: {e}")
        print(f"  将保存未排序的数据")
    
    # 保存文件
    print("\n保存文件...")
    # 确保时间格式完整保存（包含时分秒）
    if 'datatime' in merged_df.columns:
        merged_df['datatime'] = merged_df['datatime'].dt.strftime('%Y-%m-%d %H:%M:%S')
    if 'forecast_fromtime' in merged_df.columns:
        merged_df['forecast_fromtime'] = pd.to_datetime(merged_df['forecast_fromtime'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
    
    merged_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    
    file_size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"  ✅ 已保存: {OUTPUT_FILE.name}")
    print(f"  文件大小: {file_size_mb:.2f} MB")
    
    # 统计信息
    print("\n" + "="*80)
    print("合并完成！统计信息：")
    print("="*80)
    print(f"总记录数: {len(merged_df):,} 行")
    print(f"总列数: {len(merged_df.columns)} 列")
    print(f"列名: {merged_df.columns.tolist()}")
    
    if 'datatime' in merged_df.columns:
        try:
            print(f"时间范围: {merged_df['datatime'].min()} ~ {merged_df['datatime'].max()}")
        except:
            pass
    
    # 显示各列的空值统计
    print("\n空值统计:")
    null_found = False
    for col in merged_df.columns:
        null_count = merged_df[col].isna().sum()
        if null_count > 0:
            null_pct = (null_count / len(merged_df)) * 100
            print(f"  {col}: {null_count:,} ({null_pct:.2f}%)")
            null_found = True
    if not null_found:
        print("  无空值 ✅")
    
    # 显示 stationid 分布
    if 'stationid' in merged_df.columns:
        print("\nstationid 分布:")
        station_counts = merged_df['stationid'].value_counts().sort_index()
        for station_id, count in station_counts.items():
            pct = (count / len(merged_df)) * 100
            print(f"  stationid {station_id}: {count:,} ({pct:.2f}%)")
    
    # 显示 forecast_fromtime 分布（前10个）
    if 'forecast_fromtime' in merged_df.columns:
        print("\nforecast_fromtime 分布（前10个）:")
        forecast_counts = merged_df['forecast_fromtime'].value_counts().head(10)
        for forecast_time, count in forecast_counts.items():
            print(f"  {forecast_time}: {count:,} 条记录")
    
    print(f"\n输出文件: {OUTPUT_FILE}")
    print("="*80)


if __name__ == "__main__":
    try:
        merge_all()
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()

