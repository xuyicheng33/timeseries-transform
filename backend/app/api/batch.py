"""
批量操作 API 路由
提供批量删除、批量导出等功能
"""
import os
import json
import zipfile
import tempfile
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import Dataset, Configuration, Result, User
from app.config import settings
from app.services.utils import safe_rmtree
from app.services.executor import run_in_executor
from app.services.permissions import (
    check_write_access, check_read_access,
    ResourceType, ActionType
)
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/batch", tags=["batch"])


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


class ExportMetadata(BaseModel):
    """导出元数据"""
    export_time: str
    export_version: str = "1.0"
    datasets_count: int
    configs_count: int
    results_count: int


# ============ 批量删除 API ============

@router.post("/datasets/delete", response_model=BatchDeleteResult)
async def batch_delete_datasets(
    request: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    批量删除数据集
    
    会同时删除关联的配置和结果
    """
    success_count = 0
    failed_ids = []
    errors = []
    
    for dataset_id in request.ids:
        try:
            # 查询数据集
            result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
            dataset = result.scalar_one_or_none()
            
            if not dataset:
                failed_ids.append(dataset_id)
                errors.append(f"数据集 {dataset_id} 不存在")
                continue
            
            # 权限检查
            try:
                check_write_access(dataset, current_user, ActionType.DELETE, ResourceType.DATASET)
            except HTTPException as e:
                failed_ids.append(dataset_id)
                errors.append(f"数据集 {dataset_id}: {e.detail}")
                continue
            
            # 删除关联的配置
            configs = await db.execute(select(Configuration).where(Configuration.dataset_id == dataset_id))
            for config in configs.scalars().all():
                await db.delete(config)
            
            # 删除关联的结果
            results_query = await db.execute(select(Result).where(Result.dataset_id == dataset_id))
            result_dirs = []
            for res in results_query.scalars().all():
                result_dir = settings.RESULTS_DIR / str(dataset_id) / str(res.id)
                if result_dir.exists():
                    result_dirs.append(str(result_dir))
                await db.delete(res)
            
            # 删除数据集
            await db.delete(dataset)
            await db.flush()
            
            # 清理文件
            for result_dir in result_dirs:
                await run_in_executor(safe_rmtree, result_dir)
            
            dataset_dir = settings.DATASETS_DIR / str(dataset_id)
            if dataset_dir.exists():
                await run_in_executor(safe_rmtree, str(dataset_dir))
            
            success_count += 1
            
        except Exception as e:
            failed_ids.append(dataset_id)
            errors.append(f"数据集 {dataset_id}: {str(e)}")
    
    await db.commit()
    
    return BatchDeleteResult(
        success_count=success_count,
        failed_count=len(failed_ids),
        failed_ids=failed_ids,
        errors=errors[:10]  # 最多返回10条错误信息
    )


@router.post("/configurations/delete", response_model=BatchDeleteResult)
async def batch_delete_configurations(
    request: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量删除配置"""
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
            
            # 获取关联数据集检查权限
            dataset_result = await db.execute(select(Dataset).where(Dataset.id == config.dataset_id))
            dataset = dataset_result.scalar_one_or_none()
            
            try:
                check_write_access(config, current_user, ActionType.DELETE, ResourceType.CONFIGURATION, parent_dataset=dataset)
            except HTTPException as e:
                failed_ids.append(config_id)
                errors.append(f"配置 {config_id}: {e.detail}")
                continue
            
            await db.delete(config)
            await db.flush()
            success_count += 1
            
        except Exception as e:
            failed_ids.append(config_id)
            errors.append(f"配置 {config_id}: {str(e)}")
    
    await db.commit()
    
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
    """批量删除结果"""
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
            
            # 获取关联数据集检查权限
            dataset_result = await db.execute(select(Dataset).where(Dataset.id == result_obj.dataset_id))
            dataset = dataset_result.scalar_one_or_none()
            
            try:
                check_write_access(result_obj, current_user, ActionType.DELETE, ResourceType.RESULT, parent_dataset=dataset)
            except HTTPException as e:
                failed_ids.append(result_id)
                errors.append(f"结果 {result_id}: {e.detail}")
                continue
            
            # 记录要删除的目录
            result_dir = settings.RESULTS_DIR / str(result_obj.dataset_id) / str(result_id)
            
            await db.delete(result_obj)
            await db.flush()
            
            # 清理文件
            if result_dir.exists():
                await run_in_executor(safe_rmtree, str(result_dir))
            
            success_count += 1
            
        except Exception as e:
            failed_ids.append(result_id)
            errors.append(f"结果 {result_id}: {str(e)}")
    
    await db.commit()
    
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
    temp_dir: str
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
            "results_count": len(results) if include_results else 0
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
            
            # 添加数据文件
            if os.path.exists(ds.filepath):
                zf.write(ds.filepath, f"datasets/{ds.id}/data.csv")
        
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
                
                # 添加结果文件
                if os.path.exists(res.filepath):
                    zf.write(res.filepath, f"results/{res.dataset_id}/{res.id}/prediction.csv")
            
            zf.writestr("results.json", json.dumps(results_data, indent=2, ensure_ascii=False))
    
    return zip_path


@router.post("/export")
async def export_data(
    request: BatchExportRequest,
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
    try:
        zip_path = await run_in_executor(
            _create_export_zip,
            datasets,
            configs,
            results,
            request.include_results,
            temp_dir
        )
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"timeseries_export_{timestamp}.zip"
        
        return FileResponse(
            zip_path,
            filename=filename,
            media_type="application/zip",
            background=None  # 不自动删除，由客户端下载完成后清理
        )
    except Exception as e:
        await run_in_executor(safe_rmtree, temp_dir)
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


# ============ 导入 API ============

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
        # 读取元数据
        if "metadata.json" in zf.namelist():
            data["metadata"] = json.loads(zf.read("metadata.json").decode('utf-8'))
        
        # 读取数据集信息
        if "datasets.json" in zf.namelist():
            data["datasets"] = json.loads(zf.read("datasets.json").decode('utf-8'))
        
        # 读取配置信息
        if "configurations.json" in zf.namelist():
            data["configurations"] = json.loads(zf.read("configurations.json").decode('utf-8'))
        
        # 读取结果信息
        if "results.json" in zf.namelist():
            data["results"] = json.loads(zf.read("results.json").decode('utf-8'))
        
        # 记录文件列表
        for name in zf.namelist():
            if name.startswith("datasets/") and name.endswith(".csv"):
                data["files"][name] = True
            elif name.startswith("results/") and name.endswith(".csv"):
                data["files"][name] = True
    
    return data


@router.post("/import/preview")
async def preview_import(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    预览导入内容
    
    返回 ZIP 文件中包含的数据集、配置、结果数量
    """
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 ZIP 文件")
    
    # 保存到临时文件
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "import.zip")
    
    try:
        # 写入文件
        content = await file.read()
        if len(content) > 500 * 1024 * 1024:  # 500MB 限制
            raise HTTPException(status_code=400, detail="文件过大，最大支持 500MB")
        
        with open(zip_path, 'wb') as f:
            f.write(content)
        
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
    current_user: User = Depends(get_current_user)
):
    """
    导入数据集、配置和结果
    
    会创建新的数据集，ID 会重新分配
    """
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 ZIP 文件")
    
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "import.zip")
    
    try:
        # 写入文件
        content = await file.read()
        if len(content) > 500 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件过大，最大支持 500MB")
        
        with open(zip_path, 'wb') as f:
            f.write(content)
        
        # 解析 ZIP
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # 读取数据
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
                
                # 创建新数据集
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
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")
    finally:
        await run_in_executor(safe_rmtree, temp_dir)

