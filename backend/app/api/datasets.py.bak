import os
import shutil
import asyncio
import pandas as pd
import chardet
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from app.database import get_db
from app.models import Dataset, Configuration, Result
from app.schemas import DatasetCreate, DatasetUpdate, DatasetResponse, DatasetPreview
from app.config import settings
from app.services.utils import count_csv_rows

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

executor = ThreadPoolExecutor(max_workers=4)


def _write_file_sync(filepath: str, content: bytes):
    """同步写文件 - 修复：使用 with 确保文件句柄关闭"""
    with open(filepath, "wb") as f:
        f.write(content)


def _parse_csv_sync(filepath: str, encoding: str):
    """同步解析CSV"""
    df = pd.read_csv(filepath, encoding=encoding, nrows=100)
    row_count = count_csv_rows(filepath)
    return df, row_count


@router.post("/upload", response_model=DatasetResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB")
    
    try:
        detected = chardet.detect(content[:10000])
        encoding = detected.get("encoding", "utf-8") or "utf-8"
    except:
        encoding = "utf-8"
    
    dataset = Dataset(name=name, filename=file.filename, filepath="", description=description)
    db.add(dataset)
    await db.flush()
    
    dataset_dir = settings.DATASETS_DIR / str(dataset.id)
    dataset_dir.mkdir(parents=True, exist_ok=True)
    filepath = dataset_dir / "data.csv"
    
    loop = asyncio.get_event_loop()
    # 修复：使用封装函数确保文件句柄关闭
    await loop.run_in_executor(executor, _write_file_sync, str(filepath), content)
    
    try:
        df, row_count = await loop.run_in_executor(executor, _parse_csv_sync, str(filepath), encoding)
    except Exception as e:
        shutil.rmtree(dataset_dir)
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")
    
    dataset.filepath = str(filepath)
    dataset.file_size = len(content)
    dataset.row_count = row_count
    dataset.column_count = len(df.columns)
    dataset.columns = df.columns.tolist()
    
    await db.commit()
    await db.refresh(dataset)
    return dataset


@router.get("", response_model=list[DatasetResponse])
async def list_datasets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dataset).order_by(Dataset.created_at.desc()))
    return result.scalars().all()


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/{dataset_id}/preview", response_model=DatasetPreview)
async def preview_dataset(dataset_id: int, rows: int = 100, db: AsyncSession = Depends(get_db)):
    rows = min(rows, settings.PREVIEW_ROWS)
    
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(executor, lambda: pd.read_csv(dataset.filepath, nrows=rows))
    
    return DatasetPreview(
        columns=df.columns.tolist(),
        data=df.to_dict(orient="records"),
        total_rows=dataset.row_count
    )


@router.get("/{dataset_id}/download")
async def download_dataset(dataset_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return FileResponse(dataset.filepath, filename=dataset.filename, media_type="text/csv")


@router.put("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(dataset_id: int, data: DatasetUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    if data.name is not None:
        dataset.name = data.name
    if data.description is not None:
        dataset.description = data.description
    
    await db.commit()
    await db.refresh(dataset)
    return dataset


@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # 级联删除关联的配置
    configs = await db.execute(select(Configuration).where(Configuration.dataset_id == dataset_id))
    for config in configs.scalars().all():
        # 修复：delete() 是同步方法，不需要 await
        db.delete(config)
    
    # 级联删除关联的结果
    results_query = await db.execute(select(Result).where(Result.dataset_id == dataset_id))
    for res in results_query.scalars().all():
        result_dir = settings.RESULTS_DIR / str(dataset_id) / str(res.id)
        if result_dir.exists():
            shutil.rmtree(result_dir)
        # 修复：delete() 是同步方法，不需要 await
        db.delete(res)
    
    dataset_dir = settings.DATASETS_DIR / str(dataset_id)
    if dataset_dir.exists():
        shutil.rmtree(dataset_dir)
    
    # 修复：delete() 是同步方法，不需要 await
    db.delete(dataset)
    await db.commit()
    return {"message": "Dataset and related data deleted"}
