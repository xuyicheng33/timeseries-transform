import os
import shutil
import pandas as pd
import chardet
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.database import get_db
from app.models import Dataset
from app.schemas import DatasetCreate, DatasetUpdate, DatasetResponse, DatasetPreview
from app.config import settings

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


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
        raise HTTPException(status_code=400, detail="File too large")
    
    try:
        detected = chardet.detect(content)
        encoding = detected.get("encoding", "utf-8")
    except:
        encoding = "utf-8"
    
    dataset = Dataset(name=name, filename=file.filename, filepath="", description=description)
    db.add(dataset)
    await db.flush()
    
    dataset_dir = settings.DATASETS_DIR / str(dataset.id)
    dataset_dir.mkdir(parents=True, exist_ok=True)
    filepath = dataset_dir / "data.csv"
    
    with open(filepath, "wb") as f:
        f.write(content)
    
    try:
        df = pd.read_csv(filepath, encoding=encoding, nrows=1000)
        row_count = len(pd.read_csv(filepath, encoding=encoding))
    except:
        df = pd.read_csv(filepath, nrows=1000)
        row_count = len(pd.read_csv(filepath))
    
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
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    df = pd.read_csv(dataset.filepath, nrows=rows)
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
    
    dataset_dir = settings.DATASETS_DIR / str(dataset_id)
    if dataset_dir.exists():
        shutil.rmtree(dataset_dir)
    
    await db.delete(dataset)
    await db.commit()
    return {"message": "Dataset deleted"}
