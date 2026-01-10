"""
高级可视化 API

提供特征重要性分析、预测置信区间、模型注意力可视化等功能
"""
import os
import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import User, Result, Dataset
from app.api.auth import get_current_user
from app.services.permissions import can_access_result
from app.services.executor import run_in_executor
from app.services.security import validate_filepath

router = APIRouter(prefix="/api/advanced-viz", tags=["advanced-visualization"])


# ============ 请求/响应模型 ============

class FeatureImportanceRequest(BaseModel):
    """特征重要性分析请求"""
    result_id: int = Field(..., description="结果 ID")
    method: str = Field(default="correlation", description="分析方法: correlation, variance, gradient")
    top_k: int = Field(default=10, ge=1, le=50, description="返回前 K 个重要特征")


class FeatureImportance(BaseModel):
    """单个特征的重要性"""
    feature_name: str
    importance: float
    rank: int


class FeatureImportanceResponse(BaseModel):
    """特征重要性响应"""
    result_id: int
    result_name: str
    method: str
    features: List[FeatureImportance]
    total_features: int


class ConfidenceIntervalRequest(BaseModel):
    """置信区间请求"""
    result_id: int = Field(..., description="结果 ID")
    confidence_level: float = Field(default=0.95, ge=0.5, le=0.99, description="置信水平")
    window_size: int = Field(default=50, ge=10, le=500, description="滑动窗口大小")
    max_points: int = Field(default=2000, ge=100, le=10000, description="最大返回点数")


class ConfidenceIntervalPoint(BaseModel):
    """置信区间数据点"""
    index: int
    predicted: float
    lower_bound: float
    upper_bound: float
    true_value: Optional[float] = None


class ConfidenceIntervalResponse(BaseModel):
    """置信区间响应"""
    result_id: int
    result_name: str
    confidence_level: float
    data: List[ConfidenceIntervalPoint]
    coverage_rate: float  # 真实值落在置信区间内的比例
    avg_interval_width: float  # 平均区间宽度
    total_points: int
    downsampled: bool


class ErrorHeatmapRequest(BaseModel):
    """误差热力图请求"""
    result_ids: List[int] = Field(..., min_length=1, max_length=20, description="结果 ID 列表")
    bins: int = Field(default=20, ge=5, le=100, description="分箱数量")


class HeatmapCell(BaseModel):
    """热力图单元格"""
    x_bin: int  # 时间区间
    y_bin: int  # 误差区间
    count: int
    percentage: float


class ErrorHeatmapData(BaseModel):
    """单个结果的热力图数据"""
    result_id: int
    result_name: str
    model_name: str
    cells: List[HeatmapCell]
    x_labels: List[str]  # 时间区间标签
    y_labels: List[str]  # 误差区间标签
    error_range: List[float]  # [min, max]


class ErrorHeatmapResponse(BaseModel):
    """误差热力图响应"""
    heatmaps: List[ErrorHeatmapData]
    unified_error_range: List[float]  # 统一的误差范围


class PredictionDecompositionRequest(BaseModel):
    """预测分解请求"""
    result_id: int = Field(..., description="结果 ID")
    decomposition_type: str = Field(default="trend_seasonal", description="分解类型: trend_seasonal, residual")
    period: Optional[int] = Field(default=None, description="季节性周期（自动检测如果为空）")


class DecompositionComponent(BaseModel):
    """分解组件"""
    name: str
    values: List[float]
    indices: List[int]


class PredictionDecompositionResponse(BaseModel):
    """预测分解响应"""
    result_id: int
    result_name: str
    components: List[DecompositionComponent]
    detected_period: Optional[int]


# ============ 辅助函数 ============

def _read_csv_sync(filepath: str, columns: Optional[List[str]] = None):
    """同步读取 CSV"""
    if columns:
        return pd.read_csv(filepath, usecols=columns)
    return pd.read_csv(filepath)


def _calculate_correlation_importance(df: pd.DataFrame, target_col: str = "predicted_value") -> Dict[str, float]:
    """基于相关性计算特征重要性"""
    importance = {}
    target = df[target_col]
    
    for col in df.columns:
        if col in ["true_value", "predicted_value", "index", "timestamp", "date"]:
            continue
        try:
            # 计算与预测值的相关系数
            corr = df[col].corr(target)
            if pd.notna(corr):
                importance[col] = abs(corr)
        except Exception:
            continue
    
    return importance


