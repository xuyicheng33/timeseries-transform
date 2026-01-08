"""
结果 API 路由
提供预测结果的上传、查询、更新、删除等功能
"""
import os
import aiofiles
import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct, or_
from typing import Optional

from app.database import get_db
from app.models import Result, Dataset, Configuration, User
from app.schemas import ResultCreate, ResultUpdate, ResultResponse, PaginatedResponse
from app.config import settings
from app.services.utils import (
    calculate_metrics, sanitize_filename, safe_rmtree, 
    validate_form_field, validate_description,
    validate_numeric_data, NaNHandlingStrategy
)
from app.services.executor import run_in_executor
from app.services.security import validate_filepath
from app.api.auth import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/results", tags=["results"])

REQUIRED_COLUMNS = {"true_value", "predicted_value"}


def _parse_result_csv_sync(filepath: str):
    """同步解析结果CSV"""
    return pd.read_csv(filepath)


def _check_dataset_access(dataset: Dataset, user: Optional[User]) -> None:
    """检查用户是否有权访问数据集"""
    if not settings.ENABLE_DATA_ISOLATION:
        return
    
    if user is None:
        raise HTTPException(status_code=403, detail="无权访问此数据集")
    
    if user.is_admin:
        return
    
    if dataset.user_id == user.id:
        return
    
    if dataset.is_public:
        return
    
    raise HTTPException(status_code=403, detail="无权访问此数据集")


def _check_result_permission(result: Result, dataset: Optional[Dataset], user: Optional[User], action: str = "访问") -> None:
    """检查用户对结果的操作权限"""
    if not settings.ENABLE_DATA_ISOLATION:
        return
    
    if user is None:
        raise HTTPException(status_code=403, detail=f"无权{action}此结果")
    
    if user.is_admin:
        return
    
    # 结果所有者有所有权限
    if result.user_id == user.id:
        return
    
    # 数据集所有者有所有权限
    if dataset and dataset.user_id == user.id:
        return
    
    # 公开数据集的结果只能读取
    if dataset and dataset.is_public and action in ["访问", "下载"]:
        return
    
    raise HTTPException(status_code=403, detail=f"无权{action}此结果")


def _build_result_query(user: Optional[User], base_query=None):
    """构建结果查询，根据数据隔离配置过滤"""
    if base_query is None:
        base_query = select(Result)
    
    if settings.ENABLE_DATA_ISOLATION:
        if user is None:
            # 匿名用户只能看到公开数据集的结果
            base_query = base_query.join(Dataset).where(Dataset.is_public == True)
        elif not user.is_admin:
            # 普通用户只能看到自己的结果、自己数据集的结果、或公开数据集的结果
            base_query = base_query.join(Dataset).where(
                or_(
                    Result.user_id == user.id,
                    Dataset.user_id == user.id,
                    Dataset.is_public == True
                )
            )
        # 管理员不做过滤
    
    return base_query


