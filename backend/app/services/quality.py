"""
数据质量检测服务

提供数据质量分析、异常值检测、缺失值统计等功能
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.schemas import (
    DataQualityReport,
    ColumnMissingStats,
    ColumnOutlierStats,
    ColumnTypeInfo,
    ColumnBasicStats,
    TimeSeriesAnalysis,
    QualitySuggestion,
    QualityCheckRequest,
)
from app.schemas.enums import OutlierMethod, QualityLevel, ColumnDataType


class QualityAnalyzer:
    """数据质量分析器"""
    
    def __init__(self, df: pd.DataFrame, dataset_id: int, dataset_name: str):
        self.df = df
        self.dataset_id = dataset_id
        self.dataset_name = dataset_name
        self.numeric_columns: List[str] = []
        self.categorical_columns: List[str] = []
        self.datetime_columns: List[str] = []
        self._identify_column_types()
    
    def _identify_column_types(self):
        """识别列类型"""
        for col in self.df.columns:
            dtype = self.df[col].dtype
            
            # 尝试检测日期时间列
            if dtype == 'object':
                # 尝试解析为日期
                try:
                    sample = self.df[col].dropna().head(100)
                    if len(sample) > 0:
                        pd.to_datetime(sample, infer_datetime_format=True)
                        self.datetime_columns.append(col)
                        continue
                except:
                    pass
            
            if pd.api.types.is_datetime64_any_dtype(dtype):
                self.datetime_columns.append(col)
            elif pd.api.types.is_numeric_dtype(dtype):
                self.numeric_columns.append(col)
            else:
                self.categorical_columns.append(col)
    
    def analyze_missing(self) -> Tuple[List[ColumnMissingStats], int, float]:
        """分析缺失值"""
        missing_stats = []
        total_missing = 0
        
        for col in self.df.columns:
            missing_count = int(self.df[col].isna().sum())
            total_count = len(self.df)
            missing_ratio = missing_count / total_count if total_count > 0 else 0
            
            missing_stats.append(ColumnMissingStats(
                column=col,
                missing_count=missing_count,
                missing_ratio=round(missing_ratio, 4),
                total_count=total_count
            ))
            total_missing += missing_count
        
        total_cells = len(self.df) * len(self.df.columns)
        total_ratio = total_missing / total_cells if total_cells > 0 else 0
        
        return missing_stats, total_missing, round(total_ratio, 4)
    
    def detect_outliers(
        self, 
        method: str = "iqr",
        params: Dict[str, Any] = None,
        columns: Optional[List[str]] = None
    ) -> Tuple[List[ColumnOutlierStats], int, float]:
        """
        检测异常值
        
        Args:
            method: 检测方法 (iqr / zscore / mad / percentile)
            params: 方法参数
            columns: 要检测的列（None 表示所有数值列）
        
        Returns:
            (异常值统计列表, 总异常值数, 总异常值比例)
        """
        if params is None:
            params = {}
        
        target_columns = columns if columns else self.numeric_columns
        outlier_stats = []
        total_outliers = 0
        total_numeric_cells = 0
        
        for col in target_columns:
            if col not in self.df.columns:
                continue
            
            series = self.df[col].dropna()
            if len(series) == 0:
                continue
            
            # 转换为数值类型
            try:
                series = pd.to_numeric(series, errors='coerce').dropna()
            except:
                continue
            
            if len(series) == 0:
                continue
            
            # 检测异常值
            lower_bound, upper_bound = self._get_outlier_bounds(series, method, params)
            
            # 找出异常值
            outlier_mask = (series < lower_bound) | (series > upper_bound)
            outlier_indices = series[outlier_mask].index.tolist()
            outlier_count = len(outlier_indices)
            
            # 基础统计
            min_val = float(series.min())
            max_val = float(series.max())
            mean_val = float(series.mean())
            std_val = float(series.std()) if len(series) > 1 else 0.0
            
            outlier_stats.append(ColumnOutlierStats(
                column=col,
                outlier_count=outlier_count,
                outlier_ratio=round(outlier_count / len(series), 4) if len(series) > 0 else 0,
                outlier_indices=outlier_indices[:100],  # 最多返回100个索引
                lower_bound=round(lower_bound, 6) if lower_bound != float('-inf') else None,
                upper_bound=round(upper_bound, 6) if upper_bound != float('inf') else None,
                min_value=round(min_val, 6),
                max_value=round(max_val, 6),
                mean_value=round(mean_val, 6),
                std_value=round(std_val, 6)
            ))
            
            total_outliers += outlier_count
            total_numeric_cells += len(series)
        
        total_ratio = total_outliers / total_numeric_cells if total_numeric_cells > 0 else 0
        
        return outlier_stats, total_outliers, round(total_ratio, 4)
    
    def _get_outlier_bounds(
        self, 
        series: pd.Series, 
        method: str, 
        params: Dict[str, Any]
    ) -> Tuple[float, float]:
        """
        根据方法计算异常值边界
        
        Returns:
            (lower_bound, upper_bound)
        """
        if method == OutlierMethod.IQR.value or method == "iqr":
            multiplier = params.get("multiplier", 1.5)
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - multiplier * iqr
            upper = q3 + multiplier * iqr
            return float(lower), float(upper)
        
        elif method == OutlierMethod.ZSCORE.value or method == "zscore":
            threshold = params.get("threshold", 3.0)
            mean = series.mean()
            std = series.std()
            if std == 0:
                return float('-inf'), float('inf')
            lower = mean - threshold * std
            upper = mean + threshold * std
            return float(lower), float(upper)
        
        elif method == OutlierMethod.MAD.value or method == "mad":
            threshold = params.get("threshold", 3.5)
            median = series.median()
            mad = np.median(np.abs(series - median))
            if mad == 0:
                return float('-inf'), float('inf')
            # MAD 的缩放因子（假设正态分布）
            mad_scaled = mad * 1.4826
            lower = median - threshold * mad_scaled
            upper = median + threshold * mad_scaled
            return float(lower), float(upper)
        
        elif method == OutlierMethod.PERCENTILE.value or method == "percentile":
            lower_pct = params.get("lower", 1)
            upper_pct = params.get("upper", 99)
            lower = series.quantile(lower_pct / 100)
            upper = series.quantile(upper_pct / 100)
            return float(lower), float(upper)
        
        elif method == OutlierMethod.THRESHOLD.value or method == "threshold":
            lower = params.get("lower", float('-inf'))
            upper = params.get("upper", float('inf'))
            return float(lower), float(upper)
        
        else:
            # 默认使用 IQR
            return self._get_outlier_bounds(series, "iqr", {"multiplier": 1.5})
    
    def analyze_column_types(self) -> List[ColumnTypeInfo]:
        """分析列类型"""
        type_info = []
        
        for col in self.df.columns:
            series = self.df[col]
            dtype = str(series.dtype)
            unique_count = series.nunique()
            unique_ratio = unique_count / len(series) if len(series) > 0 else 0
            
            # 推断类型
            if col in self.datetime_columns:
                inferred_type = ColumnDataType.DATETIME.value
            elif col in self.numeric_columns:
                if pd.api.types.is_integer_dtype(series.dtype):
                    inferred_type = ColumnDataType.INTEGER.value
                else:
                    inferred_type = ColumnDataType.FLOAT.value
            elif series.dtype == 'bool':
                inferred_type = ColumnDataType.BOOLEAN.value
            elif unique_ratio < 0.05 and unique_count < 50:
                inferred_type = ColumnDataType.CATEGORICAL.value
            else:
                inferred_type = ColumnDataType.TEXT.value
            
            # 获取示例值
            sample_values = series.dropna().head(5).tolist()
            # 转换为可序列化的格式
            sample_values = [str(v) if not isinstance(v, (int, float, bool, str)) else v for v in sample_values]
            
            type_info.append(ColumnTypeInfo(
                column=col,
                inferred_type=inferred_type,
                original_dtype=dtype,
                unique_count=unique_count,
                unique_ratio=round(unique_ratio, 4),
                sample_values=sample_values
            ))
        
        return type_info
    
    def analyze_column_stats(self) -> List[ColumnBasicStats]:
        """计算列统计信息"""
        stats_list = []
        
        for col in self.df.columns:
            series = self.df[col]
            missing_count = int(series.isna().sum())
            missing_ratio = missing_count / len(series) if len(series) > 0 else 0
            
            stats = ColumnBasicStats(
                column=col,
                dtype=str(series.dtype),
                count=len(series),
                missing_count=missing_count,
                missing_ratio=round(missing_ratio, 4)
            )
            
            # 数值型统计
            if col in self.numeric_columns:
                numeric_series = pd.to_numeric(series, errors='coerce').dropna()
                if len(numeric_series) > 0:
                    stats.mean = round(float(numeric_series.mean()), 6)
                    stats.std = round(float(numeric_series.std()), 6) if len(numeric_series) > 1 else 0.0
                    stats.min = round(float(numeric_series.min()), 6)
                    stats.q1 = round(float(numeric_series.quantile(0.25)), 6)
                    stats.median = round(float(numeric_series.quantile(0.5)), 6)
                    stats.q3 = round(float(numeric_series.quantile(0.75)), 6)
                    stats.max = round(float(numeric_series.max()), 6)
            
            # 分类型统计
            if col in self.categorical_columns or col not in self.numeric_columns:
                stats.unique_count = series.nunique()
                value_counts = series.value_counts()
                if len(value_counts) > 0:
                    stats.top_value = str(value_counts.index[0])
                    stats.top_freq = int(value_counts.iloc[0])
            
            stats_list.append(stats)
        
        return stats_list
    
    def analyze_time_series(self) -> Optional[TimeSeriesAnalysis]:
        """分析时序特征"""
        if not self.datetime_columns:
            # 尝试从列名推断时间列
            time_col_candidates = ['time', 'timestamp', 'date', 'datetime', 'Time', 'Timestamp', 'Date']
            for candidate in time_col_candidates:
                if candidate in self.df.columns:
                    try:
                        self.df[candidate] = pd.to_datetime(self.df[candidate])
                        self.datetime_columns.append(candidate)
                        break
                    except:
                        continue
        
        if not self.datetime_columns:
            return None
        
        time_col = self.datetime_columns[0]
        try:
            time_series = pd.to_datetime(self.df[time_col]).dropna().sort_values()
            
            if len(time_series) < 2:
                return None
            
            start_time = time_series.iloc[0]
            end_time = time_series.iloc[-1]
            
            # 计算时间间隔
            diffs = time_series.diff().dropna()
            
            # 推断频率
            if len(diffs) > 0:
                median_diff = diffs.median()
                # 判断频率
                if median_diff <= pd.Timedelta(seconds=1):
                    freq = "1S"
                elif median_diff <= pd.Timedelta(minutes=1):
                    freq = "1T"
                elif median_diff <= pd.Timedelta(hours=1):
                    freq = "1H"
                elif median_diff <= pd.Timedelta(days=1):
                    freq = "1D"
                elif median_diff <= pd.Timedelta(days=7):
                    freq = "1W"
                else:
                    freq = "1M"
                
                # 检查是否规则
                std_diff = diffs.std()
                is_regular = std_diff < median_diff * 0.1 if median_diff.total_seconds() > 0 else True
                
                # 计算间隔异常数量
                threshold = median_diff * 2
                gaps_count = int((diffs > threshold).sum())
            else:
                freq = None
                is_regular = True
                gaps_count = 0
            
            return TimeSeriesAnalysis(
                time_column=time_col,
                start_time=str(start_time),
                end_time=str(end_time),
                frequency=freq,
                total_duration=str(end_time - start_time),
                gaps_count=gaps_count,
                is_regular=is_regular
            )
        except Exception:
            return None
    
    def analyze_duplicates(self) -> Tuple[int, float]:
        """分析重复行"""
        duplicate_count = int(self.df.duplicated().sum())
        duplicate_ratio = duplicate_count / len(self.df) if len(self.df) > 0 else 0
        return duplicate_count, round(duplicate_ratio, 4)
    
    def generate_suggestions(
        self,
        missing_stats: List[ColumnMissingStats],
        outlier_stats: List[ColumnOutlierStats],
        duplicate_count: int,
        time_analysis: Optional[TimeSeriesAnalysis]
    ) -> List[QualitySuggestion]:
        """生成改进建议"""
        suggestions = []
        
        # 缺失值建议
        for stat in missing_stats:
            if stat.missing_ratio > 0.5:
                suggestions.append(QualitySuggestion(
                    level="error",
                    column=stat.column,
                    issue=f"列 '{stat.column}' 缺失率高达 {stat.missing_ratio*100:.1f}%",
                    suggestion="建议删除此列，或使用领域知识进行填充",
                    auto_fixable=True
                ))
            elif stat.missing_ratio > 0.1:
                suggestions.append(QualitySuggestion(
                    level="warning",
                    column=stat.column,
                    issue=f"列 '{stat.column}' 缺失率为 {stat.missing_ratio*100:.1f}%",
                    suggestion="建议使用均值/中位数填充或前向填充",
                    auto_fixable=True
                ))
            elif stat.missing_ratio > 0:
                suggestions.append(QualitySuggestion(
                    level="info",
                    column=stat.column,
                    issue=f"列 '{stat.column}' 有少量缺失值 ({stat.missing_count} 个)",
                    suggestion="可使用插值或前向填充处理",
                    auto_fixable=True
                ))
        
        # 异常值建议
        for stat in outlier_stats:
            if stat.outlier_ratio > 0.1:
                suggestions.append(QualitySuggestion(
                    level="warning",
                    column=stat.column,
                    issue=f"列 '{stat.column}' 异常值比例较高 ({stat.outlier_ratio*100:.1f}%)",
                    suggestion="建议检查数据来源，或使用裁剪/替换处理",
                    auto_fixable=True
                ))
            elif stat.outlier_ratio > 0.01:
                suggestions.append(QualitySuggestion(
                    level="info",
                    column=stat.column,
                    issue=f"列 '{stat.column}' 检测到 {stat.outlier_count} 个异常值",
                    suggestion="可使用 IQR 裁剪或替换为边界值",
                    auto_fixable=True
                ))
        
        # 重复值建议
        if duplicate_count > 0:
            suggestions.append(QualitySuggestion(
                level="warning" if duplicate_count > len(self.df) * 0.01 else "info",
                column=None,
                issue=f"数据集包含 {duplicate_count} 行重复数据",
                suggestion="建议删除重复行以避免分析偏差",
                auto_fixable=True
            ))
        
        # 时序建议
        if time_analysis:
            if not time_analysis.is_regular:
                suggestions.append(QualitySuggestion(
                    level="warning",
                    column=time_analysis.time_column,
                    issue="时间序列间隔不规则",
                    suggestion="建议进行重采样或插值以获得规则时序",
                    auto_fixable=False
                ))
            if time_analysis.gaps_count > 0:
                suggestions.append(QualitySuggestion(
                    level="info",
                    column=time_analysis.time_column,
                    issue=f"检测到 {time_analysis.gaps_count} 个时间间隔异常",
                    suggestion="可能存在数据缺失，建议检查并填补",
                    auto_fixable=False
                ))
        
        return suggestions
    
    def calculate_quality_score(
        self,
        total_missing_ratio: float,
        total_outlier_ratio: float,
        duplicate_ratio: float,
        time_analysis: Optional[TimeSeriesAnalysis]
    ) -> Tuple[int, str]:
        """
        计算质量评分
        
        评分规则：
        - 基础分 100 分
        - 缺失值扣分：缺失率 * 30
        - 异常值扣分：异常率 * 20
        - 重复值扣分：重复率 * 15
        - 时序不规则扣分：10 分
        """
        score = 100.0
        
        # 缺失值扣分
        score -= total_missing_ratio * 30
        
        # 异常值扣分
        score -= total_outlier_ratio * 20
        
        # 重复值扣分
        score -= duplicate_ratio * 15
        
        # 时序不规则扣分
        if time_analysis and not time_analysis.is_regular:
            score -= 10
        
        # 确保分数在 0-100 之间
        score = max(0, min(100, score))
        final_score = int(round(score))
        
        # 确定等级
        if final_score >= 90:
            level = QualityLevel.EXCELLENT.value
        elif final_score >= 70:
            level = QualityLevel.GOOD.value
        elif final_score >= 50:
            level = QualityLevel.FAIR.value
        else:
            level = QualityLevel.POOR.value
        
        return final_score, level
    
    def generate_report(self, request: QualityCheckRequest = None) -> DataQualityReport:
        """生成完整的质量报告"""
        if request is None:
            request = QualityCheckRequest()
        
        # 分析缺失值
        missing_stats, total_missing, total_missing_ratio = self.analyze_missing()
        
        # 检测异常值
        outlier_stats, total_outliers, total_outlier_ratio = self.detect_outliers(
            method=request.outlier_method,
            params=request.outlier_params,
            columns=request.check_columns
        )
        
        # 分析列类型
        column_types = self.analyze_column_types()
        
        # 计算列统计
        column_stats = self.analyze_column_stats()
        
        # 分析时序特征
        time_analysis = self.analyze_time_series()
        
        # 分析重复值
        duplicate_count, duplicate_ratio = self.analyze_duplicates()
        
        # 计算质量评分
        quality_score, quality_level = self.calculate_quality_score(
            total_missing_ratio,
            total_outlier_ratio,
            duplicate_ratio,
            time_analysis
        )
        
        # 生成建议
        suggestions = []
        if request.include_suggestions:
            suggestions = self.generate_suggestions(
                missing_stats,
                outlier_stats,
                duplicate_count,
                time_analysis
            )
        
        return DataQualityReport(
            dataset_id=self.dataset_id,
            dataset_name=self.dataset_name,
            total_rows=len(self.df),
            total_columns=len(self.df.columns),
            missing_stats=missing_stats,
            total_missing_cells=total_missing,
            total_missing_ratio=total_missing_ratio,
            outlier_method=request.outlier_method,
            outlier_stats=outlier_stats,
            total_outlier_cells=total_outliers,
            total_outlier_ratio=total_outlier_ratio,
            column_types=column_types,
            numeric_columns=self.numeric_columns,
            categorical_columns=self.categorical_columns,
            datetime_columns=self.datetime_columns,
            column_stats=column_stats,
            time_analysis=time_analysis,
            duplicate_rows=duplicate_count,
            duplicate_ratio=duplicate_ratio,
            quality_score=quality_score,
            quality_level=quality_level,
            suggestions=suggestions,
            generated_at=datetime.now()
        )


def analyze_data_quality(
    df: pd.DataFrame,
    dataset_id: int,
    dataset_name: str,
    request: QualityCheckRequest = None
) -> DataQualityReport:
    """
    分析数据质量的便捷函数
    
    Args:
        df: pandas DataFrame
        dataset_id: 数据集 ID
        dataset_name: 数据集名称
        request: 质量检测请求配置
    
    Returns:
        DataQualityReport: 质量报告
    """
    analyzer = QualityAnalyzer(df, dataset_id, dataset_name)
    return analyzer.generate_report(request)

