import os
import asyncio
import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from concurrent.futures import ThreadPoolExecutor

from app.database import get_db
from app.models import Result
from app.schemas import CompareRequest, CompareResponse, ChartDataResponse, ChartDataSeries, MetricsResponse, SkippedResult
from app.config import settings
from app.services.utils import downsample, calculate_metrics

router = APIRouter(prefix="/api/visualization", tags=["visualization"])

executor = ThreadPoolExecutor(max_workers=4)


def _read_csv_sync(filepath: str):
    """同步读取CSV"""
    return pd.read_csv(filepath)


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
        
        try:
            df = await loop.run_in_executor(executor, _read_csv_sync, res.filepath)
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
        
        if len(df) > data.max_points:
            downsampled = True
            true_data = downsample(true_data, data.max_points, data.algorithm)
            pred_data = downsample(pred_data, data.max_points, data.algorithm)
        
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
        df = await loop.run_in_executor(executor, _read_csv_sync, result_obj.filepath)
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
