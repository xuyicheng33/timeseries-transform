from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Configuration, Dataset, Result, experiment_results
from app.services.executor import run_in_executor
from app.services.utils import safe_rmtree


@dataclass(frozen=True)
class DatasetDeletePlan:
    dataset_id: int
    deleted_config_count: int
    deleted_result_count: int
    dataset_dir: Path
    results_dir: Path


async def plan_dataset_delete(dataset_id: int, db: AsyncSession) -> DatasetDeletePlan:
    dataset = await db.get(Dataset, dataset_id)
    if dataset is None:
        raise ValueError(f"Dataset {dataset_id} not found")

    configs_result = await db.execute(
        select(Configuration).where(Configuration.dataset_id == dataset_id)
    )
    configs = configs_result.scalars().all()

    results_result = await db.execute(select(Result).where(Result.dataset_id == dataset_id))
    results = results_result.scalars().all()
    result_ids = [r.id for r in results]

    if result_ids:
        await db.execute(
            experiment_results.delete().where(experiment_results.c.result_id.in_(result_ids))
        )

    for config in configs:
        await db.delete(config)
    for result in results:
        await db.delete(result)
    await db.delete(dataset)

    return DatasetDeletePlan(
        dataset_id=dataset_id,
        deleted_config_count=len(configs),
        deleted_result_count=len(results),
        dataset_dir=settings.DATASETS_DIR / str(dataset_id),
        results_dir=settings.RESULTS_DIR / str(dataset_id),
    )


async def cleanup_paths(paths: Iterable[Path]) -> List[str]:
    warnings: List[str] = []
    for path in paths:
        if not path.exists():
            continue
        ok = await run_in_executor(safe_rmtree, str(path))
        if not ok:
            warnings.append(f"Failed to remove path: {path}")
    return warnings

