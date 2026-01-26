"""
可视化 API 路由
提供多结果对比、指标计算、误差分析、雷达图等功能
"""

import hashlib
import json
import os
import time
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import Dataset, Result, User
from app.schemas import (
    ChartDataResponse,
    ChartDataSeries,
    CompareRequest,
    CompareResponse,
    ErrorAnalysisRequest,
    ErrorAnalysisResponse,
    ErrorDistribution,
    MetricRanking,
    MetricsResponse,
    OverallScore,
    RadarChartResponse,
    RadarMetrics,
    RangeInfo,
    RangeMetricsRequest,
    RangeMetricsResponse,
    ResidualData,
    SingleErrorAnalysis,
    SkippedResult,
    WarningInfo,
)
from app.services.executor import run_in_executor
from app.services.permissions import can_access_result
from app.services.security import validate_filepath
from app.services.utils import (
    NaNHandlingStrategy,
    calculate_metrics,
    downsample,
    escape_csv_header,
    is_valid_numeric,
    validate_numeric_data,
)

router = APIRouter(prefix="/api/visualization", tags=["visualization"])


def _get_cache_dir() -> str:
    """获取缓存目录（延迟创建）"""
    cache_dir = str(settings.CACHE_DIR)
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _read_csv_sync(filepath: str, columns: list[str] | None = None):
    """同步读取CSV，只读取指定列"""
    if columns:
        return pd.read_csv(filepath, usecols=columns)
    return pd.read_csv(filepath)


def _get_cache_key(result_id: int, max_points: int, algorithm: str) -> str:
    """生成缓存键"""
    return f"ds_{result_id}_{max_points}_{algorithm}"


def _get_cache_path(cache_key: str) -> str:
    """获取缓存文件路径"""
    return os.path.join(_get_cache_dir(), f"{cache_key}.json")


def _load_from_cache(cache_key: str, filepath: str) -> dict | None:
    """
    从缓存加载降采样结果
    只缓存降采样后的点和元信息，不缓存全量数据
    """
    cache_path = _get_cache_path(cache_key)
    if not os.path.exists(cache_path):
        return None

    try:
        # 检查源文件是否比缓存新
        if os.path.getmtime(filepath) > os.path.getmtime(cache_path):
            return None

        # 检查缓存是否过期
        cache_age_days = (time.time() - os.path.getmtime(cache_path)) / 86400
        if cache_age_days > settings.CACHE_MAX_AGE_DAYS:
            os.remove(cache_path)
            return None

        with open(cache_path) as f:
            return json.load(f)
    except Exception:
        return None


def _save_to_cache(cache_key: str, data: dict):
    """
    保存降采样结果到缓存
    只保存降采样后的点和元信息，不保存全量数据
    """
    cache_path = _get_cache_path(cache_key)
    try:
        # 只保存必要的数据
        cache_data = {
            "downsampled_true": data.get("downsampled_true", []),
            "downsampled_pred": data.get("downsampled_pred", []),
            "total_points": data.get("total_points", 0),
            "downsampled": data.get("downsampled", False),
            "true_hash": data.get("true_hash", ""),  # 用于校验一致性
            "created_at": time.time(),
        }
        with open(cache_path, "w") as f:
            json.dump(cache_data, f)
    except Exception:
        pass  # 缓存失败不影响主流程


def _cleanup_cache_if_needed():
    """
    清理过期或超量的缓存
    同步执行，由调用方决定是否异步
    """
    try:
        cache_dir = _get_cache_dir()
        cache_files = []
        total_size = 0

        for f in os.listdir(cache_dir):
            if not f.endswith(".json"):
                continue
            path = os.path.join(cache_dir, f)
            try:
                stat = os.stat(path)
                age_days = (time.time() - stat.st_mtime) / 86400

                # 删除过期缓存
                if age_days > settings.CACHE_MAX_AGE_DAYS:
                    os.remove(path)
                    continue

                cache_files.append((path, stat.st_mtime, stat.st_size))
                total_size += stat.st_size
            except Exception:
                continue

        # 如果超过大小限制，删除最旧的文件
        max_size = settings.CACHE_MAX_SIZE_MB * 1024 * 1024
        if total_size > max_size:
            cache_files.sort(key=lambda x: x[1])  # 按修改时间排序
            for path, _, size in cache_files:
                try:
                    os.remove(path)
                    total_size -= size
                    if total_size <= max_size * 0.8:
                        break
                except Exception:
                    continue
    except Exception:
        pass


# 缓存清理锁，防止高并发时线程堆积
import threading

_cleanup_lock = threading.Lock()


