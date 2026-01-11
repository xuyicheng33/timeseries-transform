"""
实验组管理 API

提供实验组的 CRUD 操作和结果关联管理
"""
import os
import json
import zipfile
import tempfile
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import User, Experiment, Result, Dataset, Configuration, experiment_results
from app.schemas.schemas import (
    PaginatedResponse,
    ExperimentCreate,
    ExperimentUpdate,
    ExperimentResponse,
    ExperimentDetailResponse,
    ExperimentResultBrief,
    ExperimentAddResults,
    ExperimentRemoveResults,
    ExperimentSummary,
    MetricsResponse,
)
from app.api.auth import get_current_user
from app.services.permissions import check_read_access, can_access_result
from app.services.executor import run_in_executor
from app.services.utils import safe_rmtree
from app.services.security import validate_filepath
from app.config import settings


router = APIRouter(prefix="/api/experiments", tags=["experiments"])


# ============ 辅助函数 ============

import re

def _sanitize_filename(name: str) -> str:
    """
    净化文件名，防止 Zip Slip 攻击
    只允许字母、数字、下划线、连字符和点
    """
    if not name:
        return "unknown"
    # 移除路径分隔符和危险字符
    safe_name = re.sub(r'[^\w\-.]', '_', name)
    # 移除连续的点（防止 ..）
    safe_name = re.sub(r'\.{2,}', '.', safe_name)
    # 移除开头的点和连字符
    safe_name = safe_name.lstrip('.-')
    # 限制长度
    if len(safe_name) > 100:
        safe_name = safe_name[:100]
    return safe_name or "unknown"


async def check_result_access(result_id: int, db: AsyncSession, user: User) -> Result:
    """检查用户是否有权访问结果，返回结果对象"""
    result = await db.execute(
        select(Result).where(Result.id == result_id)
    )
    result_obj = result.scalar_one_or_none()
    
    if not result_obj:
        raise HTTPException(status_code=404, detail="结果不存在")
    
    # 获取关联的数据集
    dataset = None
    if result_obj.dataset_id:
        ds_result = await db.execute(
            select(Dataset).where(Dataset.id == result_obj.dataset_id)
        )
        dataset = ds_result.scalar_one_or_none()
    
    # 检查权限
    if not can_access_result(result_obj, dataset, user):
        raise HTTPException(status_code=403, detail="无权访问此结果")
    
    return result_obj


async def get_experiment_or_404(
    experiment_id: int,
    db: AsyncSession,
    user: User,
    load_results: bool = False
) -> Experiment:
    """获取实验组，不存在或无权限则抛出异常"""
    query = select(Experiment).where(Experiment.id == experiment_id)
    if load_results:
        query = query.options(selectinload(Experiment.results))
    
    result = await db.execute(query)
    experiment = result.scalar_one_or_none()
    
    if not experiment:
        raise HTTPException(status_code=404, detail="实验组不存在")
    
    # 检查权限（只能访问自己的实验组，管理员可访问所有）
    if experiment.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="无权访问此实验组")
    
    return experiment


def build_experiment_response(experiment: Experiment, result_count: int = 0, dataset_name: str = None) -> ExperimentResponse:
    """构建实验组响应"""
    return ExperimentResponse(
        id=experiment.id,
        name=experiment.name,
        description=experiment.description or "",
        objective=experiment.objective or "",
        status=experiment.status or "draft",
        tags=experiment.tags or [],
        conclusion=experiment.conclusion or "",
        user_id=experiment.user_id,
        dataset_id=experiment.dataset_id,
        dataset_name=dataset_name,
        result_count=result_count,
        created_at=experiment.created_at,
        updated_at=experiment.updated_at
    )


# ============ API 端点 ============

