"""
知乎 API 客户端
使用 Bearer Token (Access Secret) 鉴权访问知乎开放平台 API

文档: https://developer.zhihu.com/docs
"""

import time
import json
import requests
from typing import Optional, Dict, Any, List, Iterator
from loguru import logger
from ..config import config


# ═══════════════════════════════════════════════════════════════
# 知乎搜索 API 客户端
# ═══════════════════════════════════════════════════════════════

class ZhihuAPIClient:
    """知乎开放平台搜索 API 客户端

    鉴权方式:
        - Authorization: Bearer <access_secret>
        - X-Request-Timestamp: 秒级 Unix 时间戳
    """

    BASE_URL = "https://developer.zhihu.com/api/v1"

    def __init__(self, access_secret: str):
        """
        初始化知乎 API 客户端

        Args:
            access_secret: 知乎开放平台 Access Secret (Bearer Token)
        """
        self.access_secret = access_secret
        self._proxies = config.get_proxies_dict()

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            "Authorization": f"Bearer {self.access_secret}",
            "X-Request-Timestamp": str(int(time.time())),
            "Content-Type": "application/json",
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        timeout: int = 15,
        json_body: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        发起 API 请求

        Args:
            method: HTTP 方法 (GET/POST)
            endpoint: API 端点路径 (不含 BASE_URL)
            params: 查询参数 (GET)
            timeout: 超时秒数
            json_body: JSON 请求体 (POST)

        Returns:
            响应 JSON 数据，失败返回 None
        """
        url = f"{self.BASE_URL}/{endpoint}"
        headers = self._build_headers()

        try:
            response = requests.request(
                method, url, headers=headers, params=params,
                json=json_body, timeout=timeout, proxies=self._proxies,
            )
            response.raise_for_status()
            return response.json()

        except requests.HTTPError as e:
            logger.error(
                f"知乎 API HTTP 错误 [{endpoint}]: {e.response.status_code} - {e.response.text[:300]}"
            )
            return None
        except requests.RequestException as e:
            logger.error(f"知乎 API 请求失败 [{endpoint}]: {str(e)}")
            return None

    # ═══════════════════════════════════════════════════════════════
    # 搜索
    # ═══════════════════════════════════════════════════════════════

    def search(
        self,
        query: str,
        offset: int = 0,
        limit: int = 20,
    ) -> Optional[Dict[str, Any]]:
        """
        知乎搜索

        文档: https://developer.zhihu.com/docs?key=zhihu_search

        Args:
            query: 搜索关键词
            offset: 分页偏移
            limit: 返回数量

        Returns:
            搜索结果，包含 data 数组和 paging 分页信息
        """
        params = {
            "Query": query,
            "Offset": offset,
            "Limit": limit,
        }

        return self._make_request("GET", "content/zhihu_search", params=params)

    def search_all(
        self,
        query: str,
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        搜索并获取全部结果（自动翻页）

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            所有搜索结果项列表
        """
        all_items: List[Dict[str, Any]] = []
        offset = 0
        page_size = 20

        while len(all_items) < max_results:
            result = self.search(query, offset=offset, limit=page_size)
            if not result:
                break

            items = result.get("data", [])
            if not items:
                break

            all_items.extend(items)

            # 检查分页
            paging = result.get("paging", {})
            if not paging.get("is_end", True):
                offset += page_size
            else:
                break

        return all_items[:max_results]

    # ═══════════════════════════════════════════════════════════════
    # 全网搜索
    # ═══════════════════════════════════════════════════════════════

    def global_search(
        self,
        query: str,
        count: int = 10,
        filter_expr: Optional[str] = None,
        search_db: str = "all",
    ) -> Optional[Dict[str, Any]]:
        """
        全网搜索（跨索引库）

        文档: https://developer.zhihu.com/docs

        Args:
            query: 搜索关键词
            count: 请求数量（默认 10，最大 20）
            filter_expr: 高级语法筛选表达式，如 host=="example.com" AND publish_time>=1778494631
            search_db: 索引库选择 — all (全部) / realtime (实时库) / static (静态库)

        Returns:
            { Data: { HasMore: bool, Items: [Item, ...] } }
        """
        params: Dict[str, Any] = {
            "Query": query,
            "Count": min(count, 20),
            "SearchDB": search_db,
        }
        if filter_expr:
            params["Filter"] = filter_expr

        return self._make_request("GET", "content/global_search", params=params)

    def global_search_all(
        self,
        query: str,
        max_results: int = 40,
        filter_expr: Optional[str] = None,
        search_db: str = "all",
    ) -> List[Dict[str, Any]]:
        """
        全网搜索并获取全部结果（自动翻页）

        按发布时间递增偏移实现翻页 — 使用 HasMore 判断是否还有更多数据。

        Args:
            query: 搜索关键词
            max_results: 最大结果数
            filter_expr: 高级语法筛选
            search_db: 索引库选择

        Returns:
            所有 Item 列表
        """
        all_items: List[Dict[str, Any]] = []
        seen_ids: set = set()

        while len(all_items) < max_results:
            result = self.global_search(query, count=20, filter_expr=filter_expr, search_db=search_db)
            if not result:
                break

            data = result.get("Data", {})
            items = data.get("Items", [])
            if not items:
                break

            for item in items:
                cid = item.get("ContentID", "")
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    all_items.append(item)

            if not data.get("HasMore", False):
                break

        return all_items[:max_results]

    # ═══════════════════════════════════════════════════════════════
    # 工具方法
    # ═══════════════════════════════════════════════════════════════

    def check_health(self) -> bool:
        """检测 API 连通性"""
        result = self.search("test", limit=1)
        return result is not None


