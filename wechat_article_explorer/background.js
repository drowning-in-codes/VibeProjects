const MP_BOOK_PREFIX = "MP_WXS_";
const WEREAD_ORIGIN = "https://weread.qq.com";
const READER_LOAD_TIMEOUT_MS = 15000;
const OFFICIAL_HOST = "mp.weixin.qq.com";
const OFFICIAL_PAGE_SIZE = 10;

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || ![
    "getPublications", "getArticles", "searchOfficialAccounts",
    "getOfficialAccounts", "getOfficialArticles",
    "getFollowedOfficialAccounts", "setFollowedOfficialAccount"
  ].includes(message.type)) {
    return;
  }

  handleMessage(message, sender)
    .then((data) => sendResponse({ ok: true, data }))
    .catch((error) => sendResponse({ ok: false, error: serializeError(error) }));

  return true;
});

async function handleMessage(message, sender) {
  if (message.type === "getOfficialAccounts") {
    const result = await chrome.storage.local.get("officialAccounts");
    return Array.isArray(result.officialAccounts) ? result.officialAccounts : [];
  }
  if (message.type === "getFollowedOfficialAccounts") {
    const result = await chrome.storage.local.get("followedOfficialAccounts");
    return Array.isArray(result.followedOfficialAccounts) ? result.followedOfficialAccounts : [];
  }
  if (message.type === "setFollowedOfficialAccount") {
    validateFollowedAccountInput(message.account);
    return setFollowedOfficialAccount(message.account, message.followed);
  }
  if (message.type === "searchOfficialAccounts") {
    validateSearchInput(message.query);
    const payload = await requestOfficialPage("/cgi-bin/searchbiz", {
      action: "search_biz", query: message.query, begin: 0, count: OFFICIAL_PAGE_SIZE
    }, sender);
    const accounts = normalizeOfficialAccounts(payload);
    await cacheOfficialAccounts(accounts);
    return accounts;
  }
  if (message.type === "getOfficialArticles") {
    validateOfficialArticleInput(message);
    return getOfficialArticles(message.account, message.offset, sender);
  }
  if (message.type === "getPublications") {
    const payload = await requestWeread("/web/shelf/sync", { userVid: "", synckey: 0 }, sender);
    return normalizePublications(payload);
  }

  function validateSearchInput(query) {
    if (typeof query !== "string" || !query.trim() || query.trim().length > 80) {
      throw new WereadError("INPUT", "请输入 1–80 个字符的公众号名称或关键词。");
    }
  }

  function validateOfficialArticleInput(message) {
    const account = message.account;
    if (!account || typeof account !== "object" ||
        !/^[A-Za-z0-9._~-]{1,128}$/.test(String(account.fakeid || ""))) {
      throw new WereadError("INPUT", "无效的公众号标识。请重新搜索公众号后台。");
    }

    function validateFollowedAccountInput(account) {
      if (!account || typeof account !== "object" ||
          !/^[A-Za-z0-9._~-]{1,128}$/.test(String(account.fakeid || ""))) {
        throw new WereadError("INPUT", "无效的公众号标识。请重新搜索公众号。");
      }
    }
    if (!Number.isInteger(message.offset) || message.offset < 0 || message.offset > 100000) {
      throw new WereadError("INPUT", "无效的文章分页位置。");
    }
  }

  async function requestOfficialPage(path, params, sender) {
    const tabId = sender?.tab?.id;
    if (!tabId || !isOfficialUrl(sender?.tab?.url)) {
      throw new WereadError("AUTH", "请在已登录的 mp.weixin.qq.com 公众号页面中重试。");
    }
    let execution;
    try {
      execution = await chrome.scripting.executeScript({
        target: { tabId }, world: "MAIN", func: fetchOfficialPage, args: [path, params]
      });
    } catch (cause) {
      throw new WereadError("NETWORK", "无法访问公众号后台页面，请刷新页面后重试。", cause);
    }
    const result = execution[0]?.result;
    if (!result) throw new WereadError("DATA", "公众号后台没有返回有效数据。");
    if (result.challenge) throw new WereadError("RISK", "公众号后台要求安全验证，请在官方页面完成验证后再手动重试。");
    if (result.login || result.status === 401 || result.status === 403) {
      throw new WereadError("AUTH", "公众号后台登录已失效，请在官方页面重新登录。");
    }
    if (result.rateLimited) throw new WereadError("RATE_LIMIT", "公众号后台请求过于频繁，请稍后再手动重试。");
    if (result.networkError) throw new WereadError("NETWORK", "公众号后台网络请求失败，请检查网络后重试。");
    if (!result.ok) throw new WereadError("HTTP", `公众号后台接口返回 ${result.status}。`);
    if (result.parseError) throw new WereadError("DATA", "公众号后台返回了无法识别的数据。");
    return result.payload;
  }

  function isOfficialUrl(value) {
    try {
      const url = new URL(value);
      return url.protocol === "https:" && url.hostname === OFFICIAL_HOST;
    } catch { return false; }
  }

  function normalizeOfficialAccounts(payload) {
    if (responseFailed(payload)) {
      throw new WereadError("DATA", "公众号搜索返回了无法识别的数据。");
    }
    const list = Array.isArray(payload?.list) ? payload.list :
      Array.isArray(payload?.data?.list) ? payload.data.list : null;
    if (!list) throw new WereadError("DATA", "公众号搜索返回了无法识别的数据。");
    return list.map((item) => {
      const fakeid = firstIdentifier(item.fakeid, item.fakeId, item.user_name);
      return fakeid ? {
        fakeid,
        nickname: firstString(item.nickname, item.nick_name, "未命名公众号"),
        alias: firstString(item.alias, item.username, ""),
        avatar: safeHttpsUrl(firstString(item.round_head_img, item.head_img, item.avatar, "")),
        signature: firstString(item.signature, item.desc, "")
      } : null;
    }).filter(Boolean);
  }

  async function cacheOfficialAccounts(accounts) {
    const cached = await chrome.storage.local.get("officialAccounts");
    const previous = Array.isArray(cached.officialAccounts) ? cached.officialAccounts : [];
    const merged = [...previous, ...accounts].filter((item) =>
      item && typeof item.fakeid === "string" && item.fakeid
    );
    const unique = [];
    const seen = new Set();
    for (const item of merged) {
      if (seen.has(item.fakeid)) continue;
      seen.add(item.fakeid);
      unique.push(item);
    }
    await chrome.storage.local.set({ officialAccounts: unique.slice(-50) });
  }

  async function setFollowedOfficialAccount(account, followed) {
    const cached = await chrome.storage.local.get("followedOfficialAccounts");
    const previous = Array.isArray(cached.followedOfficialAccounts)
      ? cached.followedOfficialAccounts
      : [];
    const normalized = {
      fakeid: account.fakeid,
      nickname: firstString(account.nickname, "未命名公众号"),
      alias: firstString(account.alias, ""),
      avatar: safeHttpsUrl(firstString(account.avatar, "")),
      signature: firstString(account.signature, "")
    };
    const next = previous.filter((item) => item?.fakeid !== normalized.fakeid);
    if (followed) next.push(normalized);
    const accounts = next.slice(-50);
    await chrome.storage.local.set({ followedOfficialAccounts: accounts });
    return accounts;
  }

  async function getOfficialArticles(account, offset, sender) {
    const cached = await chrome.storage.local.get("officialAccounts");
    const accounts = Array.isArray(cached.officialAccounts) ? cached.officialAccounts : [];
    await chrome.storage.local.set({
      officialAccounts: [...accounts.filter((item) => item.fakeid !== account.fakeid), {
        fakeid: account.fakeid,
        nickname: firstString(account.nickname, "未命名公众号"),
        alias: firstString(account.alias, ""),
        avatar: safeHttpsUrl(firstString(account.avatar, "")),
        signature: firstString(account.signature, "")
      }].slice(-50)
    });
    let payload = await requestOfficialPage("/cgi-bin/appmsgpublish", {
      sub: "list", search_field: 7, begin: offset, count: OFFICIAL_PAGE_SIZE,
      fakeid: account.fakeid, type: "101_1", query: ""
    }, sender);
    let parsed = parsePublishPage(payload);
    if (parsed.unavailable) {
      payload = await requestOfficialPage("/cgi-bin/appmsg", {
        action: "list_ex", begin: offset, count: OFFICIAL_PAGE_SIZE,
        fakeid: account.fakeid, type: 9, query: ""
      }, sender);
      parsed = parseLegacyPage(payload);
    }
    if (parsed.unavailable) throw new WereadError("DATA", "公众号文章接口结构已变化，已停止读取，请稍后在官方页面查看。");
    const articles = parsed.articles.map((item, index) => normalizeOfficialArticle(item, account, index)).filter(Boolean);
    // The endpoint's offset counts publish-list entries, not flattened
    // articles. A multi-article push can therefore produce more than one
    // normalized article while consuming only one server-side record.
    const nextOffset = articles.length && parsed.consumed
      ? offset + parsed.consumed
      : null;
    return { articles, nextOffset, total: parsed.total };
  }

  function responseFailed(payload) {
    const base = payload?.base_resp;
    if (!base) return true;
    if (base.ret !== undefined && Number(base.ret) !== 0) {
      const text = JSON.stringify(base || payload || "");
      if (/频繁|frequency|too many/i.test(text)) throw new WereadError("RATE_LIMIT", "公众号后台请求过于频繁，请稍后再手动重试。");
      if (/登录|token|过期|unauthor/i.test(text)) throw new WereadError("AUTH", "公众号后台登录已失效，请在官方页面重新登录。");
      throw new WereadError("API", "公众号后台接口暂时无法返回数据，请稍后再手动重试。");
    }
    return false;
  }

  function parsePublishPage(payload) {
    if (responseFailed(payload)) return { unavailable: true };
    const page = parseJsonValue(payload.publish_page ?? payload.data?.publish_page);
    if (!page || !Array.isArray(page.publish_list)) return { unavailable: true };
    const articles = [];
    page.publish_list.forEach((entry) => {
      if (entry.publish_info) articles.push(entry.publish_info);
      if (Array.isArray(entry.publish_info?.multi_appmsg_item_list)) {
        articles.push(...entry.publish_info.multi_appmsg_item_list);
      }
    });
    return {
      articles,
      consumed: page.publish_list.length,
      total: Number(page.total_count) || null
    };
  }

  function parseLegacyPage(payload) {
    if (responseFailed(payload)) return { unavailable: true };
    const page = parseJsonValue(payload.general_msg_list ?? payload.data?.general_msg_list);
    if (!page || !Array.isArray(page.list)) return { unavailable: true };
    const articles = [];
    page.list.forEach((entry) => {
      const info = entry.appmsg_ext_info;
      if (info) {
        articles.push({ ...info, create_time: entry.comm_msg_info?.datetime });
        if (Array.isArray(info.multi_appmsg_item_list)) articles.push(...info.multi_appmsg_item_list);
      }
    });
    return { articles, consumed: page.list.length, total: Number(page.count) || null };
  }

  function parseJsonValue(value) {
    if (value && typeof value === "object") return value;
    if (typeof value === "string") {
      try { return JSON.parse(value); } catch { return null; }
    }
    return null;
  }

  function normalizeOfficialArticle(item, account, index) {
    const title = firstString(item.title, item.name);
    const url = safeOfficialArticleUrl(firstString(item.link, item.content_url, item.url));
    if (!title || !url) return null;
    return {
      id: firstIdentifier(item.appmsgid, item.fileid, item.id) || `${account.fakeid}:${url}`,
      accountId: account.fakeid, accountName: account.nickname,
      title, summary: firstString(item.digest, item.summary, ""),
      author: firstString(item.author, ""), cover: safeHttpsUrl(firstString(item.cover, "")),
      publishedAt: normalizeTimestamp(item.update_time ?? item.create_time),
      isOriginal: item.is_original === 1 || item.is_original === true ? true :
        item.is_original === 0 || item.is_original === false ? false : null, url
    };
  }

  function safeHttpsUrl(value) {
    try { const url = new URL(value); return url.protocol === "https:" ? url.href : ""; }
    catch { return ""; }
  }

  function safeOfficialArticleUrl(value) {
    try {
      const url = new URL(value);
      return url.protocol === "https:" && url.hostname === OFFICIAL_HOST &&
        !url.username && !url.password ? url.href : "";
    } catch { return ""; }
  }

  return getArticles(message.bookId, message.offset, message.readerUrl, sender);
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

async function requestArticlesFromReader(readerUrl, params) {
  const normalizedReaderUrl = normalizeReaderUrl(readerUrl);
  if (!normalizedReaderUrl) {
    throw new WereadError("INPUT", "公众号缺少有效的微信读书阅读页面。请刷新已关注列表后重试。");
  }

  const { tabId, temporary } = await getReaderTab(normalizedReaderUrl);
  try {
    await waitForTabLoaded(tabId);
    return await requestFromWereadPage(tabId, "/api/mp/cover", params);
  } finally {
    if (temporary) {
      try {
        await chrome.tabs.remove(tabId);
      } catch {
        // The tab may already have been closed by the user.
      }
    }
  }
}

async function getReaderTab(readerUrl) {
  const tabs = await chrome.tabs.query({ url: "https://weread.qq.com/*" });
  const matchingTab = tabs.find((tab) => tab.url === readerUrl);
  if (matchingTab?.id) return { tabId: matchingTab.id, temporary: false };

  try {
    const tab = await chrome.tabs.create({ url: readerUrl, active: false });
    if (!tab.id) throw new Error("Reader tab has no id");
    return { tabId: tab.id, temporary: true };
  } catch (cause) {
    throw new WereadError("NETWORK", "无法打开微信读书公众号页面，请稍后重试。", cause);
  }
}

function waitForTabLoaded(tabId) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const finish = (callback, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      chrome.tabs.onUpdated.removeListener(onUpdated);
      callback(value);
    };
    const onUpdated = (updatedTabId, changeInfo) => {
      if (updatedTabId === tabId && changeInfo.status === "complete") finish(resolve);
    };
    const timeout = setTimeout(() => {
      finish(reject, new WereadError("NETWORK", "微信读书页面加载超时，请检查网络后重试。"));
    }, READER_LOAD_TIMEOUT_MS);

    chrome.tabs.onUpdated.addListener(onUpdated);
    chrome.tabs.get(tabId)
      .then((tab) => {
        if (tab.status === "complete") finish(resolve);
      })
      .catch((cause) => finish(reject, new WereadError("NETWORK", "无法加载微信读书公众号页面。", cause)));
  });
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
  if (result.networkError) {
    throw new WereadError("NETWORK", "微信读书网络请求失败，请检查网络后重试。");
  }
  if (!result.ok) {
    throw new WereadError("HTTP", `微信读书接口返回 ${result.status}。`);
  }
  if (result.parseError) {
    throw new WereadError("DATA", "微信读书返回了无法识别的数据。");
  }

  const payload = result.payload;

  const apiError = payload?.errCode ?? payload?.errcode;
  const numericApiError = Number(apiError);
  const hasApiError = apiError !== undefined && apiError !== null &&
    apiError !== 0 && apiError !== "0" &&
    (Number.isFinite(numericApiError) || String(apiError).trim() !== "");
  if (hasApiError) {
    const detail = payload.errMsg ?? payload.errmsg ?? "";
    if (numericApiError === -2041) {
      throw new WereadError(
        "API",
        "微信读书暂时无法返回该公众号的最新文章（-2041）。请在微信读书中打开该公众号页面查看文章历史，稍后再重试最新文章。"
      );
    }
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
      author: stringValue(book.author, ""),
      readerUrl: readerUrlFromDeepLink(book.deepLink)
    }))
    .sort((left, right) => left.title.localeCompare(right.title, "zh-CN"));
}

