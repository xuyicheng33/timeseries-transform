"""
数据清洗服务

提供缺失值处理、异常值处理、重复值删除等数据清洗功能
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from copy import deepcopy

from app.schemas import (
    CleaningConfig,
    CleaningPreviewResponse,
    CleaningPreviewRow,
    CleaningPreviewStats,
    CleaningResult,
)
from app.schemas.enums import MissingStrategy, OutlierAction, OutlierMethod
from app.services.quality import QualityAnalyzer


class DataCleaner:
    """数据清洗器"""
    
    def __init__(self, df: pd.DataFrame):
        self.original_df = df.copy()
        self.df = df.copy()
        self.changes: List[CleaningPreviewRow] = []
        self.stats: Dict[str, CleaningPreviewStats] = {}
        
        # 识别数值列
        self.numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
    
    def _get_outlier_bounds(
        self, 
        series: pd.Series, 
        method: str, 
        params: Dict[str, Any]
    ) -> Tuple[float, float]:
        """计算异常值边界"""
        series = series.dropna()
        
        if len(series) == 0:
            return float('-inf'), float('inf')
        
        if method == "iqr":
            multiplier = params.get("multiplier", 1.5)
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - multiplier * iqr
            upper = q3 + multiplier * iqr
            return float(lower), float(upper)
        
        elif method == "zscore":
            threshold = params.get("threshold", 3.0)
            mean = series.mean()
            std = series.std()
            if std == 0:
                return float('-inf'), float('inf')
            lower = mean - threshold * std
            upper = mean + threshold * std
            return float(lower), float(upper)
        
        elif method == "mad":
            threshold = params.get("threshold", 3.5)
            median = series.median()
            mad = np.median(np.abs(series - median))
            if mad == 0:
                return float('-inf'), float('inf')
            mad_scaled = mad * 1.4826
            lower = median - threshold * mad_scaled
            upper = median + threshold * mad_scaled
            return float(lower), float(upper)
        
        elif method == "percentile":
            lower_pct = params.get("lower", 1)
            upper_pct = params.get("upper", 99)
            lower = series.quantile(lower_pct / 100)
            upper = series.quantile(upper_pct / 100)
            return float(lower), float(upper)
        
        elif method == "threshold":
            lower = params.get("lower", float('-inf'))
            upper = params.get("upper", float('inf'))
            return float(lower), float(upper)
        
        else:
            # 默认 IQR
            return self._get_outlier_bounds(series, "iqr", {"multiplier": 1.5})
    
    def _init_column_stats(self, column: str):
        """初始化列统计"""
        if column not in self.stats:
            original_series = self.original_df[column]
            self.stats[column] = CleaningPreviewStats(
                column=column,
                original_missing=int(original_series.isna().sum()),
                after_missing=int(original_series.isna().sum()),
                original_outliers=0,
                after_outliers=0,
                rows_affected=0
            )
    
    def _record_change(
        self, 
        index: int, 
        column: str, 
        original_value: Any, 
        new_value: Any, 
        action: str
    ):
        """记录变更"""
        # 限制记录数量
        if len(self.changes) < 100:
            # 处理特殊值
            if pd.isna(original_value):
                original_value = None
            elif isinstance(original_value, (np.floating, np.integer)):
                original_value = float(original_value)
            
            if pd.isna(new_value):
                new_value = None
            elif isinstance(new_value, (np.floating, np.integer)):
                new_value = float(new_value)
            
            self.changes.append(CleaningPreviewRow(
                index=int(index),
                column=column,
                original_value=original_value,
                new_value=new_value,
                action=action
            ))
        
        # 更新统计
        self._init_column_stats(column)
        self.stats[column].rows_affected += 1
    
    def handle_missing_values(self, config: CleaningConfig) -> int:
        """
        处理缺失值
        
        Returns:
            处理的单元格数量
        """
        cells_modified = 0
        target_columns = config.target_columns or self.df.columns.tolist()
        
        # 首先处理需要删除的列（缺失率过高）
        columns_to_drop = []
        for col in target_columns:
            if col not in self.df.columns:
                continue
            missing_ratio = self.df[col].isna().sum() / len(self.df)
            if missing_ratio > config.missing_drop_threshold:
                columns_to_drop.append(col)
        
        if columns_to_drop:
            self.df = self.df.drop(columns=columns_to_drop)
            for col in columns_to_drop:
                self._init_column_stats(col)
        
        # 更新目标列（排除已删除的列）
        target_columns = [c for c in target_columns if c in self.df.columns]
        
        strategy = config.missing_strategy
        
        if strategy == MissingStrategy.KEEP.value or strategy == "keep":
            return 0
        
        elif strategy == MissingStrategy.DROP_ROW.value or strategy == "drop_row":
            # 记录将被删除的行
            rows_with_missing = self.df[self.df[target_columns].isna().any(axis=1)].index
            for idx in rows_with_missing[:100]:  # 限制记录数量
                for col in target_columns:
                    if pd.isna(self.df.loc[idx, col]):
                        self._record_change(idx, col, self.df.loc[idx, col], None, "removed")
                        cells_modified += 1
            
            self.df = self.df.dropna(subset=target_columns)
        
        elif strategy in [MissingStrategy.FILL_MEAN.value, "fill_mean"]:
            for col in target_columns:
                if col in self.numeric_columns:
                    mean_val = self.df[col].mean()
                    missing_mask = self.df[col].isna()
                    for idx in self.df[missing_mask].index:
                        self._record_change(idx, col, None, mean_val, "filled")
                        cells_modified += 1
                    self.df[col] = self.df[col].fillna(mean_val)
        
        elif strategy in [MissingStrategy.FILL_MEDIAN.value, "fill_median"]:
            for col in target_columns:
                if col in self.numeric_columns:
                    median_val = self.df[col].median()
                    missing_mask = self.df[col].isna()
                    for idx in self.df[missing_mask].index:
                        self._record_change(idx, col, None, median_val, "filled")
                        cells_modified += 1
                    self.df[col] = self.df[col].fillna(median_val)
        
        elif strategy in [MissingStrategy.FILL_MODE.value, "fill_mode"]:
            for col in target_columns:
                mode_val = self.df[col].mode()
                if len(mode_val) > 0:
                    mode_val = mode_val.iloc[0]
                    missing_mask = self.df[col].isna()
                    for idx in self.df[missing_mask].index:
                        self._record_change(idx, col, None, mode_val, "filled")
                        cells_modified += 1
                    self.df[col] = self.df[col].fillna(mode_val)
        
        elif strategy in [MissingStrategy.FILL_FORWARD.value, "fill_forward"]:
            for col in target_columns:
                missing_before = self.df[col].isna()
                self.df[col] = self.df[col].ffill()
                missing_after = self.df[col].isna()
                filled_mask = missing_before & ~missing_after
                for idx in self.df[filled_mask].index:
                    self._record_change(idx, col, None, self.df.loc[idx, col], "filled")
                    cells_modified += 1
        
        elif strategy in [MissingStrategy.FILL_BACKWARD.value, "fill_backward"]:
            for col in target_columns:
                missing_before = self.df[col].isna()
                self.df[col] = self.df[col].bfill()
                missing_after = self.df[col].isna()
                filled_mask = missing_before & ~missing_after
                for idx in self.df[filled_mask].index:
                    self._record_change(idx, col, None, self.df.loc[idx, col], "filled")
                    cells_modified += 1
        
        elif strategy in [MissingStrategy.FILL_LINEAR.value, "fill_linear"]:
            for col in target_columns:
                if col in self.numeric_columns:
                    missing_before = self.df[col].isna()
                    self.df[col] = self.df[col].interpolate(method='linear')
                    missing_after = self.df[col].isna()
                    filled_mask = missing_before & ~missing_after
                    for idx in self.df[filled_mask].index:
                        self._record_change(idx, col, None, self.df.loc[idx, col], "filled")
                        cells_modified += 1
        
        elif strategy in [MissingStrategy.FILL_VALUE.value, "fill_value"]:
            fill_value = config.missing_fill_value
            if fill_value is not None:
                for col in target_columns:
                    missing_mask = self.df[col].isna()
                    for idx in self.df[missing_mask].index:
                        self._record_change(idx, col, None, fill_value, "filled")
                        cells_modified += 1
                    self.df[col] = self.df[col].fillna(fill_value)
        
        # 更新统计中的 after_missing
        for col in target_columns:
            if col in self.stats:
                self.stats[col].after_missing = int(self.df[col].isna().sum()) if col in self.df.columns else 0
        
        return cells_modified
    
    def handle_outliers(self, config: CleaningConfig) -> int:
        """
        处理异常值
        
        Returns:
            处理的单元格数量
        """
        cells_modified = 0
        action = config.outlier_action
        
        if action == OutlierAction.KEEP.value or action == "keep":
            return 0
        
        target_columns = config.target_columns or self.numeric_columns
        target_columns = [c for c in target_columns if c in self.df.columns and c in self.numeric_columns]
        
        for col in target_columns:
            series = pd.to_numeric(self.df[col], errors='coerce')
            lower_bound, upper_bound = self._get_outlier_bounds(
                series, 
                config.outlier_method, 
                config.outlier_params
            )
            
            # 找出异常值
            outlier_mask = (series < lower_bound) | (series > upper_bound)
            outlier_indices = self.df[outlier_mask].index
            
            # 初始化统计
            self._init_column_stats(col)
            self.stats[col].original_outliers = int(outlier_mask.sum())
            
            if action in [OutlierAction.REMOVE.value, "remove"]:
                # 删除包含异常值的行
                for idx in outlier_indices:
                    self._record_change(idx, col, self.df.loc[idx, col], None, "removed")
                    cells_modified += 1
                self.df = self.df[~outlier_mask]
            
            elif action in [OutlierAction.CLIP.value, "clip"]:
                # 裁剪到边界值
                for idx in outlier_indices:
                    original_val = self.df.loc[idx, col]
                    if series.loc[idx] < lower_bound:
                        new_val = lower_bound
                    else:
                        new_val = upper_bound
                    self._record_change(idx, col, original_val, new_val, "clipped")
                    cells_modified += 1
                self.df[col] = series.clip(lower=lower_bound, upper=upper_bound)
            
            elif action in [OutlierAction.REPLACE_MEAN.value, "replace_mean"]:
                # 替换为均值（排除异常值后的均值）
                clean_mean = series[~outlier_mask].mean()
                for idx in outlier_indices:
                    self._record_change(idx, col, self.df.loc[idx, col], clean_mean, "replaced")
                    cells_modified += 1
                self.df.loc[outlier_mask, col] = clean_mean
            
            elif action in [OutlierAction.REPLACE_MEDIAN.value, "replace_median"]:
                # 替换为中位数
                clean_median = series[~outlier_mask].median()
                for idx in outlier_indices:
                    self._record_change(idx, col, self.df.loc[idx, col], clean_median, "replaced")
                    cells_modified += 1
                self.df.loc[outlier_mask, col] = clean_median
            
            elif action in [OutlierAction.REPLACE_NAN.value, "replace_nan"]:
                # 替换为 NaN
                for idx in outlier_indices:
                    self._record_change(idx, col, self.df.loc[idx, col], None, "replaced")
                    cells_modified += 1
                self.df.loc[outlier_mask, col] = np.nan
            
            # 更新统计
            new_series = pd.to_numeric(self.df[col], errors='coerce') if col in self.df.columns else pd.Series()
            if len(new_series) > 0:
                new_outlier_mask = (new_series < lower_bound) | (new_series > upper_bound)
                self.stats[col].after_outliers = int(new_outlier_mask.sum())
            else:
                self.stats[col].after_outliers = 0
        
        return cells_modified
    
    def handle_duplicates(self, config: CleaningConfig) -> int:
        """
        处理重复值
        
        Returns:
            删除的行数
        """
        if not config.drop_duplicates:
            return 0
        
        rows_before = len(self.df)
        
        # 记录重复行
        duplicate_mask = self.df.duplicated(keep=config.duplicate_keep if config.duplicate_keep != "none" else False)
        duplicate_indices = self.df[duplicate_mask].index
        
        for idx in duplicate_indices[:100]:  # 限制记录数量
            self._record_change(idx, "__row__", "duplicate", None, "removed")
        
        # 删除重复行
        if config.duplicate_keep == "none":
            self.df = self.df.drop_duplicates(keep=False)
        else:
            self.df = self.df.drop_duplicates(keep=config.duplicate_keep)
        
        rows_removed = rows_before - len(self.df)
        return rows_removed
    
    def apply_column_configs(self, config: CleaningConfig) -> int:
        """
        应用列特定配置
        
        Returns:
            处理的单元格数量
        """
        cells_modified = 0
        
        for col_config in config.column_configs:
            col = col_config.column
            if col not in self.df.columns:
                continue
            
            # 处理缺失值
            if col_config.missing_strategy:
                strategy = col_config.missing_strategy
                missing_mask = self.df[col].isna()
                
                if strategy == "fill_mean" and col in self.numeric_columns:
                    fill_val = self.df[col].mean()
                    for idx in self.df[missing_mask].index:
                        self._record_change(idx, col, None, fill_val, "filled")
                        cells_modified += 1
                    self.df[col] = self.df[col].fillna(fill_val)
                
                elif strategy == "fill_median" and col in self.numeric_columns:
                    fill_val = self.df[col].median()
                    for idx in self.df[missing_mask].index:
                        self._record_change(idx, col, None, fill_val, "filled")
                        cells_modified += 1
                    self.df[col] = self.df[col].fillna(fill_val)
                
                elif strategy == "fill_value" and col_config.missing_fill_value is not None:
                    fill_val = col_config.missing_fill_value
                    for idx in self.df[missing_mask].index:
                        self._record_change(idx, col, None, fill_val, "filled")
                        cells_modified += 1
                    self.df[col] = self.df[col].fillna(fill_val)
            
            # 处理异常值（使用自定义边界）
            if col_config.outlier_action and col in self.numeric_columns:
                action = col_config.outlier_action
                lower = col_config.outlier_clip_lower
                upper = col_config.outlier_clip_upper
                
                if lower is not None or upper is not None:
                    series = pd.to_numeric(self.df[col], errors='coerce')
                    
                    if action == "clip":
                        outlier_mask = pd.Series(False, index=self.df.index)
                        if lower is not None:
                            outlier_mask |= (series < lower)
                        if upper is not None:
                            outlier_mask |= (series > upper)
                        
                        for idx in self.df[outlier_mask].index:
                            original_val = self.df.loc[idx, col]
                            new_val = np.clip(original_val, lower, upper)
                            self._record_change(idx, col, original_val, new_val, "clipped")
                            cells_modified += 1
                        
                        self.df[col] = series.clip(lower=lower, upper=upper)
        
        return cells_modified
    
    def clean(self, config: CleaningConfig) -> Tuple[pd.DataFrame, int]:
        """
        执行完整的清洗流程
        
        Returns:
            (清洗后的 DataFrame, 修改的单元格数量)
        """
        total_modified = 0
        
        # 1. 处理缺失值
        total_modified += self.handle_missing_values(config)
        
        # 2. 处理异常值
        total_modified += self.handle_outliers(config)
        
        # 3. 处理重复值
        total_modified += self.handle_duplicates(config)
        
        # 4. 应用列特定配置
        total_modified += self.apply_column_configs(config)
        
        return self.df, total_modified
    
    def preview(self, config: CleaningConfig) -> CleaningPreviewResponse:
        """
        预览清洗效果（不修改原数据）
        
        Returns:
            CleaningPreviewResponse: 预览结果
        """
        # 执行清洗
        cleaned_df, cells_modified = self.clean(config)
        
        # 计算删除的列
        columns_removed = [c for c in self.original_df.columns if c not in cleaned_df.columns]
        
        # 计算质量评分
        from app.services.quality import QualityAnalyzer
        
        # 原始质量评分
        original_analyzer = QualityAnalyzer(self.original_df, 0, "original")
        _, original_missing_ratio = original_analyzer.analyze_missing()[1:3]
        _, original_outlier_ratio = original_analyzer.detect_outliers(
            method=config.outlier_method,
            params=config.outlier_params
        )[1:3]
        original_dup_ratio = original_analyzer.analyze_duplicates()[1]
        original_score, _ = original_analyzer.calculate_quality_score(
            original_missing_ratio, original_outlier_ratio, original_dup_ratio, None
        )
        
        # 清洗后质量评分
        if len(cleaned_df) > 0:
            cleaned_analyzer = QualityAnalyzer(cleaned_df, 0, "cleaned")
            _, cleaned_missing_ratio = cleaned_analyzer.analyze_missing()[1:3]
            _, cleaned_outlier_ratio = cleaned_analyzer.detect_outliers(
                method=config.outlier_method,
                params=config.outlier_params
            )[1:3]
            cleaned_dup_ratio = cleaned_analyzer.analyze_duplicates()[1]
            cleaned_score, _ = cleaned_analyzer.calculate_quality_score(
                cleaned_missing_ratio, cleaned_outlier_ratio, cleaned_dup_ratio, None
            )
        else:
            cleaned_score = 0
        
        return CleaningPreviewResponse(
            preview_changes=self.changes[:100],
            stats=list(self.stats.values()),
            total_rows_before=len(self.original_df),
            total_rows_after=len(cleaned_df),
            rows_removed=len(self.original_df) - len(cleaned_df),
            cells_modified=cells_modified,
            columns_removed=columns_removed,
            quality_score_before=original_score,
            quality_score_after=cleaned_score
        )


def preview_cleaning(df: pd.DataFrame, config: CleaningConfig) -> CleaningPreviewResponse:
    """
    预览数据清洗效果
    
    Args:
        df: 原始 DataFrame
        config: 清洗配置
    
    Returns:
        CleaningPreviewResponse: 预览结果
    """
    cleaner = DataCleaner(df)
    return cleaner.preview(config)


def apply_cleaning(df: pd.DataFrame, config: CleaningConfig) -> Tuple[pd.DataFrame, int]:
    """
    应用数据清洗
    
    Args:
        df: 原始 DataFrame
        config: 清洗配置
    
    Returns:
        (清洗后的 DataFrame, 修改的单元格数量)
    """
    cleaner = DataCleaner(df)
    return cleaner.clean(config)

