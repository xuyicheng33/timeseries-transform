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