async function getArticles(bookId, offset = 0, readerUrl, sender) {
  if (!isValidBookId(bookId)) {
    throw new WereadError("INPUT", "无效的公众号标识。");
  }
  if (!Number.isInteger(offset) || offset < 0) {
    throw new WereadError("INPUT", "无效的文章分页位置。");
  }

  const payload = await requestArticlesFromReader(readerUrl, { bookId }, sender);
  return {
    articles: normalizeCoverResponse(payload),
    nextOffset: null
  };
}

function normalizeCoverResponse(payload) {
  const pending = [{ value: payload, depth: 0 }];
  const seen = new Set();
  while (pending.length) {
    const { value, depth } = pending.shift();
    if (!value || typeof value !== "object") continue;
    if (seen.has(value)) continue;
    seen.add(value);

    if (Array.isArray(value)) {
      for (const item of value) pending.push({ value: item, depth });
      continue;
    }

    const article = normalizeArticle(value);
    if (article) return [article];
    if (depth < 3) {
      for (const child of Object.values(value)) {
        if (child && typeof child === "object") {
          pending.push({ value: child, depth: depth + 1 });
        }
      }
    }
  }
  return [];
}

function isValidBookId(bookId) {
  return typeof bookId === "string" &&
    /^MP_WXS_[A-Za-z0-9._~-]+$/.test(bookId);
}

