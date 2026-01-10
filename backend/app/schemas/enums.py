"""
枚举类型定义
统一前后端的枚举值，避免不一致
"""
from enum import Enum


class NormalizationType(str, Enum):
    """归一化类型"""
    NONE = "none"
    MINMAX = "minmax"
    ZSCORE = "zscore"
    HEAD = "head"
    DECIMAL = "decimal"
    # 新增归一化方法
    ROBUST = "robust"        # 鲁棒归一化 (使用中位数和IQR，对异常值鲁棒)
    MAXABS = "maxabs"        # 最大绝对值归一化 (除以最大绝对值，保留稀疏性)
    LOG = "log"              # 对数变换 (适合长尾分布)
    LOG1P = "log1p"          # log(1+x) 变换 (处理含零值的数据)
    SQRT = "sqrt"            # 平方根变换 (温和的压缩变换)
    BOXCOX = "boxcox"        # Box-Cox 变换 (自动选择最佳幂次)
    YEOJOHNSON = "yeojohnson"  # Yeo-Johnson 变换 (支持负值的 Box-Cox)
    QUANTILE = "quantile"    # 分位数变换 (映射到均匀/正态分布)
    RANK = "rank"            # 排名变换 (转换为排名百分比)


class TargetType(str, Enum):
    """目标类型"""
    NEXT = "next"
    KSTEP = "kstep"
    RECONSTRUCT = "reconstruct"


class AnomalyType(str, Enum):
    """异常类型"""
    POINT = "point"
    SEGMENT = "segment"
    TREND = "trend"
    SEASONAL = "seasonal"
    NOISE = "noise"


class InjectionAlgorithm(str, Enum):
    """注入算法"""
    RANDOM = "random"
    RULE = "rule"
    PATTERN = "pattern"


class SequenceLogic(str, Enum):
    """序列逻辑"""
    ANOMALY_FIRST = "anomaly_first"
    WINDOW_FIRST = "window_first"


class DownsampleAlgorithm(str, Enum):
    """降采样算法"""
    LTTB = "lttb"
    MINMAX = "minmax"
    AVERAGE = "average"


# ============ 数据质量相关枚举 ============

class OutlierMethod(str, Enum):
    """异常值检测方法"""
    IQR = "iqr"              # 四分位距法 (Q1 - 1.5*IQR, Q3 + 1.5*IQR)
    ZSCORE = "zscore"        # Z-Score 法 (|z| > threshold)
    MAD = "mad"              # 中位数绝对偏差法 (更鲁棒)
    PERCENTILE = "percentile"  # 百分位截断法
    THRESHOLD = "threshold"  # 自定义阈值


class OutlierAction(str, Enum):
    """异常值处理方式"""
    KEEP = "keep"            # 保留不处理
    REMOVE = "remove"        # 删除整行
    CLIP = "clip"            # 裁剪到边界值
    REPLACE_MEAN = "replace_mean"      # 替换为均值
    REPLACE_MEDIAN = "replace_median"  # 替换为中位数
    REPLACE_NAN = "replace_nan"        # 替换为 NaN


class MissingStrategy(str, Enum):
    """缺失值处理策略"""
    KEEP = "keep"            # 保留不处理
    DROP_ROW = "drop_row"    # 删除包含缺失值的行
    DROP_COLUMN = "drop_column"  # 删除缺失率过高的列
    FILL_MEAN = "fill_mean"  # 均值填充
    FILL_MEDIAN = "fill_median"  # 中位数填充
    FILL_MODE = "fill_mode"  # 众数填充
    FILL_FORWARD = "fill_forward"  # 前向填充
    FILL_BACKWARD = "fill_backward"  # 后向填充
    FILL_LINEAR = "fill_linear"  # 线性插值
    FILL_VALUE = "fill_value"  # 自定义值填充


class QualityLevel(str, Enum):
    """数据质量等级"""
    EXCELLENT = "excellent"  # 优秀 (90-100)
    GOOD = "good"            # 良好 (70-89)
    FAIR = "fair"            # 一般 (50-69)
    POOR = "poor"            # 较差 (0-49)


class ColumnDataType(str, Enum):
    """列数据类型"""
    NUMERIC = "numeric"      # 数值型
    INTEGER = "integer"      # 整数型
    FLOAT = "float"          # 浮点型
    DATETIME = "datetime"    # 日期时间
    CATEGORICAL = "categorical"  # 分类型
    TEXT = "text"            # 文本型
    BOOLEAN = "boolean"      # 布尔型
    UNKNOWN = "unknown"      # 未知