@router.get("", response_model=PaginatedResponse[ExperimentResponse])
async def list_experiments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="按状态筛选"),
    tag: Optional[str] = Query(None, description="按标签筛选"),
    dataset_id: Optional[int] = Query(None, description="按数据集筛选"),
    search: Optional[str] = Query(None, description="搜索名称/描述"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取实验组列表"""
    # 基础查询
    query = select(Experiment).where(Experiment.user_id == current_user.id)
    count_query = select(func.count(Experiment.id)).where(Experiment.user_id == current_user.id)
    
    # 状态筛选
    if status:
        query = query.where(Experiment.status == status)
        count_query = count_query.where(Experiment.status == status)
    
    # 数据集筛选
    if dataset_id:
        query = query.where(Experiment.dataset_id == dataset_id)
        count_query = count_query.where(Experiment.dataset_id == dataset_id)
    
    # 标签筛选（SQLite JSON 数组查询）
    if tag:
        # 使用 JSON 函数检查数组是否包含指定值
        # SQLite: json_each + EXISTS 或 LIKE 模式匹配
        # 这里使用 LIKE 模式匹配 JSON 数组字符串，更兼容
        tag_pattern = f'%"{tag}"%'
        from sqlalchemy import cast, String
        query = query.where(cast(Experiment.tags, String).like(tag_pattern))
        count_query = count_query.where(cast(Experiment.tags, String).like(tag_pattern))
    
    # 搜索
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Experiment.name.ilike(search_pattern)) |
            (Experiment.description.ilike(search_pattern))
        )
        count_query = count_query.where(
            (Experiment.name.ilike(search_pattern)) |
            (Experiment.description.ilike(search_pattern))
        )
    
    # 总数
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页
    offset = (page - 1) * page_size
    query = query.order_by(Experiment.updated_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    experiments = result.scalars().all()
    
    if not experiments:
        return PaginatedResponse(items=[], total=total, page=page, page_size=page_size)
    
    # 批量获取结果数量（避免 N+1）
    exp_ids = [exp.id for exp in experiments]
    result_counts_query = await db.execute(
        select(
            experiment_results.c.experiment_id,
            func.count(experiment_results.c.result_id).label('count')
        ).where(
            experiment_results.c.experiment_id.in_(exp_ids)
        ).group_by(experiment_results.c.experiment_id)
    )
    result_counts = {row.experiment_id: row.count for row in result_counts_query}
    
    # 批量获取数据集名称（避免 N+1）
    dataset_ids = [exp.dataset_id for exp in experiments if exp.dataset_id]
    dataset_names = {}
    if dataset_ids:
        ds_result = await db.execute(
            select(Dataset.id, Dataset.name).where(Dataset.id.in_(dataset_ids))
        )
        dataset_names = {row.id: row.name for row in ds_result}
    
    # 构建响应
    items = []
    for exp in experiments:
        items.append(build_experiment_response(
            exp,
            result_count=result_counts.get(exp.id, 0),
            dataset_name=dataset_names.get(exp.dataset_id) if exp.dataset_id else None
        ))
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=ExperimentDetailResponse)
async def create_experiment(
    data: ExperimentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建实验组"""
    # 验证数据集（如果提供）
    dataset_name = None
    if data.dataset_id:
        ds_result = await db.execute(
            select(Dataset).where(Dataset.id == data.dataset_id)
        )
        dataset = ds_result.scalar_one_or_none()
        if not dataset:
            raise HTTPException(status_code=404, detail="数据集不存在")
        # 检查数据集读取权限（遵循共享模式规则）
        # 共享模式：所有登录用户可读
        # 隔离模式：只能访问自己的或公开的
        if settings.ENABLE_DATA_ISOLATION:
            if dataset.user_id != current_user.id and not dataset.is_public and not current_user.is_admin:
                raise HTTPException(status_code=403, detail="无权访问此数据集")
        dataset_name = dataset.name
    
    # 创建实验组
    experiment = Experiment(
        name=data.name,
        description=data.description,
        objective=data.objective,
        tags=data.tags,
        dataset_id=data.dataset_id,
        user_id=current_user.id,
        status="draft"
    )
    db.add(experiment)
    await db.flush()  # 获取 ID
    
    # 添加初始结果
    added_results = []
    skipped_result_ids = []
    if data.result_ids:
        # 获取实验组关联的数据集 ID（用于同数据集校验）
        experiment_dataset_id = data.dataset_id
        
        # 获取配置名称映射
        config_ids_to_fetch = []
        results_to_add = []
        
        for result_id in data.result_ids:
            # 验证结果存在且有权限
            try:
                result = await check_result_access(result_id, db, current_user)
                
                # 同数据集校验
                if experiment_dataset_id is None:
                    # 第一个结果，设置基准数据集
                    experiment_dataset_id = result.dataset_id
                elif result.dataset_id != experiment_dataset_id:
                    # 数据集不一致，跳过
                    skipped_result_ids.append(result_id)
                    continue
                
                experiment.results.append(result)
                results_to_add.append(result)
                if result.configuration_id:
                    config_ids_to_fetch.append(result.configuration_id)
            except HTTPException:
                skipped_result_ids.append(result_id)  # 记录跳过的结果
        
        # 如果实验组没有指定数据集，但添加了结果，更新实验组的数据集
        if data.dataset_id is None and experiment_dataset_id is not None:
            experiment.dataset_id = experiment_dataset_id
            # 获取数据集名称
            ds_result = await db.execute(
                select(Dataset.name).where(Dataset.id == experiment_dataset_id)
            )
            dataset_name = ds_result.scalar()
        
        # 批量获取配置名称
        config_names = {}
        if config_ids_to_fetch:
            cfg_result = await db.execute(
                select(Configuration.id, Configuration.name).where(Configuration.id.in_(config_ids_to_fetch))
            )
            config_names = {row.id: row.name for row in cfg_result}
        
        # 构建结果简要信息
        for result in results_to_add:
            added_results.append(ExperimentResultBrief(
                id=result.id,
                name=result.name,
                algo_name=result.algo_name,
                algo_version=result.algo_version or "",
                metrics=result.metrics or {},
                configuration_id=result.configuration_id,
                configuration_name=config_names.get(result.configuration_id) if result.configuration_id else None,
                dataset_id=result.dataset_id,
                created_at=result.created_at
            ))
    
    await db.commit()
    await db.refresh(experiment)
    
    return ExperimentDetailResponse(
        id=experiment.id,
        name=experiment.name,
        description=experiment.description or "",
        objective=experiment.objective or "",
        status=experiment.status,
        tags=experiment.tags or [],
        conclusion=experiment.conclusion or "",
        user_id=experiment.user_id,
        dataset_id=experiment.dataset_id,
        dataset_name=dataset_name,
        result_count=len(added_results),
        created_at=experiment.created_at,
        updated_at=experiment.updated_at,
        results=added_results,
        skipped_result_ids=skipped_result_ids
    )


@router.get("/{experiment_id}", response_model=ExperimentDetailResponse)
async def get_experiment(
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取实验组详情"""
    experiment = await get_experiment_or_404(experiment_id, db, current_user, load_results=True)
    
    # 数据集名称
    dataset_name = None
    if experiment.dataset_id:
        ds_result = await db.execute(
            select(Dataset.name).where(Dataset.id == experiment.dataset_id)
        )
        dataset_name = ds_result.scalar()
    
    # 批量获取配置名称
    config_ids = [r.configuration_id for r in experiment.results if r.configuration_id]
    config_names = {}
    if config_ids:
        cfg_result = await db.execute(
            select(Configuration.id, Configuration.name).where(Configuration.id.in_(config_ids))
        )
        config_names = {row.id: row.name for row in cfg_result}
    
    # 构建结果列表
    results = [
        ExperimentResultBrief(
            id=r.id,
            name=r.name,
            algo_name=r.algo_name,
            algo_version=r.algo_version or "",
            metrics=r.metrics or {},
            configuration_id=r.configuration_id,
            configuration_name=config_names.get(r.configuration_id) if r.configuration_id else None,
            dataset_id=r.dataset_id,
            created_at=r.created_at
        )
        for r in experiment.results
    ]
    
    return ExperimentDetailResponse(
        id=experiment.id,
        name=experiment.name,
        description=experiment.description or "",
        objective=experiment.objective or "",
        status=experiment.status,
        tags=experiment.tags or [],
        conclusion=experiment.conclusion or "",
        user_id=experiment.user_id,
        dataset_id=experiment.dataset_id,
        dataset_name=dataset_name,
        result_count=len(results),
        created_at=experiment.created_at,
        updated_at=experiment.updated_at,
        results=results
    )


@router.put("/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(
    experiment_id: int,
    data: ExperimentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新实验组"""
    experiment = await get_experiment_or_404(experiment_id, db, current_user)
    
    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    
    # 验证数据集（如果更新）
    dataset_name = None
    if "dataset_id" in update_data:
        if update_data["dataset_id"]:
            ds_result = await db.execute(
                select(Dataset).where(Dataset.id == update_data["dataset_id"])
            )
            dataset = ds_result.scalar_one_or_none()
            if not dataset:
                raise HTTPException(status_code=404, detail="数据集不存在")
            # 检查数据集读取权限（遵循共享模式规则）
            if settings.ENABLE_DATA_ISOLATION:
                if dataset.user_id != current_user.id and not dataset.is_public and not current_user.is_admin:
                    raise HTTPException(status_code=403, detail="无权访问此数据集")
            dataset_name = dataset.name
    elif experiment.dataset_id:
        ds_result = await db.execute(
            select(Dataset.name).where(Dataset.id == experiment.dataset_id)
        )
        dataset_name = ds_result.scalar()
    
    for key, value in update_data.items():
        setattr(experiment, key, value)
    
    await db.commit()
    await db.refresh(experiment)
    
    # 结果数量
    count_result = await db.execute(
        select(func.count()).select_from(experiment_results).where(
            experiment_results.c.experiment_id == experiment.id
        )
    )
    result_count = count_result.scalar()
    
    return build_experiment_response(experiment, result_count, dataset_name)


@router.delete("/{experiment_id}")
async def delete_experiment(
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除实验组"""
    experiment = await get_experiment_or_404(experiment_id, db, current_user)
    
    await db.delete(experiment)
    await db.commit()
    
    return {"message": "实验组已删除"}


# ============ 结果关联管理 ============

@router.post("/{experiment_id}/results", response_model=ExperimentDetailResponse)
async def add_results_to_experiment(
    experiment_id: int,
    data: ExperimentAddResults,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """添加结果到实验组（强制要求同一数据集）"""
    experiment = await get_experiment_or_404(experiment_id, db, current_user, load_results=True)
    
    # 获取实验组关联的数据集 ID（如果有）
    experiment_dataset_id = experiment.dataset_id
    
    # 如果实验组已有结果，获取第一个结果的数据集作为基准
    if not experiment_dataset_id and experiment.results:
        experiment_dataset_id = experiment.results[0].dataset_id
    
    existing_ids = {r.id for r in experiment.results}
    added = []
    skipped_result_ids = []
    
    for result_id in data.result_ids:
        if result_id in existing_ids:
            skipped_result_ids.append(result_id)  # 已存在
            continue
        
        try:
            result = await check_result_access(result_id, db, current_user)
            
            # 检查数据集一致性
            if experiment_dataset_id and result.dataset_id != experiment_dataset_id:
                skipped_result_ids.append(result_id)  # 数据集不一致
                continue
            
            # 如果是第一个结果，设置基准数据集
            if not experiment_dataset_id:
                experiment_dataset_id = result.dataset_id
            
            experiment.results.append(result)
            added.append(result)
            existing_ids.add(result_id)
        except HTTPException:
            skipped_result_ids.append(result_id)  # 无权限或不存在
    
    # 如果实验组没有关联数据集，自动关联第一个结果的数据集
    if not experiment.dataset_id and experiment_dataset_id:
        experiment.dataset_id = experiment_dataset_id
    
    await db.commit()
    await db.refresh(experiment)
    
    # 重新加载结果
    result_query = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id).options(selectinload(Experiment.results))
    )
    experiment = result_query.scalar_one()
    
    # 数据集名称
    dataset_name = None
    if experiment.dataset_id:
        ds_result = await db.execute(
            select(Dataset.name).where(Dataset.id == experiment.dataset_id)
        )
        dataset_name = ds_result.scalar()
    
    # 批量获取配置名称
    config_ids = [r.configuration_id for r in experiment.results if r.configuration_id]
    config_names = {}
    if config_ids:
        cfg_result = await db.execute(
            select(Configuration.id, Configuration.name).where(Configuration.id.in_(config_ids))
        )
        config_names = {row.id: row.name for row in cfg_result}
    
    results = [
        ExperimentResultBrief(
            id=r.id,
            name=r.name,
            algo_name=r.algo_name,
            algo_version=r.algo_version or "",
            metrics=r.metrics or {},
            configuration_id=r.configuration_id,
            configuration_name=config_names.get(r.configuration_id) if r.configuration_id else None,
            dataset_id=r.dataset_id,
            created_at=r.created_at
        )
        for r in experiment.results
    ]
    
    return ExperimentDetailResponse(
        id=experiment.id,
        name=experiment.name,
        description=experiment.description or "",
        objective=experiment.objective or "",
        status=experiment.status,
        tags=experiment.tags or [],
        conclusion=experiment.conclusion or "",
        user_id=experiment.user_id,
        dataset_id=experiment.dataset_id,
        dataset_name=dataset_name,
        result_count=len(results),
        created_at=experiment.created_at,
        updated_at=experiment.updated_at,
        results=results,
        skipped_result_ids=skipped_result_ids
    )


@router.delete("/{experiment_id}/results")
async def remove_results_from_experiment(
    experiment_id: int,
    data: ExperimentRemoveResults,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """从实验组移除结果"""
    experiment = await get_experiment_or_404(experiment_id, db, current_user, load_results=True)
    
    # 计算实际移除数量
    original_count = len(experiment.results)
    ids_to_remove = set(data.result_ids)
    experiment.results = [r for r in experiment.results if r.id not in ids_to_remove]
    actual_removed = original_count - len(experiment.results)
    
    await db.commit()
    
    return {"message": f"已移除 {actual_removed} 个结果", "removed_count": actual_removed}


# ============ 实验组分析 ============

@router.get("/{experiment_id}/summary", response_model=ExperimentSummary)
async def get_experiment_summary(
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取实验组汇总统计"""
    experiment = await get_experiment_or_404(experiment_id, db, current_user, load_results=True)
    
    results = experiment.results
    if not results:
        return ExperimentSummary(
            experiment_id=experiment.id,
            experiment_name=experiment.name,
            result_count=0,
            model_names=[]
        )
    
    # 收集模型名称
    model_names = list(set(r.algo_name for r in results))
    
    # 收集所有指标
    metrics_data = {
        "mse": [],
        "rmse": [],
        "mae": [],
        "r2": [],
        "mape": []
    }
    
    for r in results:
        if r.metrics:
            for key in metrics_data:
                if key in r.metrics:
                    metrics_data[key].append({
                        "result_id": r.id,
                        "value": r.metrics[key],
                        "model_name": r.algo_name
                    })
    
    # 找最佳值（MSE/RMSE/MAE/MAPE 越小越好，R2 越大越好）
    def find_best(data: list, minimize: bool = True):
        if not data:
            return None
        if minimize:
            return min(data, key=lambda x: x["value"])
        return max(data, key=lambda x: x["value"])
    
    best_mse = find_best(metrics_data["mse"], minimize=True)
    best_rmse = find_best(metrics_data["rmse"], minimize=True)
    best_mae = find_best(metrics_data["mae"], minimize=True)
    best_r2 = find_best(metrics_data["r2"], minimize=False)
    best_mape = find_best(metrics_data["mape"], minimize=True)
    
    # 计算平均指标
    avg_metrics = None
    if all(metrics_data[k] for k in metrics_data):
        avg_metrics = MetricsResponse(
            mse=sum(d["value"] for d in metrics_data["mse"]) / len(metrics_data["mse"]),
            rmse=sum(d["value"] for d in metrics_data["rmse"]) / len(metrics_data["rmse"]),
            mae=sum(d["value"] for d in metrics_data["mae"]) / len(metrics_data["mae"]),
            r2=sum(d["value"] for d in metrics_data["r2"]) / len(metrics_data["r2"]),
            mape=sum(d["value"] for d in metrics_data["mape"]) / len(metrics_data["mape"])
        )
    
    return ExperimentSummary(
        experiment_id=experiment.id,
        experiment_name=experiment.name,
        result_count=len(results),
        model_names=model_names,
        best_mse=best_mse,
        best_rmse=best_rmse,
        best_mae=best_mae,
        best_r2=best_r2,
        best_mape=best_mape,
        avg_metrics=avg_metrics
    )


@router.get("/tags/list")
async def list_all_tags(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户所有实验组的标签列表"""
    result = await db.execute(
        select(Experiment.tags).where(Experiment.user_id == current_user.id)
    )
    
    all_tags = set()
    for row in result.scalars():
        if row:
            all_tags.update(row)
    
    return {"tags": sorted(list(all_tags))}


# ============ 实验组导出 ============

def _create_experiment_export_zip(
    experiment: Experiment,
    results: List[Result],
    dataset: Optional[Dataset],
    configurations: List[Configuration],
    include_data_files: bool,
    temp_dir: str
) -> str:
    """创建实验组导出 ZIP 文件（同步）"""
    zip_path = os.path.join(temp_dir, "experiment_export.zip")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. 实验组元数据
        experiment_meta = {
            "id": experiment.id,
            "name": experiment.name,
            "description": experiment.description or "",
            "objective": experiment.objective or "",
            "status": experiment.status,
            "tags": experiment.tags or [],
            "conclusion": experiment.conclusion or "",
            "created_at": experiment.created_at.isoformat() if experiment.created_at else None,
            "updated_at": experiment.updated_at.isoformat() if experiment.updated_at else None,
            "export_time": datetime.now().isoformat(),
            "export_version": "1.0",
        }
        zf.writestr("experiment.json", json.dumps(experiment_meta, indent=2, ensure_ascii=False))
        
        # 2. 数据集信息
        if dataset:
            dataset_meta = {
                "id": dataset.id,
                "name": dataset.name,
                "filename": dataset.filename,
                "description": dataset.description or "",
                "row_count": dataset.row_count,
                "column_count": dataset.column_count,
                "columns": dataset.columns,
            }
            zf.writestr("dataset/metadata.json", json.dumps(dataset_meta, indent=2, ensure_ascii=False))
            
            # 数据文件
            if include_data_files and dataset.filepath and os.path.exists(dataset.filepath):
                if validate_filepath(dataset.filepath):
                    zf.write(dataset.filepath, f"dataset/{dataset.filename}")
        
        # 3. 配置信息
        if configurations:
            configs_data = []
            for cfg in configurations:
                configs_data.append({
                    "id": cfg.id,
                    "name": cfg.name,
                    "channels": cfg.channels,
                    "normalization": cfg.normalization,
                    "window_size": cfg.window_size,
                    "stride": cfg.stride,
                    "target_type": cfg.target_type,
                    "target_k": cfg.target_k,
                    "anomaly_enabled": cfg.anomaly_enabled,
                    "anomaly_type": cfg.anomaly_type,
                })
            zf.writestr("configurations.json", json.dumps(configs_data, indent=2, ensure_ascii=False))
        
        # 4. 结果信息和文件
        results_data = []
        for res in results:
            res_meta = {
                "id": res.id,
                "name": res.name,
                "algo_name": res.algo_name,
                "algo_version": res.algo_version or "",
                "description": res.description or "",
                "row_count": res.row_count,
                "metrics": res.metrics or {},
                "created_at": res.created_at.isoformat() if res.created_at else None,
            }
            results_data.append(res_meta)
            
            # 结果文件（使用净化后的文件名防止 Zip Slip）
            if include_data_files and res.filepath and os.path.exists(res.filepath):
                if validate_filepath(res.filepath):
                    safe_algo_name = _sanitize_filename(res.algo_name)
                    zf.write(res.filepath, f"results/{res.id}_{safe_algo_name}.csv")
        
        zf.writestr("results.json", json.dumps(results_data, indent=2, ensure_ascii=False))
        
        # 5. 生成 Markdown 报告
        report_lines = [
            f"# 实验报告: {experiment.name}",
            "",
            f"**导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 实验概述",
            "",
            f"- **状态**: {experiment.status}",
            f"- **目标**: {experiment.objective or '-'}",
            f"- **描述**: {experiment.description or '-'}",
            f"- **标签**: {', '.join(experiment.tags) if experiment.tags else '-'}",
            "",
        ]
        
        if dataset:
            report_lines.extend([
                "## 数据集",
                "",
                f"- **名称**: {dataset.name}",
                f"- **行数**: {dataset.row_count:,}",
                f"- **列数**: {dataset.column_count}",
                "",
            ])
        
        if results:
            report_lines.extend([
                "## 模型性能对比",
                "",
                "| 模型 | 版本 | MSE | RMSE | MAE | R² | MAPE |",
                "|------|------|-----|------|-----|-----|------|",
            ])
            
            for res in results:
                m = res.metrics or {}
                row = [
                    res.algo_name,
                    res.algo_version or "-",
                    f"{m.get('mse', '-'):.6f}" if isinstance(m.get('mse'), (int, float)) else "-",
                    f"{m.get('rmse', '-'):.6f}" if isinstance(m.get('rmse'), (int, float)) else "-",
                    f"{m.get('mae', '-'):.6f}" if isinstance(m.get('mae'), (int, float)) else "-",
                    f"{m.get('r2', '-'):.4f}" if isinstance(m.get('r2'), (int, float)) else "-",
                    f"{m.get('mape', '-'):.2f}%" if isinstance(m.get('mape'), (int, float)) else "-",
                ]
                report_lines.append("| " + " | ".join(row) + " |")
            
            report_lines.append("")
        
        if experiment.conclusion:
            report_lines.extend([
                "## 实验结论",
                "",
                experiment.conclusion,
                "",
            ])
        
        report_lines.extend([
            "---",
            "",
            "*本报告由时序预测平台自动生成*",
        ])
        
        zf.writestr("report.md", "\n".join(report_lines))
        
        # 6. 生成 LaTeX 表格
        if results:
            latex_lines = [
                "\\begin{table}[htbp]",
                "\\centering",
                f"\\caption{{实验 {experiment.name} 模型性能对比}}",
                "\\label{tab:experiment_results}",
                "\\begin{tabular}{lcccccc}",
                "\\toprule",
                "模型 & 版本 & MSE & RMSE & MAE & R² & MAPE (\\%) \\\\",
                "\\midrule",
            ]
            
            for res in results:
                m = res.metrics or {}
                row = [
                    res.algo_name.replace('_', '\\_'),
                    res.algo_version or "-",
                    f"{m.get('mse', '-'):.6f}" if isinstance(m.get('mse'), (int, float)) else "-",
                    f"{m.get('rmse', '-'):.6f}" if isinstance(m.get('rmse'), (int, float)) else "-",
                    f"{m.get('mae', '-'):.6f}" if isinstance(m.get('mae'), (int, float)) else "-",
                    f"{m.get('r2', '-'):.4f}" if isinstance(m.get('r2'), (int, float)) else "-",
                    f"{m.get('mape', '-'):.2f}" if isinstance(m.get('mape'), (int, float)) else "-",
                ]
                latex_lines.append(" & ".join(row) + " \\\\")
            
            latex_lines.extend([
                "\\bottomrule",
                "\\end{tabular}",
                "\\end{table}",
            ])
            
            zf.writestr("results_table.tex", "\n".join(latex_lines))
    
    return zip_path


def _cleanup_temp_dir(temp_dir: str):
    """清理临时目录"""
    safe_rmtree(temp_dir)


@router.get("/{experiment_id}/export")
async def export_experiment(
    experiment_id: int,
    include_data_files: bool = Query(default=True, description="是否包含数据文件"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    导出实验组
    
    导出内容包括：
    - experiment.json: 实验组元数据
    - dataset/: 数据集信息和文件
    - configurations.json: 配置信息
    - results.json: 结果元数据
    - results/: 结果文件
    - report.md: Markdown 报告
    - results_table.tex: LaTeX 表格
    """
    # 获取实验组（包含结果）
    experiment = await get_experiment_or_404(experiment_id, db, current_user, load_results=True)
    
    # 获取数据集
    dataset = None
    if experiment.dataset_id:
        ds_result = await db.execute(
            select(Dataset).where(Dataset.id == experiment.dataset_id)
        )
        dataset = ds_result.scalar_one_or_none()
    
    # 获取配置
    configurations = []
    if dataset:
        cfg_result = await db.execute(
            select(Configuration).where(Configuration.dataset_id == dataset.id)
        )
        configurations = cfg_result.scalars().all()
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 创建 ZIP 文件
        zip_path = await run_in_executor(
            _create_experiment_export_zip,
            experiment,
            experiment.results,
            dataset,
            configurations,
            include_data_files,
            temp_dir
        )
        
        # 生成文件名
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in experiment.name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"experiment_{safe_name}_{timestamp}.zip"
        
        # 使用 BackgroundTasks 在响应完成后清理
        if background_tasks:
            background_tasks.add_task(_cleanup_temp_dir, temp_dir)
        
        return FileResponse(
            zip_path,
            filename=filename,
            media_type="application/zip"
        )
    except Exception as e:
        # 出错时立即清理
        await run_in_executor(safe_rmtree, temp_dir)
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")