@router.post("/upload", response_model=ResultResponse)
async def upload_result(
    file: UploadFile = File(...),
    name: str = Form(...),
    dataset_id: int = Form(...),
    algo_name: str = Form(..., alias="model_name"),
    configuration_id: int = Form(None),
    algo_version: str = Form("", alias="model_version"),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # 需要登录
):
    """上传预测结果"""
    # 表单字段校验
    name = validate_form_field(name, "结果名称", max_length=255, min_length=1)
    algo_name = validate_form_field(algo_name, "模型名称", max_length=100, min_length=1)
    algo_version = validate_form_field(algo_version, "模型版本", max_length=50, min_length=0, required=False)
    description = validate_description(description, max_length=1000)
    
    # 大小写不敏感的扩展名校验
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="仅支持 CSV 文件")
    
    # 清理文件名
    safe_filename = sanitize_filename(file.filename)
    
    # 检查数据集是否存在
    dataset_result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = dataset_result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    # 检查用户是否有权访问该数据集
    _check_dataset_access(dataset, current_user)
    
    # 校验 configuration_id 归属
    if configuration_id is not None:
        config_result = await db.execute(select(Configuration).where(Configuration.id == configuration_id))
        config = config_result.scalar_one_or_none()
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")
        if config.dataset_id != dataset_id:
            raise HTTPException(status_code=400, detail="配置不属于指定的数据集")
    
    # 创建结果记录，关联当前用户
    result_obj = Result(
        name=name, 
        dataset_id=dataset_id, 
        configuration_id=configuration_id,
        user_id=current_user.id,
        filename=safe_filename, 
        filepath="", 
        algo_name=algo_name,
        algo_version=algo_version, 
        description=description
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
            while chunk := await file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > settings.MAX_UPLOAD_SIZE:
                    await f.close()
                    await run_in_executor(safe_rmtree, str(result_dir))
                    await db.rollback()
                    raise HTTPException(
                        status_code=400,
                        detail=f"文件过大，最大允许 {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB"
                    )
                await f.write(chunk)
    except HTTPException:
        raise
    except Exception:
        await run_in_executor(safe_rmtree, str(result_dir))
        await db.rollback()
        raise HTTPException(status_code=500, detail="文件上传失败")
    
    # 解析 CSV
    try:
        df = await run_in_executor(_parse_result_csv_sync, str(filepath))
    except Exception:
        await run_in_executor(safe_rmtree, str(result_dir))
        await db.rollback()
        raise HTTPException(status_code=400, detail="CSV 文件解析失败，请检查文件格式")
    
    # 检查必需列
    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        await run_in_executor(safe_rmtree, str(result_dir))
        await db.rollback()
        raise HTTPException(
            status_code=400, 
            detail=f"缺少必需列: {missing_cols}。文件必须包含 'true_value' 和 'predicted_value' 列"
        )
    
    result_obj.filepath = str(filepath)
    result_obj.row_count = len(df)
    
    # 计算指标 - 使用统一的 NaN 处理策略（上传时严格拒绝）
    try:
        true_vals = pd.to_numeric(df["true_value"], errors='coerce').values
        pred_vals = pd.to_numeric(df["predicted_value"], errors='coerce').values
        
        # 验证数据，拒绝包含 NaN 的数据
        true_vals, pred_vals, _ = validate_numeric_data(
            true_vals, pred_vals, 
            strategy=NaNHandlingStrategy.REJECT
        )
        
        result_obj.metrics = calculate_metrics(true_vals, pred_vals)
    except ValueError as e:
        await run_in_executor(safe_rmtree, str(result_dir))
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        await run_in_executor(safe_rmtree, str(result_dir))
        await db.rollback()
        raise HTTPException(status_code=400, detail="数据格式错误，true_value 和 predicted_value 必须为数值类型")
    
    await db.commit()
    await db.refresh(result_obj)
    return result_obj


@router.get("/model-names", response_model=list[str])
async def list_model_names(
    dataset_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """获取所有不重复的模型名称（用于筛选下拉框）"""
    query = select(distinct(Result.algo_name)).where(Result.algo_name.isnot(None))
    
    # 数据隔离过滤
    if settings.ENABLE_DATA_ISOLATION:
        if current_user is None:
            # 匿名用户只能看到公开数据集的结果
            query = query.join(Dataset).where(Dataset.is_public == True)
        elif not current_user.is_admin:
            # 普通用户
            query = query.join(Dataset).where(
                or_(
                    Result.user_id == current_user.id,
                    Dataset.user_id == current_user.id,
                    Dataset.is_public == True
                )
            )
        # 管理员不做过滤
    
    if dataset_id is not None:
        query = query.where(Result.dataset_id == dataset_id)
    
    query = query.order_by(Result.algo_name)
    
    result = await db.execute(query)
    return [row[0] for row in result.fetchall() if row[0]]


@router.get("/all", response_model=list[ResultResponse])
async def list_all_results(
    dataset_id: Optional[int] = None,
    algo_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """获取所有结果（不分页，用于下拉选择等场景，限制最多1000条）"""
    query = _build_result_query(current_user)
    query = query.order_by(Result.created_at.desc())
    
    if dataset_id is not None:
        query = query.where(Result.dataset_id == dataset_id)
    if algo_name is not None:
        query = query.where(Result.algo_name == algo_name)
    
    query = query.limit(1000)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("", response_model=PaginatedResponse[ResultResponse])
async def list_results(
    dataset_id: Optional[int] = None,
    algo_name: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """获取结果列表（分页）"""
    # 参数校验
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    offset = (page - 1) * page_size
    
    # 构建查询条件
    conditions = []
    join_dataset = False
    
    if dataset_id is not None:
        conditions.append(Result.dataset_id == dataset_id)
    if algo_name is not None:
        conditions.append(Result.algo_name == algo_name)
    
    # 数据隔离过滤
    if settings.ENABLE_DATA_ISOLATION:
        join_dataset = True
        if current_user is None:
            # 匿名用户只能看到公开数据集的结果
            conditions.append(Dataset.is_public == True)
        elif not current_user.is_admin:
            # 普通用户
            conditions.append(
                or_(
                    Result.user_id == current_user.id,
                    Dataset.user_id == current_user.id,
                    Dataset.is_public == True
                )
            )
        # 管理员不做过滤
    
    # 查询总数
    count_query = select(func.count(Result.id))
    if join_dataset:
        count_query = count_query.join(Dataset)
    for cond in conditions:
        count_query = count_query.where(cond)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 查询分页数据
    query = select(Result)
    if join_dataset:
        query = query.join(Dataset)
    query = query.order_by(Result.created_at.desc())
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
async def get_result(
    result_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """获取结果详情"""
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(status_code=404, detail="结果不存在")
    
    # 获取关联数据集
    dataset_result = await db.execute(select(Dataset).where(Dataset.id == result_obj.dataset_id))
    dataset = dataset_result.scalar_one_or_none()
    
    _check_result_permission(result_obj, dataset, current_user, "访问")
    return result_obj


@router.get("/{result_id}/download")
async def download_result(
    result_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """下载结果文件"""
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(status_code=404, detail="结果不存在")
    
    # 获取关联数据集
    dataset_result = await db.execute(select(Dataset).where(Dataset.id == result_obj.dataset_id))
    dataset = dataset_result.scalar_one_or_none()
    
    _check_result_permission(result_obj, dataset, current_user, "下载")
    
    # 检查文件是否存在
    if not os.path.exists(result_obj.filepath):
        raise HTTPException(status_code=404, detail="结果文件不存在，可能已被删除")
    
    # 验证文件路径安全
    if not validate_filepath(result_obj.filepath):
        raise HTTPException(status_code=403, detail="文件路径不安全")
    
    return FileResponse(result_obj.filepath, filename=result_obj.filename, media_type="text/csv")


@router.put("/{result_id}", response_model=ResultResponse)
async def update_result(
    result_id: int, 
    data: ResultUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # 需要登录
):
    """更新结果信息"""
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(status_code=404, detail="结果不存在")
    
    # 获取关联数据集
    dataset_result = await db.execute(select(Dataset).where(Dataset.id == result_obj.dataset_id))
    dataset = dataset_result.scalar_one_or_none()
    
    _check_result_permission(result_obj, dataset, current_user, "修改")
    
    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="没有提供要更新的字段")
    
    for key, value in update_data.items():
        setattr(result_obj, key, value)
    
    await db.commit()
    await db.refresh(result_obj)
    return result_obj


@router.delete("/{result_id}")
async def delete_result(
    result_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # 需要登录
):
    """删除结果"""
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(status_code=404, detail="结果不存在")
    
    # 获取关联数据集
    dataset_result = await db.execute(select(Dataset).where(Dataset.id == result_obj.dataset_id))
    dataset = dataset_result.scalar_one_or_none()
    
    _check_result_permission(result_obj, dataset, current_user, "删除")
    
    # 记录要删除的目录
    result_dir = settings.RESULTS_DIR / str(result_obj.dataset_id) / str(result_id)
    
    # 先删除数据库记录
    await db.delete(result_obj)
    await db.commit()
    
    # 数据库提交成功后，再清理文件
    if result_dir.exists():
        await run_in_executor(safe_rmtree, str(result_dir))
    
    return {"message": "结果已删除"}
