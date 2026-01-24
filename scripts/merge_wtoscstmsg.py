"""
全量合并 wtoscstmsg 数据集（风机/回路故障与振荡事件日志）
- 按 STARTTIME（事件开始时间）排序
- 不做任何数据清洗
- 生成一个完整文件
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 配置
SOURCE_DIR = Path(r"E:\待处理数据\wtoscstmsg")
OUTPUT_DIR = SOURCE_DIR / "wtoscstmsg_merged"
OUTPUT_FILE = OUTPUT_DIR / "wtoscstmsg_all.csv"

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
    print("全量合并 wtoscstmsg 数据集（风机/回路故障与振荡事件日志）")
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
    
    # 按 STARTTIME 排序
    print("\n按 STARTTIME（事件开始时间）排序...")
    try:
        merged_df['STARTTIME'] = pd.to_datetime(merged_df['STARTTIME'])
        merged_df = merged_df.sort_values('STARTTIME').reset_index(drop=True)
        print(f"  排序完成: {len(merged_df):,} 行")
        print(f"  STARTTIME 范围: {merged_df['STARTTIME'].min()} ~ {merged_df['STARTTIME'].max()}")
    except Exception as e:
        print(f"  ⚠️  排序时出现问题: {e}")
        print(f"  将保存未排序的数据")
    
    # 保存文件
    print("\n保存文件...")
    # 确保时间格式完整保存（包含时分秒）
    if 'STARTTIME' in merged_df.columns:
        merged_df['STARTTIME'] = merged_df['STARTTIME'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
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
    
    if 'STARTTIME' in merged_df.columns:
        try:
            print(f"\nSTARTTIME 范围: {merged_df['STARTTIME'].min()} ~ {merged_df['STARTTIME'].max()}")
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
    
    # 显示 WTID 分布（前10个）
    if 'WTID' in merged_df.columns:
        print("\nWTID 分布（前10个）:")
        wtid_counts = merged_df['WTID'].value_counts().head(10)
        for wtid, count in wtid_counts.items():
            pct = (count / len(merged_df)) * 100
            print(f"  WTID {wtid}: {count:,} ({pct:.2f}%)")
        
        total_wtid = merged_df['WTID'].nunique()
        print(f"\n  总共 {total_wtid} 个不同的 WTID")
    
    # 显示 FAULTNAME 分布（前10个）
    if 'FAULTNAME' in merged_df.columns:
        print("\nFAULTNAME 分布（前10个）:")
        fault_counts = merged_df['FAULTNAME'].value_counts().head(10)
        for fault_name, count in fault_counts.items():
            pct = (count / len(merged_df)) * 100
            print(f"  {fault_name}: {count:,} ({pct:.2f}%)")
    
    # 显示 OSCNAME 分布（前10个）
    if 'OSCNAME' in merged_df.columns:
        print("\nOSCNAME 分布（前10个）:")
        osc_counts = merged_df['OSCNAME'].value_counts().head(10)
        for osc_name, count in osc_counts.items():
            pct = (count / len(merged_df)) * 100
            print(f"  {osc_name}: {count:,} ({pct:.2f}%)")
    
    print(f"\n输出文件: {OUTPUT_FILE}")
    print("="*80)
    print("\n📋 排序说明：")
    print("  - 按 STARTTIME（事件开始时间）排序")
    print("  - 所有事件按时间顺序排列，便于时序分析")
    print("="*80)


if __name__ == "__main__":
    try:
        merge_all()
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()

