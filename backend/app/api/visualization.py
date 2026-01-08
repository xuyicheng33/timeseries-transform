"""
可视化 API 路由
提供多结果对比、指标计算等功能
"""
import os
import time
import hashlib
import json
import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any

from app.database import get_db
from app.models import Result, Dataset, User
from app.schemas import (
    CompareRequest, CompareResponse, ChartDataResponse, 
    ChartDataSeries, MetricsResponse, SkippedResult, WarningInfo
)
from app.config import settings
from app.services.utils import (
    downsample, calculate_metrics, 
    validate_numeric_data, NaNHandlingStrategy
)
from app.services.executor import run_in_executor
from app.services.security import validate_filepath
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/visualization", tags=["visualization"])


def _get_cache_dir() -> str:
    """获取缓存目录（延迟创建）"""
    cache_dir = str(settings.CACHE_DIR)
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _read_csv_sync(filepath: str, columns: Optional[List[str]] = None):
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


def _load_from_cache(cache_key: str, filepath: str) -> Optional[dict]:
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
        
        with open(cache_path, 'r') as f:
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
            "created_at": time.time()
        }
        with open(cache_path, 'w') as f:
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
            if not f.endswith('.json'):
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
    """计算数据的哈希值，用于校验一致性"""
    return hashlib.md5(values.tobytes()).hexdigest()[:16]


def _check_result_access(result: Result, dataset: Optional[Dataset], user: Optional[User]) -> bool:
    """检查用户是否有权访问结果（只读）"""
    if not settings.ENABLE_DATA_ISOLATION:
        return True
    
    # 公开数据集的结果允许匿名访问
    if dataset and dataset.is_public:
        return True
    
    # 非公开数据需要登录
    if user is None:
        return False
    
    if user.is_admin:
        return True
    
    if result.user_id == user.id:
        return True
    
    if dataset and dataset.user_id == user.id:
        return True
    
    return False