# ═══════════════════════════════════════════════════════════════
# 知乎直答 API 客户端
# ═══════════════════════════════════════════════════════════════

class ZhihuChatClient:
    """知乎直答 (Chat Completions) API 客户端

    鉴权方式与搜索 API 一致:
        - Authorization: Bearer <access_secret>
        - X-Request-Timestamp: 秒级 Unix 时间戳

    模型档位:
        - zhida-fast-1p5     快速回答
        - zhida-thinking-1p5 深度思考（返回 reasoning_content）
        - zhida-agent        智能思考
    """

    BASE_URL = "https://developer.zhihu.com/v1"

    # 可用模型
    MODELS = {
        "fast": "zhida-fast-1p5",
        "thinking": "zhida-thinking-1p5",
        "agent": "zhida-agent",
    }

    def __init__(self, access_secret: str, model: str = "fast"):
        """
        初始化直答客户端

        Args:
            access_secret: 知乎开放平台 Access Secret
            model: 模型选择 — fast / thinking / agent
        """
        self.access_secret = access_secret
        self.model = self.MODELS.get(model, model)
        self._proxies = config.get_proxies_dict()

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            "Authorization": f"Bearer {self.access_secret}",
            "X-Request-Timestamp": str(int(time.time())),
            "Content-Type": "application/json",
        }

    # ── 非流式 ──────────────────────────────────────────────

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        timeout: int = 60,
    ) -> Optional[Dict[str, Any]]:
        """
        非流式对话（一次性返回完整结果）

        Args:
            messages: 对话消息列表 [{"role": "user", "content": "..."}]
            model: 模型名称，默认使用初始化时的模型
            timeout: 超时秒数（thinking 模型需要更长时间）

        Returns:
            OpenAI-compatible 响应:
            {
              "choices": [{"message": {"role": "assistant", "content": "...",
                         "reasoning_content": "..." (仅 thinking 模型)}}]
            }
        """
        url = f"{self.BASE_URL}/chat/completions"
        headers = self._build_headers()

        body = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
        }

        try:
            response = requests.post(
                url, headers=headers, json=body, timeout=timeout, proxies=self._proxies
            )
            response.raise_for_status()
            return response.json()

        except requests.HTTPError as e:
            logger.error(
                f"直答 API HTTP 错误 [{response.status_code}]: {response.text[:300]}"
            )
            return None
        except requests.RequestException as e:
            logger.error(f"直答 API 请求失败: {str(e)}")
            return None

    # ── 流式 ────────────────────────────────────────────────

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        timeout: int = 120,
    ) -> Iterator[Dict[str, Any]]:
        """
        流式对话（SSE，逐 chunk 返回）

        Args:
            messages: 对话消息列表
            model: 模型名称
            timeout: 超时秒数

        Yields:
            每个 SSE chunk 解析后的字典:
            - content chunk: {"delta": {"content": "..."}}
            - reasoning chunk: {"delta": {"reasoning_content": "..."}}
            - stop chunk: {"delta": {}, "finish_reason": "stop"}
            - error chunk: {"delta": {}, "finish_reason": "error", "error": {...}}
        """
        url = f"{self.BASE_URL}/chat/completions"
        headers = self._build_headers()

        body = {
            "model": model or self.model,
            "messages": messages,
            "stream": True,
        }

        try:
            response = requests.post(
                url, headers=headers, json=body, timeout=timeout, stream=True,
                proxies=self._proxies,
            )
            response.raise_for_status()

            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith(": "):  # 心跳注释
                    continue
                if not line.startswith("data: "):
                    continue

                data_str = line[6:]  # 去掉 "data: " 前缀
                if data_str == "[DONE]":
                    break

                try:
                    chunk = json.loads(data_str)
                    yield chunk
                except json.JSONDecodeError:
                    logger.warning(f"直答流式解析失败: {data_str[:100]}")
                    continue

        except requests.RequestException as e:
            logger.error(f"直答流式 API 请求失败: {str(e)}")

    # ── 便捷方法 ────────────────────────────────────────────

    def ask(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[str]:
        """
        快速提问，返回纯文本回答

        Args:
            prompt: 问题内容
            system_prompt: 系统提示（可选）
            model: 模型名称

        Returns:
            回答文本，失败返回 None
        """
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        result = self.chat(messages, model=model)
        if not result:
            return None

        choices = result.get("choices", [])
        if not choices:
            return None

        message = choices[0].get("message", {})
        return message.get("content", "")

    def ask_with_reasoning(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Optional[Dict[str, str]]:
        """
        使用 thinking 模型提问，返回 reasoning + 回答

        Args:
            prompt: 问题内容
            system_prompt: 系统提示

        Returns:
            {"reasoning": "...", "answer": "..."} 或 None
        """
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        result = self.chat(messages, model=self.MODELS["thinking"])
        if not result:
            return None

        choices = result.get("choices", [])
        if not choices:
            return None

        message = choices[0].get("message", {})
        return {
            "reasoning": message.get("reasoning_content", ""),
            "answer": message.get("content", ""),
        }
