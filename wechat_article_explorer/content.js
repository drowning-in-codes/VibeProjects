/* ============================================================
 * 微信读书 · 公众号文章导出器  (content script)
 *
 * 注入两个站点：
 *   weread.qq.com     主站。同源直连微信读书 Web 接口，用你的登录态取数。
 *   mp.weixin.qq.com  公众号文章页 / 公众号后台。抽屉同样可用；此时页面级
 *                     fetch 会被 CORS 拦，接口请求改由扩展后台（bg.js）转发。
 *
 * 用到的接口（2026-10 实测存在，无 Cookie 返回 -2010「用户不存在」）：
 *   GET /web/shelf/bookIds              已订阅的书/公众号 bookId 列表
 *   GET /web/book/info?bookId=          书籍/公众号详情（取名称）
 *   GET /web/mp/articles?bookId=&offset= 公众号文章列表（主路径，offset 步长 50）
 *   GET /api/mp/cover?bookId=           仅最新一篇（兜底）
 *   POST /mp/shelf/addToShelf            把公众号加入微信读书书架（用户主动触发）
 * ============================================================ */
(function () {
  'use strict';

  if (window.__WMX_LOADED__) return;
  window.__WMX_LOADED__ = true;

  /* ---------------- 运行环境 ---------------- */
  const WR_ORIGIN = 'https://weread.qq.com';
  const IS_WEREAD = /(^|\.)weread\.qq\.com$/.test(location.hostname);
  const IS_MP = /(^|\.)mp\.weixin\.qq\.com$/.test(location.hostname);
  const WMX_INSTANCE = Math.random().toString(36).slice(2, 10);
  const WMX_NS = 'wmx-' + WMX_INSTANCE;

  /* ---------------- 常量 ---------------- */
  const EP = {
    shelfBookIds: '/web/shelf/bookIds',
    bookInfo: '/web/book/info',
    mpArticles: '/web/mp/articles',
    mpCover: '/api/mp/cover',
    addToShelf: '/mp/shelf/addToShelf'
  };
  const PAGE_STEP = 50;      // 微信读书列表接口的 offset 步长
  const DELAY_LIST = 1300;   // 列表分页间隔（ms），太快会被风控
  const DELAY_INFO = 380;    // 书籍详情间隔（ms）
  const MAX_PAGES = 80;
  const MP_PREFIX = /^MP_WXS_/;
  const LOGIN_POLL_MS = 2500;   // 登录态轮询间隔
  const LOGIN_POLL_MAX = 48;    // 最多轮询约 2 分钟
  const QR_WAIT_MS = 800;       // 镜像官方二维码的重试间隔
  const MP_ORIGIN = 'https://mp.weixin.qq.com';
  const MP_SEARCH_PATH = '/cgi-bin/searchbiz';
  const SEARCH_COUNT = 5;
  const DELAY_SEARCH = 1200;

  function readMpTokenFromPage() {
    if (!IS_MP) return '';
    const m = String(location.href).match(/[?&]token=(\d{5,20})(?:&|#|$)/);
    if (m) return m[1];
    try {
      const v = window.wx && window.wx.commonData &&
        (window.wx.commonData.t || (window.wx.commonData.data && window.wx.commonData.data.t));
      return v && /^\d{5,20}$/.test(String(v)) ? String(v) : '';
    } catch (e) {
      return '';
    }
  }

  /* ---------------- 工具 ---------------- */
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  function fmtTime(ts) {
    if (!ts) return '';
    const n = Number(ts);
    if (!isFinite(n) || n <= 0) return '';
    const d = new Date(n < 1e12 ? n * 1000 : n);
    if (isNaN(d.getTime())) return '';
    const p = (x) => String(x).padStart(2, '0');
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) +
      ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
  }

  function firstStr() {
    for (let i = 0; i < arguments.length; i++) {
      const v = arguments[i];
      if (typeof v === 'string' && v.trim()) return v.trim();
      if (typeof v === 'number' && isFinite(v)) return String(v);
    }
    return '';
  }

  function firstNum() {
    for (let i = 0; i < arguments.length; i++) {
      const v = arguments[i];
      if (typeof v === 'number' && isFinite(v) && v > 0) return v;
      if (typeof v === 'string' && /^\d{9,19}$/.test(v.trim())) return Number(v.trim());
    }
    return 0;
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function saveBlob(filename, content, mime) {
    const blob = new Blob([content], { type: (mime || 'text/plain') + ';charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 1500);
  }

  function stamp() {
    const d = new Date(), p = (x) => String(x).padStart(2, '0');
    return d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate()) + '-' + p(d.getHours()) + p(d.getMinutes());
  }

  /* ---------------- 接口层 ---------------- */
  function errHint(err) {
    if (err && err.channelFail) {
      return '扩展后台通道不可用：' + (err.message || '') +
        '　刚装好或刚更新过扩展请刷新本页面；若仍不行，可直接打开 weread.qq.com 使用。';
    }
    const c = err && err.code;
    if (c === -2010) return '未登录：微信读书没有登录态（-2010 用户不存在）。请先点「登录微信读书」扫码，然后刷新本页面。';
    if (c === -2012) return '登录超时（-2012）。请重新登录微信读书网页版，刷新页面后重试。';
    if (c === -2041) return '被风控/认证拦截（-2041）。通常是请求太频繁，等几十分钟或明天再试；也可能是 Cookie 过期。';
    if (c === -2042) return '权限不足（-2042）。该公众号可能未收录或需要书架订阅。';
    if (c) return '接口返回错误码 ' + c + '：' + (err.msg || '');
    return (err && err.message) || '未知错误';
  }

  /* 与扩展后台通信（后台落在扩展上下文里，不受被注入页面的 CORS 限制） */
  function hasRuntime() {
    return typeof chrome !== 'undefined' && chrome.runtime &&
      typeof chrome.runtime.sendMessage === 'function';
  }

  function bgSend(msg) {
    return new Promise((resolve, reject) => {
      let replied = false;
      try {
        chrome.runtime.sendMessage(msg, (resp) => {
          replied = true;
          const le = chrome.runtime.lastError;
          if (le) {
            const err = new Error(le.message || '未知');
            err.channelFail = true;
            reject(err);
            return;
          }
          if (resp === undefined) {
            const err = new Error('后台没有回应');
            err.channelFail = true;
            reject(err);
            return;
          }
          resolve(resp);
        });
      } catch (e) {
        if (!replied) {
          const err = new Error((e && e.message) || 'sendMessage 失败');
          err.channelFail = true;
          reject(err);
        }
      }
    });
  }

  async function rawApi(path, opts) {
    // 不在微信读书页面时，交给后台代理：页面里直接跨源 fetch 会被 CORS 拦
    if (!IS_WEREAD) return await bgApi(path, opts);

    const res = await fetch(path, Object.assign({
      method: 'GET',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { 'Accept': 'application/json, text/plain, */*' }
    }, opts || {}));
    const text = await res.text();
    let json = null;
    try { json = JSON.parse(text); } catch (e) {
      const err = new Error('返回的不是 JSON（HTTP ' + res.status + '）：' + text.slice(0, 160));
      err.notJson = true;
      throw err;
    }
    return { http: res.status, json: json };
  }

  async function bgApi(path, opts) {
    if (!hasRuntime()) {
      const err = new Error('当前页面拿不到扩展后台（请刷新页面，或直接打开 weread.qq.com）');
      err.channelFail = true;
      throw err;
    }
    const resp = await bgSend(Object.assign(
      { type: 'wmx:fetch', path: path, method: (opts && opts.method) || 'GET' },
      (opts && typeof opts.body === 'string') ? { body: opts.body } : null
    ));
    if (!resp.ok) throw new Error(resp.error || '后台代理失败');
    if (resp.notJson) {
      const err = new Error('返回的不是 JSON（HTTP ' + resp.http + '）：' + (resp.text || ''));
      err.notJson = true;
      throw err;
    }
    return { http: resp.http, json: resp.json };
  }

  function checkErr(json) {
    if (!json || typeof json !== 'object') return json;
    const code = (json.errCode !== undefined) ? json.errCode
      : (json.errcode !== undefined) ? json.errcode
        : (json.data && json.data.errcode !== undefined) ? json.data.errcode : undefined;
    if (typeof code === 'number' && code !== 0) {
      const err = new Error('api-error');
      err.code = code;
      err.msg = firstStr(json.errMsg, json.errmsg, json.data && json.data.errmsg);
      throw err;
    }
    // /api/mp/* 那套是另一套壳
    if (json.statusCode && json.statusCode >= 400) {
      const err = new Error('api-error');
      err.code = json.data && json.data.errcode;
      err.msg = json.statusMessage || '';
      throw err;
    }
    return json;
  }

  async function api(path, opts) {
    const r = await rawApi(path, opts);
    checkErr(r.json);
    return r.json;
  }

  /* ---------------- 解析层 ---------------- */

  // bookIds 可能是数组 / 逗号串 / 对象数组，统一成字符串数组
  function normalizeBookIds(payload) {
    const roots = [payload, payload && payload.data].filter(Boolean);
    const keys = ['bookIds', 'bookIdList', 'ids', 'books', 'shelf'];
    for (const root of roots) {
      if (Array.isArray(root)) {
        return root.map((x) => (typeof x === 'string' ? x : firstStr(x && x.bookId, x && x.id))).filter(Boolean);
      }
      for (const k of keys) {
        const v = root[k];
        if (Array.isArray(v)) {
          return v.map((x) => (typeof x === 'string' ? x : firstStr(x && x.bookId, x && x.id))).filter(Boolean);
        }
        if (typeof v === 'string' && v.trim()) {
          return v.split(',').map((s) => s.trim()).filter(Boolean);
        }
      }
    }
    return [];
  }

  function bookTitleFromInfo(json) {
    const roots = [json, json && json.data].filter(Boolean);
    for (const r of roots) {
      const t = firstStr(r.title, r.bookName, r.name, r.book && r.book.title);
      if (t) return t;
      if (r.bookInfo) {
        const t2 = firstStr(r.bookInfo.title, r.bookInfo.bookName, r.bookInfo.name);
        if (t2) return t2;
      }
    }
    return '';
  }

  // reviewId = <BOOK_ID>_<TOKEN>，TOKEN 即 mp.weixin.qq.com/s/<token> 的短链 token
  function extractToken(review, info, reviewId, bookId) {
    const cands = [
      info.originalId, review.originalId, review.origId,
      info.origId, review.articleId, info.articleId,
      info.mpArticleId, review.mpArticleId
    ];
    for (let i = 0; i < cands.length; i++) {
      const c = cands[i];
      if (!c) continue;
      const s = String(c);
      const m = s.match(/mp\.weixin\.qq\.com\/s\/([A-Za-z0-9_-]+)/);
      if (m) return m[1];
      if (/^[A-Za-z0-9_-]{15,64}$/.test(s)) return s;
    }

    if (reviewId) {
      if (bookId && reviewId.indexOf(bookId + '_') === 0) {
        const t = reviewId.slice(bookId.length + 1);
        if (t && t.length >= 15 && /^[A-Za-z0-9_-]+$/.test(t)) return t;
      }
      const parts = String(reviewId).split('_');
      const last = parts[parts.length - 1];
      if (last && last.length >= 15 && /^[A-Za-z0-9_-]+$/.test(last)) return last;
    }

    // 最后一手：在对象里扫任意长得像短链 token 的字符串
    try {
      for (const k in review) {
        const v = review[k];
        if (typeof v === 'string') {
          const m2 = v.match(/mp\.weixin\.qq\.com\/s\/([A-Za-z0-9_-]+)/);
          if (m2) return m2[1];
        }
      }
    } catch (e) { /* ignore */ }
    return '';
  }

  // 把 /web/mp/articles 的响应拍平成文章数组
  function flattenArticles(json, bookId, accountName) {
    const out = [];
    const roots = [json, json && json.data].filter(Boolean);
    let groups = null;
    for (const r of roots) {
      for (const k of ['reviews', 'reviewList', 'list', 'articles', 'items']) {
        if (Array.isArray(r[k])) { groups = r[k]; break; }
      }
      if (groups) break;
    }
    if (!groups) return out;

    for (let i = 0; i < groups.length; i++) {
      const g = groups[i];
      if (!g || typeof g !== 'object') continue;
      let subs = null;
      for (const k of ['subReviews', 'reviews', 'subReview', 'items']) {
        if (Array.isArray(g[k])) { subs = g[k]; break; }
      }
      if (!subs) subs = g.review ? [g] : [g];

      for (let j = 0; j < subs.length; j++) {
        const s = subs[j];
        const rev = (s && s.review) ? s.review : s;
        if (!rev || typeof rev !== 'object') continue;
        const info = rev.mpInfo || (s && s.mpInfo) || {};

        const title = firstStr(info.title, rev.title, info.name, rev.name);
        const reviewId = firstStr(rev.reviewId, s && s.reviewId, info.reviewId);
        const ts = firstNum(rev.createTime, info.time, rev.updateTime, rev.publishTime, info.publishTime, rev.time);
        const token = extractToken(rev, info, reviewId, bookId);

        if (!title && !token) continue;
        out.push({
          account: accountName || bookId,
          bookId: bookId,
          title: title,
          time: fmtTime(ts),
          ts: ts,
          url: token ? ('https://mp.weixin.qq.com/s/' + token) : '',
          reviewId: reviewId,
          cover: firstStr(info.pic_url, info.cover, rev.cover),
          raw: rev
        });
      }
    }
    return out;
  }

  /* ---------------- 公众号：链接解析 / 本地列表 ---------------- */
  function bizToFakid(biz) {
    if (!biz) return '';
    let s = String(biz).trim();
    try { s = decodeURIComponent(s); } catch (e) { /* 保持原样 */ }
    s = s.replace(/\s+/g, '').replace(/-/g, '+').replace(/_/g, '/').replace(/=+$/, '');
    if (!/^[A-Za-z0-9+/]{6,64}$/.test(s)) return '';
    try {
      const out = atob(s + '='.repeat((4 - (s.length % 4)) % 4));
      return /^\d{5,20}$/.test(out) ? out : '';
    } catch (e) {
      return '';
    }
  }

  function bizToBookId(biz) {
    const fakid = bizToFakid(biz);
    return fakid ? 'MP_WXS_' + fakid : '';
  }

  function parseMpInput(text) {
    const raw = String(text || '').trim();
    if (!raw) return { ok: false, reason: 'empty' };
    const id = raw.match(/MP_WXS_\d{5,20}/);
    if (id) return { ok: true, bookId: id[0], from: 'bookId' };
    const biz = raw.match(/__biz=([A-Za-z0-9+/=%_-]{8,})/);
    if (biz) {
      const bookId = bizToBookId(biz[1]);
      return bookId ? { ok: true, bookId: bookId, from: 'link' } : { ok: false, reason: 'biz' };
    }
    if (/^[A-Za-z0-9+/=_-]{12,64}$/.test(raw)) {
      const bookId = bizToBookId(raw);
      if (bookId) return { ok: true, bookId: bookId, from: 'biz' };
    }
    if (/^\d{5,20}$/.test(raw)) return { ok: true, bookId: 'MP_WXS_' + raw, from: 'fakid' };
    if (/mp\.weixin\.qq\.com\/s\/[A-Za-z0-9_-]+/.test(raw)) return { ok: false, reason: 'shortlink' };
    if (/^https?:\/\//.test(raw)) return { ok: false, reason: 'otherlink' };
    return { ok: false, reason: 'name' };
  }

  function addReasonHint(reason) {
    if (reason === 'empty') return '请输入文章长链接、__biz、MP_WXS_数字或公众号 fakid。';
    if (reason === 'shortlink') return '这是 /s/ 短链，短链里不带 __biz。请打开文章后点「收录这个号」。';
    if (reason === 'biz') return '__biz 无法解析为公众号标识，请复制完整文章链接。';
    if (reason === 'otherlink') return '链接里没有 __biz，请使用 mp.weixin.qq.com 的公众号文章链接。';
    return '无法按公众号名称搜索，请粘贴该号任意一篇文章的完整链接。';
  }

  function addSourceName(source) {
    if (source === 'page') return '当前页面';
    if (source === 'biz') return '手动填 __biz';
    if (source === 'fakid') return '手动填数字';
    if (source === 'bookId') return '手动填 bookId';
    return '粘贴链接';
  }

  function readBizFromPage() {
    if (!IS_MP) return '';
    const values = [];
    const push = (value) => { if (typeof value === 'string' && value.trim()) values.push(value.trim()); };
    try { push(window.biz); } catch (e) { /* ignore */ }
    try { push(window.__biz); } catch (e) { /* ignore */ }
    try { push(window.cgiData && window.cgiData.biz); } catch (e) { /* ignore */ }
    try { push(window.appmsg && window.appmsg.biz); } catch (e) { /* ignore */ }
    try { push(window.wx && window.wx.commonData && window.wx.commonData.data && window.wx.commonData.data.biz); } catch (e) { /* ignore */ }

    const urlMatch = location.href.match(/__biz=([A-Za-z0-9+/=%_-]{8,})/);
    if (urlMatch) values.push(urlMatch[1]);
    try {
      const links = document.querySelectorAll('#js_name, .rich_media_meta_nickname, a[href*="__biz"]');
      for (let i = 0; i < Math.min(links.length, 40); i++) {
        const href = links[i].getAttribute && links[i].getAttribute('href');
        const match = href && href.match(/__biz=([A-Za-z0-9+/=%_-]{8,})/);
        if (match) values.push(match[1]);
      }
    } catch (e) { /* ignore */ }

    for (let i = 0; i < values.length; i++) {
      if (bizToFakid(values[i])) return values[i];
    }
    try {
      const html = document.documentElement ? document.documentElement.innerHTML : '';
      const match = html.match(/var\s+biz\s*=\s*["']([A-Za-z0-9+/=_-]{8,})["']/);
      if (match && bizToFakid(match[1])) return match[1];
    } catch (e) { /* ignore */ }
    return '';
  }

  async function fetchAccountName(bookId) {
    return bookTitleFromInfo(await api(EP.bookInfo + '?bookId=' + encodeURIComponent(bookId))) || '';
  }

  function setAccountTitle(bookId, title) {
    if (!title) return;
    let dirty = false;
    state.shelf.forEach((a) => {
      if (a.bookId === bookId) { a.title = title; dirty = true; }
    });
    state.custom.forEach((a) => {
      if (a.bookId === bookId) { a.title = title; dirty = true; }
    });
    state.accounts.forEach((a) => { if (a.bookId === bookId) a.title = title; });
    if (dirty) saveCustom();
  }

  function rebuildAccounts() {
    const accounts = [];
    const push = (item, source) => {
      if (!item.bookId || accounts.some((a) => a.bookId === item.bookId)) return;
      accounts.push({
        bookId: item.bookId,
        title: item.title || '',
        source: source,
        isMp: MP_PREFIX.test(item.bookId)
      });
    };
    state.custom.forEach((a) => push(a, 'custom'));
    state.shelf.forEach((a) => push(a, 'shelf'));
    state.accounts = accounts;
    renderAccounts();
  }

  function saveCustom() {
    stor.set('wmx_custom', state.custom.map((a) => ({
      bookId: a.bookId, title: a.title, source: a.source, addedAt: a.addedAt
    })));
  }

  async function addCustomAccount(bookId, title, source) {
    const existing = state.accounts.filter((a) => a.bookId === bookId)[0];
    if (existing) {
      if (existing.source === 'shelf' && !state.custom.some((a) => a.bookId === bookId)) {
        state.custom.push({
          bookId: bookId,
          title: title || existing.title || '',
          source: source || 'shelf',
          addedAt: Date.now()
        });
        saveCustom();
        rebuildAccounts();
        log('已加入文章查看范围：' + (title || existing.title || bookId), 'ok');
        return state.custom[state.custom.length - 1];
      }
      if (!existing.title && title) { setAccountTitle(bookId, title); renderAccounts(); }
      log('这个号已经在列表里了：' + (existing.title || bookId), 'warn');
      return null;
    }
    const record = { bookId: bookId, title: title || '', source: source || 'link', addedAt: Date.now() };
    state.custom.push(record);
    saveCustom();
    rebuildAccounts();
    log('已加入本地列表：' + (record.title || record.bookId) + '（' + addSourceName(record.source) + '）', 'ok');
    return record;
  }

  function removeCustomAccount(bookId) {
    const index = state.custom.findIndex((a) => a.bookId === bookId);
    if (index < 0) return;
    const removed = state.custom.splice(index, 1)[0];
    saveCustom();
    rebuildAccounts();
    log('已从本地列表移除：' + (removed.title || removed.bookId), 'warn');
  }

  async function pushToWereadShelf(bookIds) {
    const ids = (bookIds || []).filter(Boolean);
    if (!ids.length) {
      toast('没有选中的本地公众号。', 'err');
      log('没有选中的本地公众号。', 'warn');
      return;
    }
    let success = 0;
    let firstErr = '';
    for (let i = 0; i < ids.length; i++) {
      try {
        await api(EP.addToShelf, {
          method: 'POST',
          body: JSON.stringify({ bookIds: [ids[i]] }),
          headers: { 'Content-Type': 'application/json;charset=UTF-8' }
        });
        success++;
        log('  · 已加入书架：' + ids[i], 'ok');
      } catch (e) {
        if (!firstErr) firstErr = errHint(e);
        log('  · 加入书架失败 ' + ids[i] + '：' + errHint(e), 'warn');
      }
      if (i < ids.length - 1) await sleep(DELAY_LIST);
    }
    const done = success + '/' + ids.length;
    if (success === ids.length) {
      toast('已全部添加到公众号关注（' + done + '）。', 'ok');
    } else if (success) {
      toast('部分添加到公众号关注（' + done + '）。' + firstErr, 'err');
    } else {
      toast('添加到公众号关注失败（0/' + ids.length + '）。' + firstErr, 'err');
    }
    log('加入书架完成 ' + done + '。刷新关注列表即可看到。', success ? 'ok' : 'warn');
  }

  /* ---------------- 业务动作 ---------------- */

  async function loadShelf() {
    const json = await api(EP.shelfBookIds);
    const ids = normalizeBookIds(json);
    const mps = ids.filter((id) => MP_PREFIX.test(id));
    // 如果没有一个以 MP_WXS_ 开头，就把全部 id 都给出来，让用户自己判断
    return { all: ids, mps: mps.length ? mps : ids, usedFallback: !mps.length };
  }

  async function loadAccounts(onProgress) {
    const shelf = await loadShelf();
    const list = shelf.mps.map((id) => ({ bookId: id, title: '', isMp: MP_PREFIX.test(id) }));
    state.shelf = list;
    rebuildAccounts();
    log('书架共 ' + shelf.all.length + ' 项，其中公众号候选 ' + list.length + ' 个');
    if (shelf.usedFallback && shelf.all.length) {
      log('注意：没有识别到 MP_WXS_ 前缀的 bookId，已列出全部条目，请按需添加到查看列表。', 'warn');
    }
    for (let i = 0; i < list.length; i++) {
      if (onProgress) onProgress(i + 1, list.length);
      try {
        const info = await api(EP.bookInfo + '?bookId=' + encodeURIComponent(list[i].bookId));
        list[i].title = bookTitleFromInfo(info) || '';
      } catch (e) {
        list[i].title = '';
      }
      state.accounts.forEach((a) => {
        if (a.bookId === list[i].bookId) a.title = list[i].title;
      });
      renderAccounts();
      if (i < list.length - 1) await sleep(DELAY_INFO);
    }
    stor.set('wmx_accounts', list.map((a) => ({ bookId: a.bookId, title: a.title })));
    renderAccounts();
  }

  async function fetchArticlesFor(bookId, accountName, limit, onPage) {
    const collected = [];
    const seen = Object.create(null);
    let offset = 0;
    let page = 0;
    let useCoverFallback = false;

    while (page < MAX_PAGES) {
      page++;
      let json = null;
      try {
        json = await api(EP.mpArticles + '?bookId=' + encodeURIComponent(bookId) + '&offset=' + offset);
      } catch (e) {
        if (page === 1) {
          log('  · 列表接口失败（' + errHint(e) + '），尝试 cover 兜底…', 'warn');
          useCoverFallback = true;
          break;
        }
        log('  · 第 ' + page + ' 页失败：' + errHint(e), 'warn');
        break;
      }

      const batch = flattenArticles(json, bookId, accountName);
      let added = 0;
      for (let i = 0; i < batch.length; i++) {
        const key = batch[i].reviewId || (batch[i].title + '|' + batch[i].ts);
        if (seen[key]) continue;
        seen[key] = 1;
        collected.push(batch[i]);
        added++;
      }
      if (onPage) onPage(collected.length, page);

      if (!batch.length || added === 0) {
        if (page === 1) log('  · 第一页没有解析出文章，可能字段结构与预期不同，请点「诊断」把原始返回发我。', 'warn');
        break;
      }
      if (limit && collected.length >= limit) break;
      offset += PAGE_STEP;
      await sleep(DELAY_LIST);
    }

    if (useCoverFallback) {
      try {
        const cov = await api(EP.mpCover + '?bookId=' + encodeURIComponent(bookId));
        const one = flattenArticles(cov, bookId, accountName);
        if (one.length) {
          one[0].note = '兜底：仅最新一篇';
          collected.push(one[0]);
        }
      } catch (e) {
        log('  · cover 兜底也失败：' + errHint(e), 'warn');
      }
    }

    return limit ? collected.slice(0, limit) : collected;
  }

  /* ---------------- 登录 ---------------- */

  // 登录态探针：/web/shelf/bookIds 未登录时稳定返回 -2010 / -2012
  async function probeLogin() {
    try {
      await api(EP.shelfBookIds);
      return { ok: true };
    } catch (e) {
      if (e && (e.code === -2010 || e.code === -2012)) return { ok: false, code: e.code };
      throw e;
    }
  }

  function setLogin(s, note) {
    state.login = s;
    renderLoginBar(note);
  }

  function renderLoginBar(note) {
    const bar = document.getElementById('wmx-loginbar');
    if (!bar) return;
    const dot = '<span class="wmx-dot"></span>';
    if (state.login === 'logged') {
      bar.className = 'wmx-loginbar wmx-ok';
      bar.innerHTML = dot + '<b>已登录微信读书</b><span class="wmx-note">' +
        esc(note || '登录态正常，点「刷新关注列表」开始') + '</span>';
    } else if (state.login === 'waiting') {
      bar.className = 'wmx-loginbar wmx-wait';
      bar.innerHTML = dot + '<b>等待扫码…</b><span class="wmx-note">' +
        esc(note || '请用微信扫描登录二维码') + '</span>' +
        '<button class="wmx-mini" id="wmx-login-check">我已扫码，检测</button>' +
        '<button class="wmx-mini" id="wmx-login-cancel">取消</button>';
    } else if (state.login === 'guest') {
      bar.className = 'wmx-loginbar wmx-guest';
      bar.innerHTML = dot + '<b>未登录微信读书</b><span class="wmx-note">' +
        esc(note || '插件靠你的读书登录态取数据，先登录') + '</span>' +
        '<button class="wmx-mini wmx-login-btn" id="wmx-login-go">' +
        (IS_WEREAD ? '登录微信读书' : '打开微信读书登录') + '</button>' +
        '<button class="wmx-mini" id="wmx-login-check">检测</button>';
    } else {
      bar.className = 'wmx-loginbar';
      bar.innerHTML = dot + '<b>登录状态未知</b><span class="wmx-note">' +
        esc(note || '') + '</span>' +
        '<button class="wmx-mini wmx-login-btn" id="wmx-login-go">检测登录状态</button>';
    }

    const go = document.getElementById('wmx-login-go');
    if (go) go.addEventListener('click', () => {
      if (state.login === 'guest') startLoginFlow(); else checkLogin(true);
    });
    const ck = document.getElementById('wmx-login-check');
    if (ck) ck.addEventListener('click', () => checkLogin(true));
    const cc = document.getElementById('wmx-login-cancel');
    if (cc) cc.addEventListener('click', () => {
      stopPoll();
      setLogin('guest', '已取消等待，可重新点「登录微信读书」');
    });
  }

  async function checkLogin(manual) {
    if (manual) log('正在检测登录状态…');
    try {
      const r = await probeLogin();
      if (r.ok) {
        if (state.login !== 'logged') setLogin('logged');
        if (manual) log('已登录。', 'ok');
        return true;
      }
      if (state.login !== 'waiting') {
        setLogin('guest', r.code === -2012 ? '登录态已超时，请重新登录' : '还没登录，点右边按钮登录');
      }
      if (manual) log('未登录（接口返回 ' + r.code + '）。', 'warn');
      return false;
    } catch (e) {
      if (state.login === 'unknown') setLogin('unknown', '检测失败：' + errHint(e));
      if (manual) log(errHint(e), 'err');
      return false;
    }
  }

  // 在页面上找官方登录入口（必须排除插件自己的抽屉和标签，否则会点到自己）
  function findLoginTrigger() {
    const own = document.getElementById('wmx-panel');
    const dock = document.getElementById('wmx-dock');
    const clean = (el) => el && !(own && own.contains(el)) && !(dock && dock.contains(el)) && el.offsetParent !== null;
    const sels = ['#login', '.login_container', '.navBar_login', '.wr_login_modal_trigger',
      '[class*="login_btn"]', '[class*="loginBtn"]'];
    for (const s of sels) {
      const el = document.querySelector(s);
      if (clean(el)) return el;
    }
    const nodes = document.querySelectorAll('button, a, div[role="button"]');
    const cap = Math.min(nodes.length, 3000);
    for (let i = 0; i < cap; i++) {
      const el = nodes[i];
      if (!clean(el)) continue;
      const t = (el.textContent || '').trim();
      if (t === '登录' || t === '登录/注册' || t === '微信登录' || t === '登录注册') return el;
    }
    return null;
  }

  // 把官方渲染出的二维码镜像进面板（若是跨域 iframe 则拿不到，只给文字提示）
  function mirrorQr() {
    const box = document.getElementById('wmx-qr');
    if (!box) return;

    // 不在微信读书页面：二维码在另一个标签页里，这里只给指引
    if (!IS_WEREAD) {
      box.innerHTML = '<div class="wmx-qr-tip">已为你打开微信读书页面，请在那里扫码登录。' +
        '扫码成功后本抽屉会自动检测到并继续。<br><span class="wmx-qr-dim">没有自动打开？点上方「打开微信读书」。</span></div>';
      return;
    }

    box.innerHTML = '<div class="wmx-qr-tip">二维码在页面上。若没看到，' +
      '请找页面中央弹出的登录窗口，或用微信扫页面里的「登录」入口。</div>';
    clearInterval(state.qrTimer);
    let tries = 0;
    state.qrTimer = setInterval(() => {
      tries++;
      if (tries > 40 || state.login !== 'waiting') { clearInterval(state.qrTimer); return; }
      const own = document.getElementById('wmx-panel');
      const cands = document.querySelectorAll(
        '#login_qrcode_container img, .wr_login_modal_qr_img, .wxlogin-container img, img[src*="qrcode"], img[src*="qrconnect"]'
      );
      for (let i = 0; i < cands.length; i++) {
        const img = cands[i];
        if (own && own.contains(img)) continue;
        if (img.src && img.naturalWidth >= 40) {
          box.innerHTML = '<div class="wmx-qr-tip wmx-qr-ok">用微信扫码登录</div>' +
            '<img class="wmx-qr-img" alt="登录二维码" src="' + esc(img.src) + '">';
          clearInterval(state.qrTimer);
          return;
        }
      }
    }, QR_WAIT_MS);
  }

  function stopPoll() {
    if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
    if (state.qrTimer) { clearInterval(state.qrTimer); state.qrTimer = null; }
  }

  function onLoggedIn() {
    stopPoll();
    const q = document.getElementById('wmx-qr');
    if (q) q.innerHTML = '';
    setLogin('logged', '登录成功，正在读取书架…');
    log('登录成功。', 'ok');
    setOpen(true);
    switchView('acc');
    refreshShelf();
  }

  function pollLogin() {
    stopPoll();
    state.pollLeft = LOGIN_POLL_MAX;
    setLogin('waiting');
    mirrorQr();
    state.pollTimer = setInterval(async () => {
      state.pollLeft--;
      if (state.pollLeft <= 0) {
        stopPoll();
        setLogin('guest', '等待超时。扫完码可点「检测」，或重新登录');
        return;
      }
      try {
        const r = await probeLogin();
        if (r.ok) onLoggedIn();
      } catch (e) { /* 瞬时错误忽略，继续轮询 */ }
    }, LOGIN_POLL_MS);
  }

  function startLoginFlow() {
    // 不在微信读书页面：没法在这里扫码，改成新开/切到微信读书标签页，
    // 登录态由浏览器持有，扫码后台秒级可探到，回来继续用即可
    if (!IS_WEREAD) {
      log('当前不在微信读书页面，正在为你打开微信读书用于扫码…');
      setLogin('waiting', '请在新开的微信读书页面扫码');
      openWereadTab();
      pollLogin();
      return;
    }

    log('开始登录：插件会唤起官方登录入口，请用微信扫码。');
    const t = findLoginTrigger();
    if (t) {
      try { t.click(); } catch (e) { /* ignore */ }
      log('已尝试唤起页面内的登录弹窗。', 'ok');
      pollLogin();
      return;
    }
    try { sessionStorage.setItem('wmx_auto_login', '1'); } catch (e) { /* ignore */ }
    log('当前页面没有登录入口，正在跳转微信读书首页…');
    location.href = 'https://weread.qq.com/';
  }

  async function refreshShelf() {
    if (state.running) return false;
    setBusy(true, '读取书架…');
    try {
      log('正在读取微信读书书架…');
      await loadAccounts((i, n) => setBusy(true, '读取公众号信息 ' + i + '/' + n));
      setBusy(false, '书架已读取');
      return true;
    } catch (e) {
      setBusy(false, '失败');
      log(errHint(e), 'err');
      if (e && (e.code === -2010 || e.code === -2012)) setLogin('guest', '登录态失效，请重新登录');
      return false;
    }
  }

  async function initLogin(autoTrigger) {
    const ok = await checkLogin(false);
    if (ok) {
      log('已登录微信读书。点「刷新关注列表」开始。', 'ok');
      return;
    }
    if (autoTrigger) {
      await sleep(1400);
      const t = findLoginTrigger();
      if (t) {
        try { t.click(); } catch (e) { /* ignore */ }
        log('已唤起登录弹窗，请用微信扫码。');
      } else {
        log('没找到页面上的登录入口，请手动点页面里的「登录」后扫码。', 'warn');
      }
      pollLogin();
    }
  }

  /* ---------------- 状态与日志 ---------------- */
  const state = {
    accounts: [],       // 展示用合并列表（本地 + 书架）
    shelf: [],          // 微信读书书架公众号
    custom: [],         // 本地添加公众号
    articles: [],
    running: false,
    lastRaw: null,
    login: 'unknown',   // unknown | guest | waiting | logged
    pollTimer: null,
    pollLeft: 0,
    qrTimer: null,
    firstOpen: true,
    firstEver: false,   // 首次安装使用，用于自动展开一次
    page: null,         // 非微信读书页面时，当前页面的文章信息
    view: 'acc',        // acc | art
    shelfHidden: false, // 微信读书关注列表是否隐藏
    mpToken: '',
    search: { kw: '', list: [], more: false, loading: false },
    articleVisible: Object.create(null),
    articleHidden: Object.create(null),
    theme: 'dark'
  };

  /* 本地缓存：让抽屉再次打开时立刻能看到上次的公众号与文章。
     有扩展存储时优先用 chrome.storage.local —— 这样 weread.qq.com 与
     mp.weixin.qq.com 共享同一份缓存，在哪个页面拉的数据都看得到；
     拿不到就退化为页面 localStorage。 */
  const LS = {
    get(k, d) {
      try {
        const v = localStorage.getItem(k);
        return v ? JSON.parse(v) : d;
      } catch (e) { return d; }
    },
    set(k, v) {
      try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* 配额满等情况忽略 */ }
    }
  };

  function hasStorage() {
    return typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local;
  }

  const stor = {
    async get(k, d) {
      if (hasStorage()) {
        try {
          const r = await chrome.storage.local.get(k);
          if (r && r[k] !== undefined && r[k] !== null) return r[k];
        } catch (e) { /* 退化到 localStorage */ }
      }
      return LS.get(k, d);
    },
    set(k, v) {
      if (hasStorage()) {
        try { chrome.storage.local.set({ [k]: v }); return; } catch (e) { /* 退化 */ }
      }
      LS.set(k, v);
    }
  };

  /* 打开页面时先把缓存读进来（buildUI 之后直接渲染，避免闪一下空状态） */
  async function preload() {
    const accs = await stor.get('wmx_accounts', null);
    if (Array.isArray(accs) && accs.length) {
      state.shelf = accs.map((a) => ({
        bookId: a.bookId, title: a.title || '', isMp: MP_PREFIX.test(a.bookId)
      }));
    }
    const custom = await stor.get('wmx_custom', null);
    if (Array.isArray(custom)) {
      state.custom = custom.filter((a) => a && MP_PREFIX.test(a.bookId || '')).map((a) => ({
        bookId: a.bookId, title: a.title || '', source: a.source || 'link', addedAt: a.addedAt || 0
      }));
    }
    const token = await stor.get('wmx_mp_token', '');
    if (/^\d{5,20}$/.test(String(token))) state.mpToken = String(token);
    const arts = await stor.get('wmx_articles', null);
    if (Array.isArray(arts) && arts.length) state.articles = arts;
    const v = await stor.get('wmx_view', 'acc');
    state.view = (v === 'art') ? 'art' : 'acc';
    const theme = await stor.get('wmx_theme', 'dark');
    state.theme = theme === 'light' ? 'light' : 'dark';
    // 首次安装使用时自动展开一次，之后保持收起
    const seen = await stor.get('wmx_seen', false);
    state.firstEver = !seen;
    if (!seen) stor.set('wmx_seen', true);
  }

  function log(msg, kind) {
    const box = document.getElementById('wmx-log');
    if (!box) return;
    const line = document.createElement('div');
    line.className = 'wmx-logline' + (kind ? ' wmx-' + kind : '');
    const t = new Date();
    const p = (x) => String(x).padStart(2, '0');
    line.textContent = '[' + p(t.getHours()) + ':' + p(t.getMinutes()) + ':' + p(t.getSeconds()) + '] ' + msg;
    box.appendChild(line);
    box.scrollTop = box.scrollHeight;
  }

  let _toastBox = null;
  function toast(msg, kind) {
    if (!_toastBox || !_toastBox.parentNode) {
      _toastBox = document.createElement('div');
      _toastBox.id = 'wmx-toast';
      document.body.appendChild(_toastBox);
    }
    _toastBox.classList.toggle('wmx-light', state.theme === 'light');
    const item = document.createElement('div');
    item.className = 'wmx-toast-item' + (kind === 'ok' ? ' wmx-toast-ok' : kind === 'err' ? ' wmx-toast-err' : '');
    item.textContent = msg;
    _toastBox.appendChild(item);
    while (_toastBox.children.length > 4) _toastBox.removeChild(_toastBox.firstChild);
    requestAnimationFrame(() => requestAnimationFrame(() => item.classList.add('wmx-toast-in')));
    setTimeout(() => {
      item.classList.remove('wmx-toast-in');
      item.classList.add('wmx-toast-out');
      setTimeout(() => { if (item.parentNode) item.parentNode.removeChild(item); }, 200);
    }, 2600);
  }

  function setBusy(b, text) {
    state.running = b;
    const btn = document.getElementById('wmx-run');
    if (btn) { btn.disabled = b; btn.textContent = b ? '进行中…' : '拉取文章'; }
    const st = document.getElementById('wmx-status');
    if (st) st.dataset.busy = text || '';
    renderStatus();
  }

  /* ---------------- 渲染 ---------------- */
  function toggleShelfList() {
    state.shelfHidden = !state.shelfHidden;
    const list = document.getElementById('wmx-accounts');
    const kw = document.getElementById('wmx-acc-kw');
    // 折叠时清掉不可见的过滤词，避免展开后列表被隐形过滤
    if (state.shelfHidden && kw && kw.value) kw.value = '';
    if (list) list.hidden = state.shelfHidden;
    if (kw) kw.hidden = state.shelfHidden;
    if (state.shelfHidden) renderAccounts();
    const eye = document.getElementById('wmx-shelf-eye');
    if (eye) {
      eye.classList.toggle('wmx-eye-off', state.shelfHidden);
      eye.title = state.shelfHidden ? '显示关注列表' : '隐藏关注列表';
      eye.setAttribute('aria-label', eye.title);
      eye.setAttribute('aria-pressed', state.shelfHidden ? 'true' : 'false');
    }
  }

  function renderAccounts() {
    renderSelectedAccounts();
    const box = document.getElementById('wmx-accounts');
    if (box) {
      const kwEl = document.getElementById('wmx-acc-kw');
      const kw = kwEl ? (kwEl.value || '').trim().toLowerCase() : '';
      const matches = (a) => !kw ||
        (a.title || '').toLowerCase().indexOf(kw) >= 0 ||
        a.bookId.toLowerCase().indexOf(kw) >= 0;
      const shelfOnly = state.shelf.filter((a) => !state.custom.some((c) => c.bookId === a.bookId));
      if (!shelfOnly.length) {
        box.innerHTML = '<div class="wmx-empty">刷新微信读书书架后，这里会显示你已关注的公众号。</div>';
      } else {
        const shown = shelfOnly.map((a) => ({
          a: a, i: state.shelf.indexOf(a)
        })).filter((x) => matches(x.a));
        box.innerHTML = shown.length ? shown.map((x) =>
          '<div class="wmx-acc">' +
          '<span class="wmx-selected-account-dot"></span>' +
            '<span class="wmx-accname" title="' + esc(x.a.title || '未命名公众号') + '">' +
              esc(x.a.title || '(未命名 · 拉取后回填)') + '</span>' +
            '<button class="wmx-mini wmx-shelf-add" data-shelf-add="' + x.i + '">添加到查看列表</button>' +
          '</div>'
        ).join('') : '<div class="wmx-empty">没有匹配的公众号。</div>';
      }
    }
    const localCount = document.getElementById('wmx-custom-n');
    if (localCount) localCount.textContent = '查看范围 ' + state.custom.length + ' 个';
    updateCounts();
  }

  function renderSelectedAccounts() {
    const box = document.getElementById('wmx-selected-accounts');
    if (!box) return;
    const selected = state.custom;
    box.innerHTML = selected.length ? selected.map((a) =>
      '<div class="wmx-selected-account">' +
        '<span class="wmx-selected-account-dot"></span>' +
        '<span class="wmx-selected-account-name" title="' + esc(a.title || a.bookId) + '">' +
          esc(a.title || '(未命名 · 拉取后回填)') +
        '</span>' +
        '<span class="wmx-tag wmx-tag-' + (a.source === 'custom' ? 'c' : 's') + '">' +
          (a.source === 'custom' ? '本地' : '书架') + '</span>' +
        '<button class="wmx-accdel" data-selected-del="' + esc(a.bookId) + '" title="移出查看列表">×</button>' +
      '</div>'
    ).join('') : '<div class="wmx-empty">文章查看范围还是空的，请先搜索、粘贴文章链接，或从下方书架列表添加。</div>';
  }

  // 抽屉是窄栏，文章行改成两行式：标题一行，公众号 / 时间 / 原文 一行
  function renderArticles(rows) {
    const box = document.getElementById('wmx-result');
    if (box) {
      if (!rows.length) {
        box.innerHTML = '<div class="wmx-empty">' + (state.articles.length
          ? '当前筛选条件下没有匹配的文章，清空关键词或放宽日期试试。'
          : '还没有文章。请先添加公众号到“文章查看范围”，再点击“拉取文章”。') + '</div>';
      } else {
        const groups = [];
        const grouped = Object.create(null);
        rows.slice(0, 500).forEach((r) => {
          const key = groupKeyOf(r);
          if (!grouped[key]) {
            grouped[key] = [];
            groups.push({ key: key, name: r.account || '未命名公众号', rows: grouped[key] });
          }
          grouped[key].push(r);
        });
        const body = groups.map((group) => {
          const groupKey = group.key;
          const hidden = !!state.articleHidden[groupKey];
          const visible = Math.min(group.rows.length, state.articleVisible[groupKey] || 3);
          const hasMore = visible < group.rows.length;
          const listHtml = hidden ? '' :
            group.rows.slice(0, visible).map((r) =>
              '<div class="wmx-art">' +
                '<a class="wmx-art-t" href="' + esc(r.url || '#') + '" target="_blank" rel="noreferrer" title="' +
                  esc(r.title) + (r.time ? '　' + r.time : '') + '">' + esc(r.title || '(无标题)') + '</a>' +
                '<div class="wmx-art-m">' +
                  '<span class="wmx-art-d">' + esc(r.time || '') + '</span>' +
                  (r.url
                    ? '<a class="wmx-art-o" href="' + esc(r.url) + '" target="_blank" rel="noreferrer">原文 ↗</a>'
                    : '<span class="wmx-art-o wmx-no">无链接</span>') +
                '</div>' +
              '</div>'
            ).join('') +
            (hasMore ? '<button class="wmx-more-art" data-art-more="' + esc(groupKey) + '">显示更多（剩余 ' +
              (group.rows.length - visible) + ' 篇）</button>' : '');
          return (
          '<section class="wmx-art-group">' +
            '<h3 class="wmx-art-group-title">' + esc(group.name) +
              '<span class="wmx-art-group-count">' + group.rows.length + ' 篇' + (hidden ? ' · 已隐藏' : '') + '</span>' +
              '<button class="wmx-mini wmx-eye wmx-art-group-eye' + (hidden ? ' wmx-eye-off' : '') + '"' +
                ' data-art-hide="' + esc(groupKey) + '"' +
                ' title="' + (hidden ? '显示该公众号文章' : '隐藏该公众号文章') + '"' +
                ' aria-label="' + (hidden ? '显示该公众号文章' : '隐藏该公众号文章') + '"' +
                ' aria-pressed="' + (hidden ? 'true' : 'false') + '">👁️</button>' +
            '</h3>' +
            listHtml +
          '</section>'
          );
        }).join('');
        const more = rows.length > 500
          ? '<div class="wmx-empty">仅预览前 500 条，导出可得全部 ' + rows.length + ' 条</div>' : '';
        box.innerHTML = body + more;
      }
    }
    updateCounts();
  }

  // 按当前筛选条件重绘文章列表（不重写 state.articles）
  function renderResult() {
    renderArticles(filtered());
  }

  function setTheme(theme) {
    state.theme = theme === 'light' ? 'light' : 'dark';
    const panel = document.getElementById('wmx-panel');
    if (panel) {
      panel.classList.toggle('wmx-light', state.theme === 'light');
      panel.classList.toggle(WMX_NS + '-light', state.theme === 'light');
    }
    const dock = document.getElementById('wmx-dock');
    if (dock) {
      dock.classList.toggle('wmx-light', state.theme === 'light');
      dock.classList.toggle(WMX_NS + '-light', state.theme === 'light');
    }
    const button = document.getElementById('wmx-theme');
    if (button) button.textContent = state.theme === 'light' ? '深色' : '浅色';
    stor.set('wmx_theme', state.theme);
  }

  /* ---------------- 非微信读书页面：环境提示 + 当前文章 ---------------- */

  // 顶部环境提示：说明当前在哪个站点、数据走哪条通道
  function renderEnv() {
    const box = document.getElementById('wmx-env');
    if (!box) return;
    if (IS_WEREAD) { box.hidden = true; box.innerHTML = ''; return; }
    box.hidden = false;
    box.innerHTML =
      '<span class="wmx-env-txt">当前在 ' + esc(location.hostname) +
      '，接口数据由扩展后台转发</span>' +
      '<button class="wmx-mini" id="wmx-open-wr">打开微信读书</button>';
    const go = document.getElementById('wmx-open-wr');
    if (go) go.addEventListener('click', openWereadTab);
  }

  // 读当前页面这篇公众号文章的 标题 / 号名 / 发布时间 / 链接
  function readCurrentPage() {
    if (!IS_MP) return null;
    const txt = (sel) => {
      const el = document.querySelector(sel);
      return el ? (el.textContent || '').replace(/\s+/g, ' ').trim() : '';
    };
    const title = txt('#activity-name') || txt('.rich_media_title') || txt('h1.rich_media_title');
    const account = txt('#js_name') || txt('.rich_media_meta_nickname') || txt('#js_profile_qrcode_name');
    const time = txt('#publish_time') || txt('.rich_media_meta_text');
    if (!title && !account) return null;

    // 地址优先保留 /s/<token> 短链形态，去掉跟踪参数
    let url = location.href;
    const m = url.match(/^(https?:\/\/mp\.weixin\.qq\.com\/s\/[A-Za-z0-9_-]+)/);
    url = m ? m[1] : url.split('#')[0];

    return { title: title, account: account, time: time, url: url };
  }

  function renderCtx() {
    const box = document.getElementById('wmx-ctx');
    if (!box) return;
    const cur = readCurrentPage();
    state.page = cur;
    if (!cur) { box.hidden = true; return; }
    box.hidden = false;
    const t = document.getElementById('wmx-ctx-title');
    if (t) t.textContent = cur.title || '(未读到标题)';
    const a = document.getElementById('wmx-ctx-acc');
    if (a) a.textContent = (cur.account || '未知公众号') + (cur.time ? ' · ' + cur.time : '');
    const ty = document.getElementById('wmx-ctx-type');
    if (ty) ty.textContent = '公众号文章';
  }

  function copyCurrentPage() {
    const cur = state.page || readCurrentPage();
    if (!cur) { log('当前页面没读到文章信息', 'warn'); return; }
    navigator.clipboard.writeText((cur.title || '') + '\n' + cur.url)
      .then(() => log('已复制当前文章的「标题 + 链接」'))
      .catch(() => log('复制失败，请手动复制地址栏链接', 'warn'));
  }

  function addCurrentPage() {
    const cur = state.page || readCurrentPage();
    if (!cur) { log('当前页面没读到文章信息', 'warn'); return; }
    if (state.articles.some((r) => r.url && r.url === cur.url)) {
      log('这篇已经在列表里了，没有重复收录。', 'warn');
      switchView('art');
      return;
    }
    state.articles.unshift({
      account: cur.account || '', bookId: '', title: cur.title || '',
      time: cur.time || '', ts: 0, url: cur.url, reviewId: ''
    });
    saveArticlesCache();
    renderResult();
    updateCounts();
    log('已收录：' + (cur.title || cur.url), 'ok');
    switchView('art');
  }

  async function probeFirstPage(bookId) {
    const json = await api(EP.mpArticles + '?bookId=' + encodeURIComponent(bookId) + '&offset=0');
    return flattenArticles(json, bookId, '').length;
  }

  async function addFromInput() {
    const input = document.getElementById('wmx-add-input');
    const parsed = parseMpInput(input ? input.value : '');
    if (!parsed.ok) {
      const hint = addReasonHint(parsed.reason);
      toast(hint, 'err');
      log(hint, 'warn');
      return;
    }
    if (state.custom.some((a) => a.bookId === parsed.bookId)) {
      toast('这个号已经在文章查看范围里了。', 'err');
      log('这个号已经在文章查看范围里了：' + parsed.bookId, 'warn');
      return;
    }

    // 先立即加入并给出反馈，名称和文章校验放到后台补全，避免接口卡住导致「没反应」
    const record = await addCustomAccount(parsed.bookId, '', parsed.from);
    if (!record) {
      toast('添加失败：这个号已经在列表里了。', 'err');
      return;
    }
    if (input) input.value = '';
    toast('已添加到文章查看范围：' + (record.title || record.bookId), 'ok');

    if (state.login === 'guest') {
      log('当前未登录，先保存公众号标识；登录后拉取文章会补全名称。', 'warn');
    } else {
      fetchAccountName(parsed.bookId).then((title) => {
        if (title) { setAccountTitle(parsed.bookId, title); log('号名：' + title, 'ok'); }
      }).catch((e) => log('取号名失败：' + errHint(e), 'warn'));
      probeFirstPage(parsed.bookId).then((count) => {
        log(count ? '验证通过：首页可读取 ' + count + ' 篇文章。' :
          '该公众号首页返回 0 篇，可能尚未被微信读书收录。', count ? 'ok' : 'warn');
      }).catch((e) => log('文章接口验证失败：' + errHint(e), 'warn'));
    }
  }

  async function addCurrentMpAccount() {
    const current = state.page || readCurrentPage();
    const biz = readBizFromPage();
    const bookId = bizToBookId(biz);
    if (!bookId) {
      toast('当前页面没有读到 __biz，请确认是公众号文章页，或粘贴文章长链接添加。', 'err');
      log('当前页面没有读到 __biz，请确认是公众号文章页，或粘贴文章长链接添加。', 'warn');
      return;
    }
    if (state.custom.some((a) => a.bookId === bookId)) {
      toast('这个号已经在文章查看范围里了。', 'err');
      log('这个号已经在文章查看范围里了：' + bookId, 'warn');
      return;
    }
    let title = current && current.account || '';
    const record = await addCustomAccount(bookId, title, 'page');
    if (record) {
      toast('已添加到文章查看范围：' + (title || bookId), 'ok');
    } else {
      toast('添加失败：这个号已经在列表里了。', 'err');
    }
    if (state.login !== 'guest') {
      fetchAccountName(bookId).then((t) => {
        if (t) setAccountTitle(bookId, t);
      }).catch(() => { /* 后续拉取时补全 */ });
    }
  }

  async function pushSelectedCustom() {
    const ids = state.custom.map((a) => a.bookId);
    if (!ids.length) {
      toast('文章查看范围为空，暂时没有可添加到公众号关注的号。', 'err');
      log('文章查看范围为空，暂时没有可加入书架的公众号。', 'warn');
      return;
    }
    if (state.login !== 'logged') {
      const ok = await checkLogin(true);
      if (!ok) {
        toast('需要先登录微信读书才能添加到公众号关注。', 'err');
        log('需要先登录微信读书才能加入书架。', 'warn');
        startLoginFlow();
        return;
      }
    }
    await pushToWereadShelf(ids);
  }

  async function addShelfToCustom(index) {
    const account = state.shelf[index];
    if (!account) return;
    await addCustomAccount(account.bookId, account.title, 'shelf');
  }

  function mpSearchErr(json) {
    const resp = json && json.base_resp;
    const code = resp ? Number(resp.ret) : 0;
    if (!code) return null;
    const err = new Error('searchbiz-error');
    err.code = code;
    err.msg = resp.err_msg || resp.errmsg || '';
    return err;
  }

  function mpErrHint(err) {
    if (err && err.code === 'no-token') return '按名字搜索需要登录公众号后台（不是微信读书），请先打开并登录公众号后台。';
    if (err && err.code === 200003) return '公众号后台登录态已过期，请重新打开并登录公众号后台。';
    if (err && err.code === 200013) return '公众号后台搜索被限流，请稍后重试，或改用文章链接添加。';
    if (err && err.notJson) return '公众号后台返回的不是 JSON，请确认后台已登录。';
    return (err && err.message) || '公众号后台搜索失败';
  }

  function parseSearchBiz(json) {
    const list = json && Array.isArray(json.list) ? json.list : [];
    return list.map((item) => ({
      name: firstStr(item.nickname, item.nick_name),
      biz: firstStr(item.fakeid),
      bookId: bizToBookId(item.fakeid),
      alias: firstStr(item.alias),
      desc: firstStr(item.signature),
      avatar: firstStr(item.round_head_img),
      serviceType: Number(item.service_type),
      verified: Number(item.verify_status)
    })).filter((item) => item.name);
  }

  function searchBizPath(keyword, begin, token) {
    return '/cgi-bin/searchbiz?action=search_biz&scene=1&query=' +
      encodeURIComponent(keyword) + '&begin=' + (begin || 0) +
      '&count=5&token=' + token + '&lang=zh_CN&f=json&ajax=1';
  }

  async function searchBizDirect(keyword, begin, token) {
    const res = await fetch(searchBizPath(keyword, begin, token), {
      method: 'GET', credentials: 'same-origin', cache: 'no-store',
      headers: { 'Accept': 'application/json, text/plain, */*', 'X-Requested-With': 'XMLHttpRequest' }
    });
    const text = await res.text();
    try { return JSON.parse(text); } catch (e) {
      const err = new Error('HTTP ' + res.status + ' ' + text.slice(0, 80));
      err.notJson = true;
      throw err;
    }
  }

  async function searchBizViaBg(keyword, begin, token) {
    const resp = await bgSend({ type: 'wmx:searchbiz', query: keyword, begin: begin || 0, token: token });
    if (!resp || !resp.ok) throw new Error((resp && resp.error) || '后台搜索通道不可用');
    if (resp.notJson) {
      const err = new Error('HTTP ' + resp.http + ' ' + (resp.text || ''));
      err.notJson = true;
      throw err;
    }
    return resp.json;
  }

  async function resolveMpToken() {
    const pageToken = readMpTokenFromPage();
    if (pageToken) {
      state.mpToken = pageToken;
      stor.set('wmx_mp_token', pageToken);
      return pageToken;
    }
    if (state.mpToken) return state.mpToken;
    if (hasRuntime()) {
      const resp = await bgSend({ type: 'wmx:find-mp-token' });
      if (resp && resp.ok && resp.token) {
        state.mpToken = resp.token;
        stor.set('wmx_mp_token', resp.token);
        return resp.token;
      }
    }
    return '';
  }

  async function searchBizAccounts(keyword, begin) {
    const token = await resolveMpToken();
    if (!token) {
      const err = new Error('缺少公众号后台 token');
      err.code = 'no-token';
      throw err;
    }
    const json = readMpTokenFromPage()
      ? await searchBizDirect(keyword, begin, token)
      : await searchBizViaBg(keyword, begin, token);
    const error = mpSearchErr(json);
    if (error) throw error;
    return parseSearchBiz(json);
  }

  function setSearchBusy(busy) {
    const button = document.getElementById('wmx-search-go');
    if (button) { button.disabled = busy; button.textContent = busy ? '搜索中…' : '搜索'; }
    const more = document.getElementById('wmx-search-more');
    if (more) more.disabled = busy;
  }

  function renderSearchNote() {
    // 在公众号后台页面时，先从页面里捞 token，避免误判成“未登录”
    if (!state.mpToken && IS_MP) {
      const t = readMpTokenFromPage();
      if (t) { state.mpToken = t; stor.set('wmx_mp_token', t); }
    }
    const note = document.getElementById('wmx-search-note');
    if (!note) return;
    const connected = !!state.mpToken;
    note.textContent = connected ? '已连接公众号后台' : '⚠️ 需登录公众号后台';
    note.className = 'wmx-count' + (connected ? ' wmx-count-ok' : ' wmx-count-err');
    if (connected) {
      note.removeAttribute('role');
      note.removeAttribute('tabindex');
      note.title = '已连接公众号后台';
    } else {
      note.setAttribute('role', 'button');
      note.setAttribute('tabindex', '0');
      note.title = '点击登录公众号后台';
    }
  }

  function renderSearchResults() {
    const box = document.getElementById('wmx-searchres');
    if (!box) return;
    renderSearchNote();
    if (!state.search.list.length) { box.hidden = true; box.innerHTML = ''; return; }
    let html = '<div class="wmx-searchres-head"><b>搜索结果</b>' +
      '<button class="wmx-searchres-close" id="wmx-searchres-close" type="button" aria-label="关闭搜索结果">×</button></div>' +
      state.search.list.map((item, index) => {
      const type = item.serviceType === 1 ? '服务号' : item.serviceType === 2 ? '企业号' : '订阅号';
      const exists = state.custom.some((a) => a.bookId === item.bookId);
      return '<div class="wmx-sr">' +
        (item.avatar
          ? '<img class="wmx-sr-av" src="' + esc(item.avatar) + '" data-ch="' + esc(item.name) + '" referrerpolicy="no-referrer" alt="">'
          : '<span class="wmx-sr-av wmx-sr-avt">' + esc(item.name.slice(0, 1)) + '</span>') +
        '<div class="wmx-sr-main"><div class="wmx-sr-name">' + esc(item.name) +
        '<i class="wmx-sr-tag">' + type + '</i>' +
        (item.verified ? '<i class="wmx-sr-tag wmx-sr-v">已认证</i>' : '') +
        '</div>' + (item.alias ? '<div class="wmx-sr-id">微信号 ' + esc(item.alias) + '</div>' : '') +
        (item.desc ? '<div class="wmx-sr-desc">' + esc(item.desc) + '</div>' : '') +
        '</div>' + (exists ? '<span class="wmx-sr-in">已在列表</span>' :
          '<button class="wmx-mini wmx-sr-add" data-s="' + index + '">添加</button>') + '</div>';
    }).join('');
    if (state.search.more) html += '<div class="wmx-actions"><button class="wmx-mini" id="wmx-search-more">继续搜索（还有更多）</button></div>';
    box.hidden = false;
    box.innerHTML = html;
  }

  async function doSearchAccounts(more) {
    const input = document.getElementById('wmx-search-input');
    const keyword = more ? state.search.kw : String(input && input.value || '').trim();
    if (!keyword) { log('先输入公众号名称。', 'warn'); return; }
    if (state.search.loading) return;
    const begin = more ? state.search.list.length : 0;
    state.search.loading = true;
    state.search.kw = keyword;
    if (!more) state.search.list = [];
    setSearchBusy(true);
    try {
      if (more) await sleep(DELAY_SEARCH);
      const rows = await searchBizAccounts(keyword, begin);
      state.search.list = more ? state.search.list.concat(rows) : rows;
      state.search.more = rows.length >= SEARCH_COUNT;
      log('得到 ' + rows.length + ' 个搜索结果，点“添加”收录。', 'ok');
    } catch (e) {
      log(mpErrHint(e), 'warn');
    } finally {
      state.search.loading = false;
      setSearchBusy(false);
      renderSearchResults();
    }
  }

  async function addSearchResult(index) {
    const result = state.search.list[index];
    if (!result || !result.bookId) {
      log('该搜索结果无法换算公众号 bookId。', 'warn');
      return;
    }
    await addCustomAccount(result.bookId, result.name, 'search');
    renderSearchResults();
  }

  async function openMpBackend() {
    if (hasRuntime()) {
      const resp = await bgSend({ type: 'wmx:open-mp' });
      if (resp && resp.ok) {
        log(resp.reused ? '已切到公众号后台标签页。' : '已打开公众号后台，请登录后回来搜索。', 'ok');
        return;
      }
    }
    window.open(MP_ORIGIN + '/', '_blank');
  }

  async function openWereadTab() {
    if (hasRuntime()) {
      try {
        const r = await bgSend({ type: 'wmx:open-weread' });
        if (r && r.ok) {
          log(r.reused ? '已切到已打开的微信读书标签页。' : '已新开微信读书标签页。', 'ok');
          return;
        }
        if (r && r.error) log('打开微信读书失败：' + r.error, 'warn');
      } catch (e) { /* 落到下面的兜底 */ }
    }
    try { window.open(WR_ORIGIN + '/', '_blank'); } catch (e) { /* ignore */ }
  }

  /* ---------------- 抽屉控制 ---------------- */
  function switchView(name) {
    state.view = name === 'art' ? 'art' : 'acc';
    const acc = document.getElementById('wmx-view-acc');
    const art = document.getElementById('wmx-view-art');
    if (!acc || !art) return;
    acc.hidden = state.view !== 'acc';
    art.hidden = state.view !== 'art';
    const tabs = document.querySelectorAll('#wmx-panel .wmx-tab');
    for (let i = 0; i < tabs.length; i++) {
      tabs[i].classList.toggle('wmx-tab-on', tabs[i].getAttribute('data-tab') === state.view);
    }
    stor.set('wmx_view', state.view);
  }

  function updateCounts() {
    const na = document.getElementById('wmx-n-acc');
    if (na) na.textContent = String(state.accounts.length);
    const nt = document.getElementById('wmx-n-art');
    if (nt) nt.textContent = String(state.articles.length);
    const badge = document.getElementById('wmx-badge');
    if (badge) {
      const n = state.articles.length;
      badge.textContent = n > 999 ? '999+' : String(n);
      badge.classList.toggle('wmx-badge-on', n > 0);
    }
    const picked = document.getElementById('wmx-picked');
    if (picked) {
      picked.textContent = '共 ' + state.custom.length + ' 个';
    }
    const fl = document.getElementById('wmx-filtered');
    if (fl) {
      fl.textContent = state.articles.length
        ? '匹配 ' + visibleRows().length + ' / ' + state.articles.length + ' 条' : '';
    }
    renderStatus();
  }

  function renderStatus() {
    const st = document.getElementById('wmx-status');
    if (!st) return;
    st.textContent = state.running ? st.dataset.busy || '' :
      (state.articles.length ? state.articles.length + ' 篇已入库' :
        (state.custom.length ? '待拉取 ' + state.custom.length + ' 个号' : ''));
  }

  function setOpen(open) {
    const panel = document.getElementById('wmx-panel');
    const dock = document.getElementById('wmx-dock');
    if (!panel) return;
    panel.classList.toggle('wmx-open', open);
    if (dock) dock.classList.toggle('wmx-dock-open', open);
    updateCounts();
    if (open && state.firstOpen) {
      state.firstOpen = false;
      if (state.login === 'unknown') checkLogin(true);
    }
  }

  /* ---------------- 导出 ---------------- */
  function filtered() {
    const kwEl = document.getElementById('wmx-kw');
    const fromEl = document.getElementById('wmx-from');
    const toEl = document.getElementById('wmx-to');
    const kw = kwEl ? (kwEl.value || '').trim() : '';
    const from = fromEl ? (fromEl.value || '').trim() : '';
    const to = toEl ? (toEl.value || '').trim() : '';
    return state.articles.filter((r) => {
      if (kw && (r.title || '').indexOf(kw) === -1 && (r.account || '').indexOf(kw) === -1) return false;
      if (from && r.time && r.time.slice(0, 10) < from) return false;
      if (to && r.time && r.time.slice(0, 10) > to) return false;
      return true;
    });
  }

  function groupKeyOf(r) { return r.bookId || r.account || '未命名公众号'; }

  // 关键词/日期筛选之后，再扣除被“隐藏”的公众号分组；用于导出与计数。
  function visibleRows() {
    return filtered().filter((r) => !state.articleHidden[groupKeyOf(r)]);
  }

  function exportCsv() {
    const rows = visibleRows();
    if (!rows.length) { log('没有可导出的数据', 'warn'); return; }
    const q = (s) => '"' + String(s == null ? '' : s).replace(/"/g, '""') + '"';
    const lines = ['﻿序号,公众号,标题,发布时间,链接'];
    rows.forEach((r, i) => {
      lines.push([i + 1, r.account, r.title, r.time, r.url].map(q).join(','));
    });
    saveBlob('公众号文章-' + stamp() + '.csv', lines.join('\r\n'), 'text/csv');
    log('已导出 CSV：' + rows.length + ' 条');
  }

  function exportMd() {
    const rows = visibleRows();
    if (!rows.length) { log('没有可导出的数据', 'warn'); return; }
    const md = ['# 公众号文章列表', '', '导出时间：' + new Date().toLocaleString(), '共 ' + rows.length + ' 条', '',
      '| # | 公众号 | 标题 | 发布时间 | 链接 |', '| --- | --- | --- | --- | --- |']
      .concat(rows.map((r, i) =>
        '| ' + (i + 1) + ' | ' + (r.account || '').replace(/\|/g, '\\|') +
        ' | [' + (r.title || '').replace(/\|/g, '\\|') + '](' + r.url + ')' +
        ' | ' + (r.time || '') + ' | ' + r.url + ' |'))
      .join('\n');
    saveBlob('公众号文章-' + stamp() + '.md', md, 'text/markdown');
    log('已导出 Markdown：' + rows.length + ' 条');
  }

  function copyLinks() {
    const rows = visibleRows();
    if (!rows.length) { log('没有可复制的数据', 'warn'); return; }
    const text = rows.map((r) => r.url).filter(Boolean).join('\n');
    navigator.clipboard.writeText(text)
      .then(() => log('已复制 ' + rows.length + ' 条链接'))
      .catch(() => log('复制失败，请改用导出 CSV', 'warn'));
  }

  function copyTitleLinks() {
    const rows = visibleRows();
    if (!rows.length) { log('没有可复制的数据', 'warn'); return; }
    const text = rows.map((r) => (r.title || '') + '\n' + (r.url || '')).join('\n\n');
    navigator.clipboard.writeText(text)
      .then(() => log('已复制 ' + rows.length + ' 条「标题 + 链接」'))
      .catch(() => log('复制失败，请改用导出 CSV', 'warn'));
  }

  // 文章结果落一份精简缓存（去掉 raw 字段，避免撑爆 localStorage）
  function saveArticlesCache() {
    const slim = state.articles.slice(0, 800).map((r) => ({
      account: r.account, bookId: r.bookId, title: r.title, time: r.time,
      ts: r.ts, url: r.url, reviewId: r.reviewId
    }));
    stor.set('wmx_articles', slim);
  }

  function diagnose() {
    const sample = state.lastRaw || {};
    const payload = {
      time: new Date().toISOString(),
      url: location.href,
      accounts: state.accounts.map((a) => ({ bookId: a.bookId, title: a.title })),
      articlesCount: state.articles.length,
      lastRawSample: sample
    };
    saveBlob('wmx-diagnose-' + stamp() + '.json', JSON.stringify(payload, null, 2), 'application/json');
    log('已导出诊断文件。把它发给我，我照实际返回字段改解析逻辑。');
  }

  /* ---------------- UI ---------------- */
  function buildUI() {
    if (document.getElementById('wmx-dock')) return;

    /* 右侧常驻标签 */
    const dock = document.createElement('div');
    dock.id = 'wmx-dock';
    dock.dataset.wmxInstance = WMX_INSTANCE;
    dock.classList.add(WMX_NS);
    dock.innerHTML =
      '<div class="wmx-dock-btn" id="wmx-dock-btn" title="微信读书 · 公众号文章导出">' +
        '<span class="wmx-dock-ico">📄</span>' +
        '<span class="wmx-dock-txt">公众号导出</span>' +
        '<span class="wmx-dock-badge" id="wmx-badge">0</span>' +
      '</div>';
    document.body.appendChild(dock);

    /* 抽屉主体 */
    const panel = document.createElement('div');
    panel.id = 'wmx-panel';
    panel.dataset.wmxInstance = WMX_INSTANCE;
    panel.classList.add(WMX_NS);
    panel.innerHTML = `
      <div class="wmx-head">
        <span class="wmx-head-title">
          <span class="wmx-title">微信读书 · 公众号文章导出</span>
          <a class="wmx-project-link" href="https://github.com/drowning-in-codes/VibeProjects/tree/main/wechat_article_explorer" target="_blank" rel="noopener noreferrer">查看项目 <span class="wmx-project-icon" aria-hidden="true">&lt;/&gt;</span></a>
        </span>
        <span class="wmx-head-actions">
          <button class="wmx-theme" id="wmx-theme" title="切换浅色/深色模式">浅色</button>
          <span class="wmx-close" id="wmx-close" title="收起（Esc）">×</span>
        </span>
      </div>

      <div class="wmx-loginwrap">
        <div id="wmx-loginbar" class="wmx-loginbar"><span class="wmx-dot"></span><b>登录状态未知</b><span class="wmx-note">正在检测…</span></div>
        <div id="wmx-qr" class="wmx-qr"></div>
      </div>

      <div class="wmx-env" id="wmx-env" hidden></div>

      <div class="wmx-ctx" id="wmx-ctx" hidden>
        <div class="wmx-ctx-h"><b>当前页面</b><span id="wmx-ctx-type"></span></div>
        <div class="wmx-ctx-t" id="wmx-ctx-title"></div>
        <div class="wmx-ctx-m"><span id="wmx-ctx-acc"></span></div>
        <div class="wmx-actions">
          <button class="wmx-btn wmx-primary" id="wmx-ctx-add">收录这篇</button>
          <button class="wmx-btn" id="wmx-ctx-addacc">收录这个号</button>
          <button class="wmx-mini" id="wmx-ctx-copy">复制标题+链接</button>
        </div>
      </div>

      <div class="wmx-tabs">
        <button class="wmx-tab wmx-tab-on" data-tab="acc">公众号 <i id="wmx-n-acc">0</i></button>
        <button class="wmx-tab" data-tab="art">文章 <i id="wmx-n-art">0</i></button>
      </div>

      <div class="wmx-view" id="wmx-view-acc">
        <div class="wmx-sec">
          <div class="wmx-sec-h">
            <b>文章查看与获取</b>
            <span class="wmx-count" id="wmx-picked">共 0 个</span>
          </div>
          <div class="wmx-selected-accounts" id="wmx-selected-accounts">
            <div class="wmx-empty">文章查看范围还是空的，请先从下方添加公众号。</div>
          </div>
          <div class="wmx-hint wmx-tipline">
            <span class="wmx-info" data-wmx-tip="列表中的公众号会作为本次文章拉取范围。添加公众号后，点击下方“拉取文章”即可开始获取。" aria-label="文章查看范围说明">i</span>
            <span>文章查看范围说明</span>
          </div>
          <div class="wmx-opts">
            <label>每个号最多 <input id="wmx-limit" type="number" min="0" value="10" class="wmx-num"> 篇（0=不限）</label>
          </div>
          <div class="wmx-actions">
            <button class="wmx-btn wmx-primary" id="wmx-run">拉取文章</button>
            <button class="wmx-mini" id="wmx-diag">诊断</button>
            <span class="wmx-status" id="wmx-status"></span>
          </div>
          <div class="wmx-hint wmx-tipline">
            <span class="wmx-info" data-wmx-tip="每次翻页间隔 1.3 秒，用于降低触发微信读书频率限制（-2041）的概率。公众号较多时建议分批拉取。" aria-label="翻页间隔说明">i</span>
            <span>请求节奏已自动控制</span>
          </div>
        </div>

        <div class="wmx-sec">
          <div class="wmx-sec-h">
            <b>添加公众号到查看范围</b>
            <span class="wmx-count" id="wmx-custom-n">查看范围 0 个</span>
          </div>
          <div class="wmx-sub">① 搜索公众号（需登录公众号后台）</div>
          <div class="wmx-addbox">
            <input id="wmx-search-input" class="wmx-txt wmx-add-input" placeholder="输入公众号名称，如 动漫IT收看号">
            <button class="wmx-btn wmx-primary" id="wmx-search-go">搜索</button>
          </div>
          <div class="wmx-actions">
            <button class="wmx-mini" id="wmx-mp-open">打开公众号后台</button>
            <span class="wmx-count" id="wmx-search-note" role="button" tabindex="0" title="点击登录公众号后台">需登录公众号后台</span>
          </div>
          <div class="wmx-searchres" id="wmx-searchres" hidden></div>
          <div class="wmx-sub">② 也可以用文章链接或 __biz 添加 <a class="wmx-help" href="https://github.com/drowning-in-codes/VibeProjects/blob/main/wechat_article_explorer/README.md#%E5%85%AC%E4%BC%97%E5%8F%B7%E7%AE%A1%E7%90%86" target="_blank" rel="noopener" data-wmx-tip="__biz 是微信公众号的唯一标识，藏在文章链接的 __biz= 参数里，用于定位并拉取该公众号。点击此图标查看更详细的说明。" aria-label="什么是 __biz，点击查看说明">?</a></div>
          <div class="wmx-addbox">
            <input id="wmx-add-input" class="wmx-txt wmx-add-input" placeholder="文章链接 / __biz / MP_WXS_数字">
            <button class="wmx-btn wmx-primary" id="wmx-add-go">添加</button>
          </div>
          <div class="wmx-actions">
            <button class="wmx-mini" id="wmx-add-cur" hidden>将当前页面公众号加到查看范围</button>
            <button class="wmx-mini" id="wmx-add-shelf">将查看范围公众号添加到公众号关注</button>
          </div>
          <div class="wmx-hint wmx-tipline">
            <span class="wmx-info" data-wmx-tip="可粘贴公众号文章完整链接、__biz、fakid 或 MP_WXS_数字添加，不必先关注；在公众号文章页也可以直接点击“收录这个号”。" aria-label="添加公众号说明">i</span>
            <span>添加方式说明</span>
          </div>
        </div>

        <div class="wmx-sec">
          <div class="wmx-sec-h">
            <b><span aria-hidden="true">📚</span> 微信读书关注的公众号</b>
            <span class="wmx-sec-actions">
              <button class="wmx-mini wmx-eye" id="wmx-shelf-eye" title="隐藏关注列表" aria-label="隐藏关注列表" aria-pressed="false">👁️</button>
              <button class="wmx-mini" id="wmx-refresh">刷新关注列表</button>
            </span>
          </div>
          <div class="wmx-hint wmx-tipline">
            <span class="wmx-info" data-wmx-tip="这里是微信读书中已关注的公众号；点击某个公众号旁的“添加到查看列表”后，它才会参与文章拉取。" aria-label="微信读书关注列表说明">i</span>
            <span>微信读书关注列表说明</span>
          </div>
          <input id="wmx-acc-kw" class="wmx-txt" placeholder="搜索已关注公众号名称">
          <div class="wmx-accounts" id="wmx-accounts"><div class="wmx-empty">还没有公众号。可添加文章链接，或刷新微信读书关注列表。</div></div>
        </div>

        <div class="wmx-sec">
          <div class="wmx-sec-h">
            <b>运行记录</b>
            <button class="wmx-mini" id="wmx-logclear">清空</button>
          </div>
          <div class="wmx-log" id="wmx-log"></div>
        </div>
      </div>

      <div class="wmx-view" id="wmx-view-art" hidden>
        <div class="wmx-sec">
          <div class="wmx-sec-h">
            <b>筛选与导出文章</b>
            <span class="wmx-count" id="wmx-filtered"></span>
          </div>
          <div class="wmx-opts">
            <label>标题/公众号包含 <input id="wmx-kw" class="wmx-txt" placeholder="如 新番 / 演唱会"></label>
            <label>起 <input id="wmx-from" type="date" class="wmx-date"></label>
            <label>止 <input id="wmx-to" type="date" class="wmx-date"></label>
          </div>
          <div class="wmx-actions">
            <button class="wmx-btn" id="wmx-csv">导出 CSV</button>
            <button class="wmx-btn" id="wmx-md">导出 Markdown</button>
            <button class="wmx-btn" id="wmx-copy">复制全部链接</button>
            <button class="wmx-btn" id="wmx-copy2">复制标题+链接</button>
          </div>
        </div>

        <div class="wmx-sec">
          <div class="wmx-result" id="wmx-result"><div class="wmx-empty">还没有文章。请先添加公众号到文章查看范围，再点击“拉取文章”。</div></div>
        </div>
      </div>`;
    document.body.appendChild(panel);

    /* ---- 事件绑定 ---- */
    const dockBtn = document.getElementById('wmx-dock-btn');
    dockBtn.addEventListener('click', () => setOpen(!panel.classList.contains('wmx-open')));
    document.getElementById('wmx-close').addEventListener('click', () => setOpen(false));
    document.addEventListener('keydown', (ev) => {
      if (ev.key === 'Escape' && panel.classList.contains('wmx-open')) setOpen(false);
    });

    const tabs = panel.querySelectorAll('.wmx-tab');
    for (let i = 0; i < tabs.length; i++) {
      tabs[i].addEventListener('click', () => switchView(tabs[i].getAttribute('data-tab')));
    }

    document.getElementById('wmx-refresh').addEventListener('click', async () => {
      if (state.login === 'guest') {
        log('还没登录，先点上面的「登录微信读书」。', 'warn');
        startLoginFlow();
        return;
      }
      if (state.login === 'unknown') await checkLogin(false);
      if (state.login === 'guest') {
        log('还没登录，先完成扫码登录。', 'warn');
        startLoginFlow();
        return;
      }
      switchView('acc');
      await refreshShelf();
    });

    document.getElementById('wmx-accounts').addEventListener('click', (ev) => {
      const target = ev.target;
      const shelfIndex = target && target.getAttribute && target.getAttribute('data-shelf-add');
      if (shelfIndex !== null && shelfIndex !== undefined) {
        ev.preventDefault();
        ev.stopPropagation();
        addShelfToCustom(Number(shelfIndex));
        return;
      }
      const index = target && target.getAttribute && target.getAttribute('data-del');
      if (index === null || index === undefined) return;
      ev.preventDefault();
      ev.stopPropagation();
      const account = state.accounts[Number(index)];
      if (account && account.source === 'custom') removeCustomAccount(account.bookId);
    });

    const accountKeyword = document.getElementById('wmx-acc-kw');
    if (accountKeyword) accountKeyword.addEventListener('input', renderAccounts);
    const addInput = document.getElementById('wmx-add-input');
    if (addInput) addInput.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter') { ev.preventDefault(); addFromInput(); }
    });
    document.getElementById('wmx-add-go').addEventListener('click', addFromInput);
    document.getElementById('wmx-add-shelf').addEventListener('click', pushSelectedCustom);
    document.getElementById('wmx-theme').addEventListener('click', () => {
      setTheme(state.theme === 'light' ? 'dark' : 'light');
    });

    const searchInput = document.getElementById('wmx-search-input');
    if (searchInput) searchInput.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter') { ev.preventDefault(); doSearchAccounts(false); }
    });
    const searchGo = document.getElementById('wmx-search-go');
    if (searchGo) searchGo.addEventListener('click', () => doSearchAccounts(false));
    const mpOpen = document.getElementById('wmx-mp-open');
    if (mpOpen) mpOpen.addEventListener('click', openMpBackend);
    const searchNote = document.getElementById('wmx-search-note');
    if (searchNote) {
      searchNote.addEventListener('click', () => { if (!state.mpToken) openMpBackend(); });
      searchNote.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); if (!state.mpToken) openMpBackend(); }
      });
    }
    const shelfEye = document.getElementById('wmx-shelf-eye');
    if (shelfEye) shelfEye.addEventListener('click', toggleShelfList);
    const searchResults = document.getElementById('wmx-searchres');
    if (searchResults) searchResults.addEventListener('click', (ev) => {
      const target = ev.target;
      if (target && target.id === 'wmx-searchres-close') {
        ev.preventDefault();
        searchResults.hidden = true;
        return;
      }
      const index = target && target.getAttribute && target.getAttribute('data-s');
      if (index !== null && index !== undefined) {
        ev.preventDefault();
        addSearchResult(Number(index));
      } else if (target && target.id === 'wmx-search-more') {
        ev.preventDefault();
        doSearchAccounts(true);
      }
    });
    const articleResults = document.getElementById('wmx-result');
    if (articleResults) articleResults.addEventListener('click', (ev) => {
      const target = ev.target;
      const hideName = target && target.getAttribute && target.getAttribute('data-art-hide');
      if (hideName !== null && hideName !== undefined) {
        state.articleHidden[hideName] = !state.articleHidden[hideName];
        renderResult();
        return;
      }
      const name = target && target.getAttribute && target.getAttribute('data-art-more');
      if (name !== null && name !== undefined) {
        state.articleVisible[name] = (state.articleVisible[name] || 3) + 5;
        renderResult();
      }
    });
    const selectedAccounts = document.getElementById('wmx-selected-accounts');
    if (selectedAccounts) selectedAccounts.addEventListener('click', (ev) => {
      const target = ev.target;
      const bookId = target && target.getAttribute && target.getAttribute('data-selected-del');
      if (bookId) {
        ev.preventDefault();
        removeCustomAccount(bookId);
      }
    });

    const addCurrent = document.getElementById('wmx-add-cur');
    if (IS_MP) {
      addCurrent.hidden = false;
      addCurrent.addEventListener('click', addCurrentMpAccount);
    }

    document.getElementById('wmx-logclear').addEventListener('click', () => {
      const box = document.getElementById('wmx-log');
      if (box) box.innerHTML = '';
    });

    document.getElementById('wmx-ctx-add').addEventListener('click', addCurrentPage);
    document.getElementById('wmx-ctx-copy').addEventListener('click', copyCurrentPage);
    const contextAddAccount = document.getElementById('wmx-ctx-addacc');
    if (contextAddAccount) {
      if (IS_MP) contextAddAccount.addEventListener('click', addCurrentMpAccount);
      else contextAddAccount.hidden = true;
    }

    document.getElementById('wmx-run').addEventListener('click', async () => {
      if (state.running) return;
      if (state.login === 'guest' || state.login === 'unknown') {
        const ok = await checkLogin(true);
        if (!ok) {
          log('未登录，无法拉取。请先完成扫码登录。', 'warn');
          startLoginFlow();
          return;
        }
      }
      const picked = state.custom.slice();
      if (!picked.length) { log('请先在“文章查看范围”中添加至少一个公众号。', 'warn'); switchView('acc'); return; }
      const limit = Math.max(0, Number(document.getElementById('wmx-limit').value) || 0);
      setBusy(true, '开始拉取…');
      state.articles = [];
      state.lastRaw = null;
      state.articleHidden = Object.create(null);
      state.articleVisible = Object.create(null);
      renderResult();
      try {
        for (let i = 0; i < picked.length; i++) {
          const a = picked[i];
          log('【' + (i + 1) + '/' + picked.length + '】' + (a.title || a.bookId) + ' 拉取中…');
          const before = state.articles.length;
          const rows = await fetchArticlesFor(a.bookId, a.title || a.bookId, limit, (got, page) => {
            setBusy(true, (i + 1) + '/' + picked.length + ' · ' + (a.title || a.bookId) + ' 第' + page + '页 ' + got + ' 篇');
          });
          state.articles = state.articles.concat(rows);
          if (!state.lastRaw && rows.length && rows[0].raw) state.lastRaw = rows[0].raw;
          if (rows.length && !a.title && rows[0].account) {
            setAccountTitle(a.bookId, rows[0].account);
            renderAccounts();
          }
          if (!rows.length) {
            log('  · 0 篇。常见原因：这个号没在微信读书里关注过，或该号未被微信读书收录。', 'warn');
          } else {
            log('  · 得到 ' + rows.length + ' 篇（未去重合计 ' + (state.articles.length - before) + '）', 'ok');
          }
          renderResult();
          if (i < picked.length - 1) await sleep(700);
        }
        setBusy(false, '完成，共 ' + state.articles.length + ' 篇');
        log('全部完成，共 ' + state.articles.length + ' 篇', 'ok');
        saveArticlesCache();
        updateCounts();
        if (state.articles.length) switchView('art');
      } catch (e) {
        setBusy(false, '中断');
        log(errHint(e), 'err');
      }
    });

    const kwEl = document.getElementById('wmx-kw');
    ['wmx-kw', 'wmx-from', 'wmx-to'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('input', renderResult);
    });
    if (kwEl) kwEl.addEventListener('change', renderResult);

    document.getElementById('wmx-csv').addEventListener('click', exportCsv);
    document.getElementById('wmx-md').addEventListener('click', exportMd);
    document.getElementById('wmx-copy').addEventListener('click', copyLinks);
    document.getElementById('wmx-copy2').addEventListener('click', copyTitleLinks);
    document.getElementById('wmx-diag').addEventListener('click', diagnose);

    /* ---- 初次渲染 ---- */
    renderEnv();
    renderCtx();
    renderSearchNote();
    rebuildAccounts();
    renderResult();
    setTheme(state.theme);
    switchView(state.view);
    updateCounts();

    if (state.shelf.length) {
      log('已恢复上次的关注公众号列表（' + state.shelf.length + ' 个）。点「刷新关注列表」可重新读取。');
    }
    if (state.custom.length) {
      log('已恢复本地添加的公众号（' + state.custom.length + ' 个）。');
    }
    if (state.articles.length) {
      log('已恢复上次的文章结果（' + state.articles.length + ' 篇）。如需更新请重新拉取。');
    }
    if (!IS_WEREAD) {
      log('当前页面是 ' + location.hostname + '：接口数据经扩展后台转发，用的是浏览器里的微信读书登录态。');
    }
    log('就绪。正在检测微信读书登录状态…');
  }

  /* ---------------- 启动 ---------------- */
  async function boot() {
    if (!document.body) { setTimeout(boot, 300); return; }

    await preload();       // 先把缓存读进来，渲染时就不闪空状态
    buildUI();

    // 首次安装使用时自动展开一次，之后保持收起，只留右侧标签
    if (state.firstEver) setOpen(true);

    let auto = false;
    try {
      auto = sessionStorage.getItem('wmx_auto_login') === '1';
      sessionStorage.removeItem('wmx_auto_login');
    } catch (e) { /* ignore */ }
    if (auto) setOpen(true);
    initLogin(auto);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
