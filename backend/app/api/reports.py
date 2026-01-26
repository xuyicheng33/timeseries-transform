"""
实验报告生成 API

提供 Markdown、HTML、LaTeX 格式的实验报告生成功能
"""

import html
import io
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user
from app.database import get_db
from app.models import Dataset, Experiment, Result, User
from app.services.permissions import can_access_result

router = APIRouter(prefix="/api/reports", tags=["reports"])


# ============ 请求/响应模型 ============


class ReportConfig(BaseModel):
    """报告配置"""

    include_summary: bool = Field(default=True, description="包含汇总统计")
    include_metrics_table: bool = Field(default=True, description="包含指标对比表")
    include_best_model: bool = Field(default=True, description="包含最佳模型分析")
    include_dataset_info: bool = Field(default=True, description="包含数据集信息")
    include_conclusion: bool = Field(default=True, description="包含实验结论")
    custom_title: str | None = Field(default=None, description="自定义标题")
    custom_author: str | None = Field(default=None, description="自定义作者")


class ReportRequest(BaseModel):
    """报告生成请求"""

    experiment_id: int = Field(..., description="实验组 ID")
    config: ReportConfig = Field(default_factory=ReportConfig)
    format: str = Field(default="markdown", description="输出格式: markdown, html, latex")


class MultiResultReportRequest(BaseModel):
    """多结果报告请求（不依赖实验组）"""

    result_ids: list[int] = Field(..., min_length=1, description="结果 ID 列表")
    title: str = Field(default="时序预测实验报告", description="报告标题")
    config: ReportConfig = Field(default_factory=ReportConfig)
    format: str = Field(default="markdown", description="输出格式: markdown, html, latex")


# ============ 报告生成核心函数 ============


def _format_number(value: float, precision: int = 6) -> str:
    """格式化数字"""
    if value is None:
        return "-"
    if abs(value) < 0.0001 or abs(value) > 10000:
        return f"{value:.{precision}e}"
    return f"{value:.{precision}f}"


