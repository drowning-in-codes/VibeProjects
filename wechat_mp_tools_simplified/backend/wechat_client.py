import json
import re
import threading
from pathlib import Path
from typing import Any

from .models import Account, Article

try:
    from playwright.sync_api import BrowserContext, Page, sync_playwright
except ImportError:  # pragma: no cover - exercised before dependency installation
    BrowserContext = Any
    Page = Any
    sync_playwright = None


OFFICIAL_ORIGIN = "https://mp.weixin.qq.com"
FAKEID_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{1,128}$")


class WeChatClientError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class WeChatClient:
    """Owns one persistent, user-visible browser context for official-page requests."""

    def __init__(self, profile_dir: Path):
        self.profile_dir = profile_dir
        self._playwright = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._lock = threading.RLock()

    def open_login_page(self) -> dict:
        with self._lock:
            page = self._ensure_page()
            page.goto(OFFICIAL_ORIGIN, wait_until="domcontentloaded")
            return {"connected": True, "url": page.url}

    def status(self) -> dict:
        with self._lock:
            if self._page and not self._page.is_closed():
                return {"connected": True, "url": self._page.url}
            return {"connected": False, "url": ""}

    def search_accounts(self, query: str) -> list[Account]:
        if not query or len(query) > 80:
            raise WeChatClientError("INPUT", "请输入 1–80 个字符的公众号名称或关键词。")
        payload = self._request_json(
            "/cgi-bin/searchbiz",
            {"action": "search_biz", "query": query, "begin": 0, "count": 10},
        )
        raw_items = payload.get("list") or payload.get("data", {}).get("list")
        if not isinstance(raw_items, list):
            raise WeChatClientError("DATA", "公众号搜索返回了无法识别的数据。")
        return [account for account in (self._account(item) for item in raw_items) if account]

    def list_articles(self, account: Account, offset: int = 0) -> dict:
        if not FAKEID_PATTERN.fullmatch(account.fakeid):
            raise WeChatClientError("INPUT", "无效的公众号标识。")
        if offset < 0 or offset > 100000:
            raise WeChatClientError("INPUT", "无效的文章分页位置。")
        payload = self._request_json(
            "/cgi-bin/appmsgpublish",
            {
                "sub": "list",
                "search_field": 7,
                "begin": offset,
                "count": 10,
                "fakeid": account.fakeid,
                "type": "101_1",
                "query": "",
            },
        )
        page = self._json_value(payload.get("publish_page") or payload.get("data", {}).get("publish_page"))
        if not isinstance(page, dict) or not isinstance(page.get("publish_list"), list):
            raise WeChatClientError("DATA", "公众号文章接口结构已变化，暂时无法读取文章。")

        articles = []
        for entry in page["publish_list"]:
            publish_info = entry.get("publish_info") if isinstance(entry, dict) else None
            if isinstance(publish_info, dict):
                normalized = self._article(publish_info, account)
                if normalized:
                    articles.append(normalized)
                for item in publish_info.get("multi_appmsg_item_list") or []:
                    normalized = self._article(item, account)
                    if normalized:
                        articles.append(normalized)
        consumed = len(page["publish_list"])
        next_offset = offset + consumed if consumed and articles else None
        return {"articles": [article.__dict__ for article in articles], "nextOffset": next_offset}

    def close(self) -> None:
        with self._lock:
            if self._context:
                self._context.close()
            if self._playwright:
                self._playwright.stop()
            self._context = None
            self._playwright = None
            self._page = None

    def _ensure_context(self) -> BrowserContext:
        if sync_playwright is None:
            raise WeChatClientError(
                "DEPENDENCY",
                "缺少 Playwright，请先安装 requirements.txt 并执行 playwright install chromium。",
            )
        if self._context:
            return self._context
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            str(self.profile_dir),
            headless=False,
            viewport={"width": 1440, "height": 900},
        )
        return self._context

    def _ensure_page(self) -> Page:
        context = self._ensure_context()
        if self._page and not self._page.is_closed():
            return self._page
        self._page = context.pages[0] if context.pages else context.new_page()
        return self._page

    def _request_json(self, path: str, params: dict[str, Any]) -> dict:
        with self._lock:
            page = self._ensure_page()
            if "mp.weixin.qq.com" not in page.url:
                page.goto(OFFICIAL_ORIGIN, wait_until="domcontentloaded")
            result = page.evaluate(
                """
                async ({path, params}) => {
                  const url = new URL(path, location.origin);
                  for (const [key, value] of Object.entries(params)) {
                    url.searchParams.set(key, String(value));
                  }
                  const response = await fetch(url, {
                    credentials: "include",
                    headers: {Accept: "application/json, text/plain, */*"}
                  });
                  const text = await response.text();
                  let payload;
                  try { payload = JSON.parse(text); } catch { return {parseError: true, status: response.status}; }
                  return {ok: response.ok, status: response.status, payload};
                }
                """,
                {"path": path, "params": params},
            )
        if result.get("parseError"):
            raise WeChatClientError("DATA", "公众号后台返回了无法识别的数据。")
        if result.get("status") in (401, 403):
            raise WeChatClientError("AUTH", "公众号后台登录已失效，请在打开的微信页面中重新登录。")
        if not result.get("ok"):
            raise WeChatClientError("HTTP", f"公众号后台接口返回 {result.get('status')}。")
        payload = result.get("payload")
        if not isinstance(payload, dict):
            raise WeChatClientError("DATA", "公众号后台没有返回有效数据。")
        base = payload.get("base_resp") or {}
        if base.get("ret") not in (None, 0, "0"):
            detail = json.dumps(base, ensure_ascii=False)
            if re.search(r"频繁|frequency|too many", detail, re.I):
                raise WeChatClientError("RATE_LIMIT", "公众号后台请求过于频繁，请稍后重试。")
            raise WeChatClientError("API", "公众号后台暂时无法返回数据，请稍后重试。")
        return payload

    @staticmethod
    def _account(item: Any) -> Account | None:
        if not isinstance(item, dict):
            return None
        fakeid = str(item.get("fakeid") or item.get("fakeId") or item.get("user_name") or "").strip()
        if not FAKEID_PATTERN.fullmatch(fakeid):
            return None
        return Account(
            fakeid=fakeid,
            nickname=str(item.get("nickname") or item.get("nick_name") or "未命名公众号").strip(),
            alias=str(item.get("alias") or item.get("username") or "").strip(),
            avatar=WeChatClient._https_url(item.get("round_head_img") or item.get("head_img") or item.get("avatar")),
            signature=str(item.get("signature") or item.get("desc") or "").strip(),
        )

    @staticmethod
    def _article(item: Any, account: Account) -> Article | None:
        if not isinstance(item, dict):
            return None
        title = str(item.get("title") or item.get("name") or "").strip()
        url = WeChatClient._official_url(item.get("link") or item.get("content_url") or item.get("url"))
        if not title or not url:
            return None
        article_id = str(item.get("appmsgid") or item.get("fileid") or item.get("id") or url)
        return Article(
            article_id=article_id,
            account_id=account.fakeid,
            account_name=account.nickname,
            title=title,
            summary=str(item.get("digest") or item.get("summary") or "").strip(),
            published_at=int(item.get("update_time") or item.get("create_time") or 0),
            cover=WeChatClient._https_url(item.get("cover")),
            url=url,
        )

    @staticmethod
    def _json_value(value: Any) -> Any:
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def _https_url(value: Any) -> str:
        return value if isinstance(value, str) and value.startswith("https://") else ""

    @staticmethod
    def _official_url(value: Any) -> str:
        if not isinstance(value, str) or not value.startswith("https://mp.weixin.qq.com/"):
            return ""
        return value
