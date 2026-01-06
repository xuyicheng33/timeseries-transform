import os
import shutil
import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Result, Dataset
from app.schemas import ResultCreate, ResultUpdate, ResultResponse
from app.config import settings
from app.services.utils import calculate_metrics

router = APIRouter(prefix="/api/results", tags=["results"])


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
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    dataset_result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = dataset_result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    content = await file.read()
    
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
    
    with open(filepath, "wb") as f:
        f.write(content)
    
    df = pd.read_csv(filepath)
    result_obj.filepath = str(filepath)
    result_obj.row_count = len(df)
    
    if "true_value" in df.columns and "predicted_value" in df.columns:
        true_vals = df["true_value"].values.astype(float)
        pred_vals = df["predicted_value"].values.astype(float)
        result_obj.metrics = calculate_metrics(true_vals, pred_vals)
    
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
    
    await db.delete(result_obj)
    await db.commit()
    return {"message": "Result deleted"}
