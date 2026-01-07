from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Configuration, Dataset
from app.schemas import ConfigurationCreate, ConfigurationUpdate, ConfigurationResponse, GenerateFilenameRequest, PaginatedResponse
from app.services.utils import generate_standard_filename

router = APIRouter(prefix="/api/configurations", tags=["configurations"])


@router.post("", response_model=ConfigurationResponse)
async def create_configuration(data: ConfigurationCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dataset).where(Dataset.id == data.dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
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


@router.get("", response_model=PaginatedResponse[ConfigurationResponse])
async def list_configurations(
    dataset_id: int = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """获取配置列表（分页）"""
    # 参数校验
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    offset = (page - 1) * page_size
    
    # 构建查询条件
    conditions = []
    if dataset_id:
        conditions.append(Configuration.dataset_id == dataset_id)
    
    # 查询总数
    count_query = select(func.count(Configuration.id))
    if conditions:
        for cond in conditions:
            count_query = count_query.where(cond)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 查询分页数据
    query = select(Configuration).order_by(Configuration.created_at.desc())
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


@router.get("/{config_id}", response_model=ConfigurationResponse)
async def get_configuration(config_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Configuration).where(Configuration.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return config


@router.put("/{config_id}", response_model=ConfigurationResponse)
async def update_configuration(config_id: int, data: ConfigurationUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Configuration).where(Configuration.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
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
        raise HTTPException(status_code=404, detail="配置不存在")
    db.delete(config)
    await db.commit()
    return {"message": "配置已删除"}


@router.post("/generate-name")
async def generate_filename_api(data: GenerateFilenameRequest):
    filename = generate_standard_filename(
        dataset_name=data.dataset_name, channels=data.channels, normalization=data.normalization,
        anomaly_enabled=data.anomaly_enabled, anomaly_type=data.anomaly_type or "",
        injection_algorithm=data.injection_algorithm or "", sequence_logic=data.sequence_logic or "",
        window_size=data.window_size, stride=data.stride, target_type=data.target_type, target_k=data.target_k
    )
    return {"filename": filename}
