"""
配置对比分析 API
提供超参数敏感性分析、控制变量对比、配置组管理等功能
"""

from collections import defaultdict
from typing import Any

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.models import Configuration, Dataset, Result, User
from app.services.permissions import can_access_result

router = APIRouter(prefix="/api/comparison", tags=["comparison"])


# ============ 请求/响应模型 ============


class ConfigCompareRequest(BaseModel):
    """配置对比请求"""

    result_ids: list[int] = Field(..., min_length=1, description="要对比的结果ID列表")


class ParameterValue(BaseModel):
    """参数值及其对应的指标"""

    value: Any
    result_ids: list[int]
    result_names: list[str]
    metrics: dict[str, float]  # 平均指标
    metrics_std: dict[str, float]  # 指标标准差
    count: int


class ParameterAnalysis(BaseModel):
    """单个参数的分析结果"""

    parameter_name: str
    parameter_label: str  # 中文标签
    values: list[ParameterValue]
    is_numeric: bool  # 是否为数值型参数
    sensitivity_score: float  # 敏感性得分 (0-1)


class ConfigCompareResponse(BaseModel):
    """配置对比响应"""

    total_results: int
    parameters: list[ParameterAnalysis]
    result_details: list[dict[str, Any]]  # 每个结果的详细信息
    warnings: list[str]


class ControlledCompareRequest(BaseModel):
    """控制变量对比请求"""

    result_ids: list[int] = Field(..., min_length=2, description="要对比的结果ID列表")
    control_parameter: str = Field(..., description="要分析的参数名")


class ControlledCompareResponse(BaseModel):
    """控制变量对比响应"""

    parameter_name: str
    parameter_label: str
    baseline_config: dict[str, Any]  # 基准配置（其他参数的共同值）
    config_consistent: bool  # 其他参数是否完全一致
    inconsistent_params: list[str]  # 不一致的参数列表
    variations: list[dict[str, Any]]  # 不同参数值的结果
    chart_data: dict[str, Any]  # 图表数据


class SensitivityRequest(BaseModel):
    """参数敏感性分析请求"""

    result_ids: list[int] = Field(..., min_length=2)
    target_metric: str = Field(default="rmse", description="目标指标")


class SensitivityResponse(BaseModel):
    """参数敏感性分析响应"""

    target_metric: str
    sensitivities: list[dict[str, Any]]  # 各参数的敏感性排名
    recommendations: list[str]  # 调参建议


# ============ 辅助函数 ============

# 参数中文标签映射
PARAMETER_LABELS = {
    "window_size": "窗口大小",
    "stride": "步长",
    "normalization": "归一化方法",
    "target_type": "目标类型",
    "target_k": "预测步数",
    "anomaly_enabled": "异常注入",
    "anomaly_type": "异常类型",
    "injection_algorithm": "注入算法",
    "sequence_logic": "序列逻辑",
    "channels": "通道数",
}

# 可分析的配置参数
ANALYZABLE_PARAMETERS = [
    "window_size",
    "stride",
    "normalization",
    "target_type",
    "target_k",
    "anomaly_enabled",
]

# 指标名称映射
METRIC_LABELS = {
    "mse": "MSE",
    "rmse": "RMSE",
    "mae": "MAE",
    "r2": "R²",
    "mape": "MAPE",
}


def _safe_float(value: Any) -> float | None:
    """安全转换为浮点数，处理 NaN/Inf"""
    if value is None:
        return None
    try:
        f = float(value)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _is_strictly_numeric(value: Any) -> bool:
    """
    判断是否为严格数值类型（排除 bool）
    Python 中 bool 是 int 的子类，需要显式排除
    """
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def _sort_key_for_param(value: Any) -> tuple:
    """
    参数值排序键，确保数值正确排序
    返回 (类型优先级, 排序值)
    - 数值类型按数值排序
    - 布尔类型 False < True
    - 其他类型按字符串排序
    """
    if isinstance(value, bool):
        return (1, int(value))  # False=0, True=1
    if isinstance(value, (int, float)):
        return (0, value)  # 数值优先，按数值排序
    return (2, str(value))  # 其他类型按字符串排序


def _get_config_value(config: Configuration | None, param: str) -> Any:
    """获取配置参数值"""
    if config is None:
        return None

    if param == "channels":
        # 返回通道数而非通道列表
        channels = getattr(config, param, [])
        return len(channels) if channels else 0

    return getattr(config, param, None)


