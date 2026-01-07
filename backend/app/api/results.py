import os
import re
import shutil
import asyncio
import aiofiles
import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from concurrent.futures import ThreadPoolExecutor

from app.database import get_db
from app.models import Result, Dataset, Configuration
from app.schemas import ResultCreate, ResultUpdate, ResultResponse, PaginatedResponse
from app.config import settings
from app.services.utils import calculate_metrics, sanitize_filename, safe_rmtree

router = APIRouter(prefix="/api/results", tags=["results"])

executor = ThreadPoolExecutor(max_workers=4)

REQUIRED_COLUMNS = {"true_value", "predicted_value"}


def _parse_result_csv_sync(filepath: str):
    """同步解析结果CSV"""
    return pd.read_csv(filepath)


@router.post("/upload", response_model=ResultResponse)
async def upload_result(
    file: UploadFile = File(...),
    name: str = Form(...),
    dataset_id: int = Form(...),
    algo_name: str = Form(..., alias="model_name"),  # 使用 alias 保持 API 兼容
    configuration_id: int = Form(None),
    algo_version: str = Form("", alias="model_version"),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    # 大小写不敏感的扩展名校验
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="仅支持 CSV 文件")
    
    # 清理文件名
    safe_filename = sanitize_filename(file.filename)
    
    dataset_result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = dataset_result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    # 校验 configuration_id 归属
    if configuration_id is not None:
        config_result = await db.execute(select(Configuration).where(Configuration.id == configuration_id))
        config = config_result.scalar_one_or_none()
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")
        if config.dataset_id != dataset_id:
            raise HTTPException(status_code=400, detail="配置不属于指定的数据集")
    
    result_obj = Result(
        name=name, dataset_id=dataset_id, configuration_id=configuration_id,
        filename=safe_filename, filepath="", algo_name=algo_name,
        algo_version=algo_version, description=description
    )
    db.add(result_obj)
    await db.flush()
    
    result_dir = settings.RESULTS_DIR / str(dataset_id) / str(result_obj.id)
    result_dir.mkdir(parents=True, exist_ok=True)
    filepath = result_dir / "prediction.csv"
    
    # 流式写入文件
    total_size = 0
    try:
        async with aiofiles.open(filepath, 'wb') as f:
            while chunk := await file.read(1024 * 1024):  # 每次读取1MB
                total_size += len(chunk)
                if total_size > settings.MAX_UPLOAD_SIZE:
                    await f.close()
                    shutil.rmtree(result_dir, ignore_errors=True)
                    await db.rollback()
                    raise HTTPException(
                        status_code=400,
                        detail=f"文件过大，最大允许 {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB"
                    )
                await f.write(chunk)
    except HTTPException:
        raise
    except Exception:
        shutil.rmtree(result_dir, ignore_errors=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="文件上传失败")
    
    loop = asyncio.get_running_loop()
    
    try:
        df = await loop.run_in_executor(executor, _parse_result_csv_sync, str(filepath))
    except Exception:
        shutil.rmtree(result_dir, ignore_errors=True)
        await db.rollback()
        raise HTTPException(status_code=400, detail="CSV 文件解析失败，请检查文件格式")
    
    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        shutil.rmtree(result_dir, ignore_errors=True)
        await db.rollback()
        raise HTTPException(
            status_code=400, 
            detail=f"缺少必需列: {missing_cols}。文件必须包含 'true_value' 和 'predicted_value' 列"
        )
    
    result_obj.filepath = str(filepath)
    result_obj.row_count = len(df)
    
    # 计算指标
    try:
        true_vals = pd.to_numeric(df["true_value"], errors='coerce').values
        pred_vals = pd.to_numeric(df["predicted_value"], errors='coerce').values
        
        # 检查是否有无法转换的值（NaN）
        if np.isnan(true_vals).any() or np.isnan(pred_vals).any():
            raise ValueError("列中包含无法转换为数值的数据")
        
        result_obj.metrics = calculate_metrics(true_vals, pred_vals)
    except Exception:
        shutil.rmtree(result_dir, ignore_errors=True)
        await db.rollback()
        raise HTTPException(status_code=400, detail="数据格式错误，true_value 和 predicted_value 必须为数值类型")
    
    await db.commit()
    await db.refresh(result_obj)
    return result_obj


@router.get("", response_model=PaginatedResponse[ResultResponse])
async def list_results(
    dataset_id: int = None,
    algo_name: str = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """获取结果列表（分页）"""
    # 参数校验
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    offset = (page - 1) * page_size
    
    # 构建查询条件
    conditions = []
    if dataset_id:
        conditions.append(Result.dataset_id == dataset_id)
    if algo_name:
        conditions.append(Result.algo_name == algo_name)
    
    # 查询总数
    count_query = select(func.count(Result.id))
    if conditions:
        for cond in conditions:
            count_query = count_query.where(cond)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 查询分页数据
    query = select(Result).order_by(Result.created_at.desc())
    if conditions:
        for cond in conditions:
            query = query.where(cond)
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{result_id}", response_model=ResultResponse)
async def get_result(result_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(status_code=404, detail="结果不存在")
    return result_obj


@router.get("/{result_id}/download")
async def download_result(result_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(status_code=404, detail="结果不存在")
    
    # 检查文件是否存在
    if not os.path.exists(result_obj.filepath):
        raise HTTPException(status_code=404, detail="结果文件不存在，可能已被删除")
    
    return FileResponse(result_obj.filepath, filename=result_obj.filename, media_type="text/csv")


@router.put("/{result_id}", response_model=ResultResponse)
async def update_result(result_id: int, data: ResultUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(status_code=404, detail="结果不存在")
    
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
        raise HTTPException(status_code=404, detail="结果不存在")
    
    loop = asyncio.get_running_loop()
    
    result_dir = settings.RESULTS_DIR / str(result_obj.dataset_id) / str(result_id)
    if result_dir.exists():
        # 放入线程池异步删除
        await loop.run_in_executor(executor, safe_rmtree, str(result_dir))
    
    db.delete(result_obj)
    await db.commit()
    return {"message": "结果已删除"}
