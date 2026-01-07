import os
import asyncio
import hashlib
import json
import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from app.database import get_db
from app.models import Result
from app.schemas import CompareRequest, CompareResponse, ChartDataResponse, ChartDataSeries, MetricsResponse, SkippedResult
from app.config import settings
from app.services.utils import downsample, calculate_metrics

router = APIRouter(prefix="/api/visualization", tags=["visualization"])

executor = ThreadPoolExecutor(max_workers=4)

# 降采样结果缓存目录
CACHE_DIR = os.path.join(settings.UPLOAD_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def _read_csv_sync(filepath: str, columns: Optional[List[str]] = None):
    """同步读取CSV，只读取指定列"""
    if columns:
        return pd.read_csv(filepath, usecols=columns)
    return pd.read_csv(filepath)


def _get_cache_key(result_id: int, max_points: int, algorithm: str) -> str:
    """生成缓存键"""
    return f"{result_id}_{max_points}_{algorithm}"


def _get_cache_path(cache_key: str) -> str:
    """获取缓存文件路径"""
    return os.path.join(CACHE_DIR, f"{cache_key}.json")


def _load_from_cache(cache_key: str, filepath: str) -> Optional[dict]:
    """从缓存加载降采样结果"""
    cache_path = _get_cache_path(cache_key)
    if not os.path.exists(cache_path):
        return None
    
    try:
        # 检查源文件是否比缓存新
        if os.path.getmtime(filepath) > os.path.getmtime(cache_path):
            return None
        
        with open(cache_path, 'r') as f:
            return json.load(f)
    except Exception:
        return None


def _save_to_cache(cache_key: str, data: dict):
    """保存降采样结果到缓存"""
    cache_path = _get_cache_path(cache_key)
    try:
        with open(cache_path, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass  # 缓存失败不影响主流程


@router.post("/compare", response_model=CompareResponse)
async def compare_results(data: CompareRequest, db: AsyncSession = Depends(get_db)):
    if not data.result_ids:
        raise HTTPException(status_code=400, detail="请提供至少一个结果ID")
    
    result = await db.execute(select(Result).where(Result.id.in_(data.result_ids)))
    results = result.scalars().all()
    
    # 检查哪些 ID 不存在
    found_ids = {r.id for r in results}
    missing_ids = set(data.result_ids) - found_ids
    
    series_list = []
    metrics_dict = {}
    skipped_list = []  # 跳过的结果
    total_points = 0
    downsampled = False
    
    # 添加不存在的结果到 skipped
    for mid in missing_ids:
        skipped_list.append(SkippedResult(id=mid, name=f"ID:{mid}", reason="结果不存在"))
    
    loop = asyncio.get_running_loop()
    
    dataset_true_added = set()
    
    for res in results:
        # 检查文件是否存在
        if not os.path.exists(res.filepath):
            skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="文件不存在"))
            continue
        
        # 尝试从缓存加载
        cache_key = _get_cache_key(res.id, data.max_points, data.algorithm)
        cached = _load_from_cache(cache_key, res.filepath)
        
        if cached:
            # 使用缓存的降采样数据
            true_data = cached["true_data"]
            pred_data = cached["pred_data"]
            true_vals_clean = np.array(cached["true_vals"])
            pred_vals_clean = np.array(cached["pred_vals"])
            total_points = max(total_points, cached["total_points"])
            if cached.get("downsampled"):
                downsampled = True
        else:
            # 只读取必要的列
            try:
                df = await loop.run_in_executor(
                    executor, 
                    _read_csv_sync, 
                    res.filepath, 
                    ["true_value", "predicted_value"]
                )
            except Exception as e:
                skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="文件读取失败"))
                continue
            
            if "true_value" not in df.columns or "predicted_value" not in df.columns:
                skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="缺少必需列"))
                continue
            
            try:
                true_vals = pd.to_numeric(df["true_value"], errors='coerce').values
                pred_vals = pd.to_numeric(df["predicted_value"], errors='coerce').values
                
                # 过滤掉 NaN 值
                valid_mask = ~(np.isnan(true_vals) | np.isnan(pred_vals))
                if not valid_mask.any():
                    skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="无有效数值数据"))
                    continue
                
                true_vals_clean = true_vals[valid_mask]
                pred_vals_clean = pred_vals[valid_mask]
                valid_indices = np.where(valid_mask)[0].tolist()
            except Exception:
                skipped_list.append(SkippedResult(id=res.id, name=res.name, reason="数据解析失败"))
                continue
            
            indices = valid_indices
            total_points = max(total_points, len(indices))
            
            true_data = list(zip(indices, true_vals_clean.tolist()))
            pred_data = list(zip(indices, pred_vals_clean.tolist()))
            
            is_downsampled = False
            if len(df) > data.max_points:
                is_downsampled = True
                downsampled = True
                true_data = downsample(true_data, data.max_points, data.algorithm)
                pred_data = downsample(pred_data, data.max_points, data.algorithm)
            
            # 保存到缓存
            _save_to_cache(cache_key, {
                "true_data": true_data,
                "pred_data": pred_data,
                "true_vals": true_vals_clean.tolist(),
                "pred_vals": pred_vals_clean.tolist(),
                "total_points": len(indices),
                "downsampled": is_downsampled
            })
        
        if res.dataset_id not in dataset_true_added:
            series_list.append(ChartDataSeries(
                name=f"True (Dataset {res.dataset_id})", 
                data=[[p[0], p[1]] for p in true_data]
            ))
            dataset_true_added.add(res.dataset_id)
        
        series_list.append(ChartDataSeries(
            name=f"{res.algo_name}", 
            data=[[p[0], p[1]] for p in pred_data]
        ))
        
        metrics = calculate_metrics(true_vals_clean, pred_vals_clean)
        metrics_dict[res.id] = MetricsResponse(**metrics)
    
    return CompareResponse(
        chart_data=ChartDataResponse(series=series_list, total_points=total_points, downsampled=downsampled),
        metrics=metrics_dict,
        skipped=skipped_list
    )


@router.get("/metrics/{result_id}", response_model=MetricsResponse)
async def get_metrics(result_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(status_code=404, detail="结果不存在")
    
    if result_obj.metrics:
        return MetricsResponse(**result_obj.metrics)
    
    # 检查文件是否存在
    if not os.path.exists(result_obj.filepath):
        raise HTTPException(status_code=404, detail="结果文件不存在，可能已被删除")
    
    loop = asyncio.get_running_loop()
    try:
        # 只读取必要的列
        df = await loop.run_in_executor(
            executor, 
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
        
        # 过滤掉 NaN 值
        valid_mask = ~(np.isnan(true_vals) | np.isnan(pred_vals))
        if not valid_mask.any():
            raise HTTPException(status_code=400, detail="没有有效的数值数据")
        
        true_vals = true_vals[valid_mask]
        pred_vals = pred_vals[valid_mask]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="数据格式错误")
    
    metrics = calculate_metrics(true_vals, pred_vals)
    
    return MetricsResponse(**metrics)
