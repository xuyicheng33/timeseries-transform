"""
批量操作 API 路由
提供批量删除、批量导出等功能
"""
import os
import json
import zipfile
import tempfile
import aiofiles
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import Dataset, Configuration, Result, User
from app.config import settings
from app.services.utils import safe_rmtree
from app.services.executor import run_in_executor
from app.services.security import validate_filepath
from app.services.permissions import (
    check_read_access, check_owner_or_admin,
    ResourceType
)
from app.api.auth import get_current_user, get_admin_user

router = APIRouter(prefix="/api/batch", tags=["batch"])

# 导入文件分块大小
CHUNK_SIZE = 1024 * 1024  # 1MB
MAX_IMPORT_SIZE = 500 * 1024 * 1024  # 500MB


# ============ 请求/响应模型 ============

class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    ids: List[int] = Field(..., min_length=1, max_length=100, description="要删除的 ID 列表")


class BatchDeleteResult(BaseModel):
    """批量删除结果"""
    success_count: int
    failed_count: int
    failed_ids: List[int] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class BatchExportRequest(BaseModel):
    """批量导出请求"""
    dataset_ids: List[int] = Field(default_factory=list, description="要导出的数据集 ID")
    include_configs: bool = Field(default=True, description="是否包含配置")
    include_results: bool = Field(default=False, description="是否包含结果文件")


# ============ 批量删除 API ============

@router.post("/datasets/delete", response_model=BatchDeleteResult)
async def batch_delete_datasets(
    request: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user)  # 仅管理员可用
):
    """
    批量删除数据集（仅管理员）
    
    每个数据集单独事务处理，失败不影响其他
    """
    success_count = 0
    failed_ids = []
    errors = []
    
    for dataset_id in request.ids:
        # 每个 ID 单独处理，失败时回滚当前操作
        try:
            # 查询数据集
            result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
            dataset = result.scalar_one_or_none()
            
            if not dataset:
                failed_ids.append(dataset_id)
                errors.append(f"数据集 {dataset_id} 不存在")
                continue
            
            # 收集要删除的文件目录（commit 成功后再删）
            dirs_to_delete = []
            
            # 删除关联的配置
            configs = await db.execute(select(Configuration).where(Configuration.dataset_id == dataset_id))
            for config in configs.scalars().all():
                await db.delete(config)
            
            # 删除关联的结果
            results_query = await db.execute(select(Result).where(Result.dataset_id == dataset_id))
            for res in results_query.scalars().all():
                result_dir = settings.RESULTS_DIR / str(dataset_id) / str(res.id)
                if result_dir.exists():
                    dirs_to_delete.append(str(result_dir))
                await db.delete(res)
            
            # 数据集目录
            dataset_dir = settings.DATASETS_DIR / str(dataset_id)
            if dataset_dir.exists():
                dirs_to_delete.append(str(dataset_dir))
            
            # 删除数据集
            await db.delete(dataset)
            
            # 提交当前数据集的删除
            await db.commit()
            
            # commit 成功后再清理文件
            for dir_path in dirs_to_delete:
                await run_in_executor(safe_rmtree, dir_path)
            
            success_count += 1
            
        except Exception as e:
            # 回滚当前失败的操作
            await db.rollback()
            failed_ids.append(dataset_id)
            errors.append(f"数据集 {dataset_id}: {str(e)}")
    
    return BatchDeleteResult(
        success_count=success_count,
        failed_count=len(failed_ids),
        failed_ids=failed_ids,
        errors=errors[:10]
    )


