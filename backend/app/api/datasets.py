import os
import re
import shutil
import asyncio
import aiofiles
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
from app.schemas import DatasetCreate, DatasetUpdate, DatasetResponse, DatasetPreview, PaginatedResponse
from app.config import settings
from app.services.utils import count_csv_rows, sanitize_filename, safe_rmtree, validate_form_field, validate_description

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

executor = ThreadPoolExecutor(max_workers=4)


def _parse_csv_sync(filepath: str, encoding: str):
    """同步解析CSV"""
    df = pd.read_csv(filepath, encoding=encoding, nrows=100)
    row_count = count_csv_rows(filepath, encoding)
    return df, row_count


def _detect_encoding_sync(filepath: str) -> str:
    """同步检测文件编码（只读取前10KB）"""
    with open(filepath, 'rb') as f:
        raw = f.read(10240)
    try:
        detected = chardet.detect(raw)
        return detected.get("encoding", "utf-8") or "utf-8"
    except:
        return "utf-8"


@router.post("/upload", response_model=DatasetResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    # 表单字段校验
    name = validate_form_field(name, "数据集名称", max_length=255, min_length=1)
    description = validate_description(description, max_length=1000)
    
    # 大小写不敏感的扩展名校验
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="仅支持 CSV 文件")
    
    # 清理文件名
    safe_filename = sanitize_filename(file.filename)
    
    # 先创建数据库记录获取ID
    dataset = Dataset(name=name, filename=safe_filename, filepath="", description=description)
    db.add(dataset)
    await db.flush()
    
    dataset_dir = settings.DATASETS_DIR / str(dataset.id)
    dataset_dir.mkdir(parents=True, exist_ok=True)
    filepath = dataset_dir / "data.csv"
    
    loop = asyncio.get_running_loop()
    
    # 流式写入文件，边读边写边检查大小
    total_size = 0
    try:
        async with aiofiles.open(filepath, 'wb') as f:
            while chunk := await file.read(1024 * 1024):  # 每次读取1MB
                total_size += len(chunk)
                if total_size > settings.MAX_UPLOAD_SIZE:
                    # 超过大小限制，清理并报错（异步删除）
                    await f.close()
                    await loop.run_in_executor(executor, safe_rmtree, str(dataset_dir))
                    await db.rollback()
                    raise HTTPException(
                        status_code=400, 
                        detail=f"文件过大，最大允许 {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB"
                    )
                await f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        await loop.run_in_executor(executor, safe_rmtree, str(dataset_dir))
        await db.rollback()
        raise HTTPException(status_code=500, detail="文件上传失败")
    
    # 检测编码
    encoding = await loop.run_in_executor(executor, _detect_encoding_sync, str(filepath))
    
    # 解析CSV
    try:
        df, row_count = await loop.run_in_executor(executor, _parse_csv_sync, str(filepath), encoding)
    except Exception as e:
        await loop.run_in_executor(executor, safe_rmtree, str(dataset_dir))
        await db.rollback()
        raise HTTPException(status_code=400, detail="CSV 文件解析失败，请检查文件格式")
    
    dataset.filepath = str(filepath)
    dataset.file_size = total_size
    dataset.row_count = row_count
    dataset.column_count = len(df.columns)
    dataset.columns = df.columns.tolist()
    dataset.encoding = encoding
    
    await db.commit()
    await db.refresh(dataset)
    return dataset


@router.get("/all", response_model=list[DatasetResponse])
async def list_all_datasets(db: AsyncSession = Depends(get_db)):
    """获取所有数据集（不分页，用于下拉选择等场景，限制最多1000条）"""
    result = await db.execute(
        select(Dataset)
        .order_by(Dataset.created_at.desc())
        .limit(1000)
    )
    return result.scalars().all()


@router.get("", response_model=PaginatedResponse[DatasetResponse])
async def list_datasets(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """获取数据集列表（分页）"""
    # 参数校验
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    offset = (page - 1) * page_size
    
    # 查询总数
    from sqlalchemy import func
    total_result = await db.execute(select(func.count(Dataset.id)))
    total = total_result.scalar() or 0
    
    # 查询分页数据
    result = await db.execute(
        select(Dataset)
        .order_by(Dataset.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = result.scalars().all()
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    return dataset


@router.get("/{dataset_id}/preview", response_model=DatasetPreview)
async def preview_dataset(dataset_id: int, rows: int = 100, db: AsyncSession = Depends(get_db)):
    # 防止 0/负数
    rows = max(1, min(rows, settings.PREVIEW_ROWS))
    
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    # 检查文件是否存在
    if not os.path.exists(dataset.filepath):
        raise HTTPException(status_code=404, detail="数据集文件不存在，可能已被删除")
    
    loop = asyncio.get_running_loop()
    try:
        df = await loop.run_in_executor(executor, lambda: pd.read_csv(dataset.filepath, encoding=dataset.encoding or 'utf-8', nrows=rows))
    except Exception:
        raise HTTPException(status_code=500, detail="读取数据集文件失败")
    
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
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    # 检查文件是否存在
    if not os.path.exists(dataset.filepath):
        raise HTTPException(status_code=404, detail="数据集文件不存在，可能已被删除")
    
    return FileResponse(dataset.filepath, filename=dataset.filename, media_type="text/csv")


@router.put("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(dataset_id: int, data: DatasetUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
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
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    loop = asyncio.get_running_loop()
    
    # 级联删除关联的配置
    configs = await db.execute(select(Configuration).where(Configuration.dataset_id == dataset_id))
    for config in configs.scalars().all():
        db.delete(config)
    
    # 级联删除关联的结果（异步删除文件）
    results_query = await db.execute(select(Result).where(Result.dataset_id == dataset_id))
    for res in results_query.scalars().all():
        result_dir = settings.RESULTS_DIR / str(dataset_id) / str(res.id)
        if result_dir.exists():
            # 放入线程池异步删除，避免阻塞
            await loop.run_in_executor(executor, safe_rmtree, str(result_dir))
        db.delete(res)
    
    # 删除数据集目录（异步）
    dataset_dir = settings.DATASETS_DIR / str(dataset_id)
    if dataset_dir.exists():
        await loop.run_in_executor(executor, safe_rmtree, str(dataset_dir))
    
    db.delete(dataset)
    await db.commit()
    return {"message": "数据集及相关数据已删除"}
