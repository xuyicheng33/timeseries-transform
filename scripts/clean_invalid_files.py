"""
清理无效文件：
1. 删除空文件（只有 Unnamed: 0 列的文件）
2. 删除以 ._ 开头的文件（macOS 系统文件）
"""
import pandas as pd
import os
from pathlib import Path
import chardet

# 数据源目录
SOURCE_DIR = Path(r"E:\待处理数据")

# 统计
stats = {
    "total_files": 0,
    "empty_files_deleted": 0,
    "dot_underscore_files_deleted": 0,
    "errors": []
}

def detect_encoding(file_path, sample_size=10240):
    """检测文件编码"""
    try:
        with open(file_path, 'rb') as f:
            raw = f.read(sample_size)
        result = chardet.detect(raw)
        return result.get('encoding', 'utf-8') or 'utf-8'
    except:
        return 'utf-8'

def is_empty_file(file_path):
    """检查是否为空文件（只有 Unnamed: 0 列）"""
    try:
        encoding = detect_encoding(file_path)
        df = pd.read_csv(file_path, encoding=encoding, nrows=5)
        
        # 检查是否只有一列且列名为 Unnamed: 0
        if len(df.columns) == 1 and df.columns[0] == 'Unnamed: 0':
            return True
        
        return False
    except Exception as e:
        # 如果读取失败，可能是真的空文件或损坏文件
        try:
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return True
        except:
            pass
        return False

def clean_dataset_directory(dataset_dir):
    """清理单个数据集目录"""
    dataset_name = dataset_dir.name
    print(f"\n{'='*80}")
    print(f"清理数据集: {dataset_name}")
    print(f"{'='*80}")
    
    if not dataset_dir.exists():
        print(f"⚠️  目录不存在，跳过")
        return
    
    # 获取所有文件
    all_files = list(dataset_dir.glob("*"))
    csv_files = [f for f in all_files if f.suffix.lower() == '.csv']
    
    print(f"总文件数: {len(all_files)}")
    print(f"CSV文件数: {len(csv_files)}")
    
    deleted_count = 0
    
    # 1. 删除以 ._ 开头的文件
    dot_underscore_files = [f for f in all_files if f.name.startswith('._')]
    if dot_underscore_files:
        print(f"\n发现 {len(dot_underscore_files)} 个 ._ 开头的文件:")
        for file_path in dot_underscore_files:
            try:
                print(f"  删除: {file_path.name}")
                os.remove(file_path)
                stats["dot_underscore_files_deleted"] += 1
                deleted_count += 1
            except Exception as e:
                print(f"  ❌ 删除失败: {e}")
                stats["errors"].append({
                    "file": str(file_path),
                    "error": str(e)
                })
    
    # 2. 检查并删除空文件
    print(f"\n检查空文件...")
    empty_files = []
    
    for i, file_path in enumerate(csv_files, 1):
        if i <= 10 or i % 50 == 0:  # 显示前10个和每50个
            print(f"  [{i}/{len(csv_files)}] 检查: {file_path.name}", end="")
        
        if is_empty_file(file_path):
            empty_files.append(file_path)
            if i <= 10 or i % 50 == 0:
                print(f" -> ⚠️  空文件")
        else:
            if i <= 10 or i % 50 == 0:
                print(f" -> ✅")
    
    if empty_files:
        print(f"\n发现 {len(empty_files)} 个空文件:")
        for file_path in empty_files:
            try:
                print(f"  删除: {file_path.name}")
                os.remove(file_path)
                stats["empty_files_deleted"] += 1
                deleted_count += 1
            except Exception as e:
                print(f"  ❌ 删除失败: {e}")
                stats["errors"].append({
                    "file": str(file_path),
                    "error": str(e)
                })
    else:
        print(f"\n✅ 未发现空文件")
    
    # 统计剩余文件
    remaining_files = len(list(dataset_dir.glob("*.csv")))
    print(f"\n总结:")
    print(f"  删除文件数: {deleted_count}")
    print(f"  剩余CSV文件: {remaining_files}")
    
    return deleted_count

def main():
    """主清理流程"""
    print("="*80)
    print("开始清理无效文件")
    print("="*80)
    print(f"数据源目录: {SOURCE_DIR}")
    print()
    
    # 获取所有数据集目录
    dataset_dirs = [d for d in SOURCE_DIR.iterdir() if d.is_dir()]
    dataset_dirs = sorted(dataset_dirs, key=lambda x: x.name)
    
    print(f"找到 {len(dataset_dirs)} 个数据集目录")
    print()
    
    # 逐个清理
    for dataset_dir in dataset_dirs:
        try:
            stats["total_files"] += len(list(dataset_dir.glob("*")))
            clean_dataset_directory(dataset_dir)
        except Exception as e:
            print(f"\n❌ 清理失败: {e}")
            stats["errors"].append({
                "dataset": dataset_dir.name,
                "error": str(e)
            })
    
    # 最终统计
    print("\n" + "="*80)
    print("清理完成！")
    print("="*80)
    print(f"总文件数: {stats['total_files']}")
    print(f"删除空文件: {stats['empty_files_deleted']}")
    print(f"删除 ._ 文件: {stats['dot_underscore_files_deleted']}")
    print(f"总删除数: {stats['empty_files_deleted'] + stats['dot_underscore_files_deleted']}")
    
    if stats["errors"]:
        print(f"\n⚠️  发生 {len(stats['errors'])} 个错误:")
        for error in stats["errors"][:10]:  # 只显示前10个
            print(f"  - {error.get('file', error.get('dataset', 'unknown'))}: {error['error']}")
        if len(stats["errors"]) > 10:
            print(f"  ... 还有 {len(stats['errors']) - 10} 个错误")
    
    print("\n" + "="*80)
    print("建议：清理完成后，重新运行验证脚本检查文件数是否正确")
    print("="*80)

if __name__ == "__main__":
    # 确认操作
    print("\n⚠️  警告：此操作将删除文件，无法恢复！")
    print("将要删除:")
    print("  1. 所有只有 'Unnamed: 0' 列的空文件")
    print("  2. 所有以 '._' 开头的文件（macOS 系统文件）")
    print()
    
    response = input("确认继续？(输入 yes 继续): ")
    
    if response.lower() == 'yes':
        main()
    else:
        print("操作已取消")

