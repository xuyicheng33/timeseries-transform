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
from sqlalchemy import select, func, distinct
from typing import Optional

from app.database import get_db
from app.models import Result, Dataset, Configuration, User
from app.schemas import ResultCreate, ResultUpdate, ResultResponse, PaginatedResponse
from app.config import settings
from app.services.utils import (
    calculate_metrics, sanitize_filename, sanitize_filename_for_header, safe_rmtree, 
    validate_form_field, validate_description,
    validate_numeric_data, NaNHandlingStrategy
)
from app.services.executor import run_in_executor
from app.services.security import validate_filepath
from app.services.permissions import (
    check_read_access, check_write_access, check_dataset_write_access,
    build_result_query, get_isolation_conditions,
    ResourceType, ActionType
)
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/results", tags=["results"])

# 完整结果文件必需列（包含真实值和预测值）
REQUIRED_COLUMNS_FULL = {"true_value", "predicted_value"}
# 仅预测值文件必需列
REQUIRED_COLUMNS_PRED_ONLY = {"predicted_value"}


def _parse_result_csv_sync(filepath: str):
    """同步解析结果CSV"""
    return pd.read_csv(filepath)


def _read_dataset_csv_sync(filepath: str, encoding: str = 'utf-8'):
    """同步读取数据集CSV"""
    return pd.read_csv(filepath, encoding=encoding)


@router.post("/upload", response_model=ResultResponse)
async def upload_result(
    file: UploadFile = File(...),
    name: str = Form(...),
    dataset_id: int = Form(...),
    algo_name: str = Form(..., alias="model_name"),
    configuration_id: int = Form(None),
    algo_version: str = Form("", alias="model_version"),
    description: str = Form(""),
    target_column: str = Form(None, description="数据集中的目标列名（用于只上传预测值的情况）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # 需要登录
):
    """
    上传预测结果
    
    支持两种上传模式：
    1. 完整模式：CSV 包含 true_value 和 predicted_value 两列
    2. 仅预测值模式：CSV 只包含 predicted_value 列，需要指定 target_column 参数，
       系统会自动从数据集中读取对应的真实值进行比较
    """
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
    
    # 检查用户是否有权向该数据集上传结果（只有所有者可以）
    check_dataset_write_access(dataset, current_user, "上传结果")
    
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
    
    # 检查上传模式
    has_true_value = "true_value" in df.columns
    has_predicted_value = "predicted_value" in df.columns
    
    if not has_predicted_value:
        await run_in_executor(safe_rmtree, str(result_dir))
        await db.rollback()
        raise HTTPException(
            status_code=400, 
            detail="缺少必需列: predicted_value。文件必须包含 'predicted_value' 列"
        )
    
    # 如果没有 true_value 列，需要从数据集中获取
    if not has_true_value:
        if not target_column:
            await run_in_executor(safe_rmtree, str(result_dir))
            await db.rollback()
            raise HTTPException(
                status_code=400, 
                detail="文件缺少 'true_value' 列。请提供 target_column 参数指定数据集中的目标列，或上传包含 'true_value' 列的完整文件"
            )
        
        # 检查数据集文件是否存在
        if not os.path.exists(dataset.filepath):
            await run_in_executor(safe_rmtree, str(result_dir))
            await db.rollback()
            raise HTTPException(status_code=404, detail="数据集文件不存在")
        
        # 读取数据集
        try:
            dataset_df = await run_in_executor(
                _read_dataset_csv_sync, 
                dataset.filepath, 
                dataset.encoding or 'utf-8'
            )
        except Exception:
            await run_in_executor(safe_rmtree, str(result_dir))
            await db.rollback()
            raise HTTPException(status_code=500, detail="读取数据集文件失败")
        
        # 检查目标列是否存在
        if target_column not in dataset_df.columns:
            await run_in_executor(safe_rmtree, str(result_dir))
            await db.rollback()
            raise HTTPException(
                status_code=400, 
                detail=f"数据集中不存在列 '{target_column}'。可用列: {list(dataset_df.columns)}"
            )
        
        # 检查行数是否匹配
        if len(df) != len(dataset_df):
            await run_in_executor(safe_rmtree, str(result_dir))
            await db.rollback()
            raise HTTPException(
                status_code=400, 
                detail=f"预测结果行数 ({len(df)}) 与数据集行数 ({len(dataset_df)}) 不匹配"
            )
        
        # 添加 true_value 列
        df["true_value"] = dataset_df[target_column].values
        
        # 重新保存包含 true_value 的完整文件
        try:
            await run_in_executor(lambda: df.to_csv(str(filepath), index=False))
        except Exception:
            await run_in_executor(safe_rmtree, str(result_dir))
            await db.rollback()
            raise HTTPException(status_code=500, detail="保存结果文件失败")
    
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
    current_user: User = Depends(get_current_user)
):
    """获取所有不重复的模型名称（用于筛选下拉框）"""
    query = select(distinct(Result.algo_name)).where(Result.algo_name.isnot(None))
    
    # 数据隔离过滤
    conditions, need_join = get_isolation_conditions(current_user, Result)
    if need_join:
        query = query.join(Dataset)
    for cond in conditions:
        query = query.where(cond)
    
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
    current_user: User = Depends(get_current_user)
):
    """获取所有结果（不分页，用于下拉选择等场景，限制最多1000条）"""
    query = build_result_query(current_user)
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
    current_user: User = Depends(get_current_user)
):
    """获取结果列表（分页）"""
    # 参数校验
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    offset = (page - 1) * page_size
    
    # 构建查询条件
    conditions = []
    
    if dataset_id is not None:
        conditions.append(Result.dataset_id == dataset_id)
    if algo_name is not None:
        conditions.append(Result.algo_name == algo_name)
    
    # 数据隔离过滤
    isolation_conditions, need_join = get_isolation_conditions(current_user, Result)
    conditions.extend(isolation_conditions)
    
    # 查询总数
    count_query = select(func.count(Result.id))
    if need_join:
        count_query = count_query.join(Dataset)
    for cond in conditions:
        count_query = count_query.where(cond)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 查询分页数据
    query = select(Result)
    if need_join:
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
    current_user: User = Depends(get_current_user)
):
    """获取结果详情"""
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(status_code=404, detail="结果不存在")
    
    # 获取关联数据集
    dataset_result = await db.execute(select(Dataset).where(Dataset.id == result_obj.dataset_id))
    dataset = dataset_result.scalar_one_or_none()
    
    check_read_access(result_obj, current_user, ResourceType.RESULT, parent_dataset=dataset)
    return result_obj