def _calculate_sensitivity(values: list[float], metrics: list[float]) -> float:
    """
    计算参数敏感性得分
    使用变异系数 (CV) 衡量指标随参数变化的波动程度
    """
    if len(metrics) < 2:
        return 0.0

    metrics_array = np.array([m for m in metrics if m is not None])
    if len(metrics_array) < 2:
        return 0.0

    mean_val = np.mean(metrics_array)
    if mean_val == 0:
        return 0.0

    std_val = np.std(metrics_array)
    cv = std_val / abs(mean_val)

    # 归一化到 0-1 范围
    return min(cv, 1.0)


def _aggregate_metrics(metrics_list: list[dict[str, Any]]) -> tuple[dict[str, float], dict[str, float]]:
    """聚合多个结果的指标，返回平均值和标准差"""
    if not metrics_list:
        return {}, {}

    aggregated = defaultdict(list)
    for m in metrics_list:
        if m:
            for key in ["mse", "rmse", "mae", "r2", "mape"]:
                val = _safe_float(m.get(key))
                if val is not None:
                    aggregated[key].append(val)

    means = {}
    stds = {}
    for key, values in aggregated.items():
        if values:
            means[key] = float(np.mean(values))
            stds[key] = float(np.std(values)) if len(values) > 1 else 0.0

    return means, stds


# ============ API 端点 ============


