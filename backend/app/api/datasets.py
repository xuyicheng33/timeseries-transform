"""
数据集 API 路由
提供数据集的上传、预览、下载、更新、删除等功能
"""
import os
import aiofiles
import pandas as pd
import chardet
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional

from app.database import get_db
from app.models import Dataset, Configuration, Result, User
from app.schemas import DatasetCreate, DatasetUpdate, DatasetResponse, DatasetPreview, PaginatedResponse
from app.config import settings
from app.services.utils import count_csv_rows, sanitize_filename, safe_rmtree, validate_form_field, validate_description
from app.services.executor import run_in_executor
from app.services.security import validate_filepath
from app.api.auth import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


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


def _build_dataset_query(user: Optional[User], base_query=None):
    """
    构建数据集查询，根据数据隔离配置过滤
    
    Args:
        user: 当前用户（可选）
        base_query: 基础查询（可选）
    
    Returns:
        过滤后的查询
    """
    if base_query is None:
        base_query = select(Dataset)
    
    if settings.ENABLE_DATA_ISOLATION:
        if user is None:
            # 匿名用户只能看到公开数据
            base_query = base_query.where(Dataset.is_public == True)
        elif not user.is_admin:
            # 普通用户只能看到自己的数据或公开数据
            base_query = base_query.where(
                or_(
                    Dataset.user_id == user.id,
                    Dataset.is_public == True
                )
            )
        # 管理员不做过滤，可以看到所有数据
    # 团队共享模式：不过滤
    
    return base_query


def _check_dataset_permission(dataset: Dataset, user: Optional[User], action: str = "访问") -> None:
    """
    检查用户对数据集的操作权限
    
    Args:
        dataset: 数据集对象
        user: 当前用户
        action: 操作类型（用于错误提示）
    
    Raises:
        HTTPException: 无权限时抛出 401/403
    """
    if not settings.ENABLE_DATA_ISOLATION:
        # 团队共享模式：所有人都有权限
        return
    
    # 公开数据集允许匿名读取
    if dataset.is_public and action in ["访问", "下载", "预览"]:
        return
    
    # 非公开数据或写操作需要登录
    if user is None:
        raise HTTPException(status_code=401, detail="请先登录")
    
    # 管理员有所有权限
    if user.is_admin:
        return
    
    # 所有者有所有权限
    if dataset.user_id == user.id:
        return
    
    raise HTTPException(status_code=403, detail=f"无权{action}此数据集")


@router.post("/upload", response_model=DatasetResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    is_public: bool = Form(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # 需要登录
):
    """上传数据集"""
    # 表单字段校验
    name = validate_form_field(name, "数据集名称", max_length=255, min_length=1)
    description = validate_description(description, max_length=1000)
    
    # 大小写不敏感的扩展名校验
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="仅支持 CSV 文件")
    
    # 清理文件名
    safe_filename = sanitize_filename(file.filename)
    
    # 创建数据库记录，关联当前用户
    dataset = Dataset(
        name=name, 
        filename=safe_filename, 
        filepath="", 
        description=description,
        user_id=current_user.id,
        is_public=is_public
    )
    db.add(dataset)
    await db.flush()
    
    dataset_dir = settings.DATASETS_DIR / str(dataset.id)
    dataset_dir.mkdir(parents=True, exist_ok=True)
    filepath = dataset_dir / "data.csv"
    
    # 流式写入文件，边读边写边检查大小
    total_size = 0
    try:
        async with aiofiles.open(filepath, 'wb') as f:
            while chunk := await file.read(1024 * 1024):  # 每次读取1MB
                total_size += len(chunk)
                if total_size > settings.MAX_UPLOAD_SIZE:
                    # 超过大小限制，清理并报错
                    await f.close()
                    await run_in_executor(safe_rmtree, str(dataset_dir))
                    await db.rollback()
                    raise HTTPException(
                        status_code=400, 
                        detail=f"文件过大，最大允许 {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB"
                    )
                await f.write(chunk)
    except HTTPException:
        raise
    except Exception:
        await run_in_executor(safe_rmtree, str(dataset_dir))
        await db.rollback()
        raise HTTPException(status_code=500, detail="文件上传失败")
    
    # 检测编码
    encoding = await run_in_executor(_detect_encoding_sync, str(filepath))
    
    # 解析CSV
    try:
        df, row_count = await run_in_executor(_parse_csv_sync, str(filepath), encoding)
    except Exception:
        await run_in_executor(safe_rmtree, str(dataset_dir))
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
async def list_all_datasets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """获取所有数据集（不分页，用于下拉选择等场景，限制最多1000条）"""
    query = _build_dataset_query(current_user)
    query = query.order_by(Dataset.created_at.desc()).limit(1000)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("", response_model=PaginatedResponse[DatasetResponse])
