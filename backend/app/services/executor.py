"""
统一的线程池执行器管理
解决各模块分散创建 ThreadPoolExecutor 的问题
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar, Callable, Any

T = TypeVar('T')

# 共享线程池执行器
_executor: ThreadPoolExecutor | None = None


def get_executor() -> ThreadPoolExecutor:
    """获取共享的线程池执行器"""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=8)
    return _executor


def shutdown_executor(wait: bool = True, cancel_futures: bool = False) -> None:
    """关闭线程池执行器"""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=wait, cancel_futures=cancel_futures)
        _executor = None


async def run_in_executor(func: Callable[..., T], *args: Any) -> T:
    """在线程池中运行同步函数"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(get_executor(), func, *args)