def _fire_and_forget_cleanup():
    """
    Fire-and-forget 方式清理缓存
    在后台线程执行，不阻塞主流程
    使用 threading.Lock 防止并发时线程堆积
    """
    # 尝试获取锁，如果已被占用则跳过
    if not _cleanup_lock.acquire(blocking=False):
        return

    def _do_cleanup():
        try:
            _cleanup_cache_if_needed()
        finally:
            _cleanup_lock.release()

    thread = threading.Thread(target=_do_cleanup, daemon=True)
    thread.start()


def _compute_data_hash(values: np.ndarray) -> str:
    """计算数据的哈希值，用于校验一致性（使用 SHA256，不截断）"""
    return hashlib.sha256(values.tobytes()).hexdigest()


@router.post("/compare", response_model=CompareResponse)
async def compare_results(
    data: CompareRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    多结果对比

    改进点：
    1. 只缓存降采样后的点，不缓存全量数据
    2. 校验同数据集结果的 true_value 一致性
    3. 使用统一的 NaN 处理策略
    """
    if not data.result_ids:
        raise HTTPException(status_code=400, detail="请提供至少一个结果ID")

    # 查询结果
    result = await db.execute(select(Result).where(Result.id.in_(data.result_ids)))
    results = result.scalars().all()

    # 预加载所有相关数据集
    dataset_ids = {r.dataset_id for r in results}
    datasets_result = await db.execute(select(Dataset).where(Dataset.id.in_(dataset_ids)))
    datasets_map: dict[int, Dataset] = {d.id: d for d in datasets_result.scalars().all()}

    # 检查哪些 ID 不存在
    found_ids = {r.id for r in results}
    missing_ids = set(data.result_ids) - found_ids

    series_list = []
    metrics_dict = {}
    skipped_list: list[SkippedResult] = []
    warnings_list: list[WarningInfo] = []  # 警告列表（结果已处理但有问题）
    total_points = 0
    downsampled = False

    # 添加不存在的结果到 skipped
    for mid in missing_ids:
        skipped_list.append(SkippedResult(id=mid, name=f"ID:{mid}", reason="结果不存在"))

    # 用于校验同数据集 true_value 一致性
    dataset_true_info: dict[int, dict[str, Any]] = {}  # dataset_id -> {hash, data, name}

    algorithm = data.algorithm.value if hasattr(data.algorithm, "value") else str(data.algorithm)

    for res in results:
        dataset = datasets_map.get(res.dataset_id)

        # 权限检查
        if not can_access_result(res, dataset, current_user):
            skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="无权访问"))
            continue

        # 检查文件是否存在
        if not os.path.exists(res.filepath):
            skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="文件不存在"))
            continue

        # 验证文件路径安全
        if not validate_filepath(res.filepath):
            skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="文件路径不安全"))
            continue

        # 尝试从缓存加载
        cache_key = _get_cache_key(res.id, data.max_points, algorithm)
        cached = _load_from_cache(cache_key, res.filepath)

        if cached:
            # 使用缓存的降采样数据
            true_data = cached["downsampled_true"]
            pred_data = cached["downsampled_pred"]
            cached_true_hash = cached.get("true_hash", "")
            total_points = max(total_points, cached["total_points"])
            if cached.get("downsampled"):
                downsampled = True

            # 优化：如果数据库有指标且缓存有 hash，完全跳过读文件
            if res.metrics and cached_true_hash:
                current_true_hash = cached_true_hash
                metrics_dict[res.id] = MetricsResponse(**res.metrics)
                true_vals_clean = None
                pred_vals_clean = None
            else:
                # 需要重新读取原始数据来计算指标和/或校验一致性
                try:
                    df = await run_in_executor(_read_csv_sync, res.filepath, ["true_value", "predicted_value"])
                    true_vals = pd.to_numeric(df["true_value"], errors="coerce").values
                    pred_vals = pd.to_numeric(df["predicted_value"], errors="coerce").values

                    # 过滤 NaN
                    true_vals_clean, pred_vals_clean, _ = validate_numeric_data(
                        true_vals, pred_vals, strategy=NaNHandlingStrategy.FILTER, min_valid_ratio=0.1
                    )

                    current_true_hash = _compute_data_hash(true_vals_clean)
                except Exception:
                    # 缓存可用但无法读取原始数据，使用缓存的哈希
                    current_true_hash = cached_true_hash
                    # 使用数据库中存储的指标
                    if res.metrics:
                        metrics_dict[res.id] = MetricsResponse(**res.metrics)
                    true_vals_clean = None
                    pred_vals_clean = None
        else:
            # 读取原始数据
            try:
                df = await run_in_executor(_read_csv_sync, res.filepath, ["true_value", "predicted_value"])
            except Exception:
                skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="文件读取失败"))
                continue

            if "true_value" not in df.columns or "predicted_value" not in df.columns:
                skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="缺少必需列"))
                continue

            try:
                true_vals = pd.to_numeric(df["true_value"], errors="coerce").values
                pred_vals = pd.to_numeric(df["predicted_value"], errors="coerce").values

                # 使用统一的 NaN 处理策略（可视化时过滤）
                true_vals_clean, pred_vals_clean, warning = validate_numeric_data(
                    true_vals, pred_vals, strategy=NaNHandlingStrategy.FILTER, min_valid_ratio=0.1
                )

                valid_mask = is_valid_numeric(true_vals) & is_valid_numeric(pred_vals)
                valid_indices = np.where(valid_mask)[0].tolist()
            except ValueError as e:
                skipped_list.append(SkippedResult(id=res.id, name=res.name, reason=str(e)))
                continue
            except Exception:
                skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="数据解析失败"))
                continue

            current_true_hash = _compute_data_hash(true_vals_clean)

            indices = valid_indices
            total_points = max(total_points, len(indices))

            true_data = list(zip(indices, true_vals_clean.tolist()))
            pred_data = list(zip(indices, pred_vals_clean.tolist()))

            is_downsampled = False
            if len(true_data) > data.max_points:
                is_downsampled = True
                downsampled = True
                true_data = downsample(true_data, data.max_points, algorithm)
                pred_data = downsample(pred_data, data.max_points, algorithm)

            # 保存到缓存（只保存降采样后的点）
            _save_to_cache(
                cache_key,
                {
                    "downsampled_true": true_data,
                    "downsampled_pred": pred_data,
                    "total_points": len(indices),
                    "downsampled": is_downsampled,
                    "true_hash": current_true_hash,
                },
            )

        # 校验同数据集 true_value 一致性
        if res.dataset_id in dataset_true_info:
            existing_info = dataset_true_info[res.dataset_id]
            if existing_info["hash"] != current_true_hash:
                # true_value 不一致，添加警告但继续处理（不是跳过）
                warnings_list.append(
                    WarningInfo(
                        id=res.id,
                        name=res.name,
                        message=f"true_value 与同数据集的 '{existing_info['name']}' 不一致，对比结果可能不准确",
                    )
                )
        else:
            # 记录该数据集的第一个 true_value 信息
            dataset_true_info[res.dataset_id] = {"hash": current_true_hash, "data": true_data, "name": res.name}
            # 添加 True 曲线
            series_list.append(
                ChartDataSeries(name=f"True (Dataset {res.dataset_id})", data=[[p[0], p[1]] for p in true_data])
            )

        # 添加预测曲线
        series_list.append(ChartDataSeries(name=f"{res.algo_name}", data=[[p[0], p[1]] for p in pred_data]))

        # 计算指标（优先使用数据库中的指标）
        if res.id not in metrics_dict:
            if res.metrics:
                metrics_dict[res.id] = MetricsResponse(**res.metrics)
            elif true_vals_clean is not None and pred_vals_clean is not None:
                metrics = calculate_metrics(true_vals_clean, pred_vals_clean, handle_invalid=True)
                metrics_dict[res.id] = MetricsResponse(**metrics)

    # Fire-and-forget 清理缓存（不阻塞响应，有锁防止线程堆积）
    _fire_and_forget_cleanup()

    return CompareResponse(
        chart_data=ChartDataResponse(series=series_list, total_points=total_points, downsampled=downsampled),
        metrics=metrics_dict,
        skipped=skipped_list,
        warnings=warnings_list,
    )


@router.get("/metrics/{result_id}", response_model=MetricsResponse)
async def get_metrics(
    result_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """获取单个结果的指标"""
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(status_code=404, detail="结果不存在")

    # 权限检查
    dataset_result = await db.execute(select(Dataset).where(Dataset.id == result_obj.dataset_id))
    dataset = dataset_result.scalar_one_or_none()

    # 权限检查
    if not can_access_result(result_obj, dataset, current_user):
        raise HTTPException(status_code=403, detail="无权访问此结果")

    # 优先使用数据库中存储的指标
    if result_obj.metrics:
        return MetricsResponse(**result_obj.metrics)

    # 检查文件是否存在
    if not os.path.exists(result_obj.filepath):
        raise HTTPException(status_code=404, detail="结果文件不存在，可能已被删除")

    # 验证文件路径安全
    if not validate_filepath(result_obj.filepath):
        raise HTTPException(status_code=403, detail="文件路径不安全")

    try:
        df = await run_in_executor(_read_csv_sync, result_obj.filepath, ["true_value", "predicted_value"])
    except Exception:
        raise HTTPException(status_code=500, detail="读取结果文件失败")

    if "true_value" not in df.columns or "predicted_value" not in df.columns:
        raise HTTPException(status_code=400, detail="结果文件缺少必需列")

    try:
        true_vals = pd.to_numeric(df["true_value"], errors="coerce").values
        pred_vals = pd.to_numeric(df["predicted_value"], errors="coerce").values

        # 使用统一的 NaN 处理策略
        true_vals, pred_vals, _ = validate_numeric_data(
            true_vals, pred_vals, strategy=NaNHandlingStrategy.FILTER, min_valid_ratio=0.1
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="数据格式错误")

    metrics = calculate_metrics(true_vals, pred_vals)

    return MetricsResponse(**metrics)


# ============ 新增：误差分析 API ============


def _calculate_error_distribution(
    residuals: np.ndarray, bin_edges: np.ndarray | None = None, num_bins: int = 20
) -> tuple[ErrorDistribution, np.ndarray]:
    """
    计算误差分布统计

    Args:
        residuals: 残差数组
        bin_edges: 统一的 bin 边界（如果为 None 则自动计算）
        num_bins: bin 数量（仅在 bin_edges 为 None 时使用）

    Returns:
        (ErrorDistribution, bin_edges): 分布统计和使用的 bin 边界
    """
    from app.schemas.schemas import HistogramBin

    # 基础统计
    min_val = float(np.min(residuals))
    max_val = float(np.max(residuals))
    mean_val = float(np.mean(residuals))
    std_val = float(np.std(residuals))
    median_val = float(np.median(residuals))
    q1 = float(np.percentile(residuals, 25))
    q3 = float(np.percentile(residuals, 75))

    # 直方图（使用统一的 bin_edges）
    if bin_edges is None:
        hist, bin_edges = np.histogram(residuals, bins=num_bins)
    else:
        hist, _ = np.histogram(residuals, bins=bin_edges)

    total = len(residuals)
    histogram = []
    for i in range(len(hist)):
        histogram.append(
            HistogramBin(
                bin_start=float(bin_edges[i]),
                bin_end=float(bin_edges[i + 1]),
                count=int(hist[i]),
                percentage=float(hist[i] / total * 100) if total > 0 else 0.0,
            )
        )

    return (
        ErrorDistribution(
            min=min_val, max=max_val, mean=mean_val, std=std_val, median=median_val, q1=q1, q3=q3, histogram=histogram
        ),
        bin_edges,
    )


@router.post("/error-analysis", response_model=ErrorAnalysisResponse)
async def analyze_errors(
    data: ErrorAnalysisRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    误差分析接口

    返回残差时序、误差分布统计等信息
    支持指定区间分析

    重要：所有模型使用统一的 bin_edges 计算直方图，确保可比性
    """
    if not data.result_ids:
        raise HTTPException(status_code=400, detail="请提供至少一个结果ID")

    # 查询结果
    result = await db.execute(select(Result).where(Result.id.in_(data.result_ids)))
    results = result.scalars().all()

    # 预加载数据集
    dataset_ids = {r.dataset_id for r in results}
    datasets_result = await db.execute(select(Dataset).where(Dataset.id.in_(dataset_ids)))
    datasets_map: dict[int, Dataset] = {d.id: d for d in datasets_result.scalars().all()}

    skipped_list: list[SkippedResult] = []

    # 检查不存在的 ID
    found_ids = {r.id for r in results}
    for mid in set(data.result_ids) - found_ids:
        skipped_list.append(SkippedResult(id=mid, name=f"ID:{mid}", reason="结果不存在"))

    # ========== 第一阶段：收集所有有效数据和残差 ==========
    # 用于计算全局 min/max 以统一 bin_edges
    collected_data: list[dict[str, Any]] = []
    all_residuals_for_bins: list[np.ndarray] = []

    for res in results:
        dataset = datasets_map.get(res.dataset_id)

        # 权限检查
        if not can_access_result(res, dataset, current_user):
            skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="无权访问"))
            continue

        # 文件检查
        if not os.path.exists(res.filepath):
            skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="文件不存在"))
            continue

        if not validate_filepath(res.filepath):
            skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="文件路径不安全"))
            continue

        try:
            df = await run_in_executor(_read_csv_sync, res.filepath, ["true_value", "predicted_value"])
        except Exception:
            skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="文件读取失败"))
            continue

        if "true_value" not in df.columns or "predicted_value" not in df.columns:
            skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="缺少必需列"))
            continue

        try:
            true_vals = pd.to_numeric(df["true_value"], errors="coerce").values
            pred_vals = pd.to_numeric(df["predicted_value"], errors="coerce").values

            # 过滤无效值
            valid_mask = is_valid_numeric(true_vals) & is_valid_numeric(pred_vals)
            valid_indices = np.where(valid_mask)[0]

            true_vals_clean = true_vals[valid_mask]
            pred_vals_clean = pred_vals[valid_mask]

            if len(true_vals_clean) == 0:
                skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="无有效数据"))
                continue

            # 应用区间筛选
            start_idx = data.start_index if data.start_index is not None else 0
            end_idx = data.end_index if data.end_index is not None else len(true_vals_clean)
            end_idx = min(end_idx, len(true_vals_clean))

            if start_idx >= end_idx:
                skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="区间无效"))
                continue

            # 截取区间数据
            range_indices = valid_indices[start_idx:end_idx].tolist()
            true_range = true_vals_clean[start_idx:end_idx]
            pred_range = pred_vals_clean[start_idx:end_idx]

            # 计算残差
            residuals = pred_range - true_range

            # 收集数据用于第二阶段
            collected_data.append(
                {
                    "result": res,
                    "range_indices": range_indices,
                    "true_range": true_range,
                    "pred_range": pred_range,
                    "residuals": residuals,
                }
            )

            # 收集残差用于计算全局 bin_edges
            all_residuals_for_bins.append(residuals)

        except Exception as e:
            skipped_list.append(SkippedResult(id=res.id, name=res.name, reason=f"数据处理失败: {str(e)[:50]}"))
            continue

    # ========== 计算统一的 bin_edges ==========
    unified_bin_edges: np.ndarray | None = None
    num_bins = 20

    if all_residuals_for_bins:
        # 合并所有残差计算全局 min/max
        all_residuals_concat = np.concatenate(all_residuals_for_bins)
        global_min = float(np.min(all_residuals_concat))
        global_max = float(np.max(all_residuals_concat))

        # 创建统一的 bin edges
        # 稍微扩展范围以确保所有值都在范围内
        margin = (global_max - global_min) * 0.01 if global_max > global_min else 0.1
        unified_bin_edges = np.linspace(global_min - margin, global_max + margin, num_bins + 1)

    # ========== 第二阶段：使用统一 bin_edges 计算分布 ==========
    analyses: list[SingleErrorAnalysis] = []

    for item in collected_data:
        res = item["result"]
        range_indices = item["range_indices"]
        true_range = item["true_range"]
        pred_range = item["pred_range"]
        residuals = item["residuals"]

        try:
            abs_residuals = np.abs(residuals)

            # 计算百分比误差（避免除零）
            epsilon = 1e-8
            safe_true = np.where(np.abs(true_range) > epsilon, true_range, epsilon)
            percentage_errors = np.abs(residuals / safe_true) * 100
            percentage_errors = np.clip(percentage_errors, 0, 1000)  # 限制最大值

            # 计算指标
            metrics = calculate_metrics(true_range, pred_range)

            # 计算误差分布（使用统一的 bin_edges）
            distribution, _ = _calculate_error_distribution(residuals, bin_edges=unified_bin_edges, num_bins=num_bins)

            # 降采样残差数据用于前端展示（最多2000点）
            max_display_points = 2000
            if len(range_indices) > max_display_points:
                step = len(range_indices) // max_display_points
                display_indices = range_indices[::step][:max_display_points]
                display_residuals = residuals[::step][:max_display_points].tolist()
                display_abs = abs_residuals[::step][:max_display_points].tolist()
                display_pct = percentage_errors[::step][:max_display_points].tolist()
            else:
                display_indices = range_indices
                display_residuals = residuals.tolist()
                display_abs = abs_residuals.tolist()
                display_pct = percentage_errors.tolist()

            residual_data = ResidualData(
                indices=display_indices,
                residuals=display_residuals,
                abs_residuals=display_abs,
                percentage_errors=display_pct,
            )

            analyses.append(
                SingleErrorAnalysis(
                    result_id=res.id,
                    result_name=res.name,
                    model_name=res.algo_name,
                    metrics=MetricsResponse(**metrics),
                    distribution=distribution,
                    residual_data=residual_data,
                )
            )

        except Exception as e:
            skipped_list.append(SkippedResult(id=res.id, name=res.name, reason=f"分析失败: {str(e)[:50]}"))
            continue

    range_info = RangeInfo(
        start_index=data.start_index,
        end_index=data.end_index,
        is_full_range=data.start_index is None and data.end_index is None,
    )

    return ErrorAnalysisResponse(
        analyses=analyses,
        skipped=skipped_list,
        range_info=range_info,
        unified_bin_edges=unified_bin_edges.tolist() if unified_bin_edges is not None else [],
    )


