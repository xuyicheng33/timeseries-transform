"""
按月合并 all_baseinfo 数据集
- 只按时间排序
- 不做任何数据清洗
- 每个月生成一个文件
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import os

# 配置
SOURCE_DIR = Path(r"E:\待处理数据\all_baseinfo")
OUTPUT_DIR = SOURCE_DIR / "all_baseinfo_merged"

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


def merge_by_month():
    """按月合并数据"""
    print("="*80)
    print("开始按月合并 all_baseinfo 数据集")
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
    
    # 按月分组存储数据
    monthly_data = {}
    
    # 逐个读取文件
    print("开始读取文件...")
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
            
            # 转换时间列
            df['datetime'] = pd.to_datetime(df['datetime'])
            
            # 按月分组
            for month_key, group in df.groupby(df['datetime'].dt.to_period('M')):
                month_str = str(month_key)  # 格式：2024-12
                
                if month_str not in monthly_data:
                    monthly_data[month_str] = []
                
                monthly_data[month_str].append(group)
            
            if i % 20 == 0 or i <= 10:
                print(f"  [{i}/{len(csv_files)}] {file_name} - {len(df):,} 行")
        
        except Exception as e:
            print(f"  [{i}/{len(csv_files)}] {file_name} - ❌ 错误: {e}")
    
    print(f"\n✅ 读取完成，共 {len(monthly_data)} 个月的数据")
    print()
    
    # 合并并保存每个月的数据
    print("开始合并并保存...")
    for month_str in sorted(monthly_data.keys()):
        print(f"\n处理月份: {month_str}")
        
        # 合并该月所有数据
        month_df = pd.concat(monthly_data[month_str], ignore_index=True)
        print(f"  合并前: {len(month_df):,} 行")
        
        # 按时间排序
        month_df = month_df.sort_values('datetime').reset_index(drop=True)
        print(f"  排序完成: {len(month_df):,} 行")
        
        # 保存文件
        output_file = OUTPUT_DIR / f"all_baseinfo_{month_str}.csv"
        # 确保时间格式完整保存（包含时分秒）
        if 'datetime' in month_df.columns:
            month_df['datetime'] = month_df['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        month_df.to_csv(output_file, index=False, encoding='utf-8')
        
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"  ✅ 已保存: {output_file.name} ({file_size_mb:.2f} MB)")
        print(f"  时间范围: {month_df['datetime'].min()} ~ {month_df['datetime'].max()}")
    
    print("\n" + "="*80)
    print("合并完成！")
    print("="*80)
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"生成文件数: {len(monthly_data)} 个")
    
    # 统计总结
    total_rows = sum(len(pd.concat(data, ignore_index=True)) for data in monthly_data.values())
    print(f"总记录数: {total_rows:,} 行")
    print("="*80)


if __name__ == "__main__":
    try:
        merge_by_month()
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()