function readerUrlFromDeepLink(deepLink) {
  if (typeof deepLink !== "string") return null;
  try {
    const url = new URL(deepLink);
    const value = url.searchParams.get("v");
    if (!value || !/^[A-Za-z0-9._~-]+$/.test(value)) return null;
    return `${WEREAD_ORIGIN}/web/mp/reader/${encodeURIComponent(value)}`;
  } catch {
    return null;
  }
}

function normalizeReaderUrl(readerUrl) {
  if (typeof readerUrl !== "string") return null;
  try {
    const url = new URL(readerUrl);
    if (url.origin !== WEREAD_ORIGIN || !url.pathname.startsWith("/web/mp/reader/") ||
        url.search || url.hash) return null;
    const value = url.pathname.slice("/web/mp/reader/".length);
    if (!value || value.includes("/") || !/^[A-Za-z0-9._~-]+$/.test(decodeURIComponent(value))) {
      return null;
    }
    return `${WEREAD_ORIGIN}/web/mp/reader/${encodeURIComponent(decodeURIComponent(value))}`;
  } catch {
    return null;
  }
}

function normalizeArticle(info) {
  if (!info || typeof info !== "object") {
    return null;
  }

  const title = firstString(info.title, info.articleTitle, info.name);
  const originalId = firstIdentifier(
    info.reviewId,
    info.review_id,
    info.originalId,
    info.original_id,
    info.articleId,
    info.id
  );
  if (!title || !originalId) return null;

  const explicitUrl = firstString(
    info.articleUrl,
    info.article_url,
    info.url,
    info.link,
    info.mpUrl,
    info.mp_url
  );
  const publicOriginalId = originalId.replace(/~/g, "_");
  const url = publicArticleUrl(explicitUrl) ||
    `https://mp.weixin.qq.com/s/${encodeURIComponent(publicOriginalId)}`;
  const publishedAt = normalizeTimestamp(info.publishedAt ?? info.time ?? info.publishTime);
  return {
    id: originalId,
    title,
    summary: firstString(info.content, info.summary, ""),
    publicationName: firstString(info.mpName, info.mp_name, ""),
    publishedAt,
    readCount: Number(info.readNum) || 0,
    likeCount: Number(info.likeNum) || 0,
    url,
    cover: firstString(info.cover, info.coverUrl, info.cover_url, "")
  };
}