def _format_datetime(dt: datetime) -> str:
    """格式化日期时间"""
    if dt is None:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _generate_markdown_report(
    title: str,
    author: str,
    generated_at: str,
    experiment_info: dict[str, Any] | None,
    dataset_info: dict[str, Any] | None,
    results_data: list[dict[str, Any]],
    config: ReportConfig,
) -> str:
    """生成 Markdown 格式报告"""
    lines = []

    # 标题
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**作者**: {author}")
    lines.append(f"**生成时间**: {generated_at}")
    lines.append("")

    # 实验信息
    if experiment_info:
        lines.append("## 实验概述")
        lines.append("")
        lines.append(f"- **实验名称**: {experiment_info.get('name', '-')}")
        lines.append(f"- **实验状态**: {experiment_info.get('status', '-')}")
        if experiment_info.get("objective"):
            lines.append(f"- **实验目标**: {experiment_info.get('objective')}")
        if experiment_info.get("description"):
            lines.append(f"- **实验描述**: {experiment_info.get('description')}")
        if experiment_info.get("tags"):
            tags_str = ", ".join(experiment_info.get("tags", []))
            lines.append(f"- **标签**: {tags_str}")
        lines.append("")

    # 数据集信息
    if config.include_dataset_info and dataset_info:
        lines.append("## 数据集信息")
        lines.append("")
        lines.append(f"- **数据集名称**: {dataset_info.get('name', '-')}")
        lines.append(f"- **数据行数**: {dataset_info.get('row_count', 0):,}")
        lines.append(f"- **数据列数**: {dataset_info.get('column_count', 0)}")
        if dataset_info.get("columns"):
            cols = dataset_info.get("columns", [])
            if len(cols) <= 10:
                lines.append(f"- **列名**: {', '.join(cols)}")
            else:
                lines.append(f"- **列名**: {', '.join(cols[:10])}... (共 {len(cols)} 列)")
        lines.append("")

    # 汇总统计
    if config.include_summary and results_data:
        lines.append("## 实验汇总")
        lines.append("")
        lines.append(f"- **模型数量**: {len(results_data)}")
        model_names = list(set(r.get("algo_name", "unknown") for r in results_data))
        lines.append(f"- **涉及模型**: {', '.join(model_names)}")
        lines.append("")

    # 指标对比表
    if config.include_metrics_table and results_data:
        lines.append("## 模型性能对比")
        lines.append("")

        # Markdown 表格
        lines.append("| 模型 | 版本 | MSE | RMSE | MAE | R² | MAPE (%) |")
        lines.append("|------|------|-----|------|-----|-----|----------|")

        for r in results_data:
            metrics = r.get("metrics", {})
            row = [
                r.get("algo_name", "-"),
                r.get("algo_version", "-") or "-",
                _format_number(metrics.get("mse")),
                _format_number(metrics.get("rmse")),
                _format_number(metrics.get("mae")),
                _format_number(metrics.get("r2"), 4),
                _format_number(metrics.get("mape"), 2),
            ]
            lines.append("| " + " | ".join(row) + " |")

        lines.append("")

    # 最佳模型分析
    if config.include_best_model and results_data:
        lines.append("## 最佳模型分析")
        lines.append("")

        # 找各指标最佳
        def find_best(key: str, minimize: bool = True):
            valid = [
                (r, r.get("metrics", {}).get(key)) for r in results_data if r.get("metrics", {}).get(key) is not None
            ]
            if not valid:
                return None
            if minimize:
                return min(valid, key=lambda x: x[1])
            return max(valid, key=lambda x: x[1])

        best_mse = find_best("mse", True)
        best_rmse = find_best("rmse", True)
        best_mae = find_best("mae", True)
        best_r2 = find_best("r2", False)
        best_mape = find_best("mape", True)

        lines.append("| 指标 | 最佳模型 | 最佳值 |")
        lines.append("|------|----------|--------|")

        if best_mse:
            lines.append(f"| MSE | {best_mse[0].get('algo_name')} | {_format_number(best_mse[1])} |")
        if best_rmse:
            lines.append(f"| RMSE | {best_rmse[0].get('algo_name')} | {_format_number(best_rmse[1])} |")
        if best_mae:
            lines.append(f"| MAE | {best_mae[0].get('algo_name')} | {_format_number(best_mae[1])} |")
        if best_r2:
            lines.append(f"| R² | {best_r2[0].get('algo_name')} | {_format_number(best_r2[1], 4)} |")
        if best_mape:
            lines.append(f"| MAPE | {best_mape[0].get('algo_name')} | {_format_number(best_mape[1], 2)}% |")

        lines.append("")

        # 综合最佳（基于 R² 和 RMSE）
        if best_r2:
            lines.append(f"**综合推荐**: 基于 R² 指标，**{best_r2[0].get('algo_name')}** 表现最佳，")
            lines.append(f"R² = {_format_number(best_r2[1], 4)}，表示模型解释了 {best_r2[1]*100:.2f}% 的数据方差。")
            lines.append("")

    # 实验结论
    if config.include_conclusion and experiment_info and experiment_info.get("conclusion"):
        lines.append("## 实验结论")
        lines.append("")
        lines.append(experiment_info.get("conclusion"))
        lines.append("")

    # 附录：各模型详情
    lines.append("## 附录：模型详情")
    lines.append("")

    for i, r in enumerate(results_data, 1):
        lines.append(f"### {i}. {r.get('name', 'Unknown')}")
        lines.append("")
        lines.append(f"- **模型**: {r.get('algo_name', '-')}")
        lines.append(f"- **版本**: {r.get('algo_version', '-') or '-'}")
        lines.append(f"- **数据行数**: {r.get('row_count', 0):,}")
        lines.append(f"- **创建时间**: {r.get('created_at', '-')}")
        if r.get("description"):
            lines.append(f"- **描述**: {r.get('description')}")
        lines.append("")

    # 页脚
    lines.append("---")
    lines.append("")
    lines.append(f"*本报告由时序预测平台自动生成 | {generated_at}*")

    return "\n".join(lines)