@router.get("/{result_id}/download")
async def download_result(
    result_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """下载结果文件"""
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(status_code=404, detail="结果不存在")
    
    # 获取关联数据集
    dataset_result = await db.execute(select(Dataset).where(Dataset.id == result_obj.dataset_id))
    dataset = dataset_result.scalar_one_or_none()
    
    check_read_access(result_obj, current_user, ResourceType.RESULT, parent_dataset=dataset)
    
    # 检查文件是否存在
    if not os.path.exists(result_obj.filepath):
        raise HTTPException(status_code=404, detail="结果文件不存在，可能已被删除")
    
    # 验证文件路径安全
    if not validate_filepath(result_obj.filepath):
        raise HTTPException(status_code=403, detail="文件路径不安全")
    
    # 使用安全的文件名（防止 Header 注入）
    safe_download_name = sanitize_filename_for_header(result_obj.filename)
    return FileResponse(result_obj.filepath, filename=safe_download_name, media_type="text/csv")


@router.get("/{result_id}/preview")
async def preview_result(
    result_id: int,
    rows: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """预览结果数据（前 N 行）"""
    # 限制最大行数
    rows = max(1, min(rows, 500))
    
    result = await db.execute(select(Result).where(Result.id == result_id))
    result_obj = result.scalar_one_or_none()
    if not result_obj:
        raise HTTPException(status_code=404, detail="结果不存在")
    
    # 获取关联数据集
    dataset_result = await db.execute(select(Dataset).where(Dataset.id == result_obj.dataset_id))
    dataset = dataset_result.scalar_one_or_none()
    
    check_read_access(result_obj, current_user, ResourceType.RESULT, parent_dataset=dataset)
    
    # 检查文件是否存在
    if not os.path.exists(result_obj.filepath):
        raise HTTPException(status_code=404, detail="结果文件不存在，可能已被删除")
    
    # 验证文件路径安全
    if not validate_filepath(result_obj.filepath):
        raise HTTPException(status_code=403, detail="文件路径不安全")
    
    try:
        # 读取前 N 行
        df = await run_in_executor(lambda: pd.read_csv(result_obj.filepath, nrows=rows))
        
        # 替换 NaN 为 None（JSON 兼容）
        df = df.replace({np.nan: None})
        
        return {
            "columns": df.columns.tolist(),
            "data": df.to_dict(orient="records"),
            "total_rows": result_obj.row_count or len(df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")


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
    
    check_write_access(result_obj, current_user, ActionType.WRITE, ResourceType.RESULT, parent_dataset=dataset)
    
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
    
    check_write_access(result_obj, current_user, ActionType.DELETE, ResourceType.RESULT, parent_dataset=dataset)
    
    # 记录要删除的目录
    result_dir = settings.RESULTS_DIR / str(result_obj.dataset_id) / str(result_id)
    
    # 先删除数据库记录
    await db.delete(result_obj)
    await db.commit()
    
    # 数据库提交成功后，再清理文件
    if result_dir.exists():
        await run_in_executor(safe_rmtree, str(result_dir))
    
    return {"message": "结果已删除"}