function stringValue(value, fallback) {
  return typeof value === "string" ? value : fallback;
}

function firstString(...values) {
  return values.find((value) => typeof value === "string" && value.trim())?.trim() || "";
}

function firstIdentifier(...values) {
  const value = values.find((candidate) =>
    (typeof candidate === "string" && candidate.trim()) || Number.isFinite(candidate)
  );
  return value === undefined || value === null ? "" : String(value).trim();
}

function normalizeTimestamp(value) {
  const timestamp = Number(value);
  if (!Number.isFinite(timestamp) || timestamp <= 0) return 0;
  return timestamp > 100000000000 ? Math.round(timestamp / 1000) : timestamp;
}

function publicArticleUrl(value) {
  if (!value) return "";
  try {
    const url = new URL(value);
    return url.protocol === "https:" && url.hostname === "mp.weixin.qq.com" &&
      !url.username && !url.password ? url.href : "";
  } catch {
    return "";
  }
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

  let response;
  try {
    response = await fetch(url, {
      credentials: "include",
      headers: { Accept: "application/json, text/plain, */*" }
    });
  } catch {
    return { ok: false, status: 0, networkError: true };
  }

  try {
    const payload = await response.json();
    return { ok: response.ok, status: response.status, payload };
  } catch {
    return { ok: false, status: response.status, parseError: true };
  }
}

