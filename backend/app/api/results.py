import os
import shutil
import asyncio
import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from concurrent.futures import ThreadPoolExecutor

from app.database import get_db
from app.models import Result, Dataset
from app.schemas import ResultCreate, ResultUpdate, ResultResponse
from app.config import settings
from app.services.utils import calculate_metrics

router = APIRouter(prefix="/api/results", tags=["results"])

executor = ThreadPoolExecutor(max_workers=4)

REQUIRED_COLUMNS = {"true_value", "predicted_value"}


def _write_file_sync(filepath: str, content: bytes):
    """同步写文件 - 修复：使用 with 确保文件句柄关闭"""
    with open(filepath, "wb") as f:
        f.write(content)


def _parse_result_csv_sync(filepath: str):
    """同步解析结果CSV"""
    return pd.read_csv(filepath)


@router.post("/upload", response_model=ResultResponse)
async def upload_result(
    file: UploadFile = File(...),
    name: str = Form(...),
    dataset_id: int = Form(...),
    model_name: str = Form(...),
    configuration_id: int = Form(None),
    model_version: str = Form(""),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    # 修复：大小写不敏感的扩展名校验
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    content = await file.read()
    
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB")
    
    dataset_result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = dataset_result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    result_obj = Result(
        name=name, dataset_id=dataset_id, configuration_id=configuration_id,
        filename=file.filename, filepath="", model_name=model_name,
        model_version=model_version, description=description
    )
    db.add(result_obj)
    await db.flush()
    
    result_dir = settings.RESULTS_DIR / str(dataset_id) / str(result_obj.id)
    result_dir.mkdir(parents=True, exist_ok=True)
    filepath = result_dir / "prediction.csv"
    
    loop = asyncio.get_running_loop()
    # 修复：使用封装函数确保文件句柄关闭
    await loop.run_in_executor(executor, _write_file_sync, str(filepath), content)
    
    try:
        df = await loop.run_in_executor(executor, _parse_result_csv_sync, str(filepath))
    except Exception as e:
        shutil.rmtree(result_dir)
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")
    
    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        shutil.rmtree(result_dir)
        await db.rollback()
        raise HTTPException(
            status_code=400, 
            detail=f"Missing required columns: {missing_cols}. File must contain 'true_value' and 'predicted_value' columns."
        )
    
    result_obj.filepath = str(filepath)
    result_obj.row_count = len(df)
    
    # 修复：捕获类型转换异常，避免留下孤儿文件
    try:
        true_vals = pd.to_numeric(df["true_value"], errors='coerce').values
        pred_vals = pd.to_numeric(df["predicted_value"], errors='coerce').values
        
        # 检查是否有无法转换的值（NaN）
        if np.isnan(true_vals).any() or np.isnan(pred_vals).any():
            raise ValueError("Columns contain non-numeric values that cannot be converted to float")
        
        result_obj.metrics = calculate_metrics(true_vals, pred_vals)
    except Exception as e:
        shutil.rmtree(result_dir)
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Invalid numeric data: {str(e)}")
    
    await db.commit()
    await db.refresh(result_obj)
    return result_obj


@router.get("", response_model=list[ResultResponse])
async def list_results(dataset_id: int = None, model_name: str = None, db: AsyncSession = Depends(get_db)):
    query = select(Result).order_by(Result.created_at.desc())
    if dataset_id:
        query = query.where(Result.dataset_id == dataset_id)
    if model_name:
        query = query.where(Result.model_name == model_name)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{result_id}", response_model=ResultResponse)
async def get_result(result_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(status_code=404, detail="Result not found")
    return result_obj


@router.get("/{result_id}/download")
async def download_result(result_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(status_code=404, detail="Result not found")
    return FileResponse(result_obj.filepath, filename=result_obj.filename, media_type="text/csv")


@router.put("/{result_id}", response_model=ResultResponse)
async def update_result(result_id: int, data: ResultUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(status_code=404, detail="Result not found")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(result_obj, key, value)
    
    await db.commit()
    await db.refresh(result_obj)
    return result_obj


@router.delete("/{result_id}")
async def delete_result(result_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(status_code=404, detail="Result not found")
    
    result_dir = settings.RESULTS_DIR / str(result_obj.dataset_id) / str(result_id)
    if result_dir.exists():
        shutil.rmtree(result_dir)
    
    # 修复：delete() 是同步方法，不需要 await
    db.delete(result_obj)
    await db.commit()
    return {"message": "Result deleted"}
