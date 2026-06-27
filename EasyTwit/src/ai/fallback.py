"""
API 主备切换工具
主 API 失败时自动尝试备用 API
"""
from typing import Optional, Callable, TypeVar
from loguru import logger

T = TypeVar('T')


async def try_with_fallback(
    primary_fn: Callable[[], T],
    backup_fn: Optional[Callable[[], T]] = None,
    label: str = "API",
    raise_on_all_fail: bool = True,
) -> T:
    """主备切换调用模式

    先尝试主 API，失败后自动切换到备用 API。

    Args:
        primary_fn: 主 API 调用函数
        backup_fn: 备用 API 调用函数（None 则无备用）
        label: 日志标签
        raise_on_all_fail: 全部失败时是否抛异常（False 则返回 None）

    Returns:
        API 调用结果

    Raises:
        Exception: raise_on_all_fail=True 且全部尝试失败时
    """
    # 尝试主 API
    try:
        result = primary_fn()
        return result
    except Exception as e:
        logger.warning(f"[{label}] 主 API 失败: {e}")

    # 尝试备用 API
    if backup_fn is not None:
        try:
            logger.info(f"[{label}] 切换到备用 API...")
            result = backup_fn()
            logger.success(f"[{label}] 备用 API 调用成功")
            return result
        except Exception as e:
            logger.error(f"[{label}] 备用 API 也失败: {e}")
    else:
        logger.warning(f"[{label}] 未配置备用 API")

    if raise_on_all_fail:
        raise RuntimeError(f"[{label}] 所有 API 尝试均失败")
    return None
