from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Configuration, Dataset
from app.schemas import ConfigurationCreate, ConfigurationUpdate, ConfigurationResponse, GenerateFilenameRequest
from app.services.utils import generate_standard_filename

router = APIRouter(prefix="/api/configurations", tags=["configurations"])


@router.post("", response_model=ConfigurationResponse)
async def create_configuration(data: ConfigurationCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dataset).where(Dataset.id == data.dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    filename = generate_standard_filename(
        dataset_name=dataset.name, channels=data.channels, normalization=data.normalization,
        anomaly_enabled=data.anomaly_enabled, anomaly_type=data.anomaly_type or "",
        injection_algorithm=data.injection_algorithm or "", sequence_logic=data.sequence_logic or "",
        window_size=data.window_size, stride=data.stride, target_type=data.target_type, target_k=data.target_k
    )
    
    config = Configuration(**data.model_dump(), generated_filename=filename)
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.get("", response_model=list[ConfigurationResponse])
async def list_configurations(dataset_id: int = None, db: AsyncSession = Depends(get_db)):
    query = select(Configuration).order_by(Configuration.created_at.desc())
    if dataset_id:
        query = query.where(Configuration.dataset_id == dataset_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{config_id}", response_model=ConfigurationResponse)
async def get_configuration(config_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Configuration).where(Configuration.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config


@router.put("/{config_id}", response_model=ConfigurationResponse)
async def update_configuration(config_id: int, data: ConfigurationUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Configuration).where(Configuration.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(config, key, value)
    
    dataset_result = await db.execute(select(Dataset).where(Dataset.id == config.dataset_id))
    dataset = dataset_result.scalar_one_or_none()
    if dataset:
        config.generated_filename = generate_standard_filename(
            dataset_name=dataset.name, channels=config.channels, normalization=config.normalization,
            anomaly_enabled=config.anomaly_enabled, anomaly_type=config.anomaly_type or "",
            injection_algorithm=config.injection_algorithm or "", sequence_logic=config.sequence_logic or "",
            window_size=config.window_size, stride=config.stride, target_type=config.target_type, target_k=config.target_k
        )
    
    await db.commit()
    await db.refresh(config)
    return config


@router.delete("/{config_id}")
async def delete_configuration(config_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Configuration).where(Configuration.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    await db.delete(config)
    await db.commit()
    return {"message": "Configuration deleted"}


@router.post("/generate-name")
async def generate_filename_api(data: GenerateFilenameRequest):
    filename = generate_standard_filename(
        dataset_name=data.dataset_name, channels=data.channels, normalization=data.normalization,
        anomaly_enabled=data.anomaly_enabled, anomaly_type=data.anomaly_type or "",
        injection_algorithm=data.injection_algorithm or "", sequence_logic=data.sequence_logic or "",
        window_size=data.window_size, stride=data.stride, target_type=data.target_type, target_k=data.target_k
    )
    return {"filename": filename}
