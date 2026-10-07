(() => {
  const root = document.createElement("div");
  root.id = "wechat-article-explorer-root";
  const shadow = root.attachShadow({ mode: "open" });
  const stylesheet = document.createElement("link");
  stylesheet.rel = "stylesheet";
  stylesheet.href = chrome.runtime.getURL("content.css");
  shadow.append(stylesheet);

  const interfaceRoot = document.createElement("div");
  interfaceRoot.id = "wechat-article-explorer-root";
  interfaceRoot.innerHTML = `
    <button class="trigger" type="button" aria-label="打开微信读书公众号文章">公众号文章</button>
    <aside class="panel" aria-label="微信读书公众号文章" aria-hidden="true">
      <header class="panel-header">
        <div>
          <p class="eyebrow">微信读书</p>
          <h1>公众号文章</h1>
        </div>
        <button class="icon-button close" type="button" aria-label="关闭">×</button>
      </header>
      <section class="content" aria-live="polite"></section>
    </aside>
  `;
  shadow.append(interfaceRoot);
  document.documentElement.append(root);

  const trigger = shadow.querySelector(".trigger");
  const panel = shadow.querySelector(".panel");
  const content = shadow.querySelector(".content");
  const closeButton = shadow.querySelector(".close");
  const state = {
    publications: null,
    selectedPublication: null,
    articles: [],
    nextOffset: null,
    articleRequestId: 0,
    articlesLoading: false,
    officialAccounts: [],
    followedOfficialAccounts: [],
    officialAccount: null,
    officialArticles: [],
    officialOffset: 0,
    officialHasMore: true
  };

  trigger.addEventListener("click", () => openPanel());
  closeButton.addEventListener("click", closePanel);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closePanel();
  });

  async function openPanel() {
    panel.classList.add("is-open");
    panel.setAttribute("aria-hidden", "false");
    if (location.hostname === "mp.weixin.qq.com") {
      await renderOfficialHome();
    } else if (!state.publications) await loadPublications();
  }

  function closePanel() {
    panel.classList.remove("is-open");
    panel.setAttribute("aria-hidden", "true");
  }

  async function renderOfficialHome() {
    cancelArticleRequest();
    [state.officialAccounts, state.followedOfficialAccounts] = await Promise.all([
      sendMessage({ type: "getOfficialAccounts" }).catch(() => []),
      sendMessage({ type: "getFollowedOfficialAccounts" }).catch(() => [])
    ]);
    content.replaceChildren(heading("公众号后台搜索", "官方页面"));
    const hint = document.createElement("p");
    hint.className = "history-hint";
    hint.textContent = "这里管理扩展本地关注的公众号，不等同于微信官方关注关系；搜索和读取均需手动触发。";
    content.append(hint);
    const form = document.createElement("form");
    form.className = "official-search";
    const input = document.createElement("input");
    input.type = "search";
    input.maxLength = 80;
    input.placeholder = "公众号名称或关键词";
    input.required = true;
    const button = document.createElement("button");
    button.type = "submit";
    button.textContent = "搜索";
    form.append(input, button);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      button.disabled = true;
      renderLoading("正在搜索公众号…");
      try {
        state.officialAccounts = await sendMessage({
          type: "searchOfficialAccounts", query: input.value.trim()
        });
        renderOfficialAccounts();
      } catch (error) {
        renderError(error, renderOfficialHome);
      }
    });
    content.append(form);
    renderFollowedOfficialAccounts();
    if (state.officialAccounts.length) renderOfficialAccounts(true);
  }

  function renderOfficialAccounts(append = false) {
    const list = document.createElement("div");
    list.className = "publication-list official-list";
    state.officialAccounts.forEach((account) => {
      list.append(createOfficialAccountEntry(account));
    });
    if (append) content.append(heading("已搜索公众号", `${state.officialAccounts.length} 个`), list);
    else content.append(heading("搜索结果", `${state.officialAccounts.length} 个`), list);
  }

  function renderFollowedOfficialAccounts() {
    if (!state.followedOfficialAccounts.length) return;
    const list = document.createElement("div");
    list.className = "publication-list official-list";
    state.followedOfficialAccounts.forEach((account) => {
      list.append(createOfficialAccountEntry(account));
    });
    content.append(heading("已关注公众号", `${state.followedOfficialAccounts.length} 个`), list);
  }

  function createOfficialAccountEntry(account) {
    const wrapper = document.createElement("div");
    wrapper.className = "official-account-entry";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "publication";
    button.textContent = account.nickname + (account.alias ? ` · ${account.alias}` : "");
    button.addEventListener("click", () => loadOfficialArticles(account, true));
    const followed = state.followedOfficialAccounts.some((item) => item.fakeid === account.fakeid);
    const followButton = document.createElement("button");
    followButton.type = "button";
    followButton.className = "follow";
    followButton.textContent = followed ? "已关注" : "关注";
    followButton.setAttribute("aria-pressed", String(followed));
    followButton.addEventListener("click", async () => {
      followButton.disabled = true;
      try {
        state.followedOfficialAccounts = await sendMessage({
          type: "setFollowedOfficialAccount", account, followed: !followed
        });
        renderOfficialHome();
      } catch (error) {
        renderError(error, renderOfficialHome);
      }
    });
    wrapper.append(button, followButton);
    return wrapper;
  }

  async function loadOfficialArticles(account, reset) {
    if (state.articlesLoading) return;
    state.articlesLoading = true;
    const requestId = ++state.articleRequestId;
    if (reset) {
      state.officialAccount = account;
      state.officialArticles = [];
      state.officialOffset = 0;
      state.officialHasMore = true;
      renderLoading(`正在读取「${account.nickname}」的文章…`, true);
    }
    try {
      const result = await sendMessage({
        type: "getOfficialArticles", account, offset: state.officialOffset
      });
      if (requestId !== state.articleRequestId) return;
      if (!result || !Array.isArray(result.articles) ||
          !(result.nextOffset === null ||
            (Number.isInteger(result.nextOffset) && result.nextOffset >= 0))) {
        throw Object.assign(new Error("公众号后台返回了无法识别的分页数据。"), { code: "DATA" });
      }
      if (result.nextOffset !== null && result.nextOffset <= state.officialOffset) {
        throw Object.assign(new Error("公众号后台分页没有继续前进，已停止读取。"), { code: "DATA" });
      }
      const incoming = Array.isArray(result?.articles) ? result.articles : [];
      const known = new Set(state.officialArticles.map((article) => article.id));
      const fresh = incoming.filter((article) => !known.has(article.id));
      state.officialArticles.push(...fresh);
      state.officialHasMore = Boolean(incoming.length && fresh.length && result.nextOffset !== null);
      state.officialOffset = result.nextOffset ?? state.officialOffset;
      renderOfficialArticleList();
    } catch (error) {
      if (requestId !== state.articleRequestId) return;
      renderError(error, () => loadOfficialArticles(account, false), true);
    } finally {
      if (requestId === state.articleRequestId) state.articlesLoading = false;
    }
  }

  function renderOfficialArticleList() {
    const account = state.officialAccount;
    content.replaceChildren(createBackButton(true), heading(account.nickname, "公众号后台搜索"));
    const source = document.createElement("p");
    source.className = "history-hint";
    source.textContent = "公众号后台搜索 · 仅显示文章元数据，原文将在微信官方页面打开。";
    content.append(source);
    if (!state.officialArticles.length) {
      renderEmpty("暂时没有文章", "该公众号没有返回可用的公开文章元数据。");
      return;
    }
    const list = document.createElement("div");
    list.className = "article-list";
    state.officialArticles.forEach((article) => list.append(createArticle(article)));
    content.append(list);
    if (state.officialHasMore) {
      const more = document.createElement("button");
      more.type = "button";
      more.className = "load-more";
      more.textContent = "加载更多";
      more.disabled = state.articlesLoading;
      more.addEventListener("click", () => loadOfficialArticles(account, false));
      content.append(more);
    }
  }

  async function loadPublications() {
    renderLoading("正在读取关注的公众号…");
    try {
      state.publications = await sendMessage({ type: "getPublications" });
      renderPublicationList();
    } catch (error) {
      renderError(error, loadPublications);
    }
  }

  function renderPublicationList() {
    cancelArticleRequest();
    const publications = state.publications ?? [];
    if (publications.length === 0) {
      renderEmpty("没有找到已关注的公众号", "可在微信读书中手动搜索或管理公众号，完成后返回这里重试。", true);
      return;
    }

    content.replaceChildren(
      createBackButton(false),
      heading("已关注的公众号", `${publications.length} 个`),
      createManageEntry()
    );
    const list = document.createElement("div");
    list.className = "publication-list";
    publications.forEach((publication) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "publication";
      button.textContent = publication.title;
      button.addEventListener("click", () => loadArticles(publication, true));
      list.append(button);
    });
    content.append(list);
  }

  async function loadArticles(publication, reset) {
    if (state.articlesLoading) return;
    state.articlesLoading = true;
    const requestId = ++state.articleRequestId;
    if (reset) {
      state.selectedPublication = publication;
      state.articles = [];
      state.nextOffset = null;
      renderLoading(`正在读取「${publication.title}」的文章…`, true);
    }

    try {
      const result = await sendMessage({
        type: "getArticles",
        bookId: publication.id,
        readerUrl: publication.readerUrl,
        offset: state.nextOffset ?? 0
      });
      if (requestId !== state.articleRequestId) return;
      if (!result || !Array.isArray(result.articles)) {
        throw Object.assign(new Error("微信读书返回了无法识别的数据。"), { code: "DATA" });
      }
      state.articles.push(...result.articles);
      state.nextOffset = result.nextOffset;
      renderArticleList();
    } catch (error) {
      if (requestId !== state.articleRequestId) return;
      renderError(error, () => loadArticles(publication, reset), true, publication);
    } finally {
      if (requestId === state.articleRequestId) state.articlesLoading = false;
    }
  }

  function cancelArticleRequest() {
    state.articleRequestId += 1;
    state.articlesLoading = false;
  }

  function renderArticleList() {
    const publication = state.selectedPublication;
    content.replaceChildren(createBackButton(true), heading(publication.title, "最新文章"));

    const history = document.createElement("p");
    history.className = "history-hint";
    history.textContent = "这里只显示最新文章；如需查看历史文章，请打开该公众号的微信读书页面。";
    content.append(history);
    if (publication.readerUrl) content.append(createReaderButton(publication));

    if (isCurrentArticle()) {
      const context = document.createElement("p");
      context.className = "current-context";
      context.textContent = "你正在阅读一篇公众号原文";
      content.append(context);
    }

    if (state.articles.length === 0) {
      renderEmpty("暂时没有文章", "该公众号暂未返回可阅读文章。");
      return;
    }

    const list = document.createElement("div");
    list.className = "article-list";
    state.articles.forEach((article) => list.append(createArticle(article)));
    content.append(list);

  }

  function createReaderButton(publication) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "reader-link";
    button.textContent = "打开微信读书查看全部文章";
    button.addEventListener("click", () => {
      window.open(publication.readerUrl, "_blank", "noopener,noreferrer");
    });
    return button;
  }

  function createArticle(article) {
    const element = document.createElement(article.url ? "a" : "div");
    element.className = "article";
    if (article.url) {
      element.href = article.url;
      element.target = "_blank";
      element.rel = "noopener noreferrer";
    }
    if (isHttpsImageUrl(article.cover)) {
      const cover = document.createElement("img");
      cover.className = "article-cover";
      cover.alt = "";
      cover.addEventListener("error", () => cover.remove(), { once: true });
      cover.src = article.cover;
      element.append(cover);
    }
    const details = document.createElement("div");
    details.className = "article-details";
    const title = document.createElement("h2");
    title.textContent = article.title;
    const meta = document.createElement("p");
    meta.className = "meta";
    meta.textContent = [article.publicationName || article.accountName, formatTime(article.publishedAt), meaningfulCount(article.readCount) ? `阅读 ${article.readCount}` : "", meaningfulCount(article.likeCount) ? `赞 ${article.likeCount}` : ""]
      .filter(Boolean)
      .join(" · ");
    details.append(title, meta);
    if (article.summary) {
      const summary = document.createElement("p");
      summary.className = "summary";
      summary.textContent = article.summary;
      details.append(summary);
    }
    element.append(details);
    return element;
  }

  function isHttpsImageUrl(value) {
    if (typeof value !== "string" || !value.trim()) return false;
    try {
      const url = new URL(value);
      return url.protocol === "https:" && Boolean(url.hostname);
    } catch {
      return false;
    }
  }

  function meaningfulCount(value) {
    return Number.isFinite(value) && value > 0;
  }

  function createBackButton(visible) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "back";
    button.textContent = "← 公众号列表";
    button.hidden = !visible;
    button.addEventListener("click", () => {
      if (location.hostname === "mp.weixin.qq.com") renderOfficialHome();
      else renderPublicationList();
    });
    return button;
  }

  function heading(title, subtitle) {
    const wrapper = document.createElement("div");
    wrapper.className = "section-heading";
    const titleElement = document.createElement("h2");
    titleElement.textContent = title;
    const subtitleElement = document.createElement("span");
    subtitleElement.textContent = subtitle;
    wrapper.append(titleElement, subtitleElement);
    return wrapper;
  }

  function renderLoading(message, showBack = false) {
    content.replaceChildren(createBackButton(showBack));
    const status = document.createElement("p");
    status.className = "status";
    status.textContent = message;
    content.append(status);
  }

  function renderEmpty(title, message, showManageEntry = false) {
    const empty = document.createElement("div");
    empty.className = "empty";
    const titleElement = document.createElement("h2");
    titleElement.textContent = title;
    const messageElement = document.createElement("p");
    messageElement.textContent = message;
    empty.append(titleElement, messageElement);
    if (showManageEntry) empty.append(createManageEntry());
    content.append(empty);
  }

  function createManageEntry() {
    const wrapper = document.createElement("div");
    wrapper.className = "manage-entry";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "manage";
    button.textContent = "在微信读书中搜索或管理公众号";
    button.addEventListener("click", () => {
      window.open("https://weread.qq.com/web/shelf", "_blank", "noopener,noreferrer");
    });

    const refreshButton = document.createElement("button");
    refreshButton.type = "button";
    refreshButton.className = "refresh";
    refreshButton.textContent = "刷新已关注列表";
    refreshButton.addEventListener("click", () => {
      state.publications = null;
      loadPublications();
    });

    const hint = document.createElement("p");
    hint.textContent = "将打开微信读书官方页面；搜索、关注和取消关注均由你手动完成。";
    wrapper.append(button, refreshButton, hint);
    return wrapper;
  }

  function renderError(error, retry, showBack = false, publication = null) {
    content.replaceChildren(createBackButton(showBack));
    const card = document.createElement("div");
    card.className = "error";
    const title = document.createElement("h2");
    title.textContent = showBack ? "无法获取文章" : "无法完成请求";
    const message = document.createElement("p");
    message.textContent = error.message || "发生未知错误，请稍后重试。";
    const retryButton = document.createElement("button");
    retryButton.type = "button";
    retryButton.textContent = "重试";
    retryButton.addEventListener("click", retry);
    if (publication?.readerUrl) card.append(createReaderButton(publication));
    if (error.code === "AUTH") {
      const loginButton = document.createElement("button");
      loginButton.type = "button";
      loginButton.className = "login";
      loginButton.textContent = "前往微信读书登录";
      loginButton.addEventListener("click", () => {
        window.open("https://weread.qq.com/", "_blank", "noopener,noreferrer");
      });
      card.append(loginButton);
    }
    card.append(retryButton);
    content.append(card);
  }

  function isCurrentArticle() {
    return location.hostname === "mp.weixin.qq.com" &&
      (location.pathname === "/s" || location.pathname.startsWith("/s/"));
  }

  function formatTime(timestamp) {
    if (!timestamp) return "";
    return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium" }).format(new Date(timestamp * 1000));
  }

  function sendMessage(message) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(message, (response) => {
        if (chrome.runtime.lastError) {
          reject(Object.assign(
            new Error("扩展后台不可用，请刷新页面后重试。"),
            { code: "NETWORK" }
          ));
        } else if (!response?.ok) {
          reject(Object.assign(
            new Error(response?.error?.message || "请求失败，请稍后重试。"),
            { code: response?.error?.code || "UNKNOWN" }
          ));
        } else {
          resolve(response.data);
        }
      });
    });
  }
})();
