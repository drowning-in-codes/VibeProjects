"""
定时调度模块
使用 cron 表达式定时执行任务
"""
import asyncio
import time
from datetime import datetime
from typing import Optional, Callable, Awaitable
from croniter import croniter
from loguru import logger


class Scheduler:
    """轻量级 cron 调度器"""

    def __init__(self):
        self._running = False
        self._tasks: list[dict] = []

    def add_task(self, name: str, cron_expr: str,
                 callback: Callable[[], Awaitable[None]]):
        """添加定时任务

        Args:
            name: 任务名称
            cron_expr: cron 表达式（如 "0 */4 * * *"）
            callback: 异步回调函数
        """
        self._tasks.append({
            'name': name,
            'cron': cron_expr,
            'callback': callback,
        })
        logger.info(f"调度任务已注册: '{name}' (cron: {cron_expr})")

    async def start(self):
        """启动调度器（阻塞运行）"""
        self._running = True
        logger.info(f"调度器已启动，共 {len(self._tasks)} 个任务")

        while self._running:
            now = datetime.now()

            for task in self._tasks:
                cron = croniter(task['cron'], now)
                next_time = cron.get_next(datetime)

                # 计算距离下次执行的时间
                delay = (next_time - now).total_seconds()

                if delay <= 1:
                    # 应该触发了
                    logger.info(f"触发任务: '{task['name']}' at {now.strftime('%H:%M:%S')}")
                    try:
                        await task['callback']()
                    except Exception as e:
                        logger.error(f"任务 '{task['name']}' 执行失败: {e}")

                    # 获取下次时间
                    next_next = cron.get_next(datetime)
                    delay = (next_next - datetime.now()).total_seconds()

                # 等待下次检查
                sleep_time = min(delay, 30)  # 最多等 30s，提高精度
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    await asyncio.sleep(1)

    def stop(self):
        """停止调度器"""
        self._running = False
        logger.info("调度器已停止")

    def list_tasks(self):
        """列出所有任务及其下次执行时间"""
        now = datetime.now()
        lines = []
        for task in self._tasks:
            cron = croniter(task['cron'], now)
            next_run = cron.get_next(datetime)
            lines.append(
                f"  {task['name']}: cron='{task['cron']}', next={next_run.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        return "\n".join(lines)
