"""
数据质量 API 路由
提供数据质量检测、清洗预览、清洗执行等功能
"""
import os
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Dataset, User
from app.schemas import (
    DataQualityReport,
    QualityCheckRequest,
    CleaningConfig,
    CleaningPreviewResponse,
    CleaningResult,
    DatasetResponse,
)
from app.config import settings
from app.services.quality import analyze_data_quality
from app.services.cleaning import preview_cleaning, apply_cleaning
from app.services.executor import run_in_executor
from app.services.security import validate_filepath
from app.services.permissions import check_read_access, ResourceType
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/quality", tags=["quality"])


def _read_csv_sync(filepath: str, encoding: str = "utf-8") -> pd.DataFrame:
    """同步读取 CSV 文件"""
    return pd.read_csv(filepath, encoding=encoding)


def _read_csv_with_sampling(filepath: str, encoding: str = "utf-8", max_rows: int = None, sample_size: int = None) -> tuple[pd.DataFrame, bool, int]:
    """
    读取 CSV 文件，支持大文件采样
    
    采样策略：使用 chunksize 流式读取 + 蓄水池采样算法，
    一次遍历完成行数统计和采样，保证全局均匀采样。
    
    时间复杂度：O(n) - 流式遍历一次文件
    内存复杂度：
      - 小文件 (≤ max_rows)：O(n)，直接读取
      - 大文件 (> max_rows)：O(sample_size)，蓄水池采样
    
    注意：此实现假设 CSV 文件格式规范（无字段内换行），
    如有多行字段需求，应在上传时预处理或使用专门的解析器。
    
    Args:
        filepath: 文件路径
        encoding: 编码
        max_rows: 超过此行数则采样（None 表示不采样）
        sample_size: 采样行数
    
    Returns:
        (DataFrame, is_sampled, total_rows): 数据、是否采样、总行数
    """
    import random as rng
    
    # 如果不需要采样保护，直接读取
    if not max_rows or not sample_size:
        df = pd.read_csv(filepath, encoding=encoding)
        return df, False, len(df)
    
    # 始终使用蓄水池采样，保证全局均匀
    # 蓄水池大小为 sample_size，确保内存可控
    chunk_size = max(10000, sample_size // 10)
    
    # 使用独立的 Random 实例，避免影响全局 RNG
    local_rng = rng.Random(42)  # 固定种子保证可重复性
    
    # 蓄水池存储为 list[tuple]
    reservoir: list[tuple] = []
    total_rows = 0
    columns = None
    
    # 流式读取，始终执行蓄水池采样
    for chunk in pd.read_csv(filepath, encoding=encoding, chunksize=chunk_size):
        if columns is None:
            columns = chunk.columns.tolist()
        
        for row_tuple in chunk.itertuples(index=False, name=None):
            if total_rows < sample_size:
                # 前 sample_size 个元素直接放入蓄水池
                reservoir.append(row_tuple)
            else:
                # 以 sample_size/(total_rows+1) 的概率替换蓄水池中的元素
                j = local_rng.randint(0, total_rows)
                if j < sample_size:
                    reservoir[j] = row_tuple
            total_rows += 1
    
    # 判断是否需要采样（文件行数是否超过阈值）
    if total_rows <= max_rows:
        # 小文件：蓄水池包含全部数据，直接返回
        df = pd.DataFrame(reservoir, columns=columns)
        return df, False, total_rows
    else:
        # 大文件：蓄水池是均匀采样结果
        df = pd.DataFrame(reservoir, columns=columns)
        return df, True, total_rows


def _save_csv_sync(df: pd.DataFrame, filepath: str, encoding: str = "utf-8"):
    """同步保存 CSV 文件"""
    df.to_csv(filepath, index=False, encoding=encoding)


@router.get("/{dataset_id}/report", response_model=DataQualityReport)
async def get_quality_report(
    dataset_id: int,
    outlier_method: str = "iqr",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取数据集的质量报告
    
    Args:
        dataset_id: 数据集 ID
        outlier_method: 异常值检测方法 (iqr / zscore / mad / percentile)
    
    Returns:
        DataQualityReport: 质量报告
    
    Note:
        对于超过 50 万行的大文件，会自动采样 10 万行进行分析，
        报告中会标注是否为采样分析。
    """
    # 查询数据集
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    # 权限检查
    check_read_access(dataset, current_user, ResourceType.DATASET)
    
    # 检查文件是否存在
    if not os.path.exists(dataset.filepath):
        raise HTTPException(status_code=404, detail="数据集文件不存在，可能已被删除")
    
    # 验证文件路径安全
    if not validate_filepath(dataset.filepath):
        raise HTTPException(status_code=403, detail="文件路径不安全")
    
    # 读取数据（支持大文件采样）
    try:
        df, is_sampled, total_rows = await run_in_executor(
            _read_csv_with_sampling,
            dataset.filepath,
            dataset.encoding or "utf-8",
            settings.MAX_ROWS_FOR_FULL_ANALYSIS,
            settings.SAMPLE_SIZE_FOR_LARGE_FILES
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取数据集文件失败: {str(e)}")
    
    # 构建检测请求
    request = QualityCheckRequest(
        outlier_method=outlier_method,
        include_suggestions=True
    )
    
    # 生成质量报告
    try:
        report = await run_in_executor(
            analyze_data_quality,
            df,
            dataset.id,
            dataset.name,
            request
        )
        
        # 如果是采样分析，在报告中添加说明
        if is_sampled:
            from app.schemas import QualitySuggestion
            sample_note = QualitySuggestion(
                level="info",
                column=None,
                issue=f"由于数据量较大（{total_rows:,} 行），本报告基于 {len(df):,} 行采样数据生成",
                suggestion="采样分析结果具有统计代表性，但可能无法发现所有异常值",
                auto_fixable=False
            )
            report.suggestions.insert(0, sample_note)
            # 更新总行数为实际行数
            report.total_rows = total_rows
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"质量分析失败: {str(e)}")
    
    return report


@router.post("/{dataset_id}/report", response_model=DataQualityReport)
async def generate_quality_report(
    dataset_id: int,
    request: QualityCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    生成数据集的质量报告（带自定义参数）
    
    Args:
        dataset_id: 数据集 ID
        request: 质量检测请求配置
    
    Returns:
        DataQualityReport: 质量报告
    
    Note:
        对于超过 50 万行的大文件，会自动采样 10 万行进行分析。
    """
    # 查询数据集
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    # 权限检查
    check_read_access(dataset, current_user, ResourceType.DATASET)
    
    # 检查文件是否存在
    if not os.path.exists(dataset.filepath):
        raise HTTPException(status_code=404, detail="数据集文件不存在，可能已被删除")
    
    # 验证文件路径安全
    if not validate_filepath(dataset.filepath):
        raise HTTPException(status_code=403, detail="文件路径不安全")
    
    # 读取数据（支持大文件采样）
    try:
        df, is_sampled, total_rows = await run_in_executor(
            _read_csv_with_sampling,
            dataset.filepath,
            dataset.encoding or "utf-8",
            settings.MAX_ROWS_FOR_FULL_ANALYSIS,
            settings.SAMPLE_SIZE_FOR_LARGE_FILES
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取数据集文件失败: {str(e)}")
    
    # 生成质量报告
    try:
        report = await run_in_executor(
            analyze_data_quality,
            df,
            dataset.id,
            dataset.name,
            request
        )
        
        # 如果是采样分析，在报告中添加说明
        if is_sampled:
            from app.schemas import QualitySuggestion
            sample_note = QualitySuggestion(
                level="info",
                column=None,
                issue=f"由于数据量较大（{total_rows:,} 行），本报告基于 {len(df):,} 行采样数据生成",
                suggestion="采样分析结果具有统计代表性，但可能无法发现所有异常值",
                auto_fixable=False
            )
            report.suggestions.insert(0, sample_note)
            report.total_rows = total_rows
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"质量分析失败: {str(e)}")
    
    return report


@router.post("/{dataset_id}/clean/preview", response_model=CleaningPreviewResponse)
async def preview_data_cleaning(
    dataset_id: int,
    config: CleaningConfig,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    预览数据清洗效果
    
    不会修改原数据，只返回清洗后的预览信息
    
    Args:
        dataset_id: 数据集 ID
        config: 清洗配置
    
    Returns:
        CleaningPreviewResponse: 清洗预览结果
    """
    # 查询数据集
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    # 权限检查（预览只需要读权限）
    check_read_access(dataset, current_user, ResourceType.DATASET)
    
    # 检查文件是否存在
    if not os.path.exists(dataset.filepath):
        raise HTTPException(status_code=404, detail="数据集文件不存在，可能已被删除")
    
    # 验证文件路径安全
    if not validate_filepath(dataset.filepath):
        raise HTTPException(status_code=403, detail="文件路径不安全")
    
    # 读取数据
    try:
        df = await run_in_executor(
            _read_csv_sync,
            dataset.filepath,
            dataset.encoding or "utf-8"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取数据集文件失败: {str(e)}")
    
    # 预览清洗效果
    try:
        preview_result = await run_in_executor(preview_cleaning, df, config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清洗预览失败: {str(e)}")
    
    return preview_result


@router.post("/{dataset_id}/clean/apply", response_model=CleaningResult)
async def apply_data_cleaning(
    dataset_id: int,
    config: CleaningConfig,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    执行数据清洗
    
    根据配置，可以创建新数据集或覆盖原数据集
    
    Args:
        dataset_id: 数据集 ID
        config: 清洗配置
    
    Returns:
        CleaningResult: 清洗执行结果
    """
    # 查询数据集
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    # 权限检查（执行清洗需要管理员权限，与数据集上传/编辑/删除保持一致）
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="数据清洗操作仅限管理员执行"
        )
    
    # 检查文件是否存在
    if not os.path.exists(dataset.filepath):
        raise HTTPException(status_code=404, detail="数据集文件不存在，可能已被删除")
    
    # 验证文件路径安全
    if not validate_filepath(dataset.filepath):
        raise HTTPException(status_code=403, detail="文件路径不安全")
    
    # 读取数据
    try:
        df = await run_in_executor(
            _read_csv_sync,
            dataset.filepath,
            dataset.encoding or "utf-8"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取数据集文件失败: {str(e)}")
    
    rows_before = len(df)
    
    # 执行清洗
    try:
        cleaned_df, cells_modified = await run_in_executor(apply_cleaning, df, config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据清洗失败: {str(e)}")
    
    rows_after = len(cleaned_df)
    rows_removed = rows_before - rows_after
    columns_removed = [c for c in df.columns if c not in cleaned_df.columns]
    
    # 计算清洗后的质量评分
    from app.services.quality import QualityAnalyzer
    try:
        analyzer = QualityAnalyzer(cleaned_df, dataset.id, dataset.name)
        _, missing_ratio = analyzer.analyze_missing()[1:3]
        _, outlier_ratio = analyzer.detect_outliers(
            method=config.outlier_method,
            params=config.outlier_params
        )[1:3]
        dup_ratio = analyzer.analyze_duplicates()[1]
        quality_score, _ = analyzer.calculate_quality_score(
            missing_ratio, outlier_ratio, dup_ratio, None
        )
    except:
        quality_score = 0
    
    new_dataset_id = None
    new_dataset_name = None
    
    if config.create_new_dataset:
        # 创建新数据集
        new_name = f"{dataset.name}{config.new_dataset_suffix}"
        new_filename = f"{os.path.splitext(dataset.filename)[0]}{config.new_dataset_suffix}.csv"
        
        # 创建新数据集记录
        new_dataset = Dataset(
            name=new_name,
            filename=new_filename,
            filepath="",  # 稍后更新
            description=f"由 {dataset.name} 清洗生成",
            user_id=current_user.id,
            is_public=dataset.is_public,
            file_size=0,
            row_count=len(cleaned_df),
            column_count=len(cleaned_df.columns),
            columns=cleaned_df.columns.tolist(),
            encoding=dataset.encoding or "utf-8"
        )
        db.add(new_dataset)
        await db.flush()
        
        # 创建目录并保存文件
        new_dataset_dir = settings.DATASETS_DIR / str(new_dataset.id)
        new_dataset_dir.mkdir(parents=True, exist_ok=True)
        new_filepath = new_dataset_dir / "data.csv"
        
        try:
            await run_in_executor(
                _save_csv_sync,
                cleaned_df,
                str(new_filepath),
                dataset.encoding or "utf-8"
            )
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"保存清洗后数据失败: {str(e)}")
        
        # 更新文件路径和大小
        new_dataset.filepath = str(new_filepath)
        new_dataset.file_size = os.path.getsize(new_filepath)
        
        await db.commit()
        await db.refresh(new_dataset)
        
        new_dataset_id = new_dataset.id
        new_dataset_name = new_dataset.name
        
        message = f"清洗完成，已创建新数据集: {new_name}"
    else:
        # 覆盖原数据集
        try:
            await run_in_executor(
                _save_csv_sync,
                cleaned_df,
                dataset.filepath,
                dataset.encoding or "utf-8"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"保存清洗后数据失败: {str(e)}")
        
        # 更新数据集元信息
        dataset.row_count = len(cleaned_df)
        dataset.column_count = len(cleaned_df.columns)
        dataset.columns = cleaned_df.columns.tolist()
        dataset.file_size = os.path.getsize(dataset.filepath)
        
        await db.commit()
        
        message = "清洗完成，已更新原数据集"
    
    return CleaningResult(
        success=True,
        message=message,
        new_dataset_id=new_dataset_id,
        new_dataset_name=new_dataset_name,
        rows_before=rows_before,
        rows_after=rows_after,
        rows_removed=rows_removed,
        cells_modified=cells_modified,
        columns_removed=columns_removed,
        quality_score_after=quality_score
    )


@router.get("/{dataset_id}/outliers")
async def get_outlier_details(
    dataset_id: int,
    column: str,
    method: str = "iqr",
    multiplier: float = 1.5,
    threshold: float = 3.0,
    lower_pct: int = 1,
    upper_pct: int = 99,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取指定列的异常值详情
    
    Args:
        dataset_id: 数据集 ID
        column: 列名
        method: 检测方法
        multiplier: IQR 倍数
        threshold: Z-Score/MAD 阈值
        lower_pct: 百分位下界
        upper_pct: 百分位上界
    
    Returns:
        异常值详情
    """
    # 查询数据集
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    
    # 权限检查
    check_read_access(dataset, current_user, ResourceType.DATASET)
    
    # 检查文件是否存在
    if not os.path.exists(dataset.filepath):
        raise HTTPException(status_code=404, detail="数据集文件不存在")
    
    if not validate_filepath(dataset.filepath):
        raise HTTPException(status_code=403, detail="文件路径不安全")
    
    # 读取数据
    try:
        df = await run_in_executor(
            _read_csv_sync,
            dataset.filepath,
            dataset.encoding or "utf-8"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取数据集文件失败: {str(e)}")
    
    if column not in df.columns:
        raise HTTPException(status_code=400, detail=f"列 '{column}' 不存在")
    
    # 构建参数
    params = {}
    if method == "iqr":
        params["multiplier"] = multiplier
    elif method in ["zscore", "mad"]:
        params["threshold"] = threshold
    elif method == "percentile":
        params["lower"] = lower_pct
        params["upper"] = upper_pct
    
    # 分析异常值
    from app.services.quality import QualityAnalyzer
    analyzer = QualityAnalyzer(df, dataset.id, dataset.name)
    
    try:
        outlier_stats, _, _ = await run_in_executor(
            analyzer.detect_outliers,
            method,
            params,
            [column]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"异常值检测失败: {str(e)}")
    
    if not outlier_stats:
        raise HTTPException(status_code=400, detail=f"列 '{column}' 不是数值列")
    
    stat = outlier_stats[0]
    
    # 获取异常值的具体数据
    series = pd.to_numeric(df[column], errors='coerce')
    outlier_data = []
    
    for idx in stat.outlier_indices[:100]:  # 最多返回100个
        if idx < len(df):
            outlier_data.append({
                "index": idx,
                "value": float(series.iloc[idx]) if pd.notna(series.iloc[idx]) else None
            })
    
    return {
        "column": column,
        "method": method,
        "params": params,
        "lower_bound": stat.lower_bound,
        "upper_bound": stat.upper_bound,
        "outlier_count": stat.outlier_count,
        "outlier_ratio": stat.outlier_ratio,
        "outliers": outlier_data,
        "stats": {
            "min": stat.min_value,
            "max": stat.max_value,
            "mean": stat.mean_value,
            "std": stat.std_value
        }
    }

