"""
定时调度模块
使用 cron 表达式定时执行任务
"""
import asyncio
from datetime import datetime, timedelta
from typing import Callable, Awaitable
from croniter import croniter
from loguru import logger


class Scheduler:
    """轻量级 cron 调度器"""

    def __init__(self):
        self._running = False
        self._tasks: list[dict] = []

    def add_task(self, name: str, cron_expr: str,
                 callback: Callable[[], Awaitable[None]]):
        self._tasks.append({
            'name': name,
            'cron': cron_expr,
            'callback': callback,
        })
        logger.info(f"调度任务已注册: '{name}' (cron: {cron_expr})")

    def _next_run(self, cron_expr: str) -> datetime:
        """计算下次触发时间"""
        now = datetime.now()
        cron = croniter(cron_expr, now - timedelta(seconds=1))
        return cron.get_next(datetime)

    async def start(self):
        """启动调度器（阻塞运行）"""
        self._running = True
        logger.info(f"调度器启动, 共 {len(self._tasks)} 个任务")

        while self._running:
            # 找到最近的下次触发时间
            next_task = None
            next_time = None

            for task in self._tasks:
                nt = self._next_run(task['cron'])
                if next_time is None or nt < next_time:
                    next_time = nt
                    next_task = task

            if next_task is None:
                await asyncio.sleep(30)
                continue

            # 等待到触发时间
            delay = (next_time - datetime.now()).total_seconds()
            if delay > 0:
                sleep_ms = min(delay, 30)  # 每 30s 检查一次
                await asyncio.sleep(max(sleep_ms, 1))
                continue

            # 触发!
            now = datetime.now()
            logger.info("=" * 50)
            logger.info(f"⏰ 触发: '{next_task['name']}' @ {now.strftime('%H:%M:%S')}")

            try:
                await next_task['callback']()
                logger.info(f"✅ '{next_task['name']}' 完成")
            except Exception as e:
                from .x.client import FatalApiError
                msg = str(e)
                if isinstance(e, FatalApiError) or "403" in msg or "401" in msg:
                    logger.error(f"🛑 致命错误, 停止调度: {msg[:200]}")
                    self._running = False
                    break
                else:
                    logger.error(f"❌ '{next_task['name']}' 失败, 等下次: {msg[:150]}")

            # 短暂间隔, 避免同一分钟多次触发
            await asyncio.sleep(60)

    def stop(self):
        self._running = False
        logger.info("调度器已停止")

    def list_tasks(self):
        lines = []
        for task in self._tasks:
            nt = self._next_run(task['cron'])
            lines.append(
                f"  {task['name']}: cron='{task['cron']}', "
                f"next={nt.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        return "\n".join(lines)
