"""
文件路径安全验证工具
"""
from pathlib import Path
from typing import Union

from app.config import settings


def validate_filepath(filepath: Union[str, Path]) -> bool:
    """
    验证文件路径是否在允许的目录内
    防止路径遍历攻击
    
    Args:
        filepath: 要验证的文件路径
    
    Returns:
        True 如果路径安全，False 否则
    """
    try:
        real_path = os.path.realpath(str(filepath))
        allowed_dirs = [
            os.path.realpath(str(settings.DATASETS_DIR)),
            os.path.realpath(str(settings.RESULTS_DIR)),
            os.path.realpath(str(settings.CACHE_DIR)),
        ]
        return any(real_path.startswith(d) for d in allowed_dirs)
    except Exception:
        return False


def ensure_safe_path(filepath: Union[str, Path], error_message: str = "文件路径不安全") -> str:
    """
    确保文件路径安全，不安全则抛出异常
    
    Args:
        filepath: 要验证的文件路径
        error_message: 错误消息
    
    Returns:
        验证后的路径字符串
    
    Raises:
        ValueError: 如果路径不安全
    """
    if not validate_filepath(filepath):
        raise ValueError(error_message)
    return str(filepath)

