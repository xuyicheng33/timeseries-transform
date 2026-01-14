"""
配置 API 路由
提供配置的创建、查询、更新、删除等功能
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.database import get_db
from app.models import Configuration, Dataset, User
from app.schemas import (
    ConfigurationCreate, ConfigurationUpdate, ConfigurationResponse, 
    GenerateFilenameRequest, PaginatedResponse
)
from app.services.utils import generate_standard_filename
from app.services.permissions import (
    check_read_access, check_owner_or_admin,
    build_config_query, get_isolation_conditions,
    ResourceType
)
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/configurations", tags=["configurations"])


@router.post("", response_model=ConfigurationResponse)
async def create_configuration(
    data: ConfigurationCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建配置
    
    任何登录用户都可以为公开数据集创建配置，配置归属创建者。
    """
    # 检查数据集是否存在
    result = await db.execute(select(Dataset).where(Dataset.id == data.dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    # 生成标准文件名
    filename = generate_standard_filename(
        dataset_name=dataset.name, 
        channels=data.channels, 
        normalization=data.normalization.value if hasattr(data.normalization, 'value') else str(data.normalization),
        anomaly_enabled=data.anomaly_enabled, 
        anomaly_type=data.anomaly_type.value if data.anomaly_type and hasattr(data.anomaly_type, 'value') else (data.anomaly_type or ""),
        injection_algorithm=data.injection_algorithm.value if data.injection_algorithm and hasattr(data.injection_algorithm, 'value') else (data.injection_algorithm or ""),
        sequence_logic=data.sequence_logic.value if data.sequence_logic and hasattr(data.sequence_logic, 'value') else (data.sequence_logic or ""),
        window_size=data.window_size, 
        stride=data.stride, 
        target_type=data.target_type.value if hasattr(data.target_type, 'value') else str(data.target_type),
        target_k=data.target_k
    )
    
    # 转换枚举为字符串存储
    config_data = data.model_dump()
    for key in ['normalization', 'target_type', 'anomaly_type', 'injection_algorithm', 'sequence_logic']:
        if config_data.get(key) and hasattr(config_data[key], 'value'):
            config_data[key] = config_data[key].value
        elif config_data.get(key) is None:
            config_data[key] = ""
    
    # 创建配置，关联当前用户
    config = Configuration(**config_data, generated_filename=filename, user_id=current_user.id)
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.get("/all", response_model=list[ConfigurationResponse])
async def list_all_configurations(
    dataset_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有配置（不分页，用于下拉选择等场景，限制最多1000条）"""
    query = build_config_query(current_user)
    query = query.order_by(Configuration.created_at.desc())
    
    if dataset_id is not None:
        query = query.where(Configuration.dataset_id == dataset_id)
    
    query = query.limit(1000)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("", response_model=PaginatedResponse[ConfigurationResponse])
async def list_configurations(
    dataset_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取配置列表（分页）"""
    # 参数校验
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    offset = (page - 1) * page_size
    
    # 构建查询条件
    conditions = []
    if dataset_id is not None:
        conditions.append(Configuration.dataset_id == dataset_id)
    
    # 数据隔离过滤
    isolation_conditions, need_join = get_isolation_conditions(current_user, Configuration)
    conditions.extend(isolation_conditions)
    
    # 查询总数
    count_query = select(func.count(Configuration.id))
    if need_join:
        count_query = count_query.join(Dataset)
    for cond in conditions:
        count_query = count_query.where(cond)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 查询分页数据
    query = select(Configuration)
    if need_join:
        query = query.join(Dataset)
    query = query.order_by(Configuration.created_at.desc())
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
async def get_configuration(
    config_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取配置详情"""
    result = await db.execute(select(Configuration).where(Configuration.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    # 检查关联数据集的访问权限
    dataset_result = await db.execute(select(Dataset).where(Dataset.id == config.dataset_id))
    dataset = dataset_result.scalar_one_or_none()
    if dataset:
        check_read_access(config, current_user, ResourceType.CONFIGURATION, parent_dataset=dataset)
    
    return config


@router.put("/{config_id}", response_model=ConfigurationResponse)
async def update_configuration(
    config_id: int, 
    data: ConfigurationUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新配置（所有者或管理员）
    """
    result = await db.execute(select(Configuration).where(Configuration.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    # 仅所有者或管理员可编辑
    check_owner_or_admin(config.user_id, current_user, "编辑配置")
    
    # 获取关联数据集（用于重新生成文件名）
    dataset_result = await db.execute(select(Dataset).where(Dataset.id == config.dataset_id))
    dataset = dataset_result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="关联的数据集不存在")
    
    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="没有提供要更新的字段")
    
    # 转换枚举为字符串
    for key in ['normalization', 'target_type', 'anomaly_type', 'injection_algorithm', 'sequence_logic']:
        if key in update_data and update_data[key] is not None:
            if hasattr(update_data[key], 'value'):
                update_data[key] = update_data[key].value
    
    for key, value in update_data.items():
        setattr(config, key, value)
    
    # 重新生成文件名
    config.generated_filename = generate_standard_filename(
        dataset_name=dataset.name, 
        channels=config.channels, 
        normalization=config.normalization,
        anomaly_enabled=config.anomaly_enabled, 
        anomaly_type=config.anomaly_type or "",
        injection_algorithm=config.injection_algorithm or "", 
        sequence_logic=config.sequence_logic or "",
        window_size=config.window_size, 
        stride=config.stride, 
        target_type=config.target_type, 
        target_k=config.target_k
    )
    
    await db.commit()
    await db.refresh(config)
    return config


@router.delete("/{config_id}")
async def delete_configuration(
    config_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除配置（所有者或管理员）
    """
    result = await db.execute(select(Configuration).where(Configuration.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    # 仅所有者或管理员可删除
    check_owner_or_admin(config.user_id, current_user, "删除配置")
    
    await db.delete(config)
    await db.commit()
    return {"message": "配置已删除"}


@router.post("/generate-name")
async def generate_filename_api(
    data: GenerateFilenameRequest,
    current_user: User = Depends(get_current_user)
):
    """生成标准文件名"""
    filename = generate_standard_filename(
        dataset_name=data.dataset_name, 
        channels=data.channels, 
        normalization=data.normalization.value if hasattr(data.normalization, 'value') else str(data.normalization),
        anomaly_enabled=data.anomaly_enabled, 
        anomaly_type=data.anomaly_type or "",
        injection_algorithm=data.injection_algorithm or "", 
        sequence_logic=data.sequence_logic or "",
        window_size=data.window_size, 
        stride=data.stride, 
        target_type=data.target_type.value if hasattr(data.target_type, 'value') else str(data.target_type),
        target_k=data.target_k
    )
    return {"filename": filename}
