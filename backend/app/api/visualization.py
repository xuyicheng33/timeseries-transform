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
from app.schemas import CompareRequest, CompareResponse, ChartDataResponse, ChartDataSeries, MetricsResponse
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
        raise HTTPException(status_code=400, detail="No result IDs provided")
    
    result = await db.execute(select(Result).where(Result.id.in_(data.result_ids)))
    results = result.scalars().all()
    
    if len(results) != len(data.result_ids):
        raise HTTPException(status_code=404, detail="Some results not found")
    
    series_list = []
    metrics_dict = {}
    total_points = 0
    downsampled = False
    
    loop = asyncio.get_event_loop()
    
    dataset_true_added = set()
    
    for res in results:
        df = await loop.run_in_executor(executor, _read_csv_sync, res.filepath)
        
        if "true_value" in df.columns and "predicted_value" in df.columns:
            true_vals = df["true_value"].values.astype(float)
            pred_vals = df["predicted_value"].values.astype(float)
            indices = list(range(len(df)))
            
            total_points = max(total_points, len(df))
            
            true_data = list(zip(indices, true_vals.tolist()))
            pred_data = list(zip(indices, pred_vals.tolist()))
            
            if len(df) > data.max_points:
                downsampled = True
                # 修复：使用 algorithm 参数选择降采样算法
                true_data = downsample(true_data, data.max_points, data.algorithm)
                pred_data = downsample(pred_data, data.max_points, data.algorithm)
            
            if res.dataset_id not in dataset_true_added:
                series_list.append(ChartDataSeries(
                    name=f"True (Dataset {res.dataset_id})", 
                    data=[[p[0], p[1]] for p in true_data]
                ))
                dataset_true_added.add(res.dataset_id)
            
            series_list.append(ChartDataSeries(
                name=f"{res.model_name}", 
                data=[[p[0], p[1]] for p in pred_data]
            ))
            
            metrics = calculate_metrics(true_vals, pred_vals)
            metrics_dict[res.id] = MetricsResponse(**metrics)
    
    return CompareResponse(
        chart_data=ChartDataResponse(series=series_list, total_points=total_points, downsampled=downsampled),
        metrics=metrics_dict
    )


@router.get("/metrics/{result_id}", response_model=MetricsResponse)
async def get_metrics(result_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(status_code=404, detail="Result not found")
    
    if result_obj.metrics:
        return MetricsResponse(**result_obj.metrics)
    
    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(executor, _read_csv_sync, result_obj.filepath)
    
    if "true_value" not in df.columns or "predicted_value" not in df.columns:
        raise HTTPException(status_code=400, detail="Result file missing required columns")
    
    true_vals = df["true_value"].values.astype(float)
    pred_vals = df["predicted_value"].values.astype(float)
    metrics = calculate_metrics(true_vals, pred_vals)
    
    return MetricsResponse(**metrics)
