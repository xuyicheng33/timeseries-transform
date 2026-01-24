"""
分析验证结果，提取所有差异
"""
import json
from pathlib import Path

# 读取最新的验证结果
result_dir = Path(__file__).parent.parent / "data_validation_results"
result_files = sorted(result_dir.glob("validation_results_*.json"))
latest_file = result_files[-1]

print(f"读取验证结果: {latest_file.name}")
print("="*80)

with open(latest_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"\n验证时间: {data['validation_time']}")
print(f"总数据集: {data['total_datasets']}")
print("\n" + "="*80)
print("开始分析所有差异...")
print("="*80)

# 统计
total_datasets = len(data['datasets'])
datasets_with_issues = 0
datasets_with_version_issues = 0
datasets_with_file_count_mismatch = 0

all_differences = []

for dataset_name, result in data['datasets'].items():
    issues = result.get('issues', [])
    
    if issues:
        datasets_with_issues += 1
        
        print(f"\n{'='*80}")
        print(f"数据集: {dataset_name}")
        print(f"{'='*80}")
        print(f"文件数: {result.get('file_count', 'N/A')}")
        print(f"状态: {result.get('status', 'N/A')}")
        
        # 列一致性
        columns_info = result.get('columns_found', {})
        if not columns_info.get('consistent', True):
            datasets_with_version_issues += 1
            print(f"\n⚠️  发现多版本表头问题！")
            
            versions = columns_info.get('versions', [])
            print(f"   版本数: {len(versions)}")
            
            common_cols = columns_info.get('common_columns', [])
            diff_cols = columns_info.get('diff_columns', [])
            
            print(f"\n   共同列 ({len(common_cols)}):")
            print(f"   {common_cols}")
            
            print(f"\n   差异列 ({len(diff_cols)}):")
            print(f"   {diff_cols}")
            
            print(f"\n   各版本详情:")
            for idx, version_cols in enumerate(versions, 1):
                print(f"   版本{idx} ({len(version_cols)}列): {version_cols}")
            
            all_differences.append({
                "dataset": dataset_name,
                "type": "多版本表头",
                "versions": len(versions),
                "diff_columns": diff_cols
            })
        
        # 其他问题
        print(f"\n问题列表 ({len(issues)}个):")
        for idx, issue in enumerate(issues, 1):
            issue_type = issue.get('type', 'unknown')
            print(f"\n   [{idx}] 类型: {issue_type}")
            
            if issue_type == 'file_count_mismatch':
                datasets_with_file_count_mismatch += 1
                print(f"       预期文件数: {issue.get('expected', 'N/A')}")
                print(f"       实际文件数: {issue.get('actual', 'N/A')}")
                
                all_differences.append({
                    "dataset": dataset_name,
                    "type": "文件数不匹配",
                    "expected": issue.get('expected'),
                    "actual": issue.get('actual')
                })
            
            elif issue_type == 'multiple_versions':
                print(f"       描述: {issue.get('description', 'N/A')}")
                print(f"       差异列: {issue.get('diff_columns', [])}")
            
            else:
                print(f"       描述: {issue.get('description', issue.get('error', 'N/A'))}")
                if 'file' in issue:
                    print(f"       文件: {issue['file']}")
        
        # 时间范围
        time_range = result.get('time_range', {})
        if time_range:
            print(f"\n时间范围:")
            print(f"   最小: {time_range.get('min', 'N/A')}")
            print(f"   最大: {time_range.get('max', 'N/A')}")

# 总结
print("\n" + "="*80)
print("验证总结")
print("="*80)
print(f"总数据集数: {total_datasets}")
print(f"有问题的数据集: {datasets_with_issues}")
print(f"  - 多版本表头: {datasets_with_version_issues}")
print(f"  - 文件数不匹配: {datasets_with_file_count_mismatch}")

print("\n" + "="*80)
print("所有差异汇总")
print("="*80)

if all_differences:
    print(f"\n共发现 {len(all_differences)} 处差异:\n")
    
    for idx, diff in enumerate(all_differences, 1):
        print(f"{idx}. 数据集: {diff['dataset']}")
        print(f"   差异类型: {diff['type']}")
        
        if diff['type'] == '多版本表头':
            print(f"   版本数: {diff['versions']}")
            print(f"   差异列: {diff['diff_columns']}")
        elif diff['type'] == '文件数不匹配':
            print(f"   预期: {diff['expected']} 个文件")
            print(f"   实际: {diff['actual']} 个文件")
        print()
else:
    print("\n✅ 未发现任何差异！所有数据集与报告描述完全一致。")

print("="*80)
print("分析完成！")
print("="*80)

