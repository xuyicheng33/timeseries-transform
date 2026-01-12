"""
工具函数模块
包含降采样、指标计算、文件处理等通用功能
"""
import csv
import os
import re
import shutil
import numpy as np
from typing import List, Tuple, Optional
from fastapi import HTTPException


# ============ 表单字段校验 ============

def validate_form_field(value: str, field_name: str, max_length: int = 255, 
                        min_length: int = 1, required: bool = True) -> str:
    """
    校验表单字段
    
    Args:
        value: 字段值
        field_name: 字段名称（用于错误提示）
        max_length: 最大长度
        min_length: 最小长度
        required: 是否必填
    
    Returns:
        清理后的字段值
    
    Raises:
        HTTPException: 校验失败时抛出
    """
    # 去除首尾空白
    value = value.strip() if value else ""
    
    # 必填校验
    if required and not value:
        raise HTTPException(status_code=400, detail=f"{field_name}不能为空")
    
    # 非必填且为空，直接返回
    if not required and not value:
        return value
    
    # 长度校验
    if len(value) < min_length:
        raise HTTPException(status_code=400, detail=f"{field_name}长度不能少于{min_length}个字符")
    
    if len(value) > max_length:
        raise HTTPException(status_code=400, detail=f"{field_name}长度不能超过{max_length}个字符")
    
    # 危险字符校验（防止注入）
    # 包含：控制字符、CR、LF、TAB（防止 Header 注入、日志污染、CSV 结构破坏）
    dangerous_pattern = r'[\x00-\x1f\x7f]'  # 所有控制字符（包括 \r\n\t）
    if re.search(dangerous_pattern, value):
        raise HTTPException(status_code=400, detail=f"{field_name}包含非法字符（不允许换行符、制表符等控制字符）")
    
    return value


def validate_description(value: str, max_length: int = 1000) -> str:
    """校验描述字段（允许为空，更长的长度限制）"""
    return validate_form_field(value, "描述", max_length=max_length, min_length=0, required=False)


# ============ 文件名处理 ============

