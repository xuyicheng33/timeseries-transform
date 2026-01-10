"""
实验报告生成 API

提供 Markdown 和 PDF 格式的实验报告生成功能
"""
import os
import io
import tempfile
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import User, Experiment, Result, Dataset, Configuration
from app.api.auth import get_current_user
from app.services.permissions import can_access_result
from app.services.executor import run_in_executor
from app.config import settings

router = APIRouter(prefix="/api/reports", tags=["reports"])


# ============ 请求/响应模型 ============

class ReportConfig(BaseModel):
    """报告配置"""
    include_summary: bool = Field(default=True, description="包含汇总统计")
    include_metrics_table: bool = Field(default=True, description="包含指标对比表")
    include_best_model: bool = Field(default=True, description="包含最佳模型分析")
    include_config_details: bool = Field(default=False, description="包含配置详情")
    include_dataset_info: bool = Field(default=True, description="包含数据集信息")
    include_conclusion: bool = Field(default=True, description="包含实验结论")
    custom_title: Optional[str] = Field(default=None, description="自定义标题")
    custom_author: Optional[str] = Field(default=None, description="自定义作者")


class ReportRequest(BaseModel):
    """报告生成请求"""
    experiment_id: int = Field(..., description="实验组 ID")
    config: ReportConfig = Field(default_factory=ReportConfig)
    format: str = Field(default="markdown", description="输出格式: markdown, html, latex")


class MultiResultReportRequest(BaseModel):
    """多结果报告请求（不依赖实验组）"""
    result_ids: List[int] = Field(..., min_length=1, description="结果 ID 列表")
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
    experiment_info: Optional[Dict[str, Any]],
    dataset_info: Optional[Dict[str, Any]],
    results_data: List[Dict[str, Any]],
    config: ReportConfig
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
        if experiment_info.get('objective'):
            lines.append(f"- **实验目标**: {experiment_info.get('objective')}")
        if experiment_info.get('description'):
            lines.append(f"- **实验描述**: {experiment_info.get('description')}")
        if experiment_info.get('tags'):
            tags_str = ", ".join(experiment_info.get('tags', []))
            lines.append(f"- **标签**: {tags_str}")
        lines.append("")
    
    # 数据集信息
    if config.include_dataset_info and dataset_info:
        lines.append("## 数据集信息")
        lines.append("")
        lines.append(f"- **数据集名称**: {dataset_info.get('name', '-')}")
        lines.append(f"- **数据行数**: {dataset_info.get('row_count', 0):,}")
        lines.append(f"- **数据列数**: {dataset_info.get('column_count', 0)}")
        if dataset_info.get('columns'):
            cols = dataset_info.get('columns', [])
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
        model_names = list(set(r.get('algo_name', 'unknown') for r in results_data))
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
            metrics = r.get('metrics', {})
            row = [
                r.get('algo_name', '-'),
                r.get('algo_version', '-') or '-',
                _format_number(metrics.get('mse')),
                _format_number(metrics.get('rmse')),
                _format_number(metrics.get('mae')),
                _format_number(metrics.get('r2'), 4),
                _format_number(metrics.get('mape'), 2),
            ]
            lines.append("| " + " | ".join(row) + " |")
        
        lines.append("")
    
    # 最佳模型分析
    if config.include_best_model and results_data:
        lines.append("## 最佳模型分析")
        lines.append("")
        
        # 找各指标最佳
        def find_best(key: str, minimize: bool = True):
            valid = [(r, r.get('metrics', {}).get(key)) for r in results_data if r.get('metrics', {}).get(key) is not None]
            if not valid:
                return None
            if minimize:
                return min(valid, key=lambda x: x[1])
            return max(valid, key=lambda x: x[1])
        
        best_mse = find_best('mse', True)
        best_rmse = find_best('rmse', True)
        best_mae = find_best('mae', True)
        best_r2 = find_best('r2', False)
        best_mape = find_best('mape', True)
        
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
    if config.include_conclusion and experiment_info and experiment_info.get('conclusion'):
        lines.append("## 实验结论")
        lines.append("")
        lines.append(experiment_info.get('conclusion'))
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
        if r.get('description'):
            lines.append(f"- **描述**: {r.get('description')}")
        lines.append("")
    
    # 页脚
    lines.append("---")
    lines.append("")
    lines.append(f"*本报告由时序预测平台自动生成 | {generated_at}*")
    
    return "\n".join(lines)


def _generate_latex_table(results_data: List[Dict[str, Any]]) -> str:
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
        metrics = r.get('metrics', {})
        row = [
            r.get('algo_name', '-').replace('_', '\\_'),
            r.get('algo_version', '-') or '-',
            _format_number(metrics.get('mse')),
            _format_number(metrics.get('rmse')),
            _format_number(metrics.get('mae')),
            _format_number(metrics.get('r2'), 4),
            _format_number(metrics.get('mape'), 2),
        ]
        lines.append(" & ".join(row) + " \\\\")
    
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    
    return "\n".join(lines)