# ============ 新增：雷达图 API ============


@router.post("/radar-chart", response_model=RadarChartResponse)
async def get_radar_chart(
    data: CompareRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    雷达图数据接口

    返回归一化后的指标数据，方向统一为越大越好
    同时返回排名和综合得分
    """
    if not data.result_ids:
        raise HTTPException(status_code=400, detail="请提供至少一个结果ID")

    # 查询结果
    result = await db.execute(select(Result).where(Result.id.in_(data.result_ids)))
    results = result.scalars().all()

    # 预加载数据集
    dataset_ids = {r.dataset_id for r in results}
    datasets_result = await db.execute(select(Dataset).where(Dataset.id.in_(dataset_ids)))
    datasets_map: dict[int, Dataset] = {d.id: d for d in datasets_result.scalars().all()}

    # 收集所有有效结果的指标
    valid_results: list[dict[str, Any]] = []

    for res in results:
        dataset = datasets_map.get(res.dataset_id)

        if not can_access_result(res, dataset, current_user):
            continue

        # 获取指标
        metrics = None
        if res.metrics:
            metrics = res.metrics
        elif os.path.exists(res.filepath) and validate_filepath(res.filepath):
            try:
                df = await run_in_executor(_read_csv_sync, res.filepath, ["true_value", "predicted_value"])
                true_vals = pd.to_numeric(df["true_value"], errors="coerce").values
                pred_vals = pd.to_numeric(df["predicted_value"], errors="coerce").values
                true_vals, pred_vals, _ = validate_numeric_data(
                    true_vals, pred_vals, strategy=NaNHandlingStrategy.FILTER, min_valid_ratio=0.1
                )
                metrics = calculate_metrics(true_vals, pred_vals)
            except Exception:
                continue

        if metrics:
            valid_results.append(
                {"result_id": res.id, "result_name": res.name, "model_name": res.algo_name, "metrics": metrics}
            )

    if not valid_results:
        raise HTTPException(status_code=400, detail="没有有效的结果数据")

    # 提取各指标值
    mse_vals = [r["metrics"]["mse"] for r in valid_results]
    rmse_vals = [r["metrics"]["rmse"] for r in valid_results]
    mae_vals = [r["metrics"]["mae"] for r in valid_results]
    r2_vals = [r["metrics"]["r2"] for r in valid_results]
    mape_vals = [r["metrics"]["mape"] for r in valid_results]

    # 归一化函数（越小越好的指标转换为越大越好）
    # 改进：给最差的模型一个最低分 0.1 而不是 0，避免雷达图完全塌陷
    def normalize_lower_better(vals: list[float]) -> list[float]:
        """归一化：原值越小，得分越高（最低分 0.1）"""
        min_v, max_v = min(vals), max(vals)
        if max_v == min_v:
            return [1.0] * len(vals)
        # 反转：(max - val) / (max - min)，然后映射到 [0.1, 1.0]
        normalized = [(max_v - v) / (max_v - min_v) for v in vals]
        return [0.1 + 0.9 * n for n in normalized]

    def normalize_higher_better(vals: list[float]) -> list[float]:
        """归一化：原值越大，得分越高（最低分 0.1）"""
        min_v, max_v = min(vals), max(vals)
        if max_v == min_v:
            return [1.0] * len(vals)
        # 映射到 [0.1, 1.0]
        normalized = [(v - min_v) / (max_v - min_v) for v in vals]
        return [0.1 + 0.9 * n for n in normalized]

    # 归一化（MSE/RMSE/MAE/MAPE 越小越好，R² 越大越好）
    mse_scores = normalize_lower_better(mse_vals)
    rmse_scores = normalize_lower_better(rmse_vals)
    mae_scores = normalize_lower_better(mae_vals)
    r2_scores = normalize_higher_better(r2_vals)
    mape_scores = normalize_lower_better(mape_vals)

    # 构建雷达图数据
    radar_results: list[RadarMetrics] = []
    for i, r in enumerate(valid_results):
        radar_results.append(
            RadarMetrics(
                result_id=r["result_id"],
                result_name=r["result_name"],
                model_name=r["model_name"],
                mse_score=mse_scores[i],
                rmse_score=rmse_scores[i],
                mae_score=mae_scores[i],
                r2_score=r2_scores[i],
                mape_score=mape_scores[i],
                raw_metrics=MetricsResponse(**r["metrics"]),
            )
        )

    # 计算排名
    def get_rankings(vals: list[float], result_ids: list[int], lower_better: bool = True) -> list[MetricRanking]:
        indexed = list(zip(result_ids, vals))
        sorted_list = sorted(indexed, key=lambda x: x[1], reverse=not lower_better)
        rankings = []
        for rank, (rid, val) in enumerate(sorted_list, 1):
            rankings.append(MetricRanking(result_id=rid, rank=rank, value=val))
        return rankings

    result_ids = [r["result_id"] for r in valid_results]
    rankings = {
        "mse": get_rankings(mse_vals, result_ids, lower_better=True),
        "rmse": get_rankings(rmse_vals, result_ids, lower_better=True),
        "mae": get_rankings(mae_vals, result_ids, lower_better=True),
        "r2": get_rankings(r2_vals, result_ids, lower_better=False),
        "mape": get_rankings(mape_vals, result_ids, lower_better=True),
    }

    # 计算综合得分（各指标得分的平均值）
    overall_scores_list: list[OverallScore] = []
    for i, r in enumerate(valid_results):
        avg_score = (mse_scores[i] + rmse_scores[i] + mae_scores[i] + r2_scores[i] + mape_scores[i]) / 5
        overall_scores_list.append(
            OverallScore(
                result_id=r["result_id"],
                result_name=r["result_name"],
                model_name=r["model_name"],
                score=avg_score,
                rank=0,  # 稍后填充
            )
        )

    # 按综合得分排序并设置排名
    overall_scores_list.sort(key=lambda x: x.score, reverse=True)
    for rank, item in enumerate(overall_scores_list, 1):
        item.rank = rank

    return RadarChartResponse(results=radar_results, rankings=rankings, overall_scores=overall_scores_list)


# ============ 新增：区间指标计算 API ============


@router.post("/range-metrics", response_model=RangeMetricsResponse)
async def calculate_range_metrics(
    data: RangeMetricsRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    区间指标计算接口

    计算指定区间内的评估指标
    用于 brush 选区后的指标重算
    """
    if not data.result_ids:
        raise HTTPException(status_code=400, detail="请提供至少一个结果ID")

    if data.start_index >= data.end_index:
        raise HTTPException(status_code=400, detail="区间无效：起始索引必须小于结束索引")

    # 查询结果
    result = await db.execute(select(Result).where(Result.id.in_(data.result_ids)))
    results = result.scalars().all()

    # 预加载数据集
    dataset_ids = {r.dataset_id for r in results}
    datasets_result = await db.execute(select(Dataset).where(Dataset.id.in_(dataset_ids)))
    datasets_map: dict[int, Dataset] = {d.id: d for d in datasets_result.scalars().all()}

    metrics_dict: dict[int, MetricsResponse] = {}
    skipped_list: list[SkippedResult] = []
    actual_points = 0

    # 检查不存在的 ID
    found_ids = {r.id for r in results}
    for mid in set(data.result_ids) - found_ids:
        skipped_list.append(SkippedResult(id=mid, name=f"ID:{mid}", reason="结果不存在"))

    for res in results:
        dataset = datasets_map.get(res.dataset_id)

        if not can_access_result(res, dataset, current_user):
            skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="无权访问"))
            continue

        if not os.path.exists(res.filepath):
            skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="文件不存在"))
            continue

        if not validate_filepath(res.filepath):
            skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="文件路径不安全"))
            continue

        try:
            df = await run_in_executor(_read_csv_sync, res.filepath, ["true_value", "predicted_value"])

            true_vals = pd.to_numeric(df["true_value"], errors="coerce").values
            pred_vals = pd.to_numeric(df["predicted_value"], errors="coerce").values

            # 过滤无效值
            valid_mask = is_valid_numeric(true_vals) & is_valid_numeric(pred_vals)
            true_vals_clean = true_vals[valid_mask]
            pred_vals_clean = pred_vals[valid_mask]

            # 应用区间
            end_idx = min(data.end_index, len(true_vals_clean))
            if data.start_index >= len(true_vals_clean):
                skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="区间超出数据范围"))
                continue

            true_range = true_vals_clean[data.start_index : end_idx]
            pred_range = pred_vals_clean[data.start_index : end_idx]

            if len(true_range) == 0:
                skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="区间内无有效数据"))
                continue

            actual_points = max(actual_points, len(true_range))

            # 计算指标
            metrics = calculate_metrics(true_range, pred_range)
            metrics_dict[res.id] = MetricsResponse(**metrics)

        except Exception as e:
            skipped_list.append(SkippedResult(id=res.id, name=res.name, reason=f"计算失败: {str(e)[:50]}"))
            continue

    return RangeMetricsResponse(
        range_start=data.start_index,
        range_end=data.end_index,
        total_points=actual_points,
        metrics=metrics_dict,
        skipped=skipped_list,
    )