def _calculate_variance_importance(df: pd.DataFrame) -> Dict[str, float]:
    """基于方差计算特征重要性"""
    importance = {}
    
    for col in df.columns:
        if col in ["true_value", "predicted_value", "index", "timestamp", "date"]:
            continue
        try:
            var = df[col].var()
            if pd.notna(var) and var > 0:
                importance[col] = var
        except Exception:
            continue
    
    # 归一化
    if importance:
        max_var = max(importance.values())
        importance = {k: v / max_var for k, v in importance.items()}
    
    return importance


def _calculate_gradient_importance(df: pd.DataFrame, target_col: str = "predicted_value") -> Dict[str, float]:
    """基于梯度（变化率）计算特征重要性"""
    importance = {}
    target_diff = df[target_col].diff().abs()
    
    for col in df.columns:
        if col in ["true_value", "predicted_value", "index", "timestamp", "date"]:
            continue
        try:
            col_diff = df[col].diff().abs()
            # 计算特征变化与目标变化的相关性
            corr = col_diff.corr(target_diff)
            if pd.notna(corr):
                importance[col] = abs(corr)
        except Exception:
            continue
    
    return importance


def _norm_ppf(p: float) -> float:
    """
    标准正态分布的分位点函数（逆 CDF）
    使用 Python 3.8+ 标准库 statistics.NormalDist
    """
    from statistics import NormalDist
    return NormalDist().inv_cdf(p)


def _calculate_rolling_confidence_interval(
    residuals: np.ndarray,
    predictions: np.ndarray,
    window_size: int,
    confidence_level: float
) -> tuple:
    """计算滑动窗口置信区间（不依赖 SciPy）"""
    n = len(residuals)
    lower_bounds = np.zeros(n)
    upper_bounds = np.zeros(n)
    
    # 计算 z 值（使用标准库）
    z = _norm_ppf((1 + confidence_level) / 2)
    
    # 使用 pandas 滑动窗口计算标准差（更高效）
    residuals_series = pd.Series(residuals)
    rolling_std = residuals_series.rolling(
        window=window_size, center=True, min_periods=1
    ).std().fillna(residuals_series.std()).values
    
    lower_bounds = predictions - z * rolling_std
    upper_bounds = predictions + z * rolling_std
    
    return lower_bounds, upper_bounds


def _find_peaks_simple(arr: np.ndarray, height: float = 0.3, distance: int = 10) -> List[int]:
    """
    简单的峰值检测（不依赖 SciPy）
    
    Args:
        arr: 输入数组
        height: 最小峰值高度
        distance: 峰值之间的最小距离
    
    Returns:
        峰值索引列表
    """
    peaks = []
    n = len(arr)
    
    for i in range(1, n - 1):
        # 检查是否是局部最大值
        if arr[i] > arr[i - 1] and arr[i] > arr[i + 1]:
            # 检查高度阈值
            if arr[i] >= height:
                # 检查与上一个峰值的距离
                if not peaks or (i - peaks[-1]) >= distance:
                    peaks.append(i)
    
    return peaks


def _autocorr_fft(x: np.ndarray, max_lag: int = None) -> np.ndarray:
    """
    使用 FFT 计算自相关（O(n log n) 而非 O(n²)）
    
    Args:
        x: 输入序列
        max_lag: 最大滞后（默认为序列长度的一半）
    
    Returns:
        归一化的自相关数组
    """
    n = len(x)
    if max_lag is None:
        max_lag = n // 2
    
    # 去均值
    x = x - np.mean(x)
    
    # 使用 FFT 计算自相关
    # 补零到 2n 以避免循环卷积
    fft_size = 2 ** int(np.ceil(np.log2(2 * n - 1)))
    fft_x = np.fft.fft(x, fft_size)
    autocorr = np.fft.ifft(fft_x * np.conj(fft_x)).real
    
    # 取前 max_lag 个值并归一化
    autocorr = autocorr[:max_lag]
    if autocorr[0] != 0:
        autocorr = autocorr / autocorr[0]
    
    return autocorr


def _downsample_uniform(data: List[Any], max_points: int) -> List[Any]:
    """均匀降采样"""
    if len(data) <= max_points:
        return data
    
    step = len(data) / max_points
    indices = [int(i * step) for i in range(max_points)]
    return [data[i] for i in indices]


# ============ API 端点 ============