def _generate_html_report(
    title: str,
    author: str,
    generated_at: str,
    experiment_info: Optional[Dict[str, Any]],
    dataset_info: Optional[Dict[str, Any]],
    results_data: List[Dict[str, Any]],
    config: ReportConfig
) -> str:
    """生成 HTML 格式报告"""
    # 先生成 Markdown，然后转换为简单 HTML
    md_content = _generate_markdown_report(
        title, author, generated_at, experiment_info, dataset_info, results_data, config
    )
    
    # 简单的 Markdown 到 HTML 转换
    html_lines = []
    html_lines.append("<!DOCTYPE html>")
    html_lines.append("<html lang='zh-CN'>")
    html_lines.append("<head>")
    html_lines.append("<meta charset='UTF-8'>")
    html_lines.append(f"<title>{title}</title>")
    html_lines.append("<style>")
    html_lines.append("""
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
    """)
    html_lines.append("</style>")
    html_lines.append("</head>")
    html_lines.append("<body>")
    
    # 简单转换 Markdown
    in_table = False
    table_lines = []
    
    for line in md_content.split('\n'):
        if line.startswith('# '):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith('## '):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith('### '):
            html_lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith('| '):
            if not in_table:
                in_table = True
                table_lines = []
            table_lines.append(line)
        elif in_table and not line.startswith('|'):
            # 结束表格
            html_lines.append(_convert_md_table_to_html(table_lines))
            in_table = False
            table_lines = []
            if line.strip():
                html_lines.append(f"<p>{_convert_inline_md(line)}</p>")
        elif line.startswith('- '):
            html_lines.append(f"<li>{_convert_inline_md(line[2:])}</li>")
        elif line.startswith('---'):
            html_lines.append("<hr>")
        elif line.startswith('*') and line.endswith('*'):
            html_lines.append(f"<p class='footer'><em>{line[1:-1]}</em></p>")
        elif line.strip():
            html_lines.append(f"<p>{_convert_inline_md(line)}</p>")
    
    if in_table:
        html_lines.append(_convert_md_table_to_html(table_lines))
    
    html_lines.append("</body>")
    html_lines.append("</html>")
    
    return "\n".join(html_lines)


def _convert_md_table_to_html(table_lines: List[str]) -> str:
    """将 Markdown 表格转换为 HTML"""
    if len(table_lines) < 2:
        return ""
    
    html = ["<table>"]
    
    # 表头
    header_cells = [c.strip() for c in table_lines[0].split('|')[1:-1]]
    html.append("<thead><tr>")
    for cell in header_cells:
        html.append(f"<th>{cell}</th>")
    html.append("</tr></thead>")
    
    # 表体（跳过分隔行）
    html.append("<tbody>")
    for line in table_lines[2:]:
        cells = [c.strip() for c in line.split('|')[1:-1]]
        html.append("<tr>")
        for cell in cells:
            html.append(f"<td>{cell}</td>")
        html.append("</tr>")
    html.append("</tbody>")
    
    html.append("</table>")
    return "\n".join(html)


def _convert_inline_md(text: str) -> str:
    """转换行内 Markdown 格式"""
    import re
    # **bold**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # *italic*
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # `code`
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return text


# ============ API 端点 ============

@router.post("/experiment")
async def generate_experiment_report(
    request: ReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    生成实验组报告
    
    支持 Markdown、HTML、LaTeX 格式
    """
    # 获取实验组
    result = await db.execute(
        select(Experiment)
        .where(Experiment.id == request.experiment_id)
        .options(selectinload(Experiment.results))
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
        ds_result = await db.execute(
            select(Dataset).where(Dataset.id == experiment.dataset_id)
        )
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
        results_data.append({
            "id": r.id,
            "name": r.name,
            "algo_name": r.algo_name,
            "algo_version": r.algo_version,
            "description": r.description,
            "row_count": r.row_count,
            "metrics": r.metrics or {},
            "created_at": _format_datetime(r.created_at),
        })
    
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
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.post("/results")
async def generate_results_report(
    request: MultiResultReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    生成多结果对比报告（不依赖实验组）
    
    直接选择多个结果生成报告
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
        results_data.append({
            "id": r.id,
            "name": r.name,
            "algo_name": r.algo_name,
            "algo_version": r.algo_version,
            "description": r.description,
            "row_count": r.row_count,
            "metrics": r.metrics or {},
            "created_at": _format_datetime(r.created_at),
        })
    
    # 生成报告
    title = request.title
    author = request.config.custom_author or current_user.full_name or current_user.username
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if request.format == "latex":
        content = _generate_latex_table(results_data)
        media_type = "text/plain"
        filename = "comparison_table.tex"
    elif request.format == "html":
        content = _generate_html_report(
            title, author, generated_at, None, dataset_info, results_data, request.config
        )
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
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/latex-table/{experiment_id}")
async def get_latex_table(
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    快速获取 LaTeX 表格（用于论文）
    
    返回可直接复制到 LaTeX 文档的表格代码
    """
    # 获取实验组
    result = await db.execute(
        select(Experiment)
        .where(Experiment.id == experiment_id)
        .options(selectinload(Experiment.results))
    )
    experiment = result.scalar_one_or_none()
    
    if not experiment:
        raise HTTPException(status_code=404, detail="实验组不存在")
    
    if experiment.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权访问此实验组")
    
    results_data = []
    for r in experiment.results:
        results_data.append({
            "algo_name": r.algo_name,
            "algo_version": r.algo_version,
            "metrics": r.metrics or {},
        })
    
    latex_code = _generate_latex_table(results_data)
    
    return {
        "latex": latex_code,
        "experiment_name": experiment.name,
        "result_count": len(results_data)
    }