# ============ 新增：导出对比数据 CSV ============


@router.post("/export-csv")
async def export_compare_csv(
    data: CompareRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    导出对比数据为 CSV 格式（流式输出）

    返回包含所有结果的 true_value 和 predicted_value 的 CSV 数据
    - 列顺序与请求 result_ids 顺序一致（去重）
    - 列名包含 result_id 避免同名模型冲突
    - 添加 UTF-8 BOM 兼容 Excel
    - 正确处理 numpy NaN

    注意：为了对齐各结果的行，需要预读所有数据到内存。
    对于超大数据集，建议分批导出或使用其他方案。
    """
    import csv
    import io

    from fastapi.responses import StreamingResponse

    if not data.result_ids:
        raise HTTPException(status_code=400, detail="请提供至少一个结果ID")

    # 查询结果
    result = await db.execute(select(Result).where(Result.id.in_(data.result_ids)))
    results = result.scalars().all()
    results_map = {r.id: r for r in results}

    # 预加载数据集
    dataset_ids = {r.dataset_id for r in results}
    datasets_result = await db.execute(select(Dataset).where(Dataset.id.in_(dataset_ids)))
    datasets_map: dict[int, Dataset] = {d.id: d for d in datasets_result.scalars().all()}

    # 按请求的 result_ids 顺序收集"可尝试导出"的 rid（去重）
    # 注意：这里只做权限和文件存在性检查，不做实际读取
    candidate_ids: list[int] = []
    seen_ids: set = set()

    for rid in data.result_ids:
        # 去重
        if rid in seen_ids:
            continue
        seen_ids.add(rid)

        res = results_map.get(rid)
        if not res:
            continue

        dataset = datasets_map.get(res.dataset_id)
        if not can_access_result(res, dataset, current_user):
            continue

        if not os.path.exists(res.filepath) or not validate_filepath(res.filepath):
            continue

        candidate_ids.append(rid)

    if not candidate_ids:
        raise HTTPException(status_code=400, detail="没有可导出的数据")

    # ========== 预读取所有数据 ==========
    # 使用新列表 export_ids 收集"读取成功"的 rid
    # 不要在遍历时修改原列表！
    all_data: dict[int, dict[str, Any]] = {}
    export_ids: list[int] = []  # 最终导出的 rid 列表（读取成功的）
    max_length = 0

    for rid in candidate_ids:
        res = results_map[rid]
        try:
            df = await run_in_executor(_read_csv_sync, res.filepath, ["true_value", "predicted_value"])

            true_vals = pd.to_numeric(df["true_value"], errors="coerce").values
            pred_vals = pd.to_numeric(df["predicted_value"], errors="coerce").values

            all_data[rid] = {"name": res.name, "model": res.algo_name, "true_vals": true_vals, "pred_vals": pred_vals}
            # 取两列的最大长度，避免截断
            max_length = max(max_length, len(true_vals), len(pred_vals))
            # 读取成功，加入导出列表
            export_ids.append(rid)

        except Exception:
            # 读取失败，不加入 export_ids，继续处理下一个
            continue

    # 在开始响应前检查数据是否有效
    if not export_ids:
        raise HTTPException(status_code=400, detail="所有文件读取失败，无法导出数据")

    # 预生成表头（按 export_ids 顺序，包含 result_id 避免列名冲突）
    # 使用 escape_csv_header 防止公式注入
    header_parts = ["index"]
    for rid in export_ids:
        info = all_data[rid]
        # 格式: "模型名_rID_true" 和 "模型名_rID_pred"
        # 使用 escape_csv_header 转义模型名，防止公式注入
        safe_model = escape_csv_header(info["model"])
        header_parts.append(f"{safe_model}_r{rid}_true")
        header_parts.append(f"{safe_model}_r{rid}_pred")

    def generate_csv():
        """流式生成 CSV 内容（同步生成器）"""
        # UTF-8 BOM（兼容 Excel）
        yield "\ufeff"

        # 写入表头
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header_parts)
        yield output.getvalue()

        # 分批写入数据（每批 1000 行）
        batch_size = 1000
        for batch_start in range(0, max_length, batch_size):
            output = io.StringIO()
            writer = csv.writer(output)

            batch_end = min(batch_start + batch_size, max_length)
            for i in range(batch_start, batch_end):
                row = [i]
                # 只遍历 export_ids（读取成功的），保证列数与表头一致
                for rid in export_ids:
                    info = all_data[rid]

                    # 获取值（注意两列长度可能不同）
                    true_val = info["true_vals"][i] if i < len(info["true_vals"]) else np.nan
                    pred_val = info["pred_vals"][i] if i < len(info["pred_vals"]) else np.nan

                    # 使用 pd.isna() 正确处理 numpy.float64 的 NaN
                    true_str = "" if pd.isna(true_val) else str(true_val)
                    pred_str = "" if pd.isna(pred_val) else str(pred_val)

                    row.extend([true_str, pred_str])
                writer.writerow(row)

            yield output.getvalue()

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=comparison_export_{int(time.time())}.csv"},
    )