@router.post("/analyze", response_model=ConfigCompareResponse)
async def analyze_configurations(
    data: ConfigCompareRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    配置对比分析

    分析选中结果的配置差异，识别不同参数值对性能的影响
    """
    if not data.result_ids:
        raise HTTPException(status_code=400, detail="请提供至少一个结果ID")

    # 查询结果
    result = await db.execute(select(Result).where(Result.id.in_(data.result_ids)))
    results = result.scalars().all()

    if not results:
        raise HTTPException(status_code=404, detail="未找到任何结果")

    # 预加载数据集和配置
    dataset_ids = {r.dataset_id for r in results}
    config_ids = {r.configuration_id for r in results if r.configuration_id}

    datasets_result = await db.execute(select(Dataset).where(Dataset.id.in_(dataset_ids)))
    datasets_map = {d.id: d for d in datasets_result.scalars().all()}

    configs_map: dict[int, Configuration] = {}
    if config_ids:
        configs_result = await db.execute(select(Configuration).where(Configuration.id.in_(config_ids)))
        configs_map = {c.id: c for c in configs_result.scalars().all()}

    # 过滤有权限访问的结果
    valid_results = []
    warnings = []

    for res in results:
        dataset = datasets_map.get(res.dataset_id)
        if not can_access_result(res, dataset, current_user):
            warnings.append(f"无权访问结果 '{res.name}'")
            continue

        if not res.configuration_id:
            warnings.append(f"结果 '{res.name}' 未关联配置，无法参与对比分析")
            continue

        if res.configuration_id not in configs_map:
            warnings.append(f"结果 '{res.name}' 关联的配置不存在")
            continue

        if not res.metrics:
            warnings.append(f"结果 '{res.name}' 没有指标数据")
            continue

        valid_results.append(res)

    if len(valid_results) < 1:
        raise HTTPException(status_code=400, detail="没有有效的结果可供分析")

    # 构建结果详情
    result_details = []
    for res in valid_results:
        config = configs_map.get(res.configuration_id)
        result_details.append(
            {
                "result_id": res.id,
                "result_name": res.name,
                "model_name": res.algo_name,
                "config_id": res.configuration_id,
                "config_name": config.name if config else None,
                "metrics": res.metrics,
                "parameters": (
                    {param: _get_config_value(config, param) for param in ANALYZABLE_PARAMETERS} if config else {}
                ),
            }
        )

    # 分析各参数
    parameters_analysis = []

    for param in ANALYZABLE_PARAMETERS:
        # 按参数值分组
        value_groups: dict[Any, list[dict]] = defaultdict(list)

        for detail in result_details:
            param_value = detail["parameters"].get(param)
            if param_value is not None:
                value_groups[param_value].append(detail)

        # 如果只有一个值，跳过该参数
        if len(value_groups) <= 1:
            continue

        # 构建参数值分析
        param_values = []
        all_metrics_for_sensitivity = []

        for value, group in sorted(value_groups.items(), key=lambda x: _sort_key_for_param(x[0])):
            metrics_list = [d["metrics"] for d in group]
            means, stds = _aggregate_metrics(metrics_list)

            param_values.append(
                ParameterValue(
                    value=value,
                    result_ids=[d["result_id"] for d in group],
                    result_names=[d["result_name"] for d in group],
                    metrics=means,
                    metrics_std=stds,
                    count=len(group),
                )
            )

            # 收集用于敏感性计算的指标
            if means.get("rmse") is not None:
                all_metrics_for_sensitivity.append(means["rmse"])

        # 计算敏感性得分（使用 _is_strictly_numeric 排除 bool）
        is_numeric = all(_is_strictly_numeric(pv.value) for pv in param_values)
        sensitivity = _calculate_sensitivity(
            [pv.value for pv in param_values] if is_numeric else list(range(len(param_values))),
            all_metrics_for_sensitivity,
        )

        parameters_analysis.append(
            ParameterAnalysis(
                parameter_name=param,
                parameter_label=PARAMETER_LABELS.get(param, param),
                values=param_values,
                is_numeric=is_numeric,
                sensitivity_score=sensitivity,
            )
        )

    # 按敏感性得分排序
    parameters_analysis.sort(key=lambda x: x.sensitivity_score, reverse=True)

    return ConfigCompareResponse(
        total_results=len(valid_results),
        parameters=parameters_analysis,
        result_details=result_details,
        warnings=warnings,
    )


@router.post("/controlled", response_model=ControlledCompareResponse)
async def controlled_comparison(
    data: ControlledCompareRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    控制变量对比

    固定其他参数，只变化指定参数，分析其对性能的影响
    """
    if data.control_parameter not in ANALYZABLE_PARAMETERS:
        raise HTTPException(
            status_code=400, detail=f"不支持的参数: {data.control_parameter}，可选: {ANALYZABLE_PARAMETERS}"
        )

    # 查询结果
    result = await db.execute(select(Result).where(Result.id.in_(data.result_ids)))
    results = result.scalars().all()

    # 预加载数据集和配置
    dataset_ids = {r.dataset_id for r in results}
    config_ids = {r.configuration_id for r in results if r.configuration_id}

    datasets_result = await db.execute(select(Dataset).where(Dataset.id.in_(dataset_ids)))
    datasets_map = {d.id: d for d in datasets_result.scalars().all()}

    configs_map: dict[int, Configuration] = {}
    if config_ids:
        configs_result = await db.execute(select(Configuration).where(Configuration.id.in_(config_ids)))
        configs_map = {c.id: c for c in configs_result.scalars().all()}

    # 过滤有效结果
    valid_results = []
    for res in results:
        dataset = datasets_map.get(res.dataset_id)
        if not can_access_result(res, dataset, current_user):
            continue
        if not res.configuration_id or res.configuration_id not in configs_map:
            continue
        if not res.metrics:
            continue
        valid_results.append(res)

    if len(valid_results) < 2:
        raise HTTPException(status_code=400, detail="需要至少2个有效结果进行控制变量对比")

    # 提取配置参数
    results_with_config = []
    for res in valid_results:
        config = configs_map[res.configuration_id]
        params = {param: _get_config_value(config, param) for param in ANALYZABLE_PARAMETERS}
        results_with_config.append({"result": res, "config": config, "params": params})

    # 找出除控制参数外的共同配置（基准配置）
    other_params = [p for p in ANALYZABLE_PARAMETERS if p != data.control_parameter]

    # 检查其他参数是否一致
    baseline_config = {}
    config_consistent = True
    inconsistent_params = []

    for param in other_params:
        values = set()
        for item in results_with_config:
            val = item["params"].get(param)
            # 转换为可哈希类型
            if isinstance(val, list):
                val = tuple(val)
            values.add(val)

        if len(values) == 1:
            baseline_config[param] = list(values)[0]
        else:
            config_consistent = False
            inconsistent_params.append(PARAMETER_LABELS.get(param, param))
            # 取众数作为基准
            from collections import Counter

            val_counts = Counter()
            for item in results_with_config:
                val = item["params"].get(param)
                if isinstance(val, list):
                    val = tuple(val)
                val_counts[val] += 1
            most_common = val_counts.most_common(1)[0][0]
            baseline_config[param] = most_common

    # 如果配置不一致，只保留符合基准配置的结果
    if not config_consistent:
        filtered_results = []
        for item in results_with_config:
            match = True
            for param in other_params:
                val = item["params"].get(param)
                if isinstance(val, list):
                    val = tuple(val)
                baseline_val = baseline_config.get(param)
                if isinstance(baseline_val, list):
                    baseline_val = tuple(baseline_val)
                if val != baseline_val:
                    match = False
                    break
            if match:
                filtered_results.append(item)

        # 如果过滤后结果太少，使用原始结果但标记警告
        if len(filtered_results) >= 2:
            results_with_config = filtered_results

    # 按控制参数值分组
    variations = []
    control_values = []

    grouped = defaultdict(list)
    for item in results_with_config:
        control_val = item["params"].get(data.control_parameter)
        grouped[control_val].append(item)

    for control_val, items in sorted(grouped.items(), key=lambda x: _sort_key_for_param(x[0])):
        metrics_list = [item["result"].metrics for item in items]
        means, stds = _aggregate_metrics(metrics_list)

        variations.append(
            {
                "parameter_value": control_val,
                "result_count": len(items),
                "result_ids": [item["result"].id for item in items],
                "result_names": [item["result"].name for item in items],
                "metrics": means,
                "metrics_std": stds,
            }
        )
        control_values.append(control_val)

    # 构建图表数据（使用 _is_strictly_numeric 排除 bool）
    is_numeric = all(_is_strictly_numeric(v) for v in control_values)

    chart_data = {
        "x_axis": {
            "name": PARAMETER_LABELS.get(data.control_parameter, data.control_parameter),
            "data": [str(v) for v in control_values],  # 始终转为字符串，前端更好处理
            "is_numeric": is_numeric,
        },
        "series": [],
    }

    for metric_key in ["mse", "rmse", "mae", "r2", "mape"]:
        series_data = []
        for var in variations:
            val = var["metrics"].get(metric_key)
            series_data.append(_safe_float(val))

        chart_data["series"].append(
            {"name": METRIC_LABELS.get(metric_key, metric_key), "key": metric_key, "data": series_data}
        )

    return ControlledCompareResponse(
        parameter_name=data.control_parameter,
        parameter_label=PARAMETER_LABELS.get(data.control_parameter, data.control_parameter),
        baseline_config={PARAMETER_LABELS.get(k, k): v for k, v in baseline_config.items()},
        config_consistent=config_consistent,
        inconsistent_params=inconsistent_params,
        variations=variations,
        chart_data=chart_data,
    )


@router.post("/sensitivity", response_model=SensitivityResponse)
async def analyze_sensitivity(
    data: SensitivityRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    参数敏感性分析

    分析各参数对目标指标的影响程度，给出调参建议
    """
    valid_metrics = ["mse", "rmse", "mae", "r2", "mape"]
    if data.target_metric not in valid_metrics:
        raise HTTPException(status_code=400, detail=f"不支持的指标: {data.target_metric}，可选: {valid_metrics}")

    # 查询结果
    result = await db.execute(select(Result).where(Result.id.in_(data.result_ids)))
    results = result.scalars().all()

    # 预加载数据集和配置
    dataset_ids = {r.dataset_id for r in results}
    config_ids = {r.configuration_id for r in results if r.configuration_id}

    datasets_result = await db.execute(select(Dataset).where(Dataset.id.in_(dataset_ids)))
    datasets_map = {d.id: d for d in datasets_result.scalars().all()}

    configs_map: dict[int, Configuration] = {}
    if config_ids:
        configs_result = await db.execute(select(Configuration).where(Configuration.id.in_(config_ids)))
        configs_map = {c.id: c for c in configs_result.scalars().all()}

    # 过滤有效结果
    valid_results = []
    for res in results:
        dataset = datasets_map.get(res.dataset_id)
        if not can_access_result(res, dataset, current_user):
            continue
        if not res.configuration_id or res.configuration_id not in configs_map:
            continue
        if not res.metrics:
            continue
        valid_results.append(res)

    if len(valid_results) < 2:
        raise HTTPException(status_code=400, detail="需要至少2个有效结果进行敏感性分析")

    # 计算各参数的敏感性
    sensitivities = []

    for param in ANALYZABLE_PARAMETERS:
        # 按参数值分组
        value_groups: dict[Any, list[float]] = defaultdict(list)

        for res in valid_results:
            config = configs_map.get(res.configuration_id)
            if not config:
                continue

            param_value = _get_config_value(config, param)
            metric_value = _safe_float(res.metrics.get(data.target_metric))

            if param_value is not None and metric_value is not None:
                value_groups[param_value].append(metric_value)

        # 需要至少2个不同的参数值
        if len(value_groups) < 2:
            continue

        # 计算每个参数值的平均指标（使用正确的排序）
        param_values = []
        metric_means = []

        for val, metrics in sorted(value_groups.items(), key=lambda x: _sort_key_for_param(x[0])):
            param_values.append(val)
            metric_means.append(np.mean(metrics))

        # 计算敏感性得分（使用 _is_strictly_numeric 排除 bool）
        is_numeric = all(_is_strictly_numeric(v) for v in param_values)
        sensitivity = _calculate_sensitivity(
            param_values if is_numeric else list(range(len(param_values))), metric_means
        )

        # 找出最优值
        if data.target_metric == "r2":
            # R² 越大越好
            best_idx = np.argmax(metric_means)
        else:
            # 其他指标越小越好
            best_idx = np.argmin(metric_means)

        best_value = param_values[best_idx]
        best_metric = metric_means[best_idx]

        sensitivities.append(
            {
                "parameter": param,
                "parameter_label": PARAMETER_LABELS.get(param, param),
                "sensitivity_score": round(sensitivity, 4),
                "value_count": len(param_values),
                "best_value": best_value,
                "best_metric": round(best_metric, 6),
                "is_numeric": is_numeric,
                "value_metrics": [{"value": v, "metric": round(m, 6)} for v, m in zip(param_values, metric_means)],
            }
        )

    # 按敏感性得分排序
    sensitivities.sort(key=lambda x: x["sensitivity_score"], reverse=True)

    # 生成调参建议
    recommendations = []

    if sensitivities:
        # 最敏感的参数
        top_param = sensitivities[0]
        if top_param["sensitivity_score"] > 0.1:
            recommendations.append(
                f"参数「{top_param['parameter_label']}」对 {METRIC_LABELS[data.target_metric]} 影响最大，"
                f"建议优先调整。最优值为 {top_param['best_value']}。"
            )

        # 不敏感的参数
        insensitive = [s for s in sensitivities if s["sensitivity_score"] < 0.05]
        if insensitive:
            param_names = "、".join([s["parameter_label"] for s in insensitive[:3]])
            recommendations.append(f"参数「{param_names}」对性能影响较小，可以使用默认值或根据计算资源选择。")

        # 数值型参数的趋势建议
        for s in sensitivities[:3]:
            if s["is_numeric"] and len(s["value_metrics"]) >= 3:
                values = [vm["value"] for vm in s["value_metrics"]]
                metrics = [vm["metric"] for vm in s["value_metrics"]]

                # 检查是否单调
                if data.target_metric == "r2":
                    # R² 越大越好
                    is_increasing = all(metrics[i] <= metrics[i + 1] for i in range(len(metrics) - 1))
                    is_decreasing = all(metrics[i] >= metrics[i + 1] for i in range(len(metrics) - 1))
                else:
                    # 其他指标越小越好
                    is_increasing = all(metrics[i] >= metrics[i + 1] for i in range(len(metrics) - 1))
                    is_decreasing = all(metrics[i] <= metrics[i + 1] for i in range(len(metrics) - 1))

                if is_increasing:
                    recommendations.append(
                        f"「{s['parameter_label']}」呈现单调趋势：值越大性能越好，可尝试进一步增大。"
                    )
                elif is_decreasing:
                    recommendations.append(
                        f"「{s['parameter_label']}」呈现单调趋势：值越小性能越好，可尝试进一步减小。"
                    )

    if not recommendations:
        recommendations.append("当前结果数量或参数变化不足以给出明确建议，建议增加更多实验。")

    return SensitivityResponse(
        target_metric=data.target_metric, sensitivities=sensitivities, recommendations=recommendations
    )


@router.get("/parameters")
async def get_analyzable_parameters():
    """获取可分析的参数列表"""
    return {
        "parameters": [{"name": param, "label": PARAMETER_LABELS.get(param, param)} for param in ANALYZABLE_PARAMETERS],
        "metrics": [{"name": metric, "label": label} for metric, label in METRIC_LABELS.items()],
    }
