"""
全量合并 all_day_powergeneration 数据集
- 只按时间排序
- 不做任何数据清洗
- 动态列检测（处理多版本表头）
- 生成一个完整文件
"""
import pandas as pd
from pathlib import Path
from datetime import datetime

# 配置
SOURCE_DIR = Path(r"E:\待处理数据\all_day_powergeneration")
OUTPUT_DIR = SOURCE_DIR / "all_day_powergeneration_merged"
OUTPUT_FILE = OUTPUT_DIR / "all_day_powergeneration_full.csv"

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
    print("开始全量合并 all_day_powergeneration 数据集")
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
    
    # 第一步：收集所有可能的列
    print("第一步：收集所有列名...")
    all_columns = set()
    file_columns = {}
    
    for i, file_path in enumerate(csv_files, 1):
        file_name = file_path.name
        try:
            encoding = detect_encoding(file_path)
            df = pd.read_csv(file_path, encoding=encoding, nrows=0)  # 只读表头
            columns = df.columns.tolist()
            all_columns.update(columns)
            file_columns[file_name] = columns
            print(f"  [{i}/{len(csv_files)}] {file_name} - {len(columns)} 列")
        except Exception as e:
            print(f"  [{i}/{len(csv_files)}] {file_name} - ❌ 错误: {e}")
    
    all_columns = sorted(all_columns)
    print(f"\n✅ 共发现 {len(all_columns)} 个不同的列")
    print(f"所有列: {all_columns}")
    print()
    
    # 第二步：读取并合并数据
    print("第二步：读取并合并数据...")
    all_data = []
    
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
            
            all_data.append(df)
            print(f"  [{i}/{len(csv_files)}] {file_name} - {len(df):,} 行")
        
        except Exception as e:
            print(f"  [{i}/{len(csv_files)}] {file_name} - ❌ 错误: {e}")
    
    if not all_data:
        print("\n❌ 没有可合并的数据")
        return
    
    print(f"\n✅ 读取完成，共 {len(all_data)} 个文件")
    print()
    
    # 第三步：合并所有数据
    print("第三步：合并所有数据...")
    merged_df = pd.concat(all_data, ignore_index=True)
    print(f"  合并后: {len(merged_df):,} 行")
    
    # 第四步：按时间排序
    print("\n第四步：按时间排序...")
    merged_df['datetime'] = pd.to_datetime(merged_df['datetime'])
    merged_df = merged_df.sort_values('datetime').reset_index(drop=True)
    print(f"  排序完成: {len(merged_df):,} 行")
    print(f"  时间范围: {merged_df['datetime'].min()} ~ {merged_df['datetime'].max()}")
    
    # 第五步：保存文件
    print("\n第五步：保存文件...")
    # 确保时间格式完整保存（包含时分秒）
    if 'datetime' in merged_df.columns:
        merged_df['datetime'] = merged_df['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    merged_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    
    file_size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"  ✅ 已保存: {OUTPUT_FILE.name}")
    print(f"  文件大小: {file_size_mb:.2f} MB")
    
    # 统计信息
    print("\n" + "="*80)
    print("合并完成！统计信息：")
    print("="*80)
    print(f"总记录数: {len(merged_df):,} 行")
    print(f"总列数: {len(all_columns)} 列")
    print(f"时间范围: {merged_df['datetime'].min()} ~ {merged_df['datetime'].max()}")
    print(f"输出文件: {OUTPUT_FILE}")
    print("="*80)
    
    # 显示列信息
    print("\n列信息:")
    for col in all_columns:
        non_null = merged_df[col].notna().sum()
        null_count = merged_df[col].isna().sum()
        null_pct = (null_count / len(merged_df)) * 100
        print(f"  {col}: {non_null:,} 非空, {null_count:,} 空值 ({null_pct:.1f}%)")


if __name__ == "__main__":
    try:
        merge_all()
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()

