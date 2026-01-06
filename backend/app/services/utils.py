import numpy as np
from typing import List, Tuple


def lttb_downsample(data: List[Tuple[float, float]], threshold: int) -> List[Tuple[float, float]]:
    """LTTB降采样算法 - 修复：添加边界检查防止除零"""
    if threshold <= 2:
        threshold = 3  # 最小采样点数
    
    if len(data) <= threshold:
        return data
    
    sampled = [data[0]]
    bucket_size = (len(data) - 2) / (threshold - 2)
    
    for i in range(threshold - 2):
        bucket_start = int((i + 1) * bucket_size) + 1
        bucket_end = int((i + 2) * bucket_size) + 1
        bucket_end = min(bucket_end, len(data) - 1)
        
        if bucket_start >= bucket_end:
            continue
            
        avg_x = np.mean([p[0] for p in data[bucket_start:bucket_end]])
        avg_y = np.mean([p[1] for p in data[bucket_start:bucket_end]])
        
        prev_point = sampled[-1]
        max_area = -1
        max_point = None
        
        range_start = int(i * bucket_size) + 1
        range_end = bucket_start
        
        for j in range(range_start, range_end):
            area = abs((prev_point[0] - avg_x) * (data[j][1] - prev_point[1]) -
                      (prev_point[0] - data[j][0]) * (avg_y - prev_point[1])) * 0.5
            if area > max_area:
                max_area = area
                max_point = data[j]
        
        if max_point:
            sampled.append(max_point)
    
    sampled.append(data[-1])
    return sampled


def calculate_metrics(true_values: np.ndarray, pred_values: np.ndarray) -> dict:
    """计算评估指标"""
    if len(true_values) == 0 or len(pred_values) == 0:
        return {"mse": 0.0, "rmse": 0.0, "mae": 0.0, "r2": 0.0, "mape": 0.0}
    
    mse = float(np.mean((true_values - pred_values) ** 2))
    rmse = float(np.sqrt(mse))
    mae = float(np.mean(np.abs(true_values - pred_values)))
    
    ss_res = np.sum((true_values - pred_values) ** 2)
    ss_tot = np.sum((true_values - np.mean(true_values)) ** 2)
    r2 = float(1 - (ss_res / ss_tot)) if ss_tot != 0 else 0.0
    
    mask = true_values != 0
    if np.any(mask):
        mape = float(np.mean(np.abs((true_values[mask] - pred_values[mask]) / true_values[mask])) * 100)
    else:
        mape = 0.0
    
    return {"mse": mse, "rmse": rmse, "mae": mae, "r2": r2, "mape": mape}


def generate_standard_filename(dataset_name: str, channels: List[str], normalization: str,
                               anomaly_enabled: bool, anomaly_type: str, injection_algorithm: str,
                               sequence_logic: str, window_size: int, stride: int,
                               target_type: str, target_k: int = 1) -> str:
    """生成标准文件名 - 修复：使用真实通道名而非索引"""
    parts = [dataset_name]
    
    # 修复：直接使用通道名，而非enumerate索引
    if channels:
        ch_str = "Ch_" + "-".join(channels)
        parts.append(ch_str)
    
    parts.append(f"Win{window_size}")
    parts.append(f"Str{stride}")
    
    norm_map = {"none": "NoNorm", "minmax": "MinMax", "zscore": "ZScore", "head": "Head", "decimal": "Decimal"}
    parts.append(norm_map.get(normalization, "NoNorm"))
    
    if anomaly_enabled and anomaly_type:
        type_map = {"point": "AnoP", "segment": "AnoS", "trend": "AnoT", "seasonal": "AnoSe", "noise": "AnoN"}
        parts.append(type_map.get(anomaly_type, "AnoX"))
        
        alg_map = {"random": "Rand", "rule": "Rule", "pattern": "Patt"}
        if injection_algorithm:
            parts.append(alg_map.get(injection_algorithm, ""))
        
        seq_map = {"anomaly_first": "AF", "window_first": "WF"}
        if sequence_logic:
            parts.append(seq_map.get(sequence_logic, ""))
    
    target_map = {"next": "PredN", "kstep": f"PredK{target_k}", "reconstruct": "Recon"}
    parts.append(target_map.get(target_type, "PredN"))
    
    # 过滤空字符串
    parts = [p for p in parts if p]
    
    return "_".join(parts) + ".csv"


def count_csv_rows(filepath: str) -> int:
    """高效统计CSV行数 - 不读入内存"""
    count = 0
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for _ in f:
            count += 1
    return max(0, count - 1)  # 减去表头