def _generate_latex_table(results_data: list[dict[str, Any]]) -> str:
    """生成 LaTeX 格式的指标对比表"""
    lines = []

    lines.append("\\begin{table}[htbp]")
    lines.append("\\centering")
    lines.append("\\caption{模型性能对比}")
    lines.append("\\label{tab:model_comparison}")
    lines.append("\\begin{tabular}{lcccccc}")
    lines.append("\\toprule")
    lines.append("模型 & 版本 & MSE & RMSE & MAE & R² & MAPE (\\%) \\\\")
    lines.append("\\midrule")

    for r in results_data:
        metrics = r.get("metrics", {})
        row = [
            r.get("algo_name", "-").replace("_", "\\_"),
            r.get("algo_version", "-") or "-",
            _format_number(metrics.get("mse")),
            _format_number(metrics.get("rmse")),
            _format_number(metrics.get("mae")),
            _format_number(metrics.get("r2"), 4),
            _format_number(metrics.get("mape"), 2),
        ]
        lines.append(" & ".join(row) + " \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    return "\n".join(lines)


def _escape_html(text: str) -> str:
    """HTML 转义，防止 XSS 注入"""
    if text is None:
        return ""
    return html.escape(str(text))


def _generate_html_report(
    title: str,
    author: str,
    generated_at: str,
    experiment_info: dict[str, Any] | None,
    dataset_info: dict[str, Any] | None,
    results_data: list[dict[str, Any]],
    config: ReportConfig,
) -> str:
    """生成 HTML 格式报告（带 XSS 防护）"""
    # 转义所有用户输入
    safe_title = _escape_html(title)
    safe_author = _escape_html(author)
    safe_generated_at = _escape_html(generated_at)

    # 简单的 HTML 模板
    html_parts = []
    html_parts.append("<!DOCTYPE html>")
    html_parts.append("<html lang='zh-CN'>")
    html_parts.append("<head>")
    html_parts.append("<meta charset='UTF-8'>")
    html_parts.append(f"<title>{safe_title}</title>")
    html_parts.append("<style>")
    html_parts.append("""
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               max-width: 900px; margin: 0 auto; padding: 20px; line-height: 1.6; }
        h1 { color: #1a1a1a; border-bottom: 2px solid #1890ff; padding-bottom: 10px; }
        h2 { color: #333; margin-top: 30px; }
        h3 { color: #555; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #1890ff; color: white; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        tr:hover { background-color: #f0f7ff; }
        code { background-color: #f5f5f5; padding: 2px 6px; border-radius: 3px; }
        .best { background-color: #e6ffe6; font-weight: bold; }
        hr { border: none; border-top: 1px solid #ddd; margin: 30px 0; }
        .footer { color: #888; font-size: 0.9em; text-align: center; }
        ul { padding-left: 20px; }
        li { margin: 5px 0; }
    """)
    html_parts.append("</style>")
    html_parts.append("</head>")
    html_parts.append("<body>")

    # 标题
    html_parts.append(f"<h1>{safe_title}</h1>")
    html_parts.append(f"<p><strong>作者</strong>: {safe_author}</p>")
    html_parts.append(f"<p><strong>生成时间</strong>: {safe_generated_at}</p>")

    # 实验信息
    if experiment_info:
        html_parts.append("<h2>实验概述</h2>")
        html_parts.append("<ul>")
        html_parts.append(f"<li><strong>实验名称</strong>: {_escape_html(experiment_info.get('name', '-'))}</li>")
        html_parts.append(f"<li><strong>实验状态</strong>: {_escape_html(experiment_info.get('status', '-'))}</li>")
        if experiment_info.get("objective"):
            html_parts.append(f"<li><strong>实验目标</strong>: {_escape_html(experiment_info.get('objective'))}</li>")
        if experiment_info.get("description"):
            html_parts.append(f"<li><strong>实验描述</strong>: {_escape_html(experiment_info.get('description'))}</li>")
        if experiment_info.get("tags"):
            tags_str = ", ".join(_escape_html(t) for t in experiment_info.get("tags", []))
            html_parts.append(f"<li><strong>标签</strong>: {tags_str}</li>")
        html_parts.append("</ul>")

    # 数据集信息
    if config.include_dataset_info and dataset_info:
        html_parts.append("<h2>数据集信息</h2>")
        html_parts.append("<ul>")
        html_parts.append(f"<li><strong>数据集名称</strong>: {_escape_html(dataset_info.get('name', '-'))}</li>")
        html_parts.append(f"<li><strong>数据行数</strong>: {dataset_info.get('row_count', 0):,}</li>")
        html_parts.append(f"<li><strong>数据列数</strong>: {dataset_info.get('column_count', 0)}</li>")
        if dataset_info.get("columns"):
            cols = dataset_info.get("columns", [])
            if len(cols) <= 10:
                cols_str = ", ".join(_escape_html(c) for c in cols)
            else:
                cols_str = ", ".join(_escape_html(c) for c in cols[:10]) + f"... (共 {len(cols)} 列)"
            html_parts.append(f"<li><strong>列名</strong>: {cols_str}</li>")
        html_parts.append("</ul>")

    # 汇总统计
    if config.include_summary and results_data:
        html_parts.append("<h2>实验汇总</h2>")
        html_parts.append("<ul>")
        html_parts.append(f"<li><strong>模型数量</strong>: {len(results_data)}</li>")
        model_names = list(set(_escape_html(r.get("algo_name", "unknown")) for r in results_data))
        html_parts.append(f"<li><strong>涉及模型</strong>: {', '.join(model_names)}</li>")
        html_parts.append("</ul>")

    # 指标对比表
    if config.include_metrics_table and results_data:
        html_parts.append("<h2>模型性能对比</h2>")
        html_parts.append("<table>")
        html_parts.append("<thead><tr>")
        html_parts.append("<th>模型</th><th>版本</th><th>MSE</th><th>RMSE</th><th>MAE</th><th>R²</th><th>MAPE (%)</th>")
        html_parts.append("</tr></thead>")
        html_parts.append("<tbody>")

        for r in results_data:
            metrics = r.get("metrics", {})
            html_parts.append("<tr>")
            html_parts.append(f"<td>{_escape_html(r.get('algo_name', '-'))}</td>")
            html_parts.append(f"<td>{_escape_html(r.get('algo_version', '-') or '-')}</td>")
            html_parts.append(f"<td>{_format_number(metrics.get('mse'))}</td>")
            html_parts.append(f"<td>{_format_number(metrics.get('rmse'))}</td>")
            html_parts.append(f"<td>{_format_number(metrics.get('mae'))}</td>")
            html_parts.append(f"<td>{_format_number(metrics.get('r2'), 4)}</td>")
            html_parts.append(f"<td>{_format_number(metrics.get('mape'), 2)}</td>")
            html_parts.append("</tr>")

        html_parts.append("</tbody></table>")

    # 最佳模型分析
    if config.include_best_model and results_data:
        html_parts.append("<h2>最佳模型分析</h2>")

        def find_best(key: str, minimize: bool = True):
            valid = [
                (r, r.get("metrics", {}).get(key)) for r in results_data if r.get("metrics", {}).get(key) is not None
            ]
            if not valid:
                return None
            if minimize:
                return min(valid, key=lambda x: x[1])
            return max(valid, key=lambda x: x[1])

        best_mse = find_best("mse", True)
        best_rmse = find_best("rmse", True)
        best_mae = find_best("mae", True)
        best_r2 = find_best("r2", False)
        best_mape = find_best("mape", True)

        html_parts.append("<table>")
        html_parts.append("<thead><tr><th>指标</th><th>最佳模型</th><th>最佳值</th></tr></thead>")
        html_parts.append("<tbody>")

        if best_mse:
            html_parts.append(
                f"<tr><td>MSE</td><td>{_escape_html(best_mse[0].get('algo_name'))}</td><td>{_format_number(best_mse[1])}</td></tr>"
            )
        if best_rmse:
            html_parts.append(
                f"<tr><td>RMSE</td><td>{_escape_html(best_rmse[0].get('algo_name'))}</td><td>{_format_number(best_rmse[1])}</td></tr>"
            )
        if best_mae:
            html_parts.append(
                f"<tr><td>MAE</td><td>{_escape_html(best_mae[0].get('algo_name'))}</td><td>{_format_number(best_mae[1])}</td></tr>"
            )
        if best_r2:
            html_parts.append(
                f"<tr><td>R²</td><td>{_escape_html(best_r2[0].get('algo_name'))}</td><td>{_format_number(best_r2[1], 4)}</td></tr>"
            )
        if best_mape:
            html_parts.append(
                f"<tr><td>MAPE</td><td>{_escape_html(best_mape[0].get('algo_name'))}</td><td>{_format_number(best_mape[1], 2)}%</td></tr>"
            )

        html_parts.append("</tbody></table>")

        if best_r2:
            html_parts.append(
                f"<p><strong>综合推荐</strong>: 基于 R² 指标，<strong>{_escape_html(best_r2[0].get('algo_name'))}</strong> 表现最佳，"
            )
            html_parts.append(
                f"R² = {_format_number(best_r2[1], 4)}，表示模型解释了 {best_r2[1]*100:.2f}% 的数据方差。</p>"
            )

    # 实验结论
    if config.include_conclusion and experiment_info and experiment_info.get("conclusion"):
        html_parts.append("<h2>实验结论</h2>")
        html_parts.append(f"<p>{_escape_html(experiment_info.get('conclusion'))}</p>")

    # 附录：各模型详情
    html_parts.append("<h2>附录：模型详情</h2>")

    for i, r in enumerate(results_data, 1):
        html_parts.append(f"<h3>{i}. {_escape_html(r.get('name', 'Unknown'))}</h3>")
        html_parts.append("<ul>")
        html_parts.append(f"<li><strong>模型</strong>: {_escape_html(r.get('algo_name', '-'))}</li>")
        html_parts.append(f"<li><strong>版本</strong>: {_escape_html(r.get('algo_version', '-') or '-')}</li>")
        html_parts.append(f"<li><strong>数据行数</strong>: {r.get('row_count', 0):,}</li>")
        html_parts.append(f"<li><strong>创建时间</strong>: {_escape_html(r.get('created_at', '-'))}</li>")
        if r.get("description"):
            html_parts.append(f"<li><strong>描述</strong>: {_escape_html(r.get('description'))}</li>")
        html_parts.append("</ul>")

    # 页脚
    html_parts.append("<hr>")
    html_parts.append(f"<p class='footer'><em>本报告由时序预测平台自动生成 | {safe_generated_at}</em></p>")

    html_parts.append("</body>")
    html_parts.append("</html>")

    return "\n".join(html_parts)


# ============ API 端点 ============


@router.post("/experiment")
async def generate_experiment_report(
    request: ReportRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    生成实验组报告

    支持 Markdown、HTML、LaTeX 格式
    """
    # 获取实验组
    result = await db.execute(
        select(Experiment).where(Experiment.id == request.experiment_id).options(selectinload(Experiment.results))
    )
    experiment = result.scalar_one_or_none()

    if not experiment:
        raise HTTPException(status_code=404, detail="实验组不存在")

    # 权限检查
    if experiment.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权访问此实验组")

    # 获取数据集信息
    dataset_info = None
    if experiment.dataset_id:
        ds_result = await db.execute(select(Dataset).where(Dataset.id == experiment.dataset_id))
        dataset = ds_result.scalar_one_or_none()
        if dataset:
            dataset_info = {
                "name": dataset.name,
                "row_count": dataset.row_count,
                "column_count": dataset.column_count,
                "columns": dataset.columns,
            }

    # 构建实验信息
    experiment_info = {
        "name": experiment.name,
        "description": experiment.description,
        "objective": experiment.objective,
        "status": experiment.status,
        "tags": experiment.tags,
        "conclusion": experiment.conclusion,
    }

    # 构建结果数据
    results_data = []
    for r in experiment.results:
        results_data.append(
            {
                "id": r.id,
                "name": r.name,
                "algo_name": r.algo_name,
                "algo_version": r.algo_version,
                "description": r.description,
                "row_count": r.row_count,
                "metrics": r.metrics or {},
                "created_at": _format_datetime(r.created_at),
            }
        )

    # 生成报告
    title = request.config.custom_title or f"实验报告: {experiment.name}"
    author = request.config.custom_author or current_user.full_name or current_user.username
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if request.format == "latex":
        # LaTeX 只返回表格部分
        content = _generate_latex_table(results_data)
        media_type = "text/plain"
        filename = f"report_{experiment.id}_table.tex"
    elif request.format == "html":
        content = _generate_html_report(
            title, author, generated_at, experiment_info, dataset_info, results_data, request.config
        )
        media_type = "text/html"
        filename = f"report_{experiment.id}.html"
    else:
        content = _generate_markdown_report(
            title, author, generated_at, experiment_info, dataset_info, results_data, request.config
        )
        media_type = "text/markdown"
        filename = f"report_{experiment.id}.md"

    return StreamingResponse(
        io.StringIO(content),
        media_type=f"{media_type}; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/results")
async def generate_results_report(
    request: MultiResultReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    生成多结果对比报告（不依赖实验组）

    直接选择多个结果生成报告
    """
    # 查询结果
    result = await db.execute(select(Result).where(Result.id.in_(request.result_ids)))
    results = result.scalars().all()

    if not results:
        raise HTTPException(status_code=404, detail="未找到任何结果")

    # 预加载数据集
    dataset_ids = {r.dataset_id for r in results}
    datasets_result = await db.execute(select(Dataset).where(Dataset.id.in_(dataset_ids)))
    datasets_map = {d.id: d for d in datasets_result.scalars().all()}

    # 过滤有权限的结果
    valid_results = []
    for r in results:
        dataset = datasets_map.get(r.dataset_id)
        if can_access_result(r, dataset, current_user):
            valid_results.append(r)

    if not valid_results:
        raise HTTPException(status_code=403, detail="无权访问任何结果")

    # 构建数据集信息（使用第一个结果的数据集）
    dataset_info = None
    first_dataset = datasets_map.get(valid_results[0].dataset_id)
    if first_dataset:
        dataset_info = {
            "name": first_dataset.name,
            "row_count": first_dataset.row_count,
            "column_count": first_dataset.column_count,
            "columns": first_dataset.columns,
        }

    # 构建结果数据
    results_data = []
    for r in valid_results:
        results_data.append(
            {
                "id": r.id,
                "name": r.name,
                "algo_name": r.algo_name,
                "algo_version": r.algo_version,
                "description": r.description,
                "row_count": r.row_count,
                "metrics": r.metrics or {},
                "created_at": _format_datetime(r.created_at),
            }
        )

    # 生成报告
    title = request.title
    author = request.config.custom_author or current_user.full_name or current_user.username
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if request.format == "latex":
        content = _generate_latex_table(results_data)
        media_type = "text/plain"
        filename = "comparison_table.tex"
    elif request.format == "html":
        content = _generate_html_report(title, author, generated_at, None, dataset_info, results_data, request.config)
        media_type = "text/html"
        filename = "comparison_report.html"
    else:
        content = _generate_markdown_report(
            title, author, generated_at, None, dataset_info, results_data, request.config
        )
        media_type = "text/markdown"
        filename = "comparison_report.md"

    return StreamingResponse(
        io.StringIO(content),
        media_type=f"{media_type}; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/latex-table/{experiment_id}")
async def get_latex_table(
    experiment_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    快速获取 LaTeX 表格（用于论文）

    返回可直接复制到 LaTeX 文档的表格代码
    """
    # 获取实验组
    result = await db.execute(
        select(Experiment).where(Experiment.id == experiment_id).options(selectinload(Experiment.results))
    )
    experiment = result.scalar_one_or_none()

    if not experiment:
        raise HTTPException(status_code=404, detail="实验组不存在")

    if experiment.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权访问此实验组")

    results_data = []
    for r in experiment.results:
        results_data.append(
            {
                "algo_name": r.algo_name,
                "algo_version": r.algo_version,
                "metrics": r.metrics or {},
            }
        )

    latex_code = _generate_latex_table(results_data)

    return {"latex": latex_code, "experiment_name": experiment.name, "result_count": len(results_data)}