@router.post("/compare", response_model=CompareResponse)
async def compare_results(
    data: CompareRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    datasets_map: Dict[int, Dataset] = {d.id: d for d in datasets_result.scalars().all()}
    
    # 检查哪些 ID 不存在
    found_ids = {r.id for r in results}
    missing_ids = set(data.result_ids) - found_ids
    
    series_list = []
    metrics_dict = {}
    skipped_list: List[SkippedResult] = []
    warnings_list: List[WarningInfo] = []  # 警告列表（结果已处理但有问题）
    total_points = 0
    downsampled = False
    
    # 添加不存在的结果到 skipped
    for mid in missing_ids:
        skipped_list.append(SkippedResult(id=mid, name=f"ID:{mid}", reason="结果不存在"))
    
    # 用于校验同数据集 true_value 一致性
    dataset_true_info: Dict[int, Dict[str, Any]] = {}  # dataset_id -> {hash, data, name}
    
    algorithm = data.algorithm.value if hasattr(data.algorithm, 'value') else str(data.algorithm)
    
    for res in results:
        dataset = datasets_map.get(res.dataset_id)
        
        # 权限检查
        if not _check_result_access(res, dataset, current_user):
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
                    df = await run_in_executor(
                        _read_csv_sync, 
                        res.filepath, 
                        ["true_value", "predicted_value"]
                    )
                    true_vals = pd.to_numeric(df["true_value"], errors='coerce').values
                    pred_vals = pd.to_numeric(df["predicted_value"], errors='coerce').values
                    
                    # 过滤 NaN
                    true_vals_clean, pred_vals_clean, _ = validate_numeric_data(
                        true_vals, pred_vals,
                        strategy=NaNHandlingStrategy.FILTER,
                        min_valid_ratio=0.1
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
                df = await run_in_executor(
                    _read_csv_sync, 
                    res.filepath, 
                    ["true_value", "predicted_value"]
                )
            except Exception:
                skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="文件读取失败"))
                continue
            
            if "true_value" not in df.columns or "predicted_value" not in df.columns:
                skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="缺少必需列"))
                continue
            
            try:
                true_vals = pd.to_numeric(df["true_value"], errors='coerce').values
                pred_vals = pd.to_numeric(df["predicted_value"], errors='coerce').values
                
                # 使用统一的 NaN 处理策略（可视化时过滤）
                true_vals_clean, pred_vals_clean, warning = validate_numeric_data(
                    true_vals, pred_vals,
                    strategy=NaNHandlingStrategy.FILTER,
                    min_valid_ratio=0.1
                )
                
                valid_mask = ~(np.isnan(true_vals) | np.isnan(pred_vals))
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
            _save_to_cache(cache_key, {
                "downsampled_true": true_data,
                "downsampled_pred": pred_data,
                "total_points": len(indices),
                "downsampled": is_downsampled,
                "true_hash": current_true_hash
            })
        
        # 校验同数据集 true_value 一致性
        if res.dataset_id in dataset_true_info:
            existing_info = dataset_true_info[res.dataset_id]
            if existing_info["hash"] != current_true_hash:
                # true_value 不一致，添加警告但继续处理（不是跳过）
                warnings_list.append(WarningInfo(
                    id=res.id, 
                    name=res.name, 
                    message=f"true_value 与同数据集的 '{existing_info['name']}' 不一致，对比结果可能不准确"
                ))
        else:
            # 记录该数据集的第一个 true_value 信息
            dataset_true_info[res.dataset_id] = {
                "hash": current_true_hash,
                "data": true_data,
                "name": res.name
            }
            # 添加 True 曲线
            series_list.append(ChartDataSeries(
                name=f"True (Dataset {res.dataset_id})", 
                data=[[p[0], p[1]] for p in true_data]
            ))
        
        # 添加预测曲线
        series_list.append(ChartDataSeries(
            name=f"{res.algo_name}", 
            data=[[p[0], p[1]] for p in pred_data]
        ))
        
        # 计算指标（优先使用数据库中的指标）
        if res.id not in metrics_dict:
            if res.metrics:
                metrics_dict[res.id] = MetricsResponse(**res.metrics)
            elif true_vals_clean is not None and pred_vals_clean is not None:
                metrics = calculate_metrics(true_vals_clean, pred_vals_clean, handle_nan=True)
                metrics_dict[res.id] = MetricsResponse(**metrics)
    
    # Fire-and-forget 清理缓存（不阻塞响应，有锁防止线程堆积）
    _fire_and_forget_cleanup()
    
    return CompareResponse(
        chart_data=ChartDataResponse(series=series_list, total_points=total_points, downsampled=downsampled),
        metrics=metrics_dict,
        skipped=skipped_list,
        warnings=warnings_list
    )


@router.get("/metrics/{result_id}", response_model=MetricsResponse)
async def get_metrics(
    result_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个结果的指标"""
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(status_code=404, detail="结果不存在")
    
    # 权限检查
    dataset_result = await db.execute(select(Dataset).where(Dataset.id == result_obj.dataset_id))
    dataset = dataset_result.scalar_one_or_none()
    
    if not _check_result_access(result_obj, dataset, current_user):
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
        df = await run_in_executor(
            _read_csv_sync, 
            result_obj.filepath,
            ["true_value", "predicted_value"]
        )
    except Exception:
        raise HTTPException(status_code=500, detail="读取结果文件失败")
    
    if "true_value" not in df.columns or "predicted_value" not in df.columns:
        raise HTTPException(status_code=400, detail="结果文件缺少必需列")
    
    try:
        true_vals = pd.to_numeric(df["true_value"], errors='coerce').values
        pred_vals = pd.to_numeric(df["predicted_value"], errors='coerce').values
        
        # 使用统一的 NaN 处理策略
        true_vals, pred_vals, _ = validate_numeric_data(
            true_vals, pred_vals,
            strategy=NaNHandlingStrategy.FILTER,
            min_valid_ratio=0.1
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="数据格式错误")
    
    metrics = calculate_metrics(true_vals, pred_vals)
    
    return MetricsResponse(**metrics)