async def list_datasets(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """获取数据集列表（分页）"""
    # 参数校验
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    offset = (page - 1) * page_size
    
    # 构建基础查询条件
    base_conditions = []
    if settings.ENABLE_DATA_ISOLATION:
        if current_user is None:
            # 匿名用户只能看到公开数据
            base_conditions.append(Dataset.is_public == True)
        elif not current_user.is_admin:
            # 普通用户只能看到自己的数据或公开数据
            base_conditions.append(
                or_(Dataset.user_id == current_user.id, Dataset.is_public == True)
            )
        # 管理员不做过滤
    
    # 查询总数
    count_query = select(func.count(Dataset.id))
    for cond in base_conditions:
        count_query = count_query.where(cond)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 查询分页数据
    query = select(Dataset).order_by(Dataset.created_at.desc())
    for cond in base_conditions:
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


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """获取数据集详情"""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    _check_dataset_permission(dataset, current_user, "访问")
    return dataset


@router.get("/{dataset_id}/preview", response_model=DatasetPreview)
async def preview_dataset(
    dataset_id: int, 
    rows: int = 100, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """预览数据集"""
    # 防止 0/负数
    rows = max(1, min(rows, settings.PREVIEW_ROWS))
    
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    _check_dataset_permission(dataset, current_user, "预览")
    
    # 检查文件是否存在
    if not os.path.exists(dataset.filepath):
        raise HTTPException(status_code=404, detail="数据集文件不存在，可能已被删除")
    
    # 验证文件路径安全
    if not validate_filepath(dataset.filepath):
        raise HTTPException(status_code=403, detail="文件路径不安全")
    
    try:
        df = await run_in_executor(
            lambda: pd.read_csv(dataset.filepath, encoding=dataset.encoding or 'utf-8', nrows=rows)
        )
    except Exception:
        raise HTTPException(status_code=500, detail="读取数据集文件失败")
    
    return DatasetPreview(
        columns=df.columns.tolist(),
        data=df.to_dict(orient="records"),
        total_rows=dataset.row_count
    )


@router.get("/{dataset_id}/download")
async def download_dataset(
    dataset_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """下载数据集"""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    _check_dataset_permission(dataset, current_user, "下载")
    
    # 检查文件是否存在
    if not os.path.exists(dataset.filepath):
        raise HTTPException(status_code=404, detail="数据集文件不存在，可能已被删除")
    
    # 验证文件路径安全
    if not validate_filepath(dataset.filepath):
        raise HTTPException(status_code=403, detail="文件路径不安全")
    
    return FileResponse(dataset.filepath, filename=dataset.filename, media_type="text/csv")


@router.put("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: int, 
    data: DatasetUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # 需要登录
):
    """更新数据集信息"""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    _check_dataset_permission(dataset, current_user, "修改")
    
    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="没有提供要更新的字段")
    
    for key, value in update_data.items():
        setattr(dataset, key, value)
    
    await db.commit()
    await db.refresh(dataset)
    return dataset


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # 需要登录
):
    """删除数据集"""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    _check_dataset_permission(dataset, current_user, "删除")
    
    # 先提交数据库删除，再清理文件（避免事务失败但文件已删除）
    # 级联删除关联的配置
    configs = await db.execute(select(Configuration).where(Configuration.dataset_id == dataset_id))
    for config in configs.scalars().all():
        await db.delete(config)
    
    # 级联删除关联的结果
    results_query = await db.execute(select(Result).where(Result.dataset_id == dataset_id))
    result_dirs_to_delete = []
    for res in results_query.scalars().all():
        result_dir = settings.RESULTS_DIR / str(dataset_id) / str(res.id)
        if result_dir.exists():
            result_dirs_to_delete.append(str(result_dir))
        await db.delete(res)
    
    # 删除数据集记录
    await db.delete(dataset)
    
    # 先提交数据库事务
    await db.commit()
    
    # 数据库提交成功后，再异步清理文件（失败不影响主流程）
    for result_dir in result_dirs_to_delete:
        await run_in_executor(safe_rmtree, result_dir)
    
    dataset_dir = settings.DATASETS_DIR / str(dataset_id)
    if dataset_dir.exists():
        await run_in_executor(safe_rmtree, str(dataset_dir))
    
    return {"message": "数据集及相关数据已删除"}
