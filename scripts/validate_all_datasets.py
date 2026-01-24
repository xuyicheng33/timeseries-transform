"""
全面验证所有23个数据集
对比报告描述与实际数据，找出所有差异
"""
import pandas as pd
import os
from pathlib import Path
from datetime import datetime
import json
import chardet

# 数据源目录
SOURCE_DIR = Path(r"E:\待处理数据")

# 验证结果
validation_results = {
    "validation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "total_datasets": 23,
    "datasets": {}
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

def validate_dataset(dataset_name, expected_info):
    """验证单个数据集"""
    print(f"\n{'='*80}")
    print(f"验证数据集: {dataset_name}")
    print(f"{'='*80}")
    
    dataset_dir = SOURCE_DIR / dataset_name
    
    # 检查目录是否存在
    if not dataset_dir.exists():
        print(f"❌ 目录不存在: {dataset_dir}")
        return {
            "status": "error",
            "error": "目录不存在"
        }
    
    # 获取所有CSV文件
    csv_files = sorted([f for f in dataset_dir.glob("*.csv")])
    
    if not csv_files:
        print(f"⚠️  目录中没有CSV文件")
        return {
            "status": "warning",
            "warning": "没有CSV文件"
        }
    
    print(f"✅ 找到 {len(csv_files)} 个CSV文件")
    
    result = {
        "status": "success",
        "file_count": len(csv_files),
        "sampled_files": [],
        "columns_found": {},
        "time_range": {},
        "issues": [],
        "quality_stats": {}
    }
    
    # 抽样验证（前3个、中间2个、最后3个）
    if len(csv_files) <= 8:
        sample_files = csv_files
    else:
        mid = len(csv_files) // 2
        sample_files = csv_files[:3] + csv_files[mid-1:mid+1] + csv_files[-3:]
    
    print(f"📊 抽样验证 {len(sample_files)} 个文件...")
    
    all_columns_sets = []
    time_values = []
    
    for i, file_path in enumerate(sample_files, 1):
        file_name = file_path.name
        print(f"\n  [{i}/{len(sample_files)}] {file_name}")
        
        try:
            # 检测编码
            encoding = detect_encoding(file_path)
            
            # 读取文件（只读前100行用于快速验证）
            df = pd.read_csv(file_path, encoding=encoding, nrows=100)
            
            # 记录列名
            columns = df.columns.tolist()
            all_columns_sets.append(set(columns))
            
            print(f"      列数: {len(columns)}")
            print(f"      列名: {columns[:5]}{'...' if len(columns) > 5 else ''}")
            
            # 记录到结果
            result["sampled_files"].append({
                "file": file_name,
                "columns": columns,
                "column_count": len(columns),
                "row_count_sample": len(df),
                "encoding": encoding
            })
            
            # 尝试提取时间信息
            time_cols = [col for col in columns if 'time' in col.lower() or 'date' in col.lower()]
            if time_cols:
                for time_col in time_cols[:1]:  # 只取第一个时间列
                    try:
                        time_series = pd.to_datetime(df[time_col])
                        if not time_series.isna().all():
                            time_values.extend(time_series.dropna().tolist())
                            print(f"      时间列: {time_col}")
                            print(f"      时间范围: {time_series.min()} ~ {time_series.max()}")
                    except:
                        pass
            
            # 检查特殊值
            for col in columns:
                if df[col].dtype in ['float64', 'int64']:
                    # 检查-1值
                    neg_one_count = (df[col] == -1).sum()
                    if neg_one_count > 0:
                        print(f"      ⚠️  {col}: 发现 {neg_one_count} 个 -1 值")
                    
                    # 检查0值
                    zero_count = (df[col] == 0).sum()
                    if zero_count > len(df) * 0.5:  # 超过50%
                        print(f"      ⚠️  {col}: {zero_count} 个 0 值 ({zero_count/len(df)*100:.1f}%)")
                    
                    # 检查NaN
                    nan_count = df[col].isna().sum()
                    if nan_count > 0:
                        print(f"      ⚠️  {col}: {nan_count} 个 NaN 值 ({nan_count/len(df)*100:.1f}%)")
            
        except Exception as e:
            print(f"      ❌ 读取失败: {str(e)}")
            result["issues"].append({
                "file": file_name,
                "error": str(e)
            })
    
    # 分析列的一致性
    if len(all_columns_sets) > 1:
        # 检查是否所有文件列名一致
        first_cols = all_columns_sets[0]
        all_same = all(cols == first_cols for cols in all_columns_sets)
        
        if all_same:
            print(f"\n✅ 所有抽样文件列名一致")
            result["columns_found"]["consistent"] = True
            result["columns_found"]["columns"] = list(first_cols)
        else:
            print(f"\n⚠️  发现多版本表头！")
            result["columns_found"]["consistent"] = False
            
            # 找出所有不同的列集合
            unique_column_sets = []
            for cols in all_columns_sets:
                if cols not in unique_column_sets:
                    unique_column_sets.append(cols)
            
            print(f"   共发现 {len(unique_column_sets)} 种不同的列组合:")
            for idx, cols in enumerate(unique_column_sets, 1):
                print(f"   版本{idx}: {sorted(cols)}")
            
            # 找出差异列
            all_cols = set()
            for cols in all_columns_sets:
                all_cols.update(cols)
            
            common_cols = set.intersection(*all_columns_sets)
            diff_cols = all_cols - common_cols
            
            print(f"\n   共同列 ({len(common_cols)}): {sorted(common_cols)}")
            print(f"   差异列 ({len(diff_cols)}): {sorted(diff_cols)}")
            
            result["columns_found"]["versions"] = [list(cols) for cols in unique_column_sets]
            result["columns_found"]["common_columns"] = list(common_cols)
            result["columns_found"]["diff_columns"] = list(diff_cols)
            
            result["issues"].append({
                "type": "multiple_versions",
                "description": f"发现{len(unique_column_sets)}种不同的列组合",
                "diff_columns": list(diff_cols)
            })
    
    # 时间范围统计
    if time_values:
        result["time_range"]["min"] = str(min(time_values))
        result["time_range"]["max"] = str(max(time_values))
        print(f"\n📅 整体时间范围: {result['time_range']['min']} ~ {result['time_range']['max']}")
    
    return result


# 定义所有23个数据集及其预期信息
DATASETS = {
    "all_baseinfo": {
        "expected_files": 211,
        "expected_columns": ["datetime", "pvthopower", "wpthopower"],
        "time_range": "20241211-20250709",
        "granularity": "分钟级"
    },
    "all_day_powergeneration": {
        "expected_files": 9,
        "expected_columns": ["datetime", "allproducequantity", "allselfusequantity"],
        "time_range": "202411-202507",
        "granularity": "日度"
    },
    "all_thopower": {
        "expected_files": 12,
        "expected_columns": ["datetime", "pvthopower", "wpthopower"],
        "time_range": "20241130-20241211",
        "granularity": "分钟级"
    },
    "bay_day_powergeneration": {
        "expected_files": 9,
        "expected_columns": ["datetime", "bayid", "quantity"],
        "time_range": "202411-202507",
        "granularity": "日度"
    },
    "computeschedule": {
        "expected_files": 2,
        "expected_columns": ["totalanalogid", "computedatetime"],
        "time_range": "2024-12-12 ~ 2025-07-09",
        "granularity": "批次快照"
    },
    "his_node": {
        "expected_files": 5,
        "expected_columns": ["hostname", "lastUpdateTime"],
        "time_range": "2024-10-17 ~ 2025-07-09",
        "granularity": "监控采样"
    },
    "hisaccumulator": {
        "expected_files": 24,
        "expected_columns": ["SAVETIME", "ACCUMULATORID"],
        "time_range": "20240101-20241109",
        "granularity": "记录"
    },
    "hisagcavcstation": {
        "expected_files": 1,
        "expected_columns": ["stationid", "savetime"],
        "time_range": "2024-11-25 ~ 2024-12-26",
        "granularity": "参数快照"
    },
    "hisstsgbatst": {
        "expected_files": 2,
        "expected_columns": ["id", "savetime", "todayinpt"],
        "time_range": "2024-11-21 ~ 2025-07-09",
        "granularity": "日度统计"
    },
    "hisstsgbatstation": {
        "expected_files": 2,
        "expected_columns": ["id", "savetime", "todayinpt"],
        "time_range": "2024-11-21 ~ 2025-07-09",
        "granularity": "日度统计"
    },
    "inverter_day_powergeneration": {
        "expected_files": 9,
        "expected_columns": ["datetime", "devid", "accumulatorid", "quantity"],
        "time_range": "202411-202507",
        "granularity": "日度"
    },
    "powerforecast_fd_weatherdata": {
        "expected_files": 211,
        "expected_columns": ["id", "savetime", "datatime", "temperature"],
        "time_range": "20241025-20250709",
        "granularity": "5分钟"
    },
    "powerforecast_fd_weatherforecast": {
        "expected_files": 187,
        "expected_columns": ["id", "savetime", "datatime", "temperature"],
        "time_range": "20241202-20250709",
        "granularity": "15分钟"
    },
    "powerforecast_powerstat": {
        "expected_files": 10,
        "expected_columns": ["id", "savetime", "statistictime"],
        "time_range": "202410-202507",
        "granularity": "统计"
    },
    "powerforecast_short": {
        "expected_files": 199,
        "expected_columns": ["id", "savetime", "forecastvaluetime"],
        "time_range": "20241026-20250709",
        "granularity": "15分钟"
    },
    "powerforecast_ultrashort": {
        "expected_files": 210,
        "expected_columns": ["id", "savetime", "forecast_fromtime"],
        "time_range": "20241026-20250709",
        "granularity": "16步预测"
    },
    "station_baseinfo": {
        "expected_files": 211,
        "expected_columns": ["datetime", "stationid", "thopower", "aevwindspeed"],
        "time_range": "20241211-20250709",
        "granularity": "分钟级"
    },
    "station_day_powergeneration": {
        "expected_files": 9,
        "expected_columns": ["datetime", "stationid", "producequantity"],
        "time_range": "202411-202507",
        "granularity": "日度"
    },
    "station_thopower": {
        "expected_files": 12,
        "expected_columns": ["datetime", "stationid", "thopower"],
        "time_range": "20241130-20241211",
        "granularity": "分钟级"
    },
    "windturbine_1min_windspeed": {
        "expected_files": 223,
        "expected_columns": ["datetime", "devid", "analog_id", "aevwindspeed"],
        "time_range": "20241129-20250709",
        "granularity": "1分钟"
    },
    "windturbine_day_powergeneration": {
        "expected_files": 9,
        "expected_columns": ["datetime", "devid", "accumulatorid", "quantity"],
        "time_range": "202411-202507",
        "granularity": "日度"
    },
    "windturbine_statusstat": {
        "expected_files": 3,
        "expected_columns": ["windturbineid", "stattime", "savetime"],
        "time_range": "2024-12 ~ 2025-07",
        "granularity": "月度/年度"
    },
    "wtoscstmsg": {
        "expected_files": 7,
        "expected_columns": ["id", "WTNAME", "STARTTIME"],
        "time_range": "202407-202507",
        "granularity": "事件记录"
    }
}


def main():
    """主验证流程"""
    print("="*80)
    print("开始全面验证所有23个数据集")
    print("="*80)
    print(f"数据源目录: {SOURCE_DIR}")
    print(f"验证时间: {validation_results['validation_time']}")
    print()
    
    # 逐个验证
    for dataset_name, expected_info in DATASETS.items():
        result = validate_dataset(dataset_name, expected_info)
        validation_results["datasets"][dataset_name] = result
        
        # 对比预期
        print(f"\n📋 对比预期信息:")
        print(f"   预期文件数: {expected_info['expected_files']}")
        print(f"   实际文件数: {result.get('file_count', 0)}")
        
        if result.get('file_count', 0) != expected_info['expected_files']:
            print(f"   ⚠️  文件数不匹配！")
            result["issues"].append({
                "type": "file_count_mismatch",
                "expected": expected_info['expected_files'],
                "actual": result.get('file_count', 0)
            })
    
    # 保存验证结果
    output_file = Path(__file__).parent.parent / "data_validation_results" / f"validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(validation_results, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*80)
    print("验证完成！")
    print("="*80)
    print(f"结果已保存到: {output_file}")
    
    # 统计汇总
    total = len(validation_results["datasets"])
    success = sum(1 for r in validation_results["datasets"].values() if r["status"] == "success")
    with_issues = sum(1 for r in validation_results["datasets"].values() if r.get("issues"))
    
    print(f"\n📊 验证汇总:")
    print(f"   总数据集: {total}")
    print(f"   验证成功: {success}")
    print(f"   发现问题: {with_issues}")
    
    # 列出所有有问题的数据集
    if with_issues > 0:
        print(f"\n⚠️  有问题的数据集:")
        for dataset_name, result in validation_results["datasets"].items():
            if result.get("issues"):
                print(f"\n   {dataset_name}:")
                for issue in result["issues"]:
                    print(f"      - {issue.get('type', 'unknown')}: {issue.get('description', issue.get('error', 'N/A'))}")


if __name__ == "__main__":
    main()