@router.post("/feature-importance", response_model=FeatureImportanceResponse)
async def analyze_feature_importance(
    request: FeatureImportanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    特征重要性分析
    
    分析预测结果中各特征对预测值的影响程度
    支持多种分析方法：相关性、方差、梯度
    """
    # 获取结果
    result = await db.execute(
        select(Result).where(Result.id == request.result_id)
    )
    result_obj = result.scalar_one_or_none()
    
    if not result_obj:
        raise HTTPException(status_code=404, detail="结果不存在")
    
    # 获取数据集检查权限
    dataset = None
    if result_obj.dataset_id:
        ds_result = await db.execute(
            select(Dataset).where(Dataset.id == result_obj.dataset_id)
        )
        dataset = ds_result.scalar_one_or_none()
    
    if not can_access_result(result_obj, dataset, current_user):
        raise HTTPException(status_code=403, detail="无权访问此结果")
    
    if not os.path.exists(result_obj.filepath):
        raise HTTPException(status_code=404, detail="结果文件不存在")
    
    if not validate_filepath(result_obj.filepath):
        raise HTTPException(status_code=403, detail="文件路径不安全")
    
    # 读取数据
    try:
        df = await run_in_executor(_read_csv_sync, result_obj.filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")
    
    # 计算特征重要性
    if request.method == "correlation":
        importance = _calculate_correlation_importance(df)
    elif request.method == "variance":
        importance = _calculate_variance_importance(df)
    elif request.method == "gradient":
        importance = _calculate_gradient_importance(df)
    else:
        raise HTTPException(status_code=400, detail=f"不支持的分析方法: {request.method}")
    
    if not importance:
        raise HTTPException(status_code=400, detail="无法计算特征重要性，可能缺少特征列")
    
    # 排序并取 top_k
    sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    top_features = sorted_features[:request.top_k]
    
    features = [
        FeatureImportance(
            feature_name=name,
            importance=round(imp, 6),
            rank=i + 1
        )
        for i, (name, imp) in enumerate(top_features)
    ]
    
    return FeatureImportanceResponse(
        result_id=result_obj.id,
        result_name=result_obj.name,
        method=request.method,
        features=features,
        total_features=len(importance)
    )


@router.post("/confidence-interval", response_model=ConfidenceIntervalResponse)
async def calculate_confidence_interval(
    request: ConfidenceIntervalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    预测置信区间计算
    
    基于残差的滑动窗口标准差计算置信区间
    """
    # 获取结果
    result = await db.execute(
        select(Result).where(Result.id == request.result_id)
    )
    result_obj = result.scalar_one_or_none()
    
    if not result_obj:
        raise HTTPException(status_code=404, detail="结果不存在")
    
    # 权限检查
    dataset = None
    if result_obj.dataset_id:
        ds_result = await db.execute(
            select(Dataset).where(Dataset.id == result_obj.dataset_id)
        )
        dataset = ds_result.scalar_one_or_none()
    
    if not can_access_result(result_obj, dataset, current_user):
        raise HTTPException(status_code=403, detail="无权访问此结果")
    
    if not os.path.exists(result_obj.filepath):
        raise HTTPException(status_code=404, detail="结果文件不存在")
    
    if not validate_filepath(result_obj.filepath):
        raise HTTPException(status_code=403, detail="文件路径不安全")
    
    # 读取数据
    try:
        df = await run_in_executor(
            _read_csv_sync,
            result_obj.filepath,
            ["true_value", "predicted_value"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")
    
    true_vals = pd.to_numeric(df["true_value"], errors='coerce').values
    pred_vals = pd.to_numeric(df["predicted_value"], errors='coerce').values
    
    # 过滤无效值
    valid_mask = ~(np.isnan(true_vals) | np.isnan(pred_vals))
    true_vals = true_vals[valid_mask]
    pred_vals = pred_vals[valid_mask]
    indices = np.where(valid_mask)[0]
    
    if len(true_vals) < request.window_size:
        raise HTTPException(status_code=400, detail="数据点数量不足以计算置信区间")
    
    # 计算残差
    residuals = pred_vals - true_vals
    
    # 计算置信区间
    lower_bounds, upper_bounds = _calculate_rolling_confidence_interval(
        residuals, pred_vals, request.window_size, request.confidence_level
    )
    
    # 计算覆盖率
    in_interval = (true_vals >= lower_bounds) & (true_vals <= upper_bounds)
    coverage_rate = np.mean(in_interval)
    
    # 计算平均区间宽度
    avg_width = np.mean(upper_bounds - lower_bounds)
    
    # 构建数据点
    total_points = len(true_vals)
    downsampled = total_points > request.max_points
    
    if downsampled:
        step = total_points / request.max_points
        sample_indices = [int(i * step) for i in range(request.max_points)]
    else:
        sample_indices = list(range(total_points))
    
    data = [
        ConfidenceIntervalPoint(
            index=int(indices[i]),
            predicted=float(pred_vals[i]),
            lower_bound=float(lower_bounds[i]),
            upper_bound=float(upper_bounds[i]),
            true_value=float(true_vals[i])
        )
        for i in sample_indices
    ]
    
    return ConfidenceIntervalResponse(
        result_id=result_obj.id,
        result_name=result_obj.name,
        confidence_level=request.confidence_level,
        data=data,
        coverage_rate=round(coverage_rate, 4),
        avg_interval_width=round(avg_width, 6),
        total_points=total_points,
        downsampled=downsampled
    )


@router.post("/error-heatmap", response_model=ErrorHeatmapResponse)
async def generate_error_heatmap(
    request: ErrorHeatmapRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    误差热力图
    
    展示误差在时间和误差大小两个维度上的分布
    """
    # 查询结果
    result = await db.execute(
        select(Result).where(Result.id.in_(request.result_ids))
    )
    results = result.scalars().all()
    
    if not results:
        raise HTTPException(status_code=404, detail="未找到任何结果")
    
    # 预加载数据集
    dataset_ids = {r.dataset_id for r in results}
    datasets_result = await db.execute(
        select(Dataset).where(Dataset.id.in_(dataset_ids))
    )
    datasets_map = {d.id: d for d in datasets_result.scalars().all()}
    
    # 收集所有误差用于统一范围
    all_errors = []
    valid_results = []
    
    for res in results:
        dataset = datasets_map.get(res.dataset_id)
        if not can_access_result(res, dataset, current_user):
            continue
        
        if not os.path.exists(res.filepath) or not validate_filepath(res.filepath):
            continue
        
        try:
            df = await run_in_executor(
                _read_csv_sync,
                res.filepath,
                ["true_value", "predicted_value"]
            )
            
            true_vals = pd.to_numeric(df["true_value"], errors='coerce').values
            pred_vals = pd.to_numeric(df["predicted_value"], errors='coerce').values
            
            valid_mask = ~(np.isnan(true_vals) | np.isnan(pred_vals))
            errors = (pred_vals - true_vals)[valid_mask]
            
            all_errors.extend(errors.tolist())
            valid_results.append({
                "result": res,
                "errors": errors,
                "length": len(errors)
            })
        except Exception:
            continue
    
    if not valid_results:
        raise HTTPException(status_code=400, detail="没有有效的结果数据")
    
    # 计算统一的误差范围
    all_errors = np.array(all_errors)
    error_min = float(np.percentile(all_errors, 1))  # 使用 1% 和 99% 分位数避免极端值
    error_max = float(np.percentile(all_errors, 99))
    error_bins = np.linspace(error_min, error_max, request.bins + 1)
    
    # 生成热力图数据
    heatmaps = []
    
    for item in valid_results:
        res = item["result"]
        errors = item["errors"]
        length = item["length"]
        
        # 使用 np.histogram2d 一次性计算 2D 直方图（高效）
        time_values = np.arange(length)
        time_bins = np.linspace(0, length, request.bins + 1)
        
        # histogram2d 返回 (counts, x_edges, y_edges)
        hist, _, _ = np.histogram2d(
            time_values, errors,
            bins=[time_bins, error_bins]
        )
        
        # 构建 cells 列表
        cells = []
        total = len(errors)
        
        for x in range(request.bins):
            for y in range(request.bins):
                count = int(hist[x, y])
                if count > 0:
                    cells.append(HeatmapCell(
                        x_bin=x,
                        y_bin=y,
                        count=count,
                        percentage=round(count / total * 100, 2)
                    ))
        
        # 生成标签
        x_labels = [f"{int(time_bins[i])}-{int(time_bins[i+1])}" for i in range(request.bins)]
        y_labels = [f"{error_bins[i]:.3f}" for i in range(request.bins)]
        
        heatmaps.append(ErrorHeatmapData(
            result_id=res.id,
            result_name=res.name,
            model_name=res.algo_name,
            cells=cells,
            x_labels=x_labels,
            y_labels=y_labels,
            error_range=[float(errors.min()), float(errors.max())]
        ))
    
    return ErrorHeatmapResponse(
        heatmaps=heatmaps,
        unified_error_range=[error_min, error_max]
    )


@router.post("/prediction-decomposition", response_model=PredictionDecompositionResponse)
async def decompose_prediction(
    request: PredictionDecompositionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    预测分解
    
    将预测结果分解为趋势、季节性和残差组件
    """
    # 获取结果
    result = await db.execute(
        select(Result).where(Result.id == request.result_id)
    )
    result_obj = result.scalar_one_or_none()
    
    if not result_obj:
        raise HTTPException(status_code=404, detail="结果不存在")
    
    # 权限检查
    dataset = None
    if result_obj.dataset_id:
        ds_result = await db.execute(
            select(Dataset).where(Dataset.id == result_obj.dataset_id)
        )
        dataset = ds_result.scalar_one_or_none()
    
    if not can_access_result(result_obj, dataset, current_user):
        raise HTTPException(status_code=403, detail="无权访问此结果")
    
    if not os.path.exists(result_obj.filepath):
        raise HTTPException(status_code=404, detail="结果文件不存在")
    
    if not validate_filepath(result_obj.filepath):
        raise HTTPException(status_code=403, detail="文件路径不安全")
    
    # 读取数据
    try:
        df = await run_in_executor(
            _read_csv_sync,
            result_obj.filepath,
            ["true_value", "predicted_value"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")
    
    pred_vals = pd.to_numeric(df["predicted_value"], errors='coerce').values
    true_vals = pd.to_numeric(df["true_value"], errors='coerce').values
    
    # 过滤无效值
    valid_mask = ~np.isnan(pred_vals)
    pred_vals = pred_vals[valid_mask]
    true_vals = true_vals[valid_mask]
    indices = np.where(valid_mask)[0].tolist()
    
    if len(pred_vals) < 100:
        raise HTTPException(status_code=400, detail="数据点数量不足以进行分解")
    
    components = []
    detected_period = request.period
    
    # 趋势提取（使用移动平均）
    window = min(50, len(pred_vals) // 10)
    if window < 3:
        window = 3
    trend = pd.Series(pred_vals).rolling(window=window, center=True).mean().bfill().ffill().values
    
    components.append(DecompositionComponent(
        name="trend",
        values=_downsample_uniform(trend.tolist(), 2000),
        indices=_downsample_uniform(indices, 2000)
    ))
    
    # 去趋势
    detrended = pred_vals - trend
    
    # 自动检测周期（如果未指定）
    if detected_period is None:
        try:
            # 使用 FFT 自相关检测周期（限制最大 lag 避免性能问题）
            max_lag = min(len(detrended) // 2, 1000)
            autocorr = _autocorr_fft(detrended, max_lag=max_lag)
            
            # 找第一个显著峰值（使用简单峰值检测）
            peaks = _find_peaks_simple(autocorr, height=0.3, distance=10)
            if len(peaks) > 0:
                detected_period = int(peaks[0])
        except Exception:
            detected_period = None
    
    # 季节性提取
    if detected_period and detected_period > 1:
        seasonal = np.zeros_like(detrended)
        for i in range(detected_period):
            mask = np.arange(len(detrended)) % detected_period == i
            seasonal[mask] = np.mean(detrended[mask])
        
        components.append(DecompositionComponent(
            name="seasonal",
            values=_downsample_uniform(seasonal.tolist(), 2000),
            indices=_downsample_uniform(indices, 2000)
        ))
        
        # 残差
        residual = detrended - seasonal
    else:
        residual = detrended
    
    components.append(DecompositionComponent(
        name="residual",
        values=_downsample_uniform(residual.tolist(), 2000),
        indices=_downsample_uniform(indices, 2000)
    ))
    
    # 添加原始预测和真实值
    components.append(DecompositionComponent(
        name="predicted",
        values=_downsample_uniform(pred_vals.tolist(), 2000),
        indices=_downsample_uniform(indices, 2000)
    ))
    
    components.append(DecompositionComponent(
        name="true",
        values=_downsample_uniform(true_vals.tolist(), 2000),
        indices=_downsample_uniform(indices, 2000)
    ))
    
    return PredictionDecompositionResponse(
        result_id=result_obj.id,
        result_name=result_obj.name,
        components=components,
        detected_period=detected_period
    )