@router.post("/configurations/delete", response_model=BatchDeleteResult)
async def batch_delete_configurations(
    request: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    批量删除配置（所有者或管理员）
    """
    success_count = 0
    failed_ids = []
    errors = []
    
    for config_id in request.ids:
        try:
            result = await db.execute(select(Configuration).where(Configuration.id == config_id))
            config = result.scalar_one_or_none()
            
            if not config:
                failed_ids.append(config_id)
                errors.append(f"配置 {config_id} 不存在")
                continue
            
            # 仅所有者或管理员可删除
            try:
                check_owner_or_admin(config, current_user, "删除配置")
            except HTTPException as e:
                failed_ids.append(config_id)
                errors.append(f"配置 {config_id}: {e.detail}")
                continue
            
            await db.delete(config)
            await db.commit()
            success_count += 1
            
        except Exception as e:
            await db.rollback()
            failed_ids.append(config_id)
            errors.append(f"配置 {config_id}: {str(e)}")
    
    return BatchDeleteResult(
        success_count=success_count,
        failed_count=len(failed_ids),
        failed_ids=failed_ids,
        errors=errors[:10]
    )


@router.post("/results/delete", response_model=BatchDeleteResult)
async def batch_delete_results(
    request: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    批量删除结果（所有者或管理员）
    """
    success_count = 0
    failed_ids = []
    errors = []
    
    for result_id in request.ids:
        try:
            result = await db.execute(select(Result).where(Result.id == result_id))
            result_obj = result.scalar_one_or_none()
            
            if not result_obj:
                failed_ids.append(result_id)
                errors.append(f"结果 {result_id} 不存在")
                continue
            
            # 仅所有者或管理员可删除
            try:
                check_owner_or_admin(result_obj, current_user, "删除结果")
            except HTTPException as e:
                failed_ids.append(result_id)
                errors.append(f"结果 {result_id}: {e.detail}")
                continue
            
            # 记录要删除的目录
            result_dir = settings.RESULTS_DIR / str(result_obj.dataset_id) / str(result_id)
            
            await db.delete(result_obj)
            await db.commit()
            
            # commit 成功后再清理文件
            if result_dir.exists():
                await run_in_executor(safe_rmtree, str(result_dir))
            
            success_count += 1
            
        except Exception as e:
            await db.rollback()
            failed_ids.append(result_id)
            errors.append(f"结果 {result_id}: {str(e)}")
    
    return BatchDeleteResult(
        success_count=success_count,
        failed_count=len(failed_ids),
        failed_ids=failed_ids,
        errors=errors[:10]
    )


# ============ 导出 API ============

def _create_export_zip(
    datasets: List[Dataset],
    configs: List[Configuration],
    results: List[Result],
    include_results: bool,
    temp_dir: str,
    skipped_files: List[str]
) -> str:
    """创建导出 ZIP 文件（同步）"""
    zip_path = os.path.join(temp_dir, "export.zip")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 导出元数据
        metadata = {
            "export_time": datetime.now().isoformat(),
            "export_version": "1.0",
            "datasets_count": len(datasets),
            "configs_count": len(configs),
            "results_count": len(results) if include_results else 0,
            "skipped_files": skipped_files
        }
        zf.writestr("metadata.json", json.dumps(metadata, indent=2, ensure_ascii=False))
        
        # 导出数据集信息
        datasets_data = []
        for ds in datasets:
            ds_info = {
                "id": ds.id,
                "name": ds.name,
                "filename": ds.filename,
                "description": ds.description or "",
                "row_count": ds.row_count,
                "column_count": ds.column_count,
                "columns": ds.columns,
                "encoding": ds.encoding,
                "is_public": ds.is_public
            }
            datasets_data.append(ds_info)
            
            # 添加数据文件（校验路径安全）
            if ds.filepath and os.path.exists(ds.filepath):
                if validate_filepath(ds.filepath):
                    zf.write(ds.filepath, f"datasets/{ds.id}/data.csv")
                else:
                    skipped_files.append(f"datasets/{ds.id}: 路径不安全")
        
        zf.writestr("datasets.json", json.dumps(datasets_data, indent=2, ensure_ascii=False))
        
        # 导出配置信息
        configs_data = []
        for cfg in configs:
            cfg_info = {
                "id": cfg.id,
                "name": cfg.name,
                "dataset_id": cfg.dataset_id,
                "channels": cfg.channels,
                "normalization": cfg.normalization,
                "anomaly_enabled": cfg.anomaly_enabled,
                "anomaly_type": cfg.anomaly_type or "",
                "injection_algorithm": cfg.injection_algorithm or "",
                "sequence_logic": cfg.sequence_logic or "",
                "window_size": cfg.window_size,
                "stride": cfg.stride,
                "target_type": cfg.target_type,
                "target_k": cfg.target_k,
                "generated_filename": cfg.generated_filename
            }
            configs_data.append(cfg_info)
        
        zf.writestr("configurations.json", json.dumps(configs_data, indent=2, ensure_ascii=False))
        
        # 导出结果信息
        if include_results:
            results_data = []
            for res in results:
                res_info = {
                    "id": res.id,
                    "name": res.name,
                    "dataset_id": res.dataset_id,
                    "configuration_id": res.configuration_id,
                    "filename": res.filename,
                    "row_count": res.row_count,
                    "algo_name": res.algo_name,
                    "algo_version": res.algo_version or "",
                    "description": res.description or "",
                    "metrics": res.metrics
                }
                results_data.append(res_info)
                
                # 添加结果文件（校验路径安全）
                if res.filepath and os.path.exists(res.filepath):
                    if validate_filepath(res.filepath):
                        zf.write(res.filepath, f"results/{res.dataset_id}/{res.id}/prediction.csv")
                    else:
                        skipped_files.append(f"results/{res.dataset_id}/{res.id}: 路径不安全")
            
            zf.writestr("results.json", json.dumps(results_data, indent=2, ensure_ascii=False))
    
    return zip_path


def _cleanup_temp_dir(temp_dir: str):
    """清理临时目录（用于 BackgroundTasks）"""
    safe_rmtree(temp_dir)


@router.post("/export")
async def export_data(
    request: BatchExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    导出数据集、配置和结果
    
    返回 ZIP 文件，包含：
    - metadata.json: 导出元数据
    - datasets.json: 数据集信息
    - datasets/{id}/data.csv: 数据文件
    - configurations.json: 配置信息
    - results.json: 结果信息（可选）
    - results/{dataset_id}/{id}/prediction.csv: 结果文件（可选）
    """
    if not request.dataset_ids:
        raise HTTPException(status_code=400, detail="请选择要导出的数据集")
    
    if len(request.dataset_ids) > 50:
        raise HTTPException(status_code=400, detail="单次最多导出 50 个数据集")
    
    # 查询数据集
    datasets = []
    for ds_id in request.dataset_ids:
        result = await db.execute(select(Dataset).where(Dataset.id == ds_id))
        dataset = result.scalar_one_or_none()
        if dataset:
            try:
                check_read_access(dataset, current_user, ResourceType.DATASET)
                datasets.append(dataset)
            except HTTPException:
                pass  # 跳过无权限的数据集
    
    if not datasets:
        raise HTTPException(status_code=404, detail="没有可导出的数据集")
    
    # 查询配置
    configs = []
    if request.include_configs:
        for ds in datasets:
            cfg_result = await db.execute(
                select(Configuration).where(Configuration.dataset_id == ds.id)
            )
            configs.extend(cfg_result.scalars().all())
    
    # 查询结果
    results = []
    if request.include_results:
        for ds in datasets:
            res_result = await db.execute(
                select(Result).where(Result.dataset_id == ds.id)
            )
            results.extend(res_result.scalars().all())
    
    # 创建临时目录和 ZIP 文件
    temp_dir = tempfile.mkdtemp()
    skipped_files: List[str] = []
    
    try:
        zip_path = await run_in_executor(
            _create_export_zip,
            datasets,
            configs,
            results,
            request.include_results,
            temp_dir,
            skipped_files
        )
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"timeseries_export_{timestamp}.zip"
        
        # 使用 BackgroundTasks 在响应完成后清理临时目录
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


# ============ 导入 API ============

async def _save_upload_to_temp(file: UploadFile, temp_dir: str) -> str:
    """分块保存上传文件到临时目录"""
    zip_path = os.path.join(temp_dir, "import.zip")
    total_size = 0
    
    async with aiofiles.open(zip_path, 'wb') as f:
        while chunk := await file.read(CHUNK_SIZE):
            total_size += len(chunk)
            if total_size > MAX_IMPORT_SIZE:
                raise HTTPException(status_code=400, detail=f"文件过大，最大支持 {MAX_IMPORT_SIZE // 1024 // 1024}MB")
            await f.write(chunk)
    
    return zip_path


def _parse_import_zip(zip_path: str) -> dict:
    """解析导入的 ZIP 文件（同步）"""
    data = {
        "metadata": None,
        "datasets": [],
        "configurations": [],
        "results": [],
        "files": {}
    }
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        if "metadata.json" in zf.namelist():
            data["metadata"] = json.loads(zf.read("metadata.json").decode('utf-8'))
        
        if "datasets.json" in zf.namelist():
            data["datasets"] = json.loads(zf.read("datasets.json").decode('utf-8'))
        
        if "configurations.json" in zf.namelist():
            data["configurations"] = json.loads(zf.read("configurations.json").decode('utf-8'))
        
        if "results.json" in zf.namelist():
            data["results"] = json.loads(zf.read("results.json").decode('utf-8'))
        
        for name in zf.namelist():
            if name.startswith("datasets/") and name.endswith(".csv"):
                data["files"][name] = True
            elif name.startswith("results/") and name.endswith(".csv"):
                data["files"][name] = True
    
    return data


@router.post("/import/preview")
async def preview_import(
    file: UploadFile = File(...),
    current_user: User = Depends(get_admin_user)  # 仅管理员可用
):
    """
    预览导入内容（仅管理员）
    
    返回 ZIP 文件中包含的数据集、配置、结果数量
    """
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 ZIP 文件")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 分块写入临时文件
        zip_path = await _save_upload_to_temp(file, temp_dir)
        
        # 解析 ZIP
        data = await run_in_executor(_parse_import_zip, zip_path)
        
        return {
            "metadata": data["metadata"],
            "datasets_count": len(data["datasets"]),
            "configurations_count": len(data["configurations"]),
            "results_count": len(data["results"]),
            "datasets": [{"id": d["id"], "name": d["name"]} for d in data["datasets"]],
            "has_data_files": any(k.startswith("datasets/") for k in data["files"]),
            "has_result_files": any(k.startswith("results/") for k in data["files"])
        }
    finally:
        await run_in_executor(safe_rmtree, temp_dir)


@router.post("/import")
async def import_data(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user)  # 仅管理员可用
):
    """
    导入数据集、配置和结果（仅管理员）
    
    会创建新的数据集，ID 会重新分配
    """
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 ZIP 文件")
    
    temp_dir = tempfile.mkdtemp()
    created_dirs: List[str] = []  # 记录创建的目录，失败时清理
    
    try:
        # 分块写入临时文件
        zip_path = await _save_upload_to_temp(file, temp_dir)
        
        # 解析 ZIP
        with zipfile.ZipFile(zip_path, 'r') as zf:
            datasets_data = []
            configs_data = []
            results_data = []
            
            if "datasets.json" in zf.namelist():
                datasets_data = json.loads(zf.read("datasets.json").decode('utf-8'))
            if "configurations.json" in zf.namelist():
                configs_data = json.loads(zf.read("configurations.json").decode('utf-8'))
            if "results.json" in zf.namelist():
                results_data = json.loads(zf.read("results.json").decode('utf-8'))
            
            # ID 映射（旧 ID -> 新 ID）
            dataset_id_map = {}
            config_id_map = {}
            
            imported_datasets = 0
            imported_configs = 0
            imported_results = 0
            
            # 导入数据集
            for ds_info in datasets_data:
                old_id = ds_info["id"]
                
                new_dataset = Dataset(
                    name=ds_info["name"] + " (导入)",
                    filename=ds_info["filename"],
                    filepath="",
                    description=ds_info.get("description", ""),
                    user_id=current_user.id,
                    is_public=ds_info.get("is_public", False),
                    row_count=ds_info.get("row_count", 0),
                    column_count=ds_info.get("column_count", 0),
                    columns=ds_info.get("columns", []),
                    encoding=ds_info.get("encoding", "utf-8")
                )
                db.add(new_dataset)
                await db.flush()
                
                dataset_id_map[old_id] = new_dataset.id
                
                # 提取数据文件
                data_file_path = f"datasets/{old_id}/data.csv"
                if data_file_path in zf.namelist():
                    dataset_dir = settings.DATASETS_DIR / str(new_dataset.id)
                    dataset_dir.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(str(dataset_dir))
                    
                    filepath = dataset_dir / "data.csv"
                    with zf.open(data_file_path) as src, open(filepath, 'wb') as dst:
                        dst.write(src.read())
                    
                    new_dataset.filepath = str(filepath)
                    new_dataset.file_size = os.path.getsize(filepath)
                
                imported_datasets += 1
            
            # 导入配置
            for cfg_info in configs_data:
                old_dataset_id = cfg_info["dataset_id"]
                if old_dataset_id not in dataset_id_map:
                    continue
                
                old_config_id = cfg_info["id"]
                new_config = Configuration(
                    name=cfg_info["name"],
                    dataset_id=dataset_id_map[old_dataset_id],
                    channels=cfg_info.get("channels", []),
                    normalization=cfg_info.get("normalization", "none"),
                    anomaly_enabled=cfg_info.get("anomaly_enabled", False),
                    anomaly_type=cfg_info.get("anomaly_type") or None,
                    injection_algorithm=cfg_info.get("injection_algorithm") or None,
                    sequence_logic=cfg_info.get("sequence_logic") or None,
                    window_size=cfg_info.get("window_size", 100),
                    stride=cfg_info.get("stride", 1),
                    target_type=cfg_info.get("target_type", "next"),
                    target_k=cfg_info.get("target_k", 1),
                    generated_filename=cfg_info.get("generated_filename", "")
                )
                db.add(new_config)
                await db.flush()
                
                config_id_map[old_config_id] = new_config.id
                imported_configs += 1
            
            # 导入结果
            for res_info in results_data:
                old_dataset_id = res_info["dataset_id"]
                if old_dataset_id not in dataset_id_map:
                    continue
                
                new_dataset_id = dataset_id_map[old_dataset_id]
                old_config_id = res_info.get("configuration_id")
                new_config_id = config_id_map.get(old_config_id) if old_config_id else None
                
                new_result = Result(
                    name=res_info["name"],
                    dataset_id=new_dataset_id,
                    configuration_id=new_config_id,
                    user_id=current_user.id,
                    filename=res_info["filename"],
                    filepath="",
                    row_count=res_info.get("row_count", 0),
                    algo_name=res_info.get("algo_name", "unknown"),
                    algo_version=res_info.get("algo_version", ""),
                    description=res_info.get("description", ""),
                    metrics=res_info.get("metrics", {})
                )
                db.add(new_result)
                await db.flush()
                
                # 提取结果文件
                old_result_id = res_info["id"]
                result_file_path = f"results/{old_dataset_id}/{old_result_id}/prediction.csv"
                if result_file_path in zf.namelist():
                    result_dir = settings.RESULTS_DIR / str(new_dataset_id) / str(new_result.id)
                    result_dir.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(str(result_dir))
                    
                    filepath = result_dir / "prediction.csv"
                    with zf.open(result_file_path) as src, open(filepath, 'wb') as dst:
                        dst.write(src.read())
                    
                    new_result.filepath = str(filepath)
                
                imported_results += 1
        
        await db.commit()
        
        return {
            "success": True,
            "message": "导入成功",
            "imported_datasets": imported_datasets,
            "imported_configurations": imported_configs,
            "imported_results": imported_results,
            "dataset_id_map": dataset_id_map
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # 回滚数据库
        await db.rollback()
        # 清理已创建的目录（孤儿文件）
        for dir_path in created_dirs:
            await run_in_executor(safe_rmtree, dir_path)
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")
    finally:
        # 清理临时目录
        await run_in_executor(safe_rmtree, temp_dir)
