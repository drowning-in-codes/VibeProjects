/* ============================================================
 * 扩展后台（Service Worker）· 微信读书 · 公众号文章导出器
 *
 * 只做两件事：
 *   1. wmx:fetch        —— 代 content script 请求 weread.qq.com 接口。
 *                          抽屉注入到 mp.weixin.qq.com 时，页面里直接 fetch
 *                          weread 会被 CORS 拦（跨源、且拿不到 Cookie）；
 *                          而后台按 host_permissions 发出的请求不受该限制，
 *                          并自动带上浏览器里的微信读书登录态。
 *   2. wmx:open-weread  —— 打开（或切到）微信读书标签页，供扫码登录。
 *
 * 不落任何存储、不上报、不访问白名单以外的地址。
 * ============================================================ */

const WR_ORIGIN = 'https://weread.qq.com';
const MP_ORIGIN = 'https://mp.weixin.qq.com';
const MP_SEARCH_PATH = '/cgi-bin/searchbiz';
const ALLOW_PATH = [/^\/web\//, /^\/api\//, /^\/mp\//];

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  // 只服务本扩展自己的页面脚本
  if (!sender || sender.id !== chrome.runtime.id) return;
  if (!msg || typeof msg !== 'object' || typeof msg.type !== 'string') return;

  if (msg.type === 'wmx:fetch') {
    proxyFetch(msg).then(sendResponse, (e) =>
      sendResponse({ ok: false, error: String((e && e.message) || e) }));
    return true;   // 异步回包
  }

  if (msg.type === 'wmx:searchbiz') {
    searchBizProxy(msg).then(sendResponse, (e) =>
      sendResponse({ ok: false, error: String((e && e.message) || e) }));
    return true;
  }

  if (msg.type === 'wmx:find-mp-token') {
    findMpToken().then(sendResponse, (e) =>
      sendResponse({ ok: false, error: String((e && e.message) || e) }));
    return true;
  }

  if (msg.type === 'wmx:open-weread') {
    openWeread().then(sendResponse, (e) =>
      sendResponse({ ok: false, error: String((e && e.message) || e) }));
    return true;
  }

  if (msg.type === 'wmx:open-mp') {
    openMpBackend().then(sendResponse, (e) =>
      sendResponse({ ok: false, error: String((e && e.message) || e) }));
    return true;
  }
});

/* ---------------- 接口代理 ---------------- */
async function proxyFetch(msg) {
  const path = String(msg.path || '');

  // 只放行微信读书的只读接口，避免被当成任意请求转发器
  if (!/^\/[A-Za-z0-9_\-./?=&%]*$/.test(path) || !ALLOW_PATH.some((re) => re.test(path))) {
    return { ok: false, error: '拒绝代理该路径：' + path.slice(0, 80) };
  }

  const method = (String(msg.method || 'GET').toUpperCase() === 'POST') ? 'POST' : 'GET';
  if (method === 'POST' && path !== '/mp/shelf/addToShelf') {
    return { ok: false, error: '拒绝代理该写入路径' };
  }

  const init = {
    method: method,
    credentials: 'include',
    cache: 'no-store',
    headers: { 'Accept': 'application/json, text/plain, */*' }
  };
  if (method === 'POST' && typeof msg.body === 'string' && msg.body) {
    if (msg.body.length > 4096) return { ok: false, error: '请求体过大' };
    init.headers['Content-Type'] = 'application/json;charset=UTF-8';
    init.body = msg.body;
  }

  let res;
  try {
    res = await fetch(WR_ORIGIN + path, init);
  } catch (e) {
    return { ok: false, error: '后台请求失败：' + ((e && e.message) || e) };
  }

  const text = await res.text();
  let json = null;
  let notJson = false;
  try { json = JSON.parse(text); } catch (e) { notJson = true; }

  return {
    ok: true,
    http: res.status,
    json: json,
    notJson: notJson,
    text: notJson ? text.slice(0, 200) : ''
  };
}

async function searchBizProxy(msg) {
  const query = String(msg.query || '').trim();
  const token = String(msg.token || '').trim();
  const begin = Math.max(0, Math.min(600, Number(msg.begin) || 0));
  if (!query || query.length > 40) return { ok: false, error: '搜索关键词不合法（1–40 字）' };
  if (!/^\d{5,20}$/.test(token)) return { ok: false, error: '缺少公众号后台 token' };

  const url = MP_ORIGIN + MP_SEARCH_PATH +
    '?action=search_biz&scene=1&query=' + encodeURIComponent(query) +
    '&begin=' + begin + '&count=5&token=' + token + '&lang=zh_CN&f=json&ajax=1';
  let res;
  try {
    res = await fetch(url, {
      method: 'GET',
      credentials: 'include',
      cache: 'no-store',
      headers: { 'Accept': 'application/json, text/plain, */*', 'X-Requested-With': 'XMLHttpRequest' }
    });
  } catch (e) {
    return { ok: false, error: '后台请求失败：' + ((e && e.message) || e) };
  }
  const text = await res.text();
  let json = null;
  let notJson = false;
  try { json = JSON.parse(text); } catch (e) { notJson = true; }
  return { ok: true, http: res.status, json: json, notJson: notJson, text: notJson ? text.slice(0, 200) : '' };
}

async function findMpToken() {
  let tabs = [];
  try {
    tabs = await chrome.tabs.query({ url: MP_ORIGIN + '/*' });
  } catch (e) {
    return { ok: false, error: '无法查询标签页' };
  }
  for (const tab of (tabs || [])) {
    const match = String(tab.url || '').match(/[?&]token=(\d{5,20})(?:&|#|$)/);
    if (match) return { ok: true, token: match[1] };
  }
  return { ok: false, error: '没找到已打开的公众号后台页面' };
}

/* ---------------- 打开微信读书 ---------------- */
async function openWeread() {
  try {
    const tabs = await chrome.tabs.query({ url: WR_ORIGIN + '/*' });
    if (tabs && tabs.length) {
      const t = tabs[0];
      await chrome.tabs.update(t.id, { active: true });
      if (t.windowId !== undefined && chrome.windows) {
        try { await chrome.windows.update(t.windowId, { focused: true }); } catch (e) { /* 忽略 */ }
      }
      return { ok: true, reused: true };
    }
  } catch (e) { /* 查询失败就直接新建 */ }

  try {
    await chrome.tabs.create({ url: WR_ORIGIN + '/', active: true });
    return { ok: true, reused: false };
  } catch (e) {
    return { ok: false, error: '无法打开标签页：' + ((e && e.message) || e) };
  }
}

async function openMpBackend() {
  try {
    const tabs = await chrome.tabs.query({ url: MP_ORIGIN + '/cgi-bin/*' });
    if (tabs && tabs.length) {
      const tab = tabs[0];
      await chrome.tabs.update(tab.id, { active: true });
      if (tab.windowId !== undefined && chrome.windows) {
        try { await chrome.windows.update(tab.windowId, { focused: true }); } catch (e) { /* 忽略 */ }
      }
      return { ok: true, reused: true };
    }
  } catch (e) { /* 查询失败则新建 */ }
  try {
    await chrome.tabs.create({ url: MP_ORIGIN + '/', active: true });
    return { ok: true, reused: false };
  } catch (e) {
    return { ok: false, error: '无法打开公众号后台：' + ((e && e.message) || e) };
  }
}