async function fetchOfficialPage(path, params) {
  const pageToken = (() => {
    const candidates = [
      new URL(location.href).searchParams.get("token"),
      window.wx?.cgiData?.token,
      window.cgiData?.token
    ];
    return candidates.find((value) => typeof value === "string" && /^\d{1,32}$/.test(value)) || "";
  })();
  if (!pageToken) return { ok: false, status: 401, login: true };

  const url = new URL(path, location.origin);
  const query = { ...params, token: pageToken, lang: "zh_CN", f: "json", ajax: 1, random: Date.now() };
  for (const [key, value] of Object.entries(query)) {
    url.searchParams.set(key, String(value));
  }

  let response;
  try {
    response = await fetch(url, {
      credentials: "include",
      headers: { Accept: "application/json, text/plain, */*" }
    });
  } catch {
    return { ok: false, status: 0, networkError: true };
  }

  const text = await response.text();
  // Do not match the normal search result field `verify_status`; only
  // security/challenge wording or a verification endpoint is actionable.
  if (/验证码|安全验证|captcha|security[-_ ]?check|滑块|需要验证|\/verify(?:[/?\s]|$)/i.test(text)) {
    return { ok: false, status: response.status, challenge: true };
  }
  if (/登录|login/i.test(text) && !/^\s*\{/.test(text)) {
    return { ok: false, status: response.status, login: true };
  }
  try {
    return { ok: response.ok, status: response.status, payload: JSON.parse(text) };
  } catch {
    return { ok: false, status: response.status, parseError: true };
  }
}

class WereadError extends Error {
  constructor(code, message, cause) {
    super(message, { cause });
    this.code = code;
  }
}
