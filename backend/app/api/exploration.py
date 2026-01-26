"""
数据探索 API 路由
提供数据分布、相关性分析、直方图等可视化数据
"""

import os

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.models import Dataset, User
from app.services.executor import run_in_executor
from app.services.permissions import ResourceType, check_read_access
from app.services.security import validate_filepath

router = APIRouter(prefix="/api/exploration", tags=["exploration"])


def _read_csv_sync(filepath: str, encoding: str = "utf-8") -> pd.DataFrame:
    """同步读取 CSV 文件"""
    return pd.read_csv(filepath, encoding=encoding)


def _safe_float(val) -> float | None:
    """安全转换为 JSON 兼容的浮点数，NaN/Inf 转为 None"""
    if val is None:
        return None
    if pd.isna(val) or np.isinf(val):
        return None
    return float(val)


# ============ 数据分布分析 ============


@router.get("/{dataset_id}/distribution/{column}")
async def get_column_distribution(
    dataset_id: int,
    column: str,
    bins: int = Query(default=30, ge=5, le=100, description="直方图分箱数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取单列的分布数据（直方图 + 统计信息）

    Returns:
        - histogram: 直方图数据
        - stats: 统计信息
        - boxplot: 箱线图数据
    """
    dataset = await _get_dataset_with_access(dataset_id, db, current_user)
    df = await _load_dataset(dataset)

    # 空数据集检查
    if len(df) == 0:
        return {"type": "empty", "column": column, "total_count": 0, "message": "数据集为空"}

    if column not in df.columns:
        raise HTTPException(status_code=400, detail=f"列 '{column}' 不存在")

    series = df[column]

    # 尝试转换为数值
    numeric_series = pd.to_numeric(series, errors="coerce")
    valid_data = numeric_series.dropna()

    if len(valid_data) == 0:
        # 非数值列，返回值频率统计
        value_counts = series.value_counts().head(50)
        total = len(series)
        return {
            "type": "categorical",
            "column": column,
            "total_count": total,
            "unique_count": series.nunique(),
            "missing_count": int(series.isna().sum()),
            "value_counts": [
                {"value": str(k), "count": int(v), "ratio": float(v / total) if total > 0 else 0}
                for k, v in value_counts.items()
            ],
        }

    # 数值列
    result = await run_in_executor(_compute_numeric_distribution, valid_data.values, column, bins)
    result["total_count"] = len(series)
    result["missing_count"] = int(series.isna().sum())

    return result


def _compute_numeric_distribution(data: np.ndarray, column: str, bins: int) -> dict:
    """计算数值列分布"""
    # 直方图
    hist_counts, bin_edges = np.histogram(data, bins=bins)
    histogram = [
        {
            "bin_start": float(bin_edges[i]),
            "bin_end": float(bin_edges[i + 1]),
            "count": int(hist_counts[i]),
            "ratio": float(hist_counts[i] / len(data)),
        }
        for i in range(len(hist_counts))
    ]

    # 统计信息
    stats = {
        "min": float(np.min(data)),
        "max": float(np.max(data)),
        "mean": float(np.mean(data)),
        "std": float(np.std(data)),
        "median": float(np.median(data)),
        "q1": float(np.percentile(data, 25)),
        "q3": float(np.percentile(data, 75)),
        "skewness": float(_safe_skewness(data)),
        "kurtosis": float(_safe_kurtosis(data)),
    }

    # 箱线图数据
    q1, q3 = stats["q1"], stats["q3"]
    iqr = q3 - q1
    whisker_low = max(stats["min"], q1 - 1.5 * iqr)
    whisker_high = min(stats["max"], q3 + 1.5 * iqr)

    # 找出异常点
    outliers = data[(data < whisker_low) | (data > whisker_high)]
    outlier_values = outliers.tolist()[:100]  # 最多100个

    boxplot = {
        "min": whisker_low,
        "q1": q1,
        "median": stats["median"],
        "q3": q3,
        "max": whisker_high,
        "outliers": outlier_values,
    }

    return {
        "type": "numeric",
        "column": column,
        "valid_count": len(data),
        "histogram": histogram,
        "stats": stats,
        "boxplot": boxplot,
    }


def _safe_skewness(data: np.ndarray) -> float:
    """安全计算偏度"""
    try:
        n = len(data)
        if n < 3:
            return 0.0
        mean = np.mean(data)
        std = np.std(data)
        if std < 1e-10:
            return 0.0
        return float(np.mean(((data - mean) / std) ** 3))
    except Exception:
        return 0.0


def _safe_kurtosis(data: np.ndarray) -> float:
    """安全计算峰度"""
    try:
        n = len(data)
        if n < 4:
            return 0.0
        mean = np.mean(data)
        std = np.std(data)
        if std < 1e-10:
            return 0.0
        return float(np.mean(((data - mean) / std) ** 4) - 3)
    except Exception:
        return 0.0


# ============ 相关性分析 ============


@router.get("/{dataset_id}/correlation")
async def get_correlation_matrix(
    dataset_id: int,
    columns: str | None = Query(default=None, description="逗号分隔的列名，为空则使用所有数值列"),
    method: str = Query(default="pearson", regex="^(pearson|spearman|kendall)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取相关性矩阵

    Args:
        columns: 要分析的列（逗号分隔），为空则使用所有数值列
        method: 相关性计算方法 (pearson/spearman/kendall)

    Returns:
        - columns: 列名列表
        - matrix: 相关性矩阵
        - strong_correlations: 强相关对
    """
    dataset = await _get_dataset_with_access(dataset_id, db, current_user)
    df = await _load_dataset(dataset)

    # 确定要分析的列
    if columns:
        target_columns = [c.strip() for c in columns.split(",") if c.strip()]
        # 验证列存在
        missing = [c for c in target_columns if c not in df.columns]
        if missing:
            raise HTTPException(status_code=400, detail=f"列不存在: {missing}")
    else:
        # 使用所有数值列
        target_columns = df.select_dtypes(include=[np.number]).columns.tolist()

    if len(target_columns) < 2:
        raise HTTPException(status_code=400, detail="至少需要2个数值列进行相关性分析")

    # 限制列数（避免矩阵过大）
    if len(target_columns) > 50:
        target_columns = target_columns[:50]

    result = await run_in_executor(_compute_correlation, df[target_columns], method)

    return result


def _compute_correlation(df: pd.DataFrame, method: str) -> dict:
    """计算相关性矩阵"""
    # 计算相关性
    corr_matrix = df.corr(method=method, numeric_only=True)

    # 转换为列表格式
    columns = corr_matrix.columns.tolist()
    matrix = []
    for i, _row_name in enumerate(columns):
        row = []
        for j, _col_name in enumerate(columns):
            val = corr_matrix.iloc[i, j]
            row.append(float(val) if pd.notna(val) else None)
        matrix.append(row)

    # 找出强相关对（|r| > 0.7，排除自相关）
    strong_correlations = []
    for i in range(len(columns)):
        for j in range(i + 1, len(columns)):
            val = corr_matrix.iloc[i, j]
            if pd.notna(val) and abs(val) > 0.7:
                strong_correlations.append(
                    {
                        "column1": columns[i],
                        "column2": columns[j],
                        "correlation": float(val),
                        "strength": "strong" if abs(val) > 0.9 else "moderate",
                    }
                )

    # 按相关性绝对值排序
    strong_correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)

    return {
        "columns": columns,
        "matrix": matrix,
        "method": method,
        "strong_correlations": strong_correlations[:20],  # 最多返回20对
    }


# ============ 时序趋势分析 ============


@router.get("/{dataset_id}/trend/{column}")
async def get_trend_analysis(
    dataset_id: int,
    column: str,
    time_column: str | None = Query(default=None, description="时间列名"),
    window: int = Query(default=10, ge=2, le=1000, description="移动平均窗口"),
    max_points: int = Query(default=2000, ge=100, le=10000, description="最大返回点数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取时序趋势分析数据

    Returns:
        - raw_data: 原始数据（降采样后）
        - moving_avg: 移动平均
        - trend: 趋势线
        - stats: 统计信息
    """
    dataset = await _get_dataset_with_access(dataset_id, db, current_user)
    df = await _load_dataset(dataset)

    if column not in df.columns:
        raise HTTPException(status_code=400, detail=f"列 '{column}' 不存在")

    # 转换为数值
    series = pd.to_numeric(df[column], errors="coerce")
    valid_mask = series.notna()

    if valid_mask.sum() < 10:
        raise HTTPException(status_code=400, detail=f"列 '{column}' 有效数值不足")

    # 确定 x 轴
    if time_column and time_column in df.columns:
        try:
            x_values = pd.to_datetime(df[time_column])
            x_values = (x_values - x_values.min()).dt.total_seconds().values
        except Exception:
            x_values = np.arange(len(df))
    else:
        x_values = np.arange(len(df))

    result = await run_in_executor(_compute_trend, x_values[valid_mask], series[valid_mask].values, window, max_points)

    return result


def _compute_trend(x: np.ndarray, y: np.ndarray, window: int, max_points: int) -> dict:
    """计算趋势数据"""
    n = len(y)

    # 降采样
    if n > max_points:
        step = n // max_points
        indices = np.arange(0, n, step)[:max_points]
        x_sampled = x[indices]
        y_sampled = y[indices]
    else:
        indices = np.arange(n)
        x_sampled = x
        y_sampled = y

    # 移动平均
    if len(y_sampled) >= window:
        ma = np.convolve(y_sampled, np.ones(window) / window, mode="valid")
        # 补齐前面的 NaN
        ma_padded = np.concatenate([np.full(window - 1, np.nan), ma])
    else:
        ma_padded = np.full(len(y_sampled), np.nan)

    # 线性趋势
    try:
        z = np.polyfit(x_sampled, y_sampled, 1)
        trend_line = np.polyval(z, x_sampled)
        slope = float(z[0])
        trend_direction = "increasing" if slope > 0.001 else ("decreasing" if slope < -0.001 else "stable")
    except Exception:
        trend_line = np.full(len(y_sampled), np.mean(y_sampled))
        slope = 0.0
        trend_direction = "stable"

    # 统计
    stats = {
        "min": float(np.min(y)),
        "max": float(np.max(y)),
        "mean": float(np.mean(y)),
        "std": float(np.std(y)),
        "trend_slope": slope,
        "trend_direction": trend_direction,
        "total_points": n,
        "sampled_points": len(y_sampled),
    }

    return {
        "raw_data": [[float(x_sampled[i]), float(y_sampled[i])] for i in range(len(y_sampled))],
        "moving_avg": [
            [float(x_sampled[i]), float(ma_padded[i])] for i in range(len(y_sampled)) if not np.isnan(ma_padded[i])
        ],
        "trend_line": [[float(x_sampled[i]), float(trend_line[i])] for i in range(len(y_sampled))],
        "stats": stats,
    }


# ============ 多列对比 ============


@router.get("/{dataset_id}/compare")
async def compare_columns(
    dataset_id: int,
    columns: str = Query(..., description="逗号分隔的列名（2-5列）"),
    normalize: bool = Query(default=True, description="是否归一化以便对比"),
    max_points: int = Query(default=2000, ge=100, le=10000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    多列数据对比

    Returns:
        - series: 各列数据
        - stats: 各列统计
        - correlation: 列间相关性
    """
    dataset = await _get_dataset_with_access(dataset_id, db, current_user)
    df = await _load_dataset(dataset)

    target_columns = [c.strip() for c in columns.split(",") if c.strip()]

    if len(target_columns) < 2:
        raise HTTPException(status_code=400, detail="至少需要2列进行对比")
    if len(target_columns) > 5:
        raise HTTPException(status_code=400, detail="最多支持5列对比")

    missing = [c for c in target_columns if c not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"列不存在: {missing}")

    result = await run_in_executor(_compute_comparison, df, target_columns, normalize, max_points)

    return result


def _compute_comparison(df: pd.DataFrame, columns: list[str], normalize: bool, max_points: int) -> dict:
    """计算多列对比数据"""
    n = len(df)

    # 空数据集检查
    if n == 0:
        return {
            "series": [],
            "stats": [],
            "correlation": {"columns": columns, "matrix": []},
            "normalized": normalize,
            "total_points": 0,
            "sampled_points": 0,
        }

    # 降采样
    if n > max_points:
        step = n // max_points
        indices = list(range(0, n, step))[:max_points]
    else:
        indices = list(range(n))

    series_data = []
    stats_data = []

    for col in columns:
        values = pd.to_numeric(df[col], errors="coerce").values
        valid_values = values[~np.isnan(values)]

        if len(valid_values) == 0:
            continue

        # 归一化
        if normalize and len(valid_values) > 0:
            vmin, vmax = np.min(valid_values), np.max(valid_values)
            if vmax - vmin > 1e-10:
                normalized = (values - vmin) / (vmax - vmin)
            else:
                normalized = np.zeros_like(values)
        else:
            normalized = values

        # 采样数据
        sampled = [[i, _safe_float(normalized[idx])] for i, idx in enumerate(indices)]

        series_data.append({"name": col, "data": sampled})

        stats_data.append(
            {
                "column": col,
                "min": _safe_float(np.nanmin(values)),
                "max": _safe_float(np.nanmax(values)),
                "mean": _safe_float(np.nanmean(values)),
                "std": _safe_float(np.nanstd(values)),
                "valid_count": int(np.sum(~np.isnan(values))),
            }
        )

    # 计算相关性 - 安全处理 NaN
    corr_df = df[columns].apply(pd.to_numeric, errors="coerce")
    corr_matrix_raw = corr_df.corr()

    # 逐元素转换，NaN -> None
    corr_matrix = []
    for i in range(len(columns)):
        row = []
        for j in range(len(columns)):
            val = corr_matrix_raw.iloc[i, j] if i < len(corr_matrix_raw) and j < len(corr_matrix_raw.columns) else None
            row.append(_safe_float(val))
        corr_matrix.append(row)

    return {
        "series": series_data,
        "stats": stats_data,
        "correlation": {"columns": columns, "matrix": corr_matrix},
        "normalized": normalize,
        "total_points": n,
        "sampled_points": len(indices),
    }


# ============ 数据概览 ============


@router.get("/{dataset_id}/overview")
async def get_data_overview(
    dataset_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    获取数据集概览信息

    Returns:
        - basic_info: 基础信息
        - column_summary: 列摘要
        - numeric_summary: 数值列统计摘要
        - memory_usage: 内存使用
    """
    dataset = await _get_dataset_with_access(dataset_id, db, current_user)
    df = await _load_dataset(dataset)

    result = await run_in_executor(_compute_overview, df, dataset.name)

    return result


def _compute_overview(df: pd.DataFrame, dataset_name: str) -> dict:
    """计算数据概览"""
    n_rows = len(df)

    # 基础信息
    basic_info = {
        "name": dataset_name,
        "rows": n_rows,
        "columns": len(df.columns),
        "memory_mb": float(df.memory_usage(deep=True).sum() / 1024 / 1024),
    }

    # 空数据集检查
    if n_rows == 0:
        return {
            "basic_info": basic_info,
            "column_summary": [
                {
                    "name": col,
                    "dtype": str(df[col].dtype),
                    "inferred_type": "unknown",
                    "missing": 0,
                    "missing_ratio": 0,
                    "unique": 0,
                }
                for col in df.columns
            ],
            "numeric_summary": {},
            "numeric_columns": [],
            "categorical_columns": [],
        }

    # 列摘要
    column_summary = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        missing = int(df[col].isna().sum())
        unique = int(df[col].nunique())

        # 推断类型（安全除法）
        unique_ratio = unique / n_rows if n_rows > 0 else 0

        if pd.api.types.is_numeric_dtype(df[col]):
            inferred = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            inferred = "datetime"
        elif pd.api.types.is_bool_dtype(df[col]):
            inferred = "boolean"
        elif unique_ratio < 0.05 and unique < 100:
            inferred = "categorical"
        else:
            inferred = "text"

        column_summary.append(
            {
                "name": col,
                "dtype": dtype,
                "inferred_type": inferred,
                "missing": missing,
                "missing_ratio": float(missing / n_rows) if n_rows > 0 else 0,
                "unique": unique,
            }
        )

    # 数值列统计
    numeric_df = df.select_dtypes(include=[np.number])
    numeric_summary = {}
    if len(numeric_df.columns) > 0 and n_rows > 0:
        desc = numeric_df.describe()
        for col in desc.columns:
            numeric_summary[col] = {
                "count": int(desc.loc["count", col]),
                "mean": _safe_float(desc.loc["mean", col]),
                "std": _safe_float(desc.loc["std", col]),
                "min": _safe_float(desc.loc["min", col]),
                "q1": _safe_float(desc.loc["25%", col]),
                "median": _safe_float(desc.loc["50%", col]),
                "q3": _safe_float(desc.loc["75%", col]),
                "max": _safe_float(desc.loc["max", col]),
            }

    return {
        "basic_info": basic_info,
        "column_summary": column_summary,
        "numeric_summary": numeric_summary,
        "numeric_columns": numeric_df.columns.tolist(),
        "categorical_columns": [c["name"] for c in column_summary if c["inferred_type"] == "categorical"],
    }


# ============ 辅助函数 ============


async def _get_dataset_with_access(dataset_id: int, db: AsyncSession, current_user: User) -> Dataset:
    """获取数据集并检查权限"""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()

    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")

    check_read_access(dataset, current_user, ResourceType.DATASET)

    if not os.path.exists(dataset.filepath):
        raise HTTPException(status_code=404, detail="数据集文件不存在")

    if not validate_filepath(dataset.filepath):
        raise HTTPException(status_code=403, detail="文件路径不安全")

    return dataset


async def _load_dataset(dataset: Dataset) -> pd.DataFrame:
    """加载数据集"""
    try:
        df = await run_in_executor(_read_csv_sync, dataset.filepath, dataset.encoding or "utf-8")
        return df
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取数据集失败: {str(e)}") from e
