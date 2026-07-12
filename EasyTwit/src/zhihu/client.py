"""
知乎 API 客户端
使用 Bearer Token 鉴权访问知乎开放平台

热榜: 无需参数
搜索: GET /content/zhihu_search
全网搜索: GET /content/global_search
"""
import time
import requests
from typing import Optional, Dict, Any, List
from loguru import logger

from ..config import config


class ZhihuClient:
    """知乎开放平台客户端"""

    BASE_URL = "https://developer.zhihu.com/api/v1"

    def __init__(self):
        self.token = config.zhihu_access_secret
        if not self.token:
            logger.warning("未配置 ZHIHU_ACCESS_SECRET，知乎数据源不可用")
            self._ready = False
        else:
            self._ready = True
            logger.info("知乎客户端就绪")

    @property
    def ready(self) -> bool:
        return self._ready

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "X-Request-Timestamp": str(int(time.time())),
            "Content-Type": "application/json",
        }

    def _get(self, endpoint: str, params: dict = None, timeout: int = 15) -> Optional[dict]:
        if not self._ready:
            return None
        try:
            r = requests.get(
                f"{self.BASE_URL}/{endpoint}",
                headers=self._headers(),
                params=params,
                timeout=timeout,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"知乎 API 失败 [{endpoint}]: {e}")
            return None

    # ── 热榜 ──────────────────────────────────────────

    def hot_list(self, limit: int = 10) -> List[Dict[str, Any]]:
        """知乎热榜"""
        result = self._get("content/hot_list", params={"Limit": min(limit, 30)})
        if not result:
            return []
        data = result.get("Data", {})
        items = data.get("Items", [])
        return items[:limit] if isinstance(items, list) else []

    # ── 搜索 ──────────────────────────────────────────

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """知乎搜索"""
        result = self._get("content/zhihu_search", params={
            "Query": query, "Count": min(limit, 10),
        })
        if not result:
            return []
        data = result.get("Data", {})
        items = data.get("Items", [])
        return items[:limit] if isinstance(items, list) else []

    # ── 全网搜索 ───────────────────────────────────────

    def global_search(self, query: str, count: int = 10) -> List[Dict[str, Any]]:
        """全网搜索"""
        result = self._get("content/global_search", params={
            "Query": query, "Count": min(count, 20), "SearchDB": "all",
        })
        if not result:
            return []
        data = result.get("Data", {})
        items = data.get("Items", [])
        return items[:count] if isinstance(items, list) else []

    # ── 直答 AI ───────────────────────────────────────
    # 文档: https://developer.zhihu.com/docs?key=zhida

    ZHIDA_URL = "https://developer.zhihu.com/v1/chat/completions"

    def zhida_ask(self, question: str, model: str = "zhida-fast-1p5") -> Optional[str]:
        """知乎直答 AI 问答 (快速/思考/智能)"""
        if not self._ready:
            return None
        try:
            r = requests.post(
                self.ZHIDA_URL,
                headers=self._headers(),
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": question}],
                },
                timeout=60,
            )
            r.raise_for_status()
            data = r.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return None
        except Exception as e:
            logger.warning(f"直答 AI 失败: {e}")
            return None

    # ── 聚合 ──────────────────────────────────────────

    def fetch_context(self, data_sources: List[str], query: str = None,
                      limit: int = 5) -> str:
        """根据 data_sources 拉取数据，返回格式化的上下文字符串"""
        parts = []

        for ds in data_sources:
            # 兼容 dict 格式 {"zhihu_search": "关键词"} 和字符串格式
            if isinstance(ds, dict):
                ds = next(iter(ds.items()))  # ("zhihu_search", "关键词")
                ds = f"{ds[0]}: {ds[1]}"
            ds = ds.strip().lower()
            try:
                if ds == "zhihu_hot":
                    items = self.hot_list(limit=limit)
                    if items:
                        titles = []
                        for it in items:
                            t = it.get("Title", "")
                            if t:
                                titles.append(t)
                        if titles:
                            parts.append("## 知乎热榜\n" + "\n".join(
                                f"- {t}" for t in titles[:limit]))

                elif ds.startswith("zhihu_search:"):
                    q = ds.split(":", 1)[1] or query or "科技"
                    items = self.search(q, limit=limit)
                    if items:
                        contents = []
                        for it in items:
                            title = it.get("Title", "")
                            excerpt = it.get("ContentText", "")[:200]
                            if title:
                                contents.append(f"- **{title}**\n  {excerpt}")
                        if contents:
                            parts.append(f"## 知乎搜索: {q}\n" + "\n".join(contents[:limit]))

                elif ds.startswith("zhihu_global:"):
                    q = ds.split(":", 1)[1] or query or "科技"
                    items = self.global_search(q, count=limit)
                    if items:
                        contents = []
                        for it in items:
                            title = it.get("Title", "")
                            text = it.get("ContentText", "")[:200]
                            if title:
                                contents.append(f"- **{title}**\n  {text}")
                        if contents:
                            parts.append(f"## 全网搜索: {q}\n" + "\n".join(contents[:limit]))
                elif ds.startswith("zhida:"):
                    q = ds.split(":", 1)[1] or query or "最新热点"
                    model = "zhida-fast-1p5"
                    answer = self.zhida_ask(q, model=model)
                    if answer:
                        parts.append(f"## 知乎直答: {q}\n{answer[:500]}")

            except Exception as e:
                logger.warning(f"知乎数据源 {ds} 失败: {e}")

        return "\n\n".join(parts) if parts else ""
