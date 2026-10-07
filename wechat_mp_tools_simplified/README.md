# 微信公众号搜索与文章浏览器

一个本地运行的 Flask Web 应用，用于搜索微信公众号、维护本地关注清单、浏览公众号历史文章并打开官方原文。

本项目不是浏览器插件，也不会自动执行微信官方关注、文章下载或文章导出。

## 功能

- 通过登录后的 `mp.weixin.qq.com` 页面搜索公众号。
- 将公众号加入/移出本地关注清单。
- 查看公众号历史文章元数据。
- 在新标签页打开微信官方原文。
- 使用持久化浏览器 Profile 保留用户手动登录状态。
- SQLite 保存公众号展示信息和本地关注关系。

## 不包含

- 文章正文抓取、下载、Markdown/HTML/PDF 导出。
- 自动登录、验证码处理、绕过风控。
- 微信官方关注/取消关注自动化。
- 多用户账号、云端同步和后台定时抓取。

## 运行

```powershell
cd D:\VibeProjects\wechat_mp_tools_simplified
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
python app.py
```

打开 `http://127.0.0.1:5200`，点击“打开微信页面并登录”，在打开的浏览器窗口中完成登录后返回应用搜索。

首次搜索前必须在打开的微信页面中手动完成登录。应用只在本机 Playwright Profile 中使用登录状态，不把 Cookie 或 Token 写入数据库。

## 项目结构

```text
wechat_mp_tools_simplified/
├── app.py
├── requirements.txt
├── backend/
│   ├── __init__.py
│   ├── database.py
│   ├── models.py
│   ├── wechat_client.py
│   └── routes.py
└── frontend/
    ├── index.html
    ├── app.js
    └── style.css
```

## 数据来源限制

公众号搜索和文章列表使用微信官方页面当前登录上下文中的内部请求，接口字段可能变化、限流或要求验证。遇到登录失效、风控或未知响应时，应用会停止请求并显示错误，不会自动绕过。
