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
    
    使用 Path.resolve() 进行安全校验，
    避免 startswith 的前缀绕过和大小写问题
    
    Args:
        filepath: 要验证的文件路径
    
    Returns:
        True 如果路径安全，False 否则
    """
    try:
        # 解析为绝对路径，消除 .. 等
        resolved_path = Path(filepath).resolve()
        
        # 允许的目录列表
        allowed_dirs = [
            Path(settings.DATASETS_DIR).resolve(),
            Path(settings.RESULTS_DIR).resolve(),
            Path(settings.CACHE_DIR).resolve(),
        ]
        
        # 检查路径是否在允许的目录内
        for allowed_dir in allowed_dirs:
            try:
                # is_relative_to 在 Python 3.9+ 可用
                if hasattr(resolved_path, 'is_relative_to'):
                    if resolved_path.is_relative_to(allowed_dir):
                        return True
                else:
                    # Python 3.8 兼容：使用 relative_to 检查
                    resolved_path.relative_to(allowed_dir)
                    return True
            except ValueError:
                continue
        
        return False
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

