import numpy as np
from typing import List, Tuple


def lttb_downsample(data: List[Tuple[float, float]], threshold: int) -> List[Tuple[float, float]]:
    if len(data) <= threshold:
        return data
    
    sampled = [data[0]]
    bucket_size = (len(data) - 2) / (threshold - 2)
    
    for i in range(threshold - 2):
        bucket_start = int((i + 1) * bucket_size) + 1
        bucket_end = int((i + 2) * bucket_size) + 1
        bucket_end = min(bucket_end, len(data) - 1)
        
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
    n = len(true_values)
    mse = np.mean((true_values - pred_values) ** 2)
    rmse = np.sqrt(mse)
    mae = np.mean(np.abs(true_values - pred_values))
    
    ss_res = np.sum((true_values - pred_values) ** 2)
    ss_tot = np.sum((true_values - np.mean(true_values)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
    
    mask = true_values != 0
    if np.any(mask):
        mape = np.mean(np.abs((true_values[mask] - pred_values[mask]) / true_values[mask])) * 100
    else:
        mape = 0
    
    return {"mse": float(mse), "rmse": float(rmse), "mae": float(mae), "r2": float(r2), "mape": float(mape)}


def generate_standard_filename(dataset_name: str, channels: List[str], normalization: str,
                               anomaly_enabled: bool, anomaly_type: str, injection_algorithm: str,
                               sequence_logic: str, window_size: int, stride: int,
                               target_type: str, target_k: int = 1) -> str:
    parts = [dataset_name]
    
    if channels:
        ch_str = "Ch" + "-".join([str(i) for i, _ in enumerate(channels)])
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
    
    return "_".join(parts) + ".csv"
