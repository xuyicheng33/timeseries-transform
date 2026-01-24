from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_admin_user, get_current_user
from app.database import get_db
from app.models import Dataset, Folder, User
from app.schemas import (
    FolderCreate,
    FolderListResponse,
    FolderResponse,
    FolderSortOrderUpdate,
    FolderUpdate,
)
from app.services.dataset_service import cleanup_paths, plan_dataset_delete
from app.services.permissions import get_isolation_conditions
from app.services.utils import validate_form_field

router = APIRouter(prefix="/api/folders", tags=["folders"])


def _validate_sort(sort_by: str, order: str) -> None:
    if sort_by not in {"manual", "name", "time"}:
        raise HTTPException(status_code=400, detail="Invalid sort_by")
    if order not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="Invalid order")


@router.get("", response_model=FolderListResponse)
async def list_folders(
    sort_by: str = Query("manual"),
    order: str = Query("asc"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_sort(sort_by, order)

    conditions, _ = get_isolation_conditions(current_user, Dataset)

    dataset_count_query = select(
        Dataset.folder_id, func.count(Dataset.id).label("dataset_count")
    ).group_by(Dataset.folder_id)
    if conditions:
        dataset_count_query = dataset_count_query.where(*conditions)
    dataset_count_subq = dataset_count_query.subquery()

    query = (
        select(
            Folder,
            func.coalesce(dataset_count_subq.c.dataset_count, 0).label("dataset_count"),
        )
        .outerjoin(dataset_count_subq, Folder.id == dataset_count_subq.c.folder_id)
        .where(Folder.parent_id.is_(None))
    )

    if sort_by == "name":
        query = query.order_by(Folder.name.asc() if order == "asc" else Folder.name.desc())
    elif sort_by == "time":
        query = query.order_by(
            Folder.created_at.asc() if order == "asc" else Folder.created_at.desc()
        )
    else:
        query = query.order_by(Folder.sort_order.asc(), Folder.id.asc())

    result = await db.execute(query)
    rows = result.all()

    root_count_query = select(func.count(Dataset.id)).where(Dataset.folder_id.is_(None))
    if conditions:
        root_count_query = root_count_query.where(*conditions)
    root_dataset_count = (await db.execute(root_count_query)).scalar() or 0

    items = [
        FolderResponse(
            id=folder.id,
            name=folder.name,
            parent_id=folder.parent_id,
            sort_order=folder.sort_order,
            dataset_count=dataset_count,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
        )
        for folder, dataset_count in rows
    ]

    return FolderListResponse(
        items=items, total=len(items), root_dataset_count=root_dataset_count
    )


@router.post("", response_model=FolderResponse)
async def create_folder(
    data: FolderCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    if data.parent_id is not None:
        raise HTTPException(status_code=400, detail="Only root folders are supported")

    name = validate_form_field(data.name, "Folder name", max_length=255, min_length=1)

    existing = await db.execute(
        select(Folder.id).where(Folder.parent_id.is_(None), Folder.name == name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Folder name already exists")

    max_sort_result = await db.execute(
        select(func.max(Folder.sort_order)).where(Folder.parent_id.is_(None))
    )
    max_sort_order = max_sort_result.scalar()
    sort_order = (max_sort_order if max_sort_order is not None else -1) + 1

    folder = Folder(name=name, parent_id=None, sort_order=sort_order, user_id=admin.id)
    db.add(folder)
    await db.commit()
    await db.refresh(folder)

    return FolderResponse(
        id=folder.id,
        name=folder.name,
        parent_id=folder.parent_id,
        sort_order=folder.sort_order,
        dataset_count=0,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
    )


@router.put("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: int,
    data: FolderUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    folder = await db.get(Folder, folder_id)
    if folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    if folder.parent_id is not None:
        raise HTTPException(status_code=400, detail="Only root folders are supported")

    if data.name is not None:
        name = validate_form_field(data.name, "Folder name", max_length=255, min_length=1)
        existing = await db.execute(
            select(Folder.id).where(
                Folder.parent_id.is_(None),
                Folder.name == name,
                Folder.id != folder_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Folder name already exists")
        folder.name = name

    await db.commit()
    await db.refresh(folder)

    dataset_count = (
        await db.execute(select(func.count(Dataset.id)).where(Dataset.folder_id == folder_id))
    ).scalar() or 0

    return FolderResponse(
        id=folder.id,
        name=folder.name,
        parent_id=folder.parent_id,
        sort_order=folder.sort_order,
        dataset_count=dataset_count,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
    )


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: int,
    action: str = Query(..., regex="^(move_to_root|cascade)$"),
    confirm_name: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    folder = await db.get(Folder, folder_id)
    if folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    if folder.parent_id is not None:
        raise HTTPException(status_code=400, detail="Only root folders are supported")

    dataset_ids_result = await db.execute(
        select(Dataset.id).where(Dataset.folder_id == folder_id)
    )
    dataset_ids = dataset_ids_result.scalars().all()

    if action == "move_to_root":
        datasets_result = await db.execute(
            select(Dataset).where(Dataset.folder_id == folder_id)
        )
        datasets = datasets_result.scalars().all()
        for dataset in datasets:
            dataset.folder_id = None
        await db.delete(folder)
        await db.commit()
        return {"message": "Folder deleted", "moved_datasets": len(dataset_ids)}

    if confirm_name != folder.name:
        raise HTTPException(status_code=400, detail="confirm_name mismatch")

    cleanup_targets = set()
    deleted_datasets = 0
    deleted_configs = 0
    deleted_results = 0

    try:
        for dataset_id in dataset_ids:
            plan = await plan_dataset_delete(dataset_id, db)
            deleted_datasets += 1
            deleted_configs += plan.deleted_config_count
            deleted_results += plan.deleted_result_count
            cleanup_targets.add(plan.dataset_dir)
            cleanup_targets.add(plan.results_dir)

        await db.delete(folder)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete folder") from exc

    warnings = await cleanup_paths(cleanup_targets)
    response = {
        "message": "Folder and datasets deleted",
        "deleted_datasets": deleted_datasets,
        "deleted_configs": deleted_configs,
        "deleted_results": deleted_results,
    }
    if warnings:
        response["disk_cleanup_warnings"] = warnings
    return response


@router.put("/reorder")
async def reorder_folders(
    data: FolderSortOrderUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    if not data.orders:
        raise HTTPException(status_code=400, detail="No orders provided")

    folder_ids = [item.id for item in data.orders]
    existing_result = await db.execute(
        select(Folder.id).where(Folder.id.in_(folder_ids), Folder.parent_id.is_(None))
    )
    existing_ids = set(existing_result.scalars().all())
    missing_ids = set(folder_ids) - existing_ids
    if missing_ids:
        raise HTTPException(status_code=404, detail=f"Missing folders: {sorted(missing_ids)}")

    for item in data.orders:
        folder = await db.get(Folder, item.id)
        if folder is None:
            continue
        folder.sort_order = item.sort_order

    await db.commit()
    return {"message": "Folder order updated"}
