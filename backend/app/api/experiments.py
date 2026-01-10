"""
实验组管理 API

提供实验组的 CRUD 操作和结果关联管理
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import User, Experiment, Result, Dataset, experiment_results
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


router = APIRouter(prefix="/api/experiments", tags=["experiments"])


# ============ 辅助函数 ============

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
    
    # 标签筛选（JSON 数组包含）
    if tag:
        # SQLite JSON 查询
        query = query.where(Experiment.tags.contains(tag))
        count_query = count_query.where(Experiment.tags.contains(tag))
    
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
    
    # 获取每个实验组的结果数量和数据集名称
    items = []
    for exp in experiments:
        # 结果数量
        count_result = await db.execute(
            select(func.count()).select_from(experiment_results).where(
                experiment_results.c.experiment_id == exp.id
            )
        )
        result_count = count_result.scalar()
        
        # 数据集名称
        dataset_name = None
        if exp.dataset_id:
            ds_result = await db.execute(
                select(Dataset.name).where(Dataset.id == exp.dataset_id)
            )
            dataset_name = ds_result.scalar()
        
        items.append(build_experiment_response(exp, result_count, dataset_name))
    
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
        # 检查数据集权限
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
    if data.result_ids:
        for result_id in data.result_ids:
            # 验证结果存在且有权限
            try:
                result = await check_result_access(result_id, db, current_user)
                experiment.results.append(result)
                added_results.append(ExperimentResultBrief(
                    id=result.id,
                    name=result.name,
                    algo_name=result.algo_name,
                    algo_version=result.algo_version or "",
                    metrics=result.metrics or {},
                    created_at=result.created_at
                ))
            except HTTPException:
                continue  # 跳过无权限的结果
    
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
        results=added_results
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
    
    # 构建结果列表
    results = [
        ExperimentResultBrief(
            id=r.id,
            name=r.name,
            algo_name=r.algo_name,
            algo_version=r.algo_version or "",
            metrics=r.metrics or {},
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
    """添加结果到实验组"""
    experiment = await get_experiment_or_404(experiment_id, db, current_user, load_results=True)
    
    existing_ids = {r.id for r in experiment.results}
    added = []
    skipped = []
    
    for result_id in data.result_ids:
        if result_id in existing_ids:
            skipped.append(result_id)
            continue
        
        try:
            result = await check_result_access(result_id, db, current_user)
            experiment.results.append(result)
            added.append(result)
            existing_ids.add(result_id)
        except HTTPException:
            skipped.append(result_id)
    
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
    
    results = [
        ExperimentResultBrief(
            id=r.id,
            name=r.name,
            algo_name=r.algo_name,
            algo_version=r.algo_version or "",
            metrics=r.metrics or {},
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


@router.delete("/{experiment_id}/results")
async def remove_results_from_experiment(
    experiment_id: int,
    data: ExperimentRemoveResults,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """从实验组移除结果"""
    experiment = await get_experiment_or_404(experiment_id, db, current_user, load_results=True)
    
    # 移除指定结果
    experiment.results = [r for r in experiment.results if r.id not in data.result_ids]
    
    await db.commit()
    
    return {"message": f"已移除 {len(data.result_ids)} 个结果"}


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