def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符
    用于存储时的文件名净化
    """
    # 移除 Windows 和 Unix 不允许的字符
    # Windows: \ / : * ? " < > |
    # 保留中文、字母、数字、下划线、连字符、点
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', filename)
    # 移除连续的下划线
    safe_name = re.sub(r'_+', '_', safe_name)
    # 移除首尾的下划线和空格
    safe_name = safe_name.strip('_ ')
    # 如果文件名为空，使用默认名
    if not safe_name:
        safe_name = "unnamed_file"
    return safe_name


def sanitize_filename_for_header(filename: str) -> str:
    """
    清理文件名用于 HTTP Header（Content-Disposition）
    更严格的净化，防止 Header 注入
    """
    # 先进行基础净化
    safe_name = sanitize_filename(filename)
    # 移除所有控制字符（包括 \r \n \t）
    safe_name = re.sub(r'[\x00-\x1f\x7f]', '', safe_name)
    # 移除可能导致 Header 注入的字符
    safe_name = re.sub(r'[;\r\n]', '', safe_name)
    # 限制长度（避免过长的文件名）
    if len(safe_name) > 200:
        # 保留扩展名
        name, ext = os.path.splitext(safe_name)
        safe_name = name[:200-len(ext)] + ext
    return safe_name or "download"


def safe_rmtree(path: str) -> bool:
    """安全删除目录，失败时不抛异常"""
    try:
        shutil.rmtree(path, ignore_errors=True)
        return True
    except Exception:
        return False


# ============ 降采样算法 ============

def lttb_downsample(data: List[Tuple[float, float]], threshold: int) -> List[Tuple[float, float]]:
    """LTTB降采样算法 - 保留视觉特征最优"""
    if threshold <= 2:
        threshold = 3
    
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


def minmax_downsample(data: List[Tuple[float, float]], threshold: int) -> List[Tuple[float, float]]:
    """MinMax降采样算法 - 保留每个桶的最大最小值"""
    if threshold <= 2:
        threshold = 4
    
    if len(data) <= threshold:
        return data
    
    # 每个桶保留2个点（min和max），所以桶数是 threshold/2
    num_buckets = threshold // 2
    bucket_size = len(data) / num_buckets
    
    sampled = []
    for i in range(num_buckets):
        start = int(i * bucket_size)
        end = int((i + 1) * bucket_size)
        end = min(end, len(data))
        
        if start >= end:
            continue
        
        bucket = data[start:end]
        min_point = min(bucket, key=lambda p: p[1])
        max_point = max(bucket, key=lambda p: p[1])
        
        # 按x坐标顺序添加
        if min_point[0] <= max_point[0]:
            sampled.append(min_point)
            if min_point != max_point:
                sampled.append(max_point)
        else:
            sampled.append(max_point)
            if min_point != max_point:
                sampled.append(min_point)
    
    return sampled


def average_downsample(data: List[Tuple[float, float]], threshold: int) -> List[Tuple[float, float]]:
    """Average降采样算法 - 每个桶取平均值"""
    if threshold <= 2:
        threshold = 3
    
    if len(data) <= threshold:
        return data
    
    bucket_size = len(data) / threshold
    sampled = []
    
    for i in range(threshold):
        start = int(i * bucket_size)
        end = int((i + 1) * bucket_size)
        end = min(end, len(data))
        
        if start >= end:
            continue
        
        bucket = data[start:end]
        avg_x = np.mean([p[0] for p in bucket])
        avg_y = np.mean([p[1] for p in bucket])
        sampled.append((avg_x, avg_y))
    
    return sampled


def downsample(data: List[Tuple[float, float]], threshold: int, algorithm: str = "lttb") -> List[Tuple[float, float]]:
    """统一降采样入口 - 根据算法选择"""
    if algorithm == "minmax":
        return minmax_downsample(data, threshold)
    elif algorithm == "average":
        return average_downsample(data, threshold)
    else:  # 默认 lttb
        return lttb_downsample(data, threshold)


# ============ 数值合法性处理 ============

class NaNHandlingStrategy:
    """无效数值处理策略"""
    REJECT = "reject"      # 拒绝包含无效值的数据
    FILTER = "filter"      # 过滤掉无效值
    INTERPOLATE = "interpolate"  # 插值填充（暂未实现）


def is_valid_numeric(arr: np.ndarray) -> np.ndarray:
    """
    检查数组中的值是否为有效数值（非 NaN 且非 ±Infinity）
    
    Args:
        arr: numpy 数组
    
    Returns:
        布尔数组，True 表示有效值
    """
    return np.isfinite(arr)


def validate_numeric_data(
    true_values: np.ndarray, 
    pred_values: np.ndarray,
    strategy: str = NaNHandlingStrategy.REJECT,
    min_valid_ratio: float = 0.5
) -> Tuple[np.ndarray, np.ndarray, Optional[str]]:
    """
    验证和处理数值数据中的无效值（NaN 和 ±Infinity）
    
    在严格 JSON 序列化场景下，NaN 和 ±Infinity 都会导致问题，
    因此统一使用 np.isfinite() 进行检查。
    
    Args:
        true_values: 真实值数组
        pred_values: 预测值数组
        strategy: 无效值处理策略
        min_valid_ratio: 最小有效数据比例（用于 FILTER 策略）
    
    Returns:
        (处理后的真实值, 处理后的预测值, 警告信息或None)
    
    Raises:
        ValueError: 数据无效时抛出
    """
    if len(true_values) != len(pred_values):
        raise ValueError(f"数据长度不一致: true_value={len(true_values)}, predicted_value={len(pred_values)}")
    
    if len(true_values) == 0:
        raise ValueError("数据为空")
    
    # 检测无效值（NaN 或 ±Infinity）
    # np.isfinite() 对 NaN 和 ±Infinity 都返回 False
    true_valid_mask = is_valid_numeric(true_values)
    pred_valid_mask = is_valid_numeric(pred_values)
    both_valid_mask = true_valid_mask & pred_valid_mask
    
    invalid_count = np.sum(~both_valid_mask)
    total_count = len(true_values)
    
    # 分别统计 NaN 和 Infinity 的数量（用于更详细的错误信息）
    # 使用 ~np.isfinite 而非 np.isnan，确保在极端 dtype 下也能正确处理
    true_inf_mask = np.isinf(true_values)
    pred_inf_mask = np.isinf(pred_values)
    inf_count = int(np.sum(true_inf_mask | pred_inf_mask))
    nan_count = invalid_count - inf_count  # 剩余的无效值都是 NaN
    
    if invalid_count == 0:
        # 没有无效值，直接返回
        return true_values, pred_values, None
    
    # 构建详细的错误描述
    def _build_invalid_desc() -> str:
        parts = []
        if nan_count > 0:
            parts.append(f"{nan_count} 个 NaN")
        if inf_count > 0:
            parts.append(f"{inf_count} 个 Infinity")
        return "、".join(parts)
    
    if strategy == NaNHandlingStrategy.REJECT:
        # 拒绝策略：有任何无效值就报错
        raise ValueError(
            f"数据包含 {invalid_count} 个无效值（{_build_invalid_desc()}），"
            f"占比 {invalid_count/total_count*100:.1f}%。"
            f"请确保 true_value 和 predicted_value 列都是有效的有限数值。"
        )
    
    elif strategy == NaNHandlingStrategy.FILTER:
        # 过滤策略：移除包含无效值的行
        valid_count = np.sum(both_valid_mask)
        
        if valid_count == 0:
            raise ValueError("过滤无效值后没有有效数据")
        
        valid_ratio = valid_count / total_count
        if valid_ratio < min_valid_ratio:
            raise ValueError(
                f"有效数据比例过低: {valid_ratio*100:.1f}% < {min_valid_ratio*100:.1f}%。"
                f"共 {total_count} 行，其中 {invalid_count} 行包含无效值（{_build_invalid_desc()}）。"
            )
        
        warning = None
        if invalid_count > 0:
            warning = f"已过滤 {invalid_count} 行无效数据（{_build_invalid_desc()}，占比 {invalid_count/total_count*100:.1f}%）"
        
        return true_values[both_valid_mask], pred_values[both_valid_mask], warning
    
    else:
        raise ValueError(f"未知的无效值处理策略: {strategy}")


# ============ 指标计算 ============

def calculate_metrics(
    true_values: np.ndarray, 
    pred_values: np.ndarray,
    handle_invalid: bool = False
) -> dict:
    """
    计算评估指标
    
    Args:
        true_values: 真实值数组
        pred_values: 预测值数组
        handle_invalid: 是否自动过滤无效值（NaN/Infinity，用于可视化对比）
    
    Returns:
        包含各项指标的字典
    """
    if len(true_values) == 0 or len(pred_values) == 0:
        return {"mse": 0.0, "rmse": 0.0, "mae": 0.0, "r2": 0.0, "mape": 0.0}
    
    # 处理无效值（NaN 和 ±Infinity）
    if handle_invalid:
        try:
            true_values, pred_values, _ = validate_numeric_data(
                true_values, pred_values, 
                strategy=NaNHandlingStrategy.FILTER,
                min_valid_ratio=0.1  # 可视化时允许更低的有效比例
            )
        except ValueError:
            return {"mse": 0.0, "rmse": 0.0, "mae": 0.0, "r2": 0.0, "mape": 0.0}
    
    # MSE
    mse = float(np.mean((true_values - pred_values) ** 2))
    
    # RMSE
    rmse = float(np.sqrt(mse))
    
    # MAE
    mae = float(np.mean(np.abs(true_values - pred_values)))
    
    # R²
    ss_res = np.sum((true_values - pred_values) ** 2)
    ss_tot = np.sum((true_values - np.mean(true_values)) ** 2)
    # 当所有真实值相同时，R² 无意义，返回 0
    r2 = float(1 - (ss_res / ss_tot)) if ss_tot > 1e-10 else 0.0
    
    # MAPE - 带数值稳定性处理
    mape = calculate_mape(true_values, pred_values)
    
    return {"mse": mse, "rmse": rmse, "mae": mae, "r2": r2, "mape": mape}


def calculate_mape(true_values: np.ndarray, pred_values: np.ndarray, epsilon: float = 1e-8) -> float:
    """
    计算 MAPE（平均绝对百分比误差）
    带数值稳定性处理，避免除零和极大值
    
    Args:
        true_values: 真实值数组
        pred_values: 预测值数组
        epsilon: 最小阈值，避免除以接近零的值
    
    Returns:
        MAPE 值（百分比），最大限制为 1000%
    """
    # 只计算真实值绝对值大于 epsilon 的点
    mask = np.abs(true_values) > epsilon
    
    if not np.any(mask):
        return 0.0
    
    true_masked = true_values[mask]
    pred_masked = pred_values[mask]
    
    # 计算百分比误差
    percentage_errors = np.abs((true_masked - pred_masked) / true_masked)
    
    # 限制单个点的最大误差为 10（1000%）
    percentage_errors = np.clip(percentage_errors, 0, 10)
    
    mape = float(np.mean(percentage_errors) * 100)
    
    # 最终结果限制在 1000% 以内
    return min(mape, 1000.0)


# ============ 文件名生成 ============

def generate_standard_filename(dataset_name: str, channels: List[str], normalization: str,
                               anomaly_enabled: bool, anomaly_type: str, injection_algorithm: str,
                               sequence_logic: str, window_size: int, stride: int,
                               target_type: str, target_k: int = 1) -> str:
    """
    生成标准文件名
    
    文件名格式: {数据集名}_{通道}_{窗口}_{步长}_{归一化}_{异常}_{目标}.csv
    通道格式: Ch0-1-2（使用连字符分隔，无下划线）
    """
    # 先清理数据集名称中的非法字符
    safe_dataset_name = sanitize_filename(dataset_name).replace('.csv', '').replace('.CSV', '')
    
    parts = [safe_dataset_name]
    
    if channels:
        # 清理通道名中的非法字符，使用连字符分隔（Ch0-1-2 格式）
        safe_channels = [re.sub(r'[\\/:*?"<>|\s_]', '', ch) for ch in channels]
        ch_str = "Ch" + "-".join(safe_channels)
        parts.append(ch_str)
    
    parts.append(f"Win{window_size}")
    parts.append(f"Str{stride}")
    
    norm_map = {
        "none": "NoNorm", 
        "minmax": "MinMax", 
        "zscore": "ZScore", 
        "head": "Head", 
        "decimal": "Decimal",
        # 扩展归一化方法
        "robust": "Robust",
        "maxabs": "MaxAbs",
        "log": "Log",
        "log1p": "Log1p",
        "sqrt": "Sqrt",
        "boxcox": "BoxCox",
        "yeojohnson": "YeoJohn",
        "quantile": "Quantile",
        "rank": "Rank"
    }
    parts.append(norm_map.get(normalization, "NoNorm"))
    
    if anomaly_enabled and anomaly_type:
        type_map = {
            "point": "SoftRep",
            "segment": "UniRep",
            "noise": "PeakNoise",
            "trend": "LenAdj",
            "seasonal": "Seasonal",
        }
        parts.append(type_map.get(anomaly_type, "AnoX"))
        
        alg_map = {"random": "ByWin", "rule": "BySeq", "pattern": "Pattern"}
        if injection_algorithm:
            parts.append(alg_map.get(injection_algorithm, ""))
        
        seq_map = {"anomaly_first": "AF", "window_first": "WF"}
        if sequence_logic:
            parts.append(seq_map.get(sequence_logic, ""))
    
    target_map = {"next": "Pred1", "kstep": f"PredK{target_k}", "reconstruct": "Recon"}
    parts.append(target_map.get(target_type, "Pred1"))
    
    parts = [p for p in parts if p]
    
    return "_".join(parts) + ".csv"


# ============ CSV 处理 ============

# CSV 公式注入危险前缀字符
CSV_FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r', '\n')


def escape_csv_value(value: str) -> str:
    """
    转义 CSV 单元格值，防止公式注入攻击
    
    当 CSV 被 Excel/表格软件打开时，以 = + - @ 等开头的单元格
    可能被解释为公式执行，导致安全风险。
    
    常见做法：在危险前缀前添加单引号 ' 使其被视为文本
    
    Args:
        value: 原始单元格值
    
    Returns:
        转义后的安全值
    """
    if not value:
        return value
    
    # 检查是否以危险字符开头
    if value.startswith(CSV_FORMULA_PREFIXES):
        # 在前面添加单引号，Excel 会将其视为文本前缀
        return "'" + value
    
    return value


def escape_csv_header(header: str) -> str:
    """
    转义 CSV 表头，防止公式注入
    同时移除可能破坏 CSV 结构的字符
    
    Args:
        header: 原始表头
    
    Returns:
        安全的表头字符串
    """
    if not header:
        return "column"
    
    # 移除换行符和制表符（可能破坏 CSV 结构）
    safe_header = re.sub(r'[\r\n\t]', ' ', header)
    # 移除逗号和引号（CSV 分隔符和引用符）
    safe_header = safe_header.replace(',', '_').replace('"', "'")
    # 转义公式前缀
    safe_header = escape_csv_value(safe_header)
    
    return safe_header or "column"


def count_csv_rows(filepath: str, encoding: str = 'utf-8') -> int:
    """准确统计CSV行数 - 使用 csv.reader 正确处理字段内换行"""
    count = 0
    try:
        with open(filepath, 'r', encoding=encoding, errors='ignore', newline='') as f:
            reader = csv.reader(f)
            next(reader, None)  # 跳过表头
            for _ in reader:
                count += 1
    except Exception:
        # 回退到简单计数
        try:
            with open(filepath, 'r', encoding=encoding, errors='ignore') as f:
                count = sum(1 for _ in f) - 1
        except Exception:
            count = 0
    return max(0, count)
