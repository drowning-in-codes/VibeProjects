const WEREAD_ORIGIN = "https://weread.qq.com";
const MP_BOOK_PREFIX = "MP_WXS_";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !["getPublications", "getArticles"].includes(message.type)) {
    return;
  }

  handleMessage(message, sender)
    .then((data) => sendResponse({ ok: true, data }))
    .catch((error) => sendResponse({ ok: false, error: serializeError(error) }));

  return true;
});

async function handleMessage(message, sender) {
  if (message.type === "getPublications") {
    const payload = await requestWeread("/web/shelf/sync", { userVid: "", synckey: 0 }, sender);
    return normalizePublications(payload);
  }

  return getArticles(message.bookId, message.offset, sender);
}

async function requestWeread(path, params = {}, sender) {
  const tabId = await findWereadTab(sender);
  if (tabId) {
    return requestFromWereadPage(tabId, path, params);
  }

  throw new WereadError(
    "AUTH",
    "请先打开微信读书网页并完成登录，然后返回此页面重试。"
  );
}

async function findWereadTab(sender) {
  let senderHost = "";
  try {
    senderHost = sender?.tab?.url ? new URL(sender.tab.url).hostname : "";
  } catch {
    senderHost = "";
  }
  if (sender?.tab?.id && senderHost === "weread.qq.com") {
    return sender.tab.id;
  }

  const tabs = await chrome.tabs.query({ url: "https://weread.qq.com/*" });
  return tabs[0]?.id;
}

async function requestFromWereadPage(tabId, path, params) {
  let execution;
  try {
    execution = await chrome.scripting.executeScript({
      target: { tabId },
      world: "MAIN",
      func: fetchFromWereadPage,
      args: [path, params]
    });
  } catch (cause) {
    throw new WereadError(
      "NETWORK",
      "无法访问微信读书页面。请刷新微信读书网页后重试。",
      cause
    );
  }

  const result = execution[0]?.result;
  if (!result) {
    throw new WereadError("DATA", "微信读书没有返回有效数据。");
  }

  if (result.status === 401 || result.status === 403) {
    throw new WereadError("AUTH", "微信读书登录已失效，请打开微信读书网页重新扫码登录。");
  }
  if (!result.ok) {
    throw new WereadError("HTTP", `微信读书接口返回 ${result.status}。`);
  }
  if (result.parseError) {
    throw new WereadError("DATA", "微信读书返回了无法识别的数据。");
  }

  const payload = result.payload;

  const apiError = payload?.errCode ?? payload?.errcode;
  if (apiError && apiError !== 0) {
    const detail = payload.errMsg ?? payload.errmsg ?? "";
    const isAuthError = /用户不存在|登录|token|过期/i.test(detail);
    throw new WereadError(
      isAuthError ? "AUTH" : "API",
      isAuthError ? "微信读书登录已失效，请重新扫码登录。" : `微信读书接口错误：${detail || apiError}`
    );
  }

  return payload;
}

function normalizePublications(payload) {
  const books = Array.isArray(payload?.books) ? payload.books : [];
  return books
    .filter((book) => typeof book.bookId === "string" && book.bookId.startsWith(MP_BOOK_PREFIX))
    .map((book) => ({
      id: book.bookId,
      title: stringValue(book.title, "未命名公众号"),
      author: stringValue(book.author, "")
    }))
    .sort((left, right) => left.title.localeCompare(right.title, "zh-CN"));
}

async function getArticles(bookId, offset = 0, sender) {
  if (typeof bookId !== "string" || !bookId.startsWith(MP_BOOK_PREFIX)) {
    throw new WereadError("INPUT", "无效的公众号标识。");
  }
  if (!Number.isInteger(offset) || offset < 0) {
    throw new WereadError("INPUT", "无效的文章分页位置。");
  }

  const payload = await requestWeread("/web/mp/articles", { bookId, offset }, sender);
  const reviews = Array.isArray(payload?.reviews) ? payload.reviews : [];
  const articles = reviews.flatMap((review) =>
    (Array.isArray(review?.subReviews) ? review.subReviews : [])
      .map((subReview) => normalizeArticle(subReview?.review?.mpInfo))
      .filter(Boolean)
  );

  const timestamps = reviews
    .map((review) => Number(review?.createTime))
    .filter((timestamp) => Number.isFinite(timestamp) && timestamp > 0);

  return {
    articles,
    nextOffset: payload?.clearAll || timestamps.length === 0 ? null : Math.min(...timestamps)
  };
}

function normalizeArticle(info) {
  if (!info || !info.title) {
    return null;
  }

  const originalId = stringValue(info.originalId, "");
  return {
    id: originalId || `${info.title}-${info.time ?? ""}`,
    title: stringValue(info.title, "未命名文章"),
    summary: stringValue(info.content, ""),
    publicationName: stringValue(info.mp_name, ""),
    publishedAt: Number(info.time) || 0,
    readCount: Number(info.readNum) || 0,
    likeCount: Number(info.likeNum) || 0,
    url: originalId ? `https://mp.weixin.qq.com/s/${encodeURIComponent(originalId)}` : ""
  };
}

function stringValue(value, fallback) {
  return typeof value === "string" ? value : fallback;
}

function serializeError(error) {
  return {
    code: error?.code ?? "UNKNOWN",
    message: error?.message ?? "发生未知错误，请稍后重试。"
  };
}

async function fetchFromWereadPage(path, params) {
  const url = new URL(path, location.origin);
  for (const [key, value] of Object.entries(params)) {
    url.searchParams.set(key, String(value));
  }

  try {
    const response = await fetch(url, {
      credentials: "include",
      headers: { Accept: "application/json, text/plain, */*" }
    });
    const payload = await response.json();
    return { ok: response.ok, status: response.status, payload };
  } catch {
    return { ok: false, status: 0, parseError: true };
  }
}

class WereadError extends Error {
  constructor(code, message, cause) {
    super(message, { cause });
    this.code = code;
  }
}
