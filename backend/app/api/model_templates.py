"""
模型模板 API 路由
提供模型模板的增删改查、预置模板初始化等功能
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.database import get_db
from app.models import ModelTemplate, User
from app.schemas import (
    ModelTemplateCreate, ModelTemplateUpdate, ModelTemplateResponse, 
    ModelTemplateBrief, PaginatedResponse, PRESET_MODEL_TEMPLATES
)
from app.config import settings
from app.services.permissions import check_owner_or_admin
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/model-templates", tags=["model-templates"])


@router.post("/init-presets", response_model=dict)
async def init_preset_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    初始化预置模型模板（仅管理员可用）
    如果模板已存在则跳过
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可以初始化预置模板")
    
    created_count = 0
    skipped_count = 0
    
    for template_data in PRESET_MODEL_TEMPLATES:
        # 检查是否已存在同名系统模板
        existing = await db.execute(
            select(ModelTemplate).where(
                ModelTemplate.name == template_data["name"],
                ModelTemplate.is_system == True
            )
        )
        if existing.scalar_one_or_none():
            skipped_count += 1
            continue
        
        # 创建新模板
        template = ModelTemplate(
            name=template_data["name"],
            version=template_data.get("version", "1.0"),
            category=template_data.get("category", "deep_learning"),
            description=template_data.get("description", ""),
            hyperparameters=template_data.get("hyperparameters", {}),
            training_config=template_data.get("training_config", {}),
            task_types=template_data.get("task_types", []),
            recommended_features=template_data.get("recommended_features", ""),
            is_system=True,
            is_public=True,
            user_id=None
        )
        db.add(template)
        created_count += 1
    
    await db.commit()
    
    return {
        "message": f"预置模板初始化完成",
        "created": created_count,
        "skipped": skipped_count
    }


@router.post("", response_model=ModelTemplateResponse)
async def create_template(
    data: ModelTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建模型模板"""
    template = ModelTemplate(
        name=data.name,
        version=data.version,
        category=data.category,
        description=data.description or "",
        hyperparameters=data.hyperparameters,
        training_config=data.training_config,
        task_types=data.task_types,
        recommended_features=data.recommended_features or "",
        is_system=False,
        is_public=data.is_public,
        user_id=current_user.id
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.get("", response_model=PaginatedResponse[ModelTemplateResponse])
async def list_templates(
    page: int = 1,
    page_size: int = 20,
    category: str = None,
    search: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取模型模板列表（分页）"""
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    offset = (page - 1) * page_size
    
    # 构建查询条件：系统模板 + 公开模板 + 自己的模板
    conditions = [
        or_(
            ModelTemplate.is_system == True,
            ModelTemplate.is_public == True,
            ModelTemplate.user_id == current_user.id
        )
    ]
    
    if category:
        conditions.append(ModelTemplate.category == category)
    
    if search:
        conditions.append(
            or_(
                ModelTemplate.name.ilike(f"%{search}%"),
                ModelTemplate.description.ilike(f"%{search}%")
            )
        )
    
    # 查询总数
    count_query = select(func.count(ModelTemplate.id))
    for cond in conditions:
        count_query = count_query.where(cond)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 查询分页数据
    query = select(ModelTemplate).order_by(
        ModelTemplate.is_system.desc(),  # 系统模板优先
        ModelTemplate.usage_count.desc(),
        ModelTemplate.created_at.desc()
    )
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


@router.get("/all", response_model=list[ModelTemplateBrief])
async def list_all_templates(
    category: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有模型模板（不分页，用于下拉选择）"""
    conditions = [
        or_(
            ModelTemplate.is_system == True,
            ModelTemplate.is_public == True,
            ModelTemplate.user_id == current_user.id
        )
    ]
    
    if category:
        conditions.append(ModelTemplate.category == category)
    
    query = select(ModelTemplate).order_by(
        ModelTemplate.is_system.desc(),
        ModelTemplate.name.asc()
    )
    for cond in conditions:
        query = query.where(cond)
    query = query.limit(200)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/categories", response_model=list[dict])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有模型类别"""
    result = await db.execute(
        select(ModelTemplate.category, func.count(ModelTemplate.id))
        .group_by(ModelTemplate.category)
        .order_by(func.count(ModelTemplate.id).desc())
    )
    
    categories = [
        {"value": row[0], "label": row[0], "count": row[1]}
        for row in result.all()
    ]
    
    # 添加预定义类别（如果不存在）
    predefined = [
        {"value": "deep_learning", "label": "深度学习"},
        {"value": "traditional", "label": "传统方法"},
        {"value": "ensemble", "label": "集成方法"},
        {"value": "hybrid", "label": "混合方法"},
    ]
    
    existing_values = {c["value"] for c in categories}
    for p in predefined:
        if p["value"] not in existing_values:
            categories.append({**p, "count": 0})
    
    return categories


@router.get("/{template_id}", response_model=ModelTemplateResponse)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取模型模板详情"""
    result = await db.execute(
        select(ModelTemplate).where(ModelTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="模型模板不存在")
    
    # 权限检查：系统模板、公开模板、自己的模板
    if not (template.is_system or template.is_public or template.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权访问此模板")
    
    return template


@router.put("/{template_id}", response_model=ModelTemplateResponse)
async def update_template(
    template_id: int,
    data: ModelTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新模型模板（所有者或管理员）
    
    系统模板仅管理员可修改，用户模板仅所有者或管理员可修改。
    """
    result = await db.execute(
        select(ModelTemplate).where(ModelTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="模型模板不存在")
    
    # 使用统一的所有者或管理员检查
    check_owner_or_admin(template.user_id, current_user, "编辑模型模板")
    
    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="没有提供要更新的字段")
    
    for key, value in update_data.items():
        setattr(template, key, value)
    
    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除模型模板（所有者或管理员）
    
    系统模板仅管理员可删除，用户模板仅所有者或管理员可删除。
    """
    result = await db.execute(
        select(ModelTemplate).where(ModelTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="模型模板不存在")
    
    # 使用统一的所有者或管理员检查
    check_owner_or_admin(template.user_id, current_user, "删除模型模板")
    
    await db.delete(template)
    await db.commit()
    
    return {"message": "模型模板已删除"}


@router.post("/{template_id}/duplicate", response_model=ModelTemplateResponse)
async def duplicate_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """复制模型模板（创建副本）"""
    result = await db.execute(
        select(ModelTemplate).where(ModelTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="模型模板不存在")
    
    # 权限检查
    if not (template.is_system or template.is_public or template.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权复制此模板")
    
    # 创建副本
    new_template = ModelTemplate(
        name=f"{template.name} (副本)",
        version=template.version,
        category=template.category,
        description=template.description,
        hyperparameters=template.hyperparameters.copy() if template.hyperparameters else {},
        training_config=template.training_config.copy() if template.training_config else {},
        task_types=template.task_types.copy() if template.task_types else [],
        recommended_features=template.recommended_features,
        is_system=False,
        is_public=False,
        user_id=current_user.id
    )
    db.add(new_template)
    await db.commit()
    await db.refresh(new_template)
    
    return new_template


@router.post("/{template_id}/increment-usage")
async def increment_usage(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """增加模板使用次数（仅当用户有权访问该模板时）"""
    result = await db.execute(
        select(ModelTemplate).where(ModelTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="模型模板不存在")
    
    # 权限检查：只有能访问模板的用户才能增加使用次数
    if not (template.is_system or template.is_public or template.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权访问此模板")
    
    template.usage_count = (template.usage_count or 0) + 1
    await db.commit()
    
    return {"success": True}

