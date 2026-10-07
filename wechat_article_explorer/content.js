(() => {
  const root = document.createElement("div");
  root.id = "wechat-article-explorer-root";
  const shadow = root.attachShadow({ mode: "open" });
  const pageUrl = window.location.href;

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
  const state = { publications: null, selectedPublication: null, articles: [], nextOffset: null };

  trigger.addEventListener("click", () => openPanel());
  closeButton.addEventListener("click", closePanel);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closePanel();
  });

  async function openPanel() {
    panel.classList.add("is-open");
    panel.setAttribute("aria-hidden", "false");
    if (!state.publications) await loadPublications();
  }

  function closePanel() {
    panel.classList.remove("is-open");
    panel.setAttribute("aria-hidden", "true");
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
    const publications = state.publications ?? [];
    if (publications.length === 0) {
      renderEmpty("没有找到已关注的公众号", "请先在微信读书 App 中关注公众号，然后刷新后重试。");
      return;
    }

    content.replaceChildren(createBackButton(false), heading("已关注的公众号", `${publications.length} 个`));
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
    if (reset) {
      state.selectedPublication = publication;
      state.articles = [];
      state.nextOffset = 0;
      renderLoading(`正在读取「${publication.title}」的文章…`, true);
    }

    try {
      const result = await sendMessage({
        type: "getArticles",
        bookId: publication.id,
        offset: state.nextOffset ?? 0
      });
      state.articles.push(...result.articles);
      state.nextOffset = result.nextOffset;
      renderArticleList();
    } catch (error) {
      renderError(error, () => loadArticles(publication, reset), true);
    }
  }

  function renderArticleList() {
    const publication = state.selectedPublication;
    content.replaceChildren(createBackButton(true), heading(publication.title, `${state.articles.length} 篇`));

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

    if (state.nextOffset !== null) {
      const more = document.createElement("button");
      more.type = "button";
      more.className = "load-more";
      more.textContent = "加载更多";
      more.addEventListener("click", () => loadArticles(publication, false));
      content.append(more);
    }
  }

  function createArticle(article) {
    const element = document.createElement(article.url ? "a" : "div");
    element.className = "article";
    if (article.url) {
      element.href = article.url;
      element.target = "_blank";
      element.rel = "noopener noreferrer";
    }
    const title = document.createElement("h2");
    title.textContent = article.title;
    const meta = document.createElement("p");
    meta.className = "meta";
    meta.textContent = [formatTime(article.publishedAt), article.readCount ? `阅读 ${article.readCount}` : "", article.likeCount ? `赞 ${article.likeCount}` : ""]
      .filter(Boolean)
      .join(" · ");
    element.append(title, meta);
    if (article.summary) {
      const summary = document.createElement("p");
      summary.className = "summary";
      summary.textContent = article.summary;
      element.append(summary);
    }
    return element;
  }

  function createBackButton(visible) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "back";
    button.textContent = "← 公众号列表";
    button.hidden = !visible;
    button.addEventListener("click", renderPublicationList);
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

  function renderEmpty(title, message) {
    const empty = document.createElement("div");
    empty.className = "empty";
    const titleElement = document.createElement("h2");
    titleElement.textContent = title;
    const messageElement = document.createElement("p");
    messageElement.textContent = message;
    empty.append(titleElement, messageElement);
    content.append(empty);
  }

  function renderError(error, retry, showBack = false) {
    content.replaceChildren(createBackButton(showBack));
    const card = document.createElement("div");
    card.className = "error";
    const title = document.createElement("h2");
    title.textContent = "无法获取文章";
    const message = document.createElement("p");
    message.textContent = error.message || "发生未知错误，请稍后重试。";
    const retryButton = document.createElement("button");
    retryButton.type = "button";
    retryButton.textContent = "重试";
    retryButton.addEventListener("click", retry);
    card.append(title, message, retryButton);
    content.append(card);
  }

  function isCurrentArticle() {
    return location.hostname === "mp.weixin.qq.com" && pageUrl.includes("/s");
  }

  function formatTime(timestamp) {
    if (!timestamp) return "";
    return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium" }).format(new Date(timestamp * 1000));
  }

  function sendMessage(message) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(message, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error("扩展后台不可用，请刷新页面后重试。"));
        } else if (!response?.ok) {
          reject(new Error(response?.error?.message || "请求失败，请稍后重试。"));
        } else {
          resolve(response.data);
        }
      });
    });
  }
})();
