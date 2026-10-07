const state = { results: [], followed: [], selected: null, articles: [], offset: 0, hasMore: false, loading: false };
const $ = (selector) => document.querySelector(selector);

function showMessage(text, error = false) {
  const element = $("#message");
  element.hidden = !text;
  element.textContent = text;
  element.className = `message${error ? " error" : ""}`;
}

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const payload = await response.json();
  if (!payload.ok) throw new Error(payload.error?.message || "请求失败。");
  return payload.data;
}

function accountCard(account) {
  const wrapper = document.createElement("article");
  wrapper.className = "account-card";
  const name = document.createElement("button");
  name.className = "account-name";
  name.textContent = account.nickname + (account.alias ? ` · ${account.alias}` : "");
  name.onclick = () => loadArticles(account, true);
  const description = document.createElement("p");
  description.textContent = account.signature || "暂无简介";
  const followed = state.followed.some((item) => item.fakeid === account.fakeid);
  const follow = document.createElement("button");
  follow.className = "small-button";
  follow.textContent = followed ? "已加入" : "加入清单";
  follow.title = followed ? "从本地阅读清单移除" : "加入本地阅读清单";
  follow.onclick = async () => {
    try {
      state.followed = await api("/api/accounts/follow", {
        method: "POST",
        body: JSON.stringify({ account, followed: !followed }),
      });
      renderFollowed();
      renderResults();
    } catch (error) {
      showMessage(error.message, true);
    }
  };
  wrapper.append(name, description, follow);
  return wrapper;
}

function renderResults() {
  const container = $("#results");
  container.replaceChildren(...state.results.map(accountCard));
  $("#result-count").textContent = `${state.results.length} 个`;
}

function renderFollowed() {
  const container = $("#followed");
  container.replaceChildren(...state.followed.map(accountCard));
  $("#followed-count").textContent = `${state.followed.length} 个`;
}

async function loadArticles(account, reset) {
  if (state.loading) return;
  state.loading = true;
  state.selected = account;
  if (reset) {
    state.articles = [];
    state.offset = 0;
    state.hasMore = true;
    $("#articles-title").textContent = `${account.nickname} · 历史文章`;
    $("#articles-panel").hidden = false;
    $("#articles").replaceChildren();
  }
  try {
    const result = await api("/api/accounts/articles", {
      method: "POST",
      body: JSON.stringify({ account, offset: state.offset }),
    });
    state.articles.push(...result.articles);
    state.hasMore = result.nextOffset !== null;
    state.offset = result.nextOffset ?? state.offset;
    renderArticles();
    showMessage("");
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    state.loading = false;
  }
}

function renderArticles() {
  const container = $("#articles");
  container.replaceChildren(...state.articles.map((article) => {
    const element = document.createElement("a");
    element.className = "article";
    element.href = article.url;
    element.target = "_blank";
    element.rel = "noopener noreferrer";
    const title = document.createElement("h3");
    title.textContent = article.title;
    const meta = document.createElement("p");
    meta.textContent = article.summary || "打开原文查看完整内容";
    element.append(title, meta);
    return element;
  }));
  $("#load-more").hidden = !state.hasMore || !state.articles.length;
}

$("#search-form").onsubmit = async (event) => {
  event.preventDefault();
  showMessage("正在搜索…");
  try {
    state.results = await api("/api/accounts/search", {
      method: "POST",
      body: JSON.stringify({ query: $("#search-input").value.trim() }),
    });
    renderResults();
    showMessage(`找到 ${state.results.length} 个公众号`);
  } catch (error) {
    showMessage(error.message, true);
  }
};

$("#open-session").onclick = async () => {
  try {
    await api("/api/session/open", { method: "POST" });
    $("#session-status").textContent = "微信页面已打开，请完成登录后搜索";
    showMessage("请在打开的微信页面中完成登录，然后返回这里搜索。");
  } catch (error) {
    showMessage(error.message, true);
  }
};

$("#load-more").onclick = () => loadArticles(state.selected, false);
$("#close-articles").onclick = () => { $("#articles-panel").hidden = true; };

api("/api/accounts/followed").then((items) => {
  state.followed = items;
  renderFollowed();
}).catch((error) => showMessage(error.message, true));
